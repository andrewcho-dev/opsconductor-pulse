# 003: Ingest Guards for Per-Device Subscription

## Task

Update the ingest service to check the device's subscription status instead of the tenant's subscription.

## File to Modify

`services/ingest_iot/ingest.py`

## Changes Required

### 1. Update SubscriptionCache

Change from tenant-level caching to device-level caching:

```python
class DeviceSubscriptionCache:
    """Cache device subscription status to avoid DB lookups on every message."""

    def __init__(self, ttl_seconds: int = 60, max_size: int = 50000):
        self.ttl = ttl_seconds
        self.max_size = max_size
        self._cache: dict[tuple[str, str], dict] = {}  # (tenant_id, device_id) -> {status, subscription_id, expires_at}
        self._lock = asyncio.Lock()

    async def get(self, tenant_id: str, device_id: str) -> dict | None:
        """Get cached subscription status for device. Returns None if not cached or expired."""
        key = (tenant_id, device_id)
        entry = self._cache.get(key)
        if entry and time.time() < entry['expires_at']:
            return entry
        return None

    async def put(
        self,
        tenant_id: str,
        device_id: str,
        subscription_id: str | None,
        status: str | None,
    ) -> None:
        """Cache device subscription status."""
        key = (tenant_id, device_id)
        async with self._lock:
            if len(self._cache) >= self.max_size:
                # Evict expired entries
                now = time.time()
                self._cache = {k: v for k, v in self._cache.items() if v['expires_at'] > now}
            self._cache[key] = {
                'subscription_id': subscription_id,
                'status': status,
                'expires_at': time.time() + self.ttl,
            }

    def invalidate(self, tenant_id: str, device_id: str) -> None:
        """Remove device from cache."""
        self._cache.pop((tenant_id, device_id), None)

    def invalidate_subscription(self, subscription_id: str) -> None:
        """Invalidate all devices on a subscription (call when subscription status changes)."""
        to_remove = [k for k, v in self._cache.items() if v.get('subscription_id') == subscription_id]
        for key in to_remove:
            self._cache.pop(key, None)
```

### 2. Update Ingestor.__init__

Replace tenant subscription cache with device subscription cache:

```python
def __init__(self):
    # ... existing code ...
    self.device_subscription_cache = DeviceSubscriptionCache(ttl_seconds=60, max_size=50000)
```

### 3. Add Device Subscription Check Method

```python
async def _get_device_subscription_status(
    self,
    tenant_id: str,
    device_id: str,
) -> tuple[str | None, str | None]:
    """
    Get device's subscription status.
    Returns: (subscription_id, status)
    Returns (None, None) if device has no subscription (legacy or unassigned).
    """
    # Check cache first
    cached = await self.device_subscription_cache.get(tenant_id, device_id)
    if cached:
        return cached['subscription_id'], cached['status']

    # Fetch from database
    async with self.pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT d.subscription_id, s.status
            FROM device_registry d
            LEFT JOIN subscriptions s ON d.subscription_id = s.subscription_id
            WHERE d.tenant_id = $1 AND d.device_id = $2
            """,
            tenant_id, device_id
        )

    if row:
        subscription_id = row['subscription_id']
        status = row['status']
    else:
        # Device not found - will be handled by existing UNREGISTERED_DEVICE check
        subscription_id = None
        status = None

    await self.device_subscription_cache.put(tenant_id, device_id, subscription_id, status)
    return subscription_id, status
```

### 4. Update db_worker Subscription Check

Replace the tenant-level subscription check with device-level check.

Find the existing tenant subscription check (around line 385-395) and replace with:

```python
# Check device subscription status (per-device, not per-tenant)
subscription_id, sub_status = await self._get_device_subscription_status(tenant_id, device_id)

# If device has no subscription, that's OK for now (legacy devices)
# But if it has a subscription that's suspended/expired, reject
if subscription_id and sub_status in ('SUSPENDED', 'EXPIRED'):
    await self._insert_quarantine(
        topic, tenant_id, site_id, device_id, msg_type,
        f"SUBSCRIPTION_{sub_status}", payload, event_ts
    )
    continue
```

### 5. Update Auto-Provision Logic

When auto-provisioning a device, we need to decide which subscription to assign it to. Options:

**Option A (Simple):** Don't auto-assign subscription, leave as NULL. Device works but has no subscription.

**Option B (Smart):** Find tenant's MAIN subscription with capacity and assign.

Implement Option B:

```python
if reg is None:
    if AUTO_PROVISION:
        # Find a subscription with capacity for this tenant
        async with self.pool.acquire() as conn:
            sub = await conn.fetchrow(
                """
                SELECT subscription_id, device_limit, active_device_count
                FROM subscriptions
                WHERE tenant_id = $1
                  AND status = 'ACTIVE'
                  AND subscription_type = 'MAIN'
                  AND active_device_count < device_limit
                ORDER BY created_at
                LIMIT 1
                """,
                tenant_id
            )

            if not sub:
                # No subscription with capacity - reject
                await self._insert_quarantine(
                    topic, tenant_id, site_id, device_id, msg_type,
                    "NO_SUBSCRIPTION_CAPACITY", payload, event_ts
                )
                continue

            subscription_id = sub['subscription_id']

            # Create device with subscription
            await conn.execute(
                """
                INSERT INTO device_registry (tenant_id, device_id, site_id, subscription_id, status)
                VALUES ($1, $2, $3, $4, 'ACTIVE')
                """,
                tenant_id, device_id, site_id, subscription_id
            )

            # Increment subscription count
            await conn.execute(
                """
                UPDATE subscriptions
                SET active_device_count = active_device_count + 1, updated_at = now()
                WHERE subscription_id = $1
                """,
                subscription_id
            )

            # Invalidate cache
            self.device_subscription_cache.invalidate(tenant_id, device_id)

    await self._insert_quarantine(
        topic, tenant_id, site_id, device_id, msg_type,
        "UNREGISTERED_DEVICE", payload, event_ts
    )
    continue
```

### 6. New Quarantine Reasons

Add these new rejection reasons:
- `SUBSCRIPTION_SUSPENDED` - Device's subscription is suspended
- `SUBSCRIPTION_EXPIRED` - Device's subscription is expired
- `NO_SUBSCRIPTION_CAPACITY` - Auto-provision blocked, no subscription has capacity

## Testing

```bash
# Test device on expired subscription
# 1. Create subscription, assign device
# 2. Set subscription status = EXPIRED
# 3. Send telemetry for device → should be quarantined

# Test auto-provision to subscription
# 1. Ensure tenant has MAIN subscription with capacity
# 2. Send telemetry for new device
# 3. Device should be created and assigned to subscription

# Test no capacity
# 1. Set all subscriptions to device_limit = active_device_count
# 2. Send telemetry for new device → should be quarantined with NO_SUBSCRIPTION_CAPACITY
```
