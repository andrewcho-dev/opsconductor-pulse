# Task 001: Device Auth Cache for High-Frequency Ingestion

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

**THE PROBLEM**: Every MQTT message triggers a PostgreSQL query to validate the device's provision token. At high message rates (100+ msg/sec), this per-message DB round-trip becomes the primary bottleneck. The query is in the `db_worker` method:

```python
SELECT site_id, status, provision_token_hash
FROM device_registry
WHERE tenant_id=$1 AND device_id=$2
```

Most devices send messages repeatedly. The same (tenant_id, device_id) is looked up thousands of times per hour, and the result rarely changes.

**Read first**:
- `services/ingest_iot/ingest.py` (entire file — focus on `db_worker` method and the device registry query)

---

## Task

### 1.1 Add DeviceAuthCache class

**File**: `services/ingest_iot/ingest.py`

Add a new class `DeviceAuthCache` near the top of the file (after the imports and constants, before the `Ingestor` class). This class provides TTL-based caching of device_registry lookups.

**Requirements**:
- `__init__(self, ttl_seconds=60, max_size=10000)`: Store ttl and max_size. Initialize `self._cache = {}` and `self._hits = 0`, `self._misses = 0`.
- `get(self, tenant_id, device_id)`: Look up `(tenant_id, device_id)` in `self._cache`. If found AND `time.time() - entry["cached_at"] < self._ttl`: increment `self._hits`, return the entry dict. Otherwise: increment `self._misses`, delete the stale entry if present, return `None`.
- `put(self, tenant_id, device_id, token_hash, site_id, status)`: If cache size >= max_size, evict the oldest 10% of entries by `cached_at`. Store `{"token_hash": token_hash, "site_id": site_id, "status": status, "cached_at": time.time()}` keyed by `(tenant_id, device_id)`.
- `invalidate(self, tenant_id, device_id)`: Remove entry if present.
- `stats(self)`: Return dict with `{"size": len(self._cache), "hits": self._hits, "misses": self._misses}`.

### 1.2 Add environment variables

**File**: `services/ingest_iot/ingest.py`

Add near the other environment variable declarations (around line 29, after `INFLUXDB_TOKEN`):

```python
AUTH_CACHE_TTL = int(os.getenv("AUTH_CACHE_TTL_SECONDS", "60"))
AUTH_CACHE_MAX_SIZE = int(os.getenv("AUTH_CACHE_MAX_SIZE", "10000"))
```

### 1.3 Initialize cache in Ingestor

**File**: `services/ingest_iot/ingest.py`

In the `Ingestor.__init__` method (around line 162), add:

```python
self.auth_cache = DeviceAuthCache(ttl_seconds=AUTH_CACHE_TTL, max_size=AUTH_CACHE_MAX_SIZE)
```

### 1.4 Modify db_worker to use cache

**File**: `services/ingest_iot/ingest.py`

In the `db_worker` method, find lines 376-388 where it computes `token_hash` and then queries `device_registry`. Replace the unconditional DB query with a cache-first pattern:

**Before** (current flow at lines 376-388):
1. Compute token_hash (line 377)
2. Acquire PG connection (line 380)
3. Query device_registry (lines 381-388)
4. If no row found -> quarantine UNREGISTERED_DEVICE
5. Validate status, site_id, token

**After** (new flow):
1. Compute token_hash (keep as-is, line 377)
2. Check `self.auth_cache.get(tenant_id, device_id)`
3. If cache HIT -> use cached values (`token_hash` as `cached["token_hash"]`, `site_id` as `cached["site_id"]`, `status` as `cached["status"]`). Construct a dict `reg` with keys `site_id`, `status`, `provision_token_hash` from the cached values so the rest of the validation logic works unchanged.
4. If cache MISS -> acquire PG connection, query PostgreSQL as before -> on success (row found), call `self.auth_cache.put(tenant_id, device_id, reg["provision_token_hash"], reg["site_id"], reg["status"])` to populate cache
5. If no row found in DB -> quarantine UNREGISTERED_DEVICE (do NOT cache misses)
6. Continue with existing validation logic (token check at lines 410-420, status check at line 402, site_id check at line 406) using the values from cache or DB

**Critical**: The `async with self.pool.acquire() as conn:` block (lines 379-420) currently wraps both the SELECT and all validation. After the change, the PG connection acquisition should only happen on cache miss. Move the validation checks (status, site_id, token) OUTSIDE the `async with` block so they work with both cached and DB-fetched values.

**Important**: Do NOT cache failed lookups (unregistered devices). Only cache successful device_registry rows. Also keep the AUTO_PROVISION logic (lines 391-398) inside the DB-miss path only.

### 1.5 Add cache stats to periodic logging

**File**: `services/ingest_iot/ingest.py`

Find the `stats_worker` method (line 252). In the print statement (lines 256-259), add cache stats:

```python
cache_stats = self.auth_cache.stats()
```

And append to the print:
```
f"auth_cache_hits={cache_stats['hits']} auth_cache_misses={cache_stats['misses']} auth_cache_size={cache_stats['size']}"
```

### 1.6 Add cache environment variables to docker-compose

**File**: `compose/docker-compose.yml`

In the `ingest` service environment section (around line 79, after the INFLUXDB_TOKEN line), add:

```yaml
AUTH_CACHE_TTL_SECONDS: "${AUTH_CACHE_TTL_SECONDS:-60}"
AUTH_CACHE_MAX_SIZE: "${AUTH_CACHE_MAX_SIZE:-10000}"
```

---

## Files to Modify

| Action | Path | What changes |
|--------|------|--------------|
| MODIFY | `services/ingest_iot/ingest.py` | Add DeviceAuthCache class, env vars, cache integration in db_worker, stats logging |
| MODIFY | `compose/docker-compose.yml` | Add AUTH_CACHE_* env vars to ingest service |

---

## Test

### Step 1: Run existing unit tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

All existing tests must continue to pass. The cache is an internal optimization and should not change external behavior.

### Step 2: Verify cache class

After making the changes, read `services/ingest_iot/ingest.py` and confirm:
- [ ] `DeviceAuthCache` class exists with `get`, `put`, `invalidate`, `stats` methods
- [ ] Cache uses TTL-based expiration (checks `time.time() - cached_at < ttl`)
- [ ] Cache has max_size eviction (evicts oldest 10% when full)
- [ ] `db_worker` checks cache before querying PostgreSQL
- [ ] Cache is populated on DB hit, not on DB miss
- [ ] Stats are logged periodically

---

## Acceptance Criteria

- [ ] `DeviceAuthCache` class with TTL expiration and max_size eviction
- [ ] `db_worker` checks cache before PostgreSQL query
- [ ] Cache populated on successful DB lookup only
- [ ] Cache stats logged periodically (hits, misses, size)
- [ ] `AUTH_CACHE_TTL_SECONDS` and `AUTH_CACHE_MAX_SIZE` env vars configurable
- [ ] docker-compose.yml updated with new env vars
- [ ] All existing unit tests pass

---

## Commit

```
Add device auth cache to eliminate per-message DB lookups

At high message rates, the per-message PostgreSQL query for device
authentication becomes the primary bottleneck. Add TTL-based in-memory
cache for device_registry lookups with configurable TTL and max size.

Phase 14 Task 1: Device Auth Cache
```
