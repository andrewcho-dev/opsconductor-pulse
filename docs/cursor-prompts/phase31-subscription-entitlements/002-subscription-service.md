# 002: Subscription Service Layer

## Task

Create a new service module for subscription business logic.

## File to Create

`services/ui_iot/services/subscription.py`

## Required Functions

### 1. get_subscription

```python
async def get_subscription(conn: asyncpg.Connection, tenant_id: str) -> dict | None:
    """
    Fetch current subscription for a tenant.
    Returns dict with: tenant_id, device_limit, active_device_count, term_start,
                       term_end, plan_id, status, grace_end, created_at, updated_at
    Returns None if no subscription exists.
    """
```

### 2. check_device_limit

```python
async def check_device_limit(conn: asyncpg.Connection, tenant_id: str) -> tuple[bool, int, int]:
    """
    Check if tenant can add a new device.
    Returns: (can_add, current_count, limit)

    Logic:
    - Fetch subscription for tenant
    - If no subscription, return (False, 0, 0)
    - If active_device_count >= device_limit, return (False, count, limit)
    - Otherwise return (True, count, limit)
    """
```

### 3. increment_device_count

```python
async def increment_device_count(conn: asyncpg.Connection, tenant_id: str) -> int:
    """
    Increment active_device_count by 1 after device creation.
    Returns the new count.
    Also updates updated_at timestamp.
    """
```

### 4. decrement_device_count

```python
async def decrement_device_count(conn: asyncpg.Connection, tenant_id: str) -> int:
    """
    Decrement active_device_count by 1 after device deletion.
    Returns the new count (minimum 0).
    Also updates updated_at timestamp.
    """
```

### 5. check_access_allowed

```python
async def check_access_allowed(conn: asyncpg.Connection, tenant_id: str) -> tuple[bool, str]:
    """
    Check if tenant has active access (not suspended/expired).
    Returns: (allowed, reason)

    Logic:
    - If status in ('SUSPENDED', 'EXPIRED'), return (False, 'Subscription {status}')
    - Otherwise return (True, '')
    """
```

### 6. log_subscription_event

```python
async def log_subscription_event(
    conn: asyncpg.Connection,
    tenant_id: str,
    event_type: str,
    actor_type: str | None = None,
    actor_id: str | None = None,
    previous_state: dict | None = None,
    new_state: dict | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
) -> None:
    """
    Insert a record into subscription_audit table.

    Event types:
    - CREATED, RENEWED, UPGRADED, DOWNGRADED
    - DEVICE_ADDED, DEVICE_REMOVED
    - LIMIT_CHANGED, PAYMENT_RECEIVED
    - GRACE_STARTED, SUSPENDED, EXPIRED, REACTIVATED
    """
```

### 7. reconcile_device_count

```python
async def reconcile_device_count(conn: asyncpg.Connection, tenant_id: str) -> int:
    """
    Recalculate active_device_count from device_registry.
    Used for nightly reconciliation.

    Logic:
    - COUNT(*) FROM device_registry WHERE tenant_id = $1 AND status = 'ACTIVE'
    - UPDATE tenant_subscription SET active_device_count = count
    - Return the new count
    """
```

## Implementation Notes

- Use parameterized queries with asyncpg
- All functions should accept a connection object (not create their own)
- Use `RETURNING` clause for UPDATE operations when possible
- Handle edge cases: no subscription record, count going negative

## Reference Files

- `services/ui_iot/db/queries.py` - query patterns
- `services/ui_iot/db/audit.py` - audit logging patterns

## Example Usage

```python
from services.subscription import check_device_limit, increment_device_count

async with tenant_connection(pool, tenant_id) as conn:
    can_add, current, limit = await check_device_limit(conn, tenant_id)
    if not can_add:
        raise HTTPException(403, f"Device limit reached ({current}/{limit})")

    # Create device...

    await increment_device_count(conn, tenant_id)
```
