# 002: Data Integrity Fixes

## Priority: CRITICAL

## Issues to Fix

### 1. Race Condition in Auto-Provisioning

**File:** `services/ingest_iot/ingest.py`
**Lines:** 500-548

**Problem:** Multiple concurrent messages from same device can create duplicate registrations and over-increment active_device_count.

**Fix:** Use advisory lock and transaction:
```python
async def auto_provision_device(conn, tenant_id: str, device_id: str, subscription_id: str) -> bool:
    """Auto-provision device with proper locking to prevent duplicates."""
    # Use advisory lock keyed on device_id hash
    lock_key = hash(f"{tenant_id}:{device_id}") & 0x7FFFFFFF

    try:
        # Acquire advisory lock (will wait if another process has it)
        await conn.execute("SELECT pg_advisory_xact_lock($1)", lock_key)

        # Check if device already exists (inside transaction)
        existing = await conn.fetchval(
            "SELECT 1 FROM device_registry WHERE device_id = $1",
            device_id
        )
        if existing:
            return True  # Already provisioned by another process

        # Check subscription capacity
        sub = await conn.fetchrow(
            """
            SELECT device_limit, active_device_count
            FROM subscriptions
            WHERE subscription_id = $1
            FOR UPDATE  -- Lock the row
            """,
            subscription_id
        )

        if not sub or sub['active_device_count'] >= sub['device_limit']:
            return False  # No capacity

        # Insert device
        await conn.execute(
            """
            INSERT INTO device_registry (device_id, tenant_id, subscription_id, status)
            VALUES ($1, $2, $3, 'ACTIVE')
            """,
            device_id, tenant_id, subscription_id
        )

        # Increment count
        await conn.execute(
            """
            UPDATE subscriptions
            SET active_device_count = active_device_count + 1
            WHERE subscription_id = $1
            """,
            subscription_id
        )

        return True

    except Exception as e:
        logger.error(f"Auto-provision failed for {device_id}: {e}")
        raise
```

**Caller should use transaction:**
```python
async with pool.acquire() as conn:
    async with conn.transaction():
        success = await auto_provision_device(conn, tenant_id, device_id, subscription_id)
```

---

### 2. Token Bucket Memory Leak

**File:** `services/ingest_iot/ingest.py`
**Lines:** 420-437

**Problem:** Unbounded dictionary grows with every unique device. No cleanup.

**Fix:** Add TTL-based cleanup:
```python
from dataclasses import dataclass
from time import time

@dataclass
class TokenBucket:
    tokens: float
    last_update: float
    last_access: float  # NEW: track last access

# Configuration
BUCKET_TTL_SECONDS = 3600  # Remove buckets not accessed in 1 hour
BUCKET_CLEANUP_INTERVAL = 300  # Run cleanup every 5 minutes

_token_buckets: dict[str, TokenBucket] = {}
_last_cleanup: float = 0

def cleanup_stale_buckets():
    """Remove token buckets not accessed recently."""
    global _last_cleanup
    now = time()

    if now - _last_cleanup < BUCKET_CLEANUP_INTERVAL:
        return

    _last_cleanup = now
    cutoff = now - BUCKET_TTL_SECONDS

    stale_keys = [
        key for key, bucket in _token_buckets.items()
        if bucket.last_access < cutoff
    ]

    for key in stale_keys:
        del _token_buckets[key]

    if stale_keys:
        logger.info(f"Cleaned up {len(stale_keys)} stale token buckets")

def check_rate_limit(device_id: str, rate: float, burst: int) -> bool:
    """Check rate limit with automatic cleanup."""
    cleanup_stale_buckets()  # Periodic cleanup

    now = time()
    key = device_id

    if key not in _token_buckets:
        _token_buckets[key] = TokenBucket(
            tokens=burst,
            last_update=now,
            last_access=now
        )
        return True

    bucket = _token_buckets[key]
    bucket.last_access = now  # Update access time

    # Refill tokens
    elapsed = now - bucket.last_update
    bucket.tokens = min(burst, bucket.tokens + elapsed * rate)
    bucket.last_update = now

    if bucket.tokens >= 1:
        bucket.tokens -= 1
        return True

    return False
```

---

### 3. Auto-Provision Always Quarantines (Missing Return)

**File:** `services/ingest_iot/ingest.py`
**Lines:** 549-559

**Problem:** After successful auto-provisioning, code continues to quarantine with "UNREGISTERED_DEVICE".

**Fix:** Add return after successful auto-provision:
```python
# After auto-provision succeeds
if auto_provision_success:
    logger.info(f"Auto-provisioned device {device_id} for tenant {tenant_id}")
    # Process the message normally now that device exists
    await process_valid_message(msg)
    return  # <-- ADD THIS RETURN

# Only quarantine if auto-provision failed or wasn't attempted
await quarantine_message(msg, "UNREGISTERED_DEVICE")
```

---

### 4. fleet_alert Queries Wrong Column

**File:** `services/ui_iot/routes/customer.py`
**Lines:** 1127-1136

**Problem:** Queries `fleet_alert.alert_id` but table uses `fleet_alert.id`.

**Fix:** Change column name:
```python
# WRONG:
await conn.fetchrow(
    "SELECT * FROM fleet_alert WHERE alert_id = $1 AND tenant_id = $2",
    alert_id, tenant_id
)

# RIGHT:
await conn.fetchrow(
    "SELECT * FROM fleet_alert WHERE id = $1 AND tenant_id = $2",
    alert_id, tenant_id
)
```

**Also check and fix:**
- Any DELETE queries referencing alert_id
- Any UPDATE queries referencing alert_id
- Frontend API calls expecting alert_id in response

---

### 5. integration_routes.severities Column Doesn't Exist

**File:** `services/ui_iot/db/queries.py`
**Lines:** 310, 333, 350, 358, 360, 366, 377, 390-392, 406

**Problem:** Schema has `min_severity INT` but code queries `severities TEXT[]`.

**Option A - Add column to schema (preferred):**

Create migration `db/migrations/033_fix_integration_routes_severities.sql`:
```sql
-- Add severities array column to match code expectations
ALTER TABLE integration_routes
ADD COLUMN IF NOT EXISTS severities TEXT[] DEFAULT '{}';

-- Migrate data from min_severity to severities
UPDATE integration_routes
SET severities = CASE
    WHEN min_severity = 1 THEN ARRAY['critical', 'high', 'medium', 'low', 'info']
    WHEN min_severity = 2 THEN ARRAY['critical', 'high', 'medium', 'low']
    WHEN min_severity = 3 THEN ARRAY['critical', 'high', 'medium']
    WHEN min_severity = 4 THEN ARRAY['critical', 'high']
    WHEN min_severity = 5 THEN ARRAY['critical']
    ELSE ARRAY['critical', 'high', 'medium', 'low', 'info']
END
WHERE severities = '{}' OR severities IS NULL;

-- Optionally drop old column after verification
-- ALTER TABLE integration_routes DROP COLUMN min_severity;
```

**Option B - Change code to use min_severity:**
Update all queries in queries.py to use `min_severity` instead of `severities`.

---

### 6. Race Condition in Subscription Renewal

**File:** `services/ui_iot/routes/customer.py`
**Lines:** 711-817

**Problem:** Concurrent renewal requests can cause double-deactivation.

**Fix:** Use transaction with row locking:
```python
@router.post("/subscription/renew")
async def renew_subscription(data: RenewalRequest, request: Request):
    tenant_id = get_tenant_id()
    pool = await get_pool()

    async with tenant_connection(pool, tenant_id) as conn:
        # Use transaction for atomicity
        async with conn.transaction():
            # Lock subscription row
            sub = await conn.fetchrow(
                """
                SELECT * FROM subscriptions
                WHERE subscription_id = $1 AND tenant_id = $2
                FOR UPDATE
                """,
                data.subscription_id, tenant_id
            )

            if not sub:
                raise HTTPException(404, "Subscription not found")

            # Check for concurrent renewal (idempotency)
            if sub['status'] == 'ACTIVE' and sub['term_end'] > datetime.now(timezone.utc) + timedelta(days=30):
                # Already renewed recently, return success
                return {"subscription_id": data.subscription_id, "renewed": True, "note": "Already active"}

            # Proceed with renewal logic...
            # All changes happen within transaction
```

---

### 7. Inconsistent Delete Result Checking

**File:** `services/ui_iot/routes/customer.py`
**Lines:** 1246, 1379

**Problem:** Some check `result.endswith("0")`, others check `result == "DELETE 0"`.

**Fix:** Standardize to consistent pattern:
```python
def check_delete_result(result: str) -> bool:
    """Check if DELETE affected any rows."""
    # asyncpg returns "DELETE N" where N is row count
    if not result:
        return False
    parts = result.split()
    if len(parts) != 2 or parts[0] != "DELETE":
        return False
    try:
        return int(parts[1]) > 0
    except ValueError:
        return False

# Usage:
result = await conn.execute("DELETE FROM table WHERE id = $1", id)
if not check_delete_result(result):
    raise HTTPException(404, "Not found")
```

---

### 8. Cache Invalidation While Iterating

**File:** `services/ingest_iot/ingest.py`
**Lines:** 222-228

**Problem:** `invalidate_subscription` iterates dict while potentially modifying it.

**Fix:** Iterate over copy of keys:
```python
def invalidate_subscription(subscription_id: str):
    """Invalidate cached subscription data."""
    # Create list of keys to delete (don't modify while iterating)
    keys_to_delete = [
        key for key in list(_subscription_cache.keys())
        if key.startswith(f"sub:{subscription_id}")
    ]

    for key in keys_to_delete:
        _subscription_cache.pop(key, None)
```

---

### 9. JSON Parse Error Continues Processing

**File:** `services/ingest_iot/ingest.py`
**Lines:** 677-682

**Problem:** JSON parse error creates malformed payload but continues.

**Fix:** Reject immediately on parse error:
```python
def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON in MQTT message: {e}")
        # Reject immediately, don't process further
        COUNTERS["invalid_json"] += 1
        return
    except UnicodeDecodeError as e:
        logger.warning(f"Invalid encoding in MQTT message: {e}")
        COUNTERS["invalid_encoding"] += 1
        return

    # Only continue if payload is valid
    loop.call_soon_threadsafe(
        lambda: asyncio.create_task(process_message(payload))
    )
```

---

## Verification

```bash
# Test auto-provision race condition
# Send 100 concurrent messages for same new device
for i in {1..100}; do
  curl -X POST https://localhost/ingest/tenant/test/device/new-device-$RANDOM/telemetry \
    -H "Content-Type: application/json" \
    -d '{"temperature": 25}' &
done
wait

# Check only one device created
psql -c "SELECT COUNT(*) FROM device_registry WHERE device_id LIKE 'new-device-%'"
# Should be exactly number of unique device IDs

# Test subscription renewal idempotency
# Send same renewal request twice
curl -X POST https://localhost/customer/subscription/renew -d '...'
curl -X POST https://localhost/customer/subscription/renew -d '...'
# Both should succeed, second should note "Already active"
```

## Files Changed

- `services/ingest_iot/ingest.py`
- `services/ui_iot/routes/customer.py`
- `services/ui_iot/db/queries.py`
- `db/migrations/033_fix_integration_routes_severities.sql` (NEW)
