# 004: Ingest Service Subscription Guards

## Task

Add subscription status and device limit checks to the ingest service for:
1. Rejecting telemetry from suspended/expired tenants
2. Checking device limit before auto-provisioning new devices

## File to Modify

`services/ingest_iot/ingest.py`

## Changes Required

### 1. Add Subscription Cache Class

Add a new cache class similar to `DeviceAuthCache` for subscription status:

```python
class SubscriptionCache:
    """Cache subscription status to avoid DB lookups on every message."""

    def __init__(self, ttl_seconds: int = 60, max_size: int = 1000):
        self.ttl = ttl_seconds
        self.max_size = max_size
        self._cache: dict[str, dict] = {}  # tenant_id -> {status, device_limit, active_count, expires_at}
        self._lock = asyncio.Lock()

    async def get(self, tenant_id: str) -> dict | None:
        """Get cached subscription. Returns None if not cached or expired."""
        entry = self._cache.get(tenant_id)
        if entry and time.time() < entry['expires_at']:
            return entry
        return None

    async def put(self, tenant_id: str, status: str, device_limit: int, active_count: int) -> None:
        """Cache subscription status."""
        async with self._lock:
            if len(self._cache) >= self.max_size:
                # Evict oldest entries
                now = time.time()
                self._cache = {k: v for k, v in self._cache.items() if v['expires_at'] > now}
            self._cache[tenant_id] = {
                'status': status,
                'device_limit': device_limit,
                'active_count': active_count,
                'expires_at': time.time() + self.ttl,
            }

    def invalidate(self, tenant_id: str) -> None:
        """Remove tenant from cache (call after device count changes)."""
        self._cache.pop(tenant_id, None)
```

### 2. Add Cache Instance to Ingestor

In the `Ingestor.__init__` method, add:

```python
self.subscription_cache = SubscriptionCache(ttl_seconds=60, max_size=1000)
```

### 3. Add Subscription Fetch Method

Add a method to fetch subscription from database:

```python
async def _get_subscription_status(self, tenant_id: str) -> tuple[str, int, int]:
    """
    Get subscription status for tenant.
    Returns: (status, device_limit, active_device_count)
    Returns ('ACTIVE', 999999, 0) if no subscription exists (legacy tenants).
    """
    # Check cache first
    cached = await self.subscription_cache.get(tenant_id)
    if cached:
        return cached['status'], cached['device_limit'], cached['active_count']

    # Fetch from database
    async with self.pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT status, device_limit, active_device_count
            FROM tenant_subscription
            WHERE tenant_id = $1
            """,
            tenant_id
        )

    if row:
        status = row['status']
        limit = row['device_limit']
        count = row['active_device_count']
    else:
        # No subscription record = legacy tenant, allow everything
        status = 'ACTIVE'
        limit = 999999
        count = 0

    await self.subscription_cache.put(tenant_id, status, limit, count)
    return status, limit, count
```

### 4. Add Subscription Check in db_worker

In the `db_worker` method, BEFORE any other validation (right after extracting tenant_id), add:

```python
# Check subscription status (early rejection for suspended tenants)
sub_status, device_limit, device_count = await self._get_subscription_status(tenant_id)
if sub_status in ('SUSPENDED', 'EXPIRED'):
    await self._insert_quarantine(
        topic, tenant_id, site_id, device_id, msg_type,
        f"TENANT_{sub_status}", payload, event_ts
    )
    continue
```

### 5. Modify Auto-Provision Logic

Find the auto-provision section (around line 418-426). Modify it to check device limit:

```python
if reg is None:
    if AUTO_PROVISION:
        # Check device limit before auto-provisioning
        if device_count >= device_limit:
            await self._insert_quarantine(
                topic, tenant_id, site_id, device_id, msg_type,
                "DEVICE_LIMIT_REACHED", payload, event_ts
            )
            continue

        await conn.execute(
            """
            INSERT INTO device_registry (tenant_id, device_id, site_id, status)
            VALUES ($1,$2,$3,'ACTIVE')
            """,
            tenant_id, device_id, site_id
        )

        # Increment subscription device count
        await conn.execute(
            """
            UPDATE tenant_subscription
            SET active_device_count = active_device_count + 1,
                updated_at = now()
            WHERE tenant_id = $1
            """,
            tenant_id
        )

        # Invalidate cache since count changed
        self.subscription_cache.invalidate(tenant_id)

    await self._insert_quarantine(topic, tenant_id, site_id, device_id, msg_type, "UNREGISTERED_DEVICE", payload, event_ts)
    continue
```

## New Quarantine Reasons

Add these new rejection reasons:
- `TENANT_SUSPENDED` - Tenant subscription is suspended
- `TENANT_EXPIRED` - Tenant subscription is expired
- `DEVICE_LIMIT_REACHED` - Auto-provision blocked due to device limit

## Performance Considerations

1. Cache TTL of 60 seconds means subscription changes take up to 1 minute to take effect
2. Cache is invalidated when device count changes due to auto-provision
3. Cache has max size of 1000 tenants to prevent memory issues

## Testing

```bash
# Test suspended tenant rejection
UPDATE tenant_subscription SET status = 'SUSPENDED' WHERE tenant_id = 'test-tenant';
# Send MQTT message → should be quarantined with reason TENANT_SUSPENDED

# Test device limit on auto-provision
UPDATE tenant_subscription SET device_limit = 5, active_device_count = 5 WHERE tenant_id = 'test-tenant';
# Send MQTT message for new device → should be quarantined with reason DEVICE_LIMIT_REACHED
```
