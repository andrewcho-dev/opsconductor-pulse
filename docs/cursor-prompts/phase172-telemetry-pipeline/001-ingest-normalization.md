# Task 1: Ingest Pipeline — metric_key_map Normalization

## Modify file: `services/ingest_iot/ingest.py`

### Overview

Add a metric key normalization step in the telemetry processing pipeline. This happens **after** message validation and **before** batch write.

### Step 1: Build a metric_key_map cache

The ingest service already has caching patterns (DeviceAuthCache, subscription cache). Add a similar cache for metric_key_maps.

Create a `MetricKeyMapCache` class (or add to existing cache infrastructure):

```python
class MetricKeyMapCache:
    """Cache of merged metric_key_map per device.

    Merges all active device_modules' metric_key_maps into a single
    {raw_key: semantic_key} dict per device.
    """

    def __init__(self, ttl_seconds: int = 300, max_size: int = 10000):
        self._cache: dict[str, tuple[float, dict[str, str]]] = {}
        self._ttl = ttl_seconds
        self._max_size = max_size

    async def get(self, pool, tenant_id: str, device_id: str) -> dict[str, str]:
        """Get merged metric_key_map for a device. Returns empty dict if no mappings."""
        cache_key = f"{tenant_id}:{device_id}"
        now = time.time()

        # Check cache
        if cache_key in self._cache:
            ts, mapping = self._cache[cache_key]
            if now - ts < self._ttl:
                return mapping

        # Cache miss — query DB
        mapping = await self._load_from_db(pool, tenant_id, device_id)

        # Evict if cache too large
        if len(self._cache) >= self._max_size:
            # Remove oldest entries
            oldest = sorted(self._cache.items(), key=lambda x: x[1][0])[:self._max_size // 4]
            for k, _ in oldest:
                del self._cache[k]

        self._cache[cache_key] = (now, mapping)
        return mapping

    async def _load_from_db(self, pool, tenant_id: str, device_id: str) -> dict[str, str]:
        """Load and merge all active device_modules' metric_key_maps."""
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT metric_key_map FROM device_modules
                WHERE tenant_id = $1 AND device_id = $2 AND status = 'active'
                AND metric_key_map != '{}'::jsonb
                """,
                tenant_id, device_id,
            )

        merged: dict[str, str] = {}
        for row in rows:
            mkm = row["metric_key_map"]
            if isinstance(mkm, str):
                import json
                mkm = json.loads(mkm)
            merged.update(mkm)
        return merged

    def invalidate(self, tenant_id: str, device_id: str):
        """Invalidate cache entry when modules change."""
        cache_key = f"{tenant_id}:{device_id}"
        self._cache.pop(cache_key, None)
```

### Step 2: Initialize the cache

In the ingest service startup (where other caches are initialized), create the cache instance:

```python
metric_key_map_cache = MetricKeyMapCache(
    ttl_seconds=int(os.environ.get("METRIC_MAP_CACHE_TTL", "300")),
    max_size=int(os.environ.get("METRIC_MAP_CACHE_SIZE", "10000")),
)
```

### Step 3: Apply normalization in the telemetry processing pipeline

Find the telemetry message processing function (the one that handles messages from the `TELEMETRY` JetStream stream). After validation and before the batch writer receives the record, add normalization:

```python
async def normalize_telemetry_keys(payload: dict, tenant_id: str, device_id: str) -> dict:
    """Translate raw firmware keys to semantic metric names using metric_key_map."""
    mapping = await metric_key_map_cache.get(pool, tenant_id, device_id)

    if not mapping:
        return payload  # No mappings — pass through unchanged

    normalized = {}
    for key, value in payload.items():
        semantic_key = mapping.get(key, key)  # Use mapped name or original
        normalized[semantic_key] = value

    return normalized
```

Insert this call in the telemetry processing flow:

```python
# Existing flow (simplified):
# 1. Parse message
# 2. Validate device auth
# 3. Rate limit check
# 4. Extract payload from message

# ADD HERE:
# 5. Normalize metric keys
payload = await normalize_telemetry_keys(payload, tenant_id, device_id)

# 6. Auto-discover sensors (existing)
# 7. Batch write (existing)
```

### Step 4: Update sensor auto-discovery

The existing sensor auto-discovery creates `sensors` table entries. Update it to also check/create `device_sensors` entries:

After normalization, for each key in the payload that doesn't already have a `device_sensors` entry, auto-create one with `source='unmodeled'`:

```python
# After normalization, check for new metric keys
for metric_key in payload.keys():
    # Check if device_sensor exists (use a cache or batch lookup)
    # If not, create with source='unmodeled'
```

This can be deferred to the existing auto-discovery logic if it's already adapted to use `device_sensors` in Phase 169.

### Step 5: Add Prometheus metrics

```python
from prometheus_client import Counter, Histogram

metric_keys_normalized = Counter(
    "ingest_metric_keys_normalized_total",
    "Number of telemetry keys that were normalized via metric_key_map",
    ["tenant_id"],
)

metric_key_map_cache_hits = Counter(
    "ingest_metric_key_map_cache_hits_total",
    "Cache hits for metric_key_map lookups",
)

metric_key_map_cache_misses = Counter(
    "ingest_metric_key_map_cache_misses_total",
    "Cache misses for metric_key_map lookups",
)
```

## Modify file: `services/ui_iot/routes/ingest.py`

Apply the same normalization in the HTTP ingest endpoint. The HTTP ingest publishes to NATS JetStream, so normalization should happen **before** publishing:

1. Import or instantiate the same `MetricKeyMapCache`
2. Before building the NATS message payload, run normalization:
   ```python
   payload = await normalize_telemetry_keys(payload, tenant_id, device_id)
   ```

Note: The HTTP ingest service shares the same database pool, so the cache can query the same way. If the HTTP ingest runs in the `ui_iot` process, it can share the cache instance. If separate, instantiate its own.

## Verification

1. Set up a device with a module that has `metric_key_map: {"port_3_temp": "temperature"}`
2. Send telemetry with `{"port_3_temp": 23.5}`
3. Verify stored telemetry has `{"temperature": 23.5}`
4. Send telemetry with unmapped key `{"battery": 85}`
5. Verify it passes through unchanged
6. Check Prometheus metrics show normalization counts
