# 002: Multi-Subscription Service Layer

## Task

Update the subscription service to support multiple subscriptions per tenant with device-level assignment.

## File to Modify

`services/ui_iot/services/subscription.py`

## New/Updated Functions

### 1. create_subscription

```python
async def create_subscription(
    conn: asyncpg.Connection,
    tenant_id: str,
    subscription_type: str,  # MAIN, ADDON, TRIAL, TEMPORARY
    device_limit: int,
    term_start: datetime,
    term_end: datetime,
    parent_subscription_id: str | None = None,
    plan_id: str | None = None,
    description: str | None = None,
    created_by: str | None = None,
) -> dict:
    """
    Create a new subscription.

    For ADDON type:
    - parent_subscription_id is required
    - term_end is automatically synced to parent's term_end

    Returns the created subscription dict.
    """
    # Generate subscription ID
    subscription_id = await conn.fetchval("SELECT generate_subscription_id()")

    # Validate ADDON has parent
    if subscription_type == 'ADDON' and not parent_subscription_id:
        raise ValueError("ADDON subscription requires parent_subscription_id")

    # Validate parent exists and is MAIN
    if parent_subscription_id:
        parent = await conn.fetchrow(
            "SELECT subscription_type, term_end FROM subscriptions WHERE subscription_id = $1",
            parent_subscription_id
        )
        if not parent:
            raise ValueError(f"Parent subscription {parent_subscription_id} not found")
        if parent['subscription_type'] != 'MAIN':
            raise ValueError("Parent subscription must be MAIN type")
        # ADDON inherits term_end from parent
        if subscription_type == 'ADDON':
            term_end = parent['term_end']

    row = await conn.fetchrow(
        """
        INSERT INTO subscriptions (
            subscription_id, tenant_id, subscription_type, parent_subscription_id,
            device_limit, term_start, term_end, status, plan_id, description, created_by
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        RETURNING *
        """,
        subscription_id, tenant_id, subscription_type, parent_subscription_id,
        device_limit, term_start, term_end, 'ACTIVE', plan_id, description, created_by
    )

    return dict(row)
```

### 2. get_subscription

```python
async def get_subscription(conn: asyncpg.Connection, subscription_id: str) -> dict | None:
    """Fetch a single subscription by ID."""
    row = await conn.fetchrow(
        "SELECT * FROM subscriptions WHERE subscription_id = $1",
        subscription_id
    )
    return dict(row) if row else None
```

### 3. get_tenant_subscriptions

```python
async def get_tenant_subscriptions(
    conn: asyncpg.Connection,
    tenant_id: str,
    include_expired: bool = False,
) -> list[dict]:
    """
    Get all subscriptions for a tenant.
    By default excludes EXPIRED subscriptions.
    """
    if include_expired:
        rows = await conn.fetch(
            """
            SELECT * FROM subscriptions
            WHERE tenant_id = $1
            ORDER BY subscription_type, term_end DESC
            """,
            tenant_id
        )
    else:
        rows = await conn.fetch(
            """
            SELECT * FROM subscriptions
            WHERE tenant_id = $1 AND status != 'EXPIRED'
            ORDER BY subscription_type, term_end DESC
            """,
            tenant_id
        )
    return [dict(r) for r in rows]
```

### 4. get_device_subscription

```python
async def get_device_subscription(
    conn: asyncpg.Connection,
    tenant_id: str,
    device_id: str,
) -> dict | None:
    """Get the subscription for a specific device."""
    row = await conn.fetchrow(
        """
        SELECT s.*
        FROM device_registry d
        JOIN subscriptions s ON d.subscription_id = s.subscription_id
        WHERE d.tenant_id = $1 AND d.device_id = $2
        """,
        tenant_id, device_id
    )
    return dict(row) if row else None
```

### 5. assign_device_to_subscription

```python
async def assign_device_to_subscription(
    conn: asyncpg.Connection,
    tenant_id: str,
    device_id: str,
    subscription_id: str,
    actor_id: str | None = None,
) -> dict:
    """
    Assign a device to a subscription.

    - Validates subscription belongs to same tenant
    - Validates subscription has capacity
    - Updates device count on old and new subscriptions
    - Logs audit trail
    """
    # Get device's current subscription
    device = await conn.fetchrow(
        "SELECT subscription_id FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
        tenant_id, device_id
    )
    if not device:
        raise ValueError(f"Device {device_id} not found")

    old_subscription_id = device['subscription_id']

    # Validate new subscription
    new_sub = await conn.fetchrow(
        "SELECT * FROM subscriptions WHERE subscription_id = $1 AND tenant_id = $2",
        subscription_id, tenant_id
    )
    if not new_sub:
        raise ValueError(f"Subscription {subscription_id} not found for tenant")

    if new_sub['status'] in ('SUSPENDED', 'EXPIRED'):
        raise ValueError(f"Cannot assign to {new_sub['status']} subscription")

    if new_sub['active_device_count'] >= new_sub['device_limit']:
        raise ValueError(f"Subscription {subscription_id} is at device limit")

    # Update device
    await conn.execute(
        "UPDATE device_registry SET subscription_id = $1 WHERE tenant_id = $2 AND device_id = $3",
        subscription_id, tenant_id, device_id
    )

    # Decrement old subscription count (if had one)
    if old_subscription_id:
        await conn.execute(
            """
            UPDATE subscriptions
            SET active_device_count = GREATEST(0, active_device_count - 1), updated_at = now()
            WHERE subscription_id = $1
            """,
            old_subscription_id
        )

    # Increment new subscription count
    await conn.execute(
        """
        UPDATE subscriptions
        SET active_device_count = active_device_count + 1, updated_at = now()
        WHERE subscription_id = $1
        """,
        subscription_id
    )

    # Audit log
    await log_subscription_event(
        conn, tenant_id, 'DEVICE_REASSIGNED',
        actor_type='admin', actor_id=actor_id,
        details={
            'device_id': device_id,
            'from_subscription': old_subscription_id,
            'to_subscription': subscription_id,
        }
    )

    return {'device_id': device_id, 'subscription_id': subscription_id}
```

### 6. check_subscription_limit (updated)

```python
async def check_subscription_limit(
    conn: asyncpg.Connection,
    subscription_id: str,
) -> tuple[bool, int, int]:
    """
    Check if a subscription can accept more devices.
    Returns: (can_add, current_count, limit)
    """
    row = await conn.fetchrow(
        "SELECT active_device_count, device_limit, status FROM subscriptions WHERE subscription_id = $1",
        subscription_id
    )
    if not row:
        return (False, 0, 0)

    if row['status'] in ('SUSPENDED', 'EXPIRED'):
        return (False, row['active_device_count'], row['device_limit'])

    can_add = row['active_device_count'] < row['device_limit']
    return (can_add, row['active_device_count'], row['device_limit'])
```

### 7. check_device_access (new - for ingest)

```python
async def check_device_access(
    conn: asyncpg.Connection,
    tenant_id: str,
    device_id: str,
) -> tuple[bool, str]:
    """
    Check if a device's subscription allows access.
    Used by ingest to determine if telemetry should be accepted.

    Returns: (allowed, reason)
    """
    row = await conn.fetchrow(
        """
        SELECT s.status, s.subscription_id
        FROM device_registry d
        LEFT JOIN subscriptions s ON d.subscription_id = s.subscription_id
        WHERE d.tenant_id = $1 AND d.device_id = $2
        """,
        tenant_id, device_id
    )

    if not row:
        return (False, 'DEVICE_NOT_FOUND')

    if row['subscription_id'] is None:
        return (False, 'NO_SUBSCRIPTION')

    if row['status'] in ('SUSPENDED', 'EXPIRED'):
        return (False, f"SUBSCRIPTION_{row['status']}")

    return (True, '')
```

### 8. get_subscription_devices

```python
async def get_subscription_devices(
    conn: asyncpg.Connection,
    subscription_id: str,
) -> list[dict]:
    """Get all devices assigned to a subscription."""
    rows = await conn.fetch(
        """
        SELECT d.device_id, d.site_id, d.status, ds.last_seen_at
        FROM device_registry d
        LEFT JOIN device_state ds ON d.tenant_id = ds.tenant_id AND d.device_id = ds.device_id
        WHERE d.subscription_id = $1
        ORDER BY d.device_id
        """,
        subscription_id
    )
    return [dict(r) for r in rows]
```

## Update Existing Functions

### update check_device_limit for device creation

When creating a device, you now need to specify which subscription it goes on:

```python
async def create_device_on_subscription(
    conn: asyncpg.Connection,
    tenant_id: str,
    device_id: str,
    site_id: str,
    subscription_id: str,
    actor_id: str | None = None,
) -> dict:
    """Create a device and assign it to a subscription."""
    # Check subscription capacity
    can_add, current, limit = await check_subscription_limit(conn, subscription_id)
    if not can_add:
        raise ValueError(f"Subscription at limit ({current}/{limit})")

    # Verify subscription belongs to tenant
    sub = await conn.fetchrow(
        "SELECT tenant_id, status FROM subscriptions WHERE subscription_id = $1",
        subscription_id
    )
    if not sub or sub['tenant_id'] != tenant_id:
        raise ValueError("Invalid subscription for tenant")

    if sub['status'] in ('SUSPENDED', 'EXPIRED'):
        raise ValueError(f"Cannot add to {sub['status']} subscription")

    # Create device
    await conn.execute(
        """
        INSERT INTO device_registry (tenant_id, device_id, site_id, subscription_id, status)
        VALUES ($1, $2, $3, $4, 'ACTIVE')
        """,
        tenant_id, device_id, site_id, subscription_id
    )

    # Increment count
    await conn.execute(
        """
        UPDATE subscriptions
        SET active_device_count = active_device_count + 1, updated_at = now()
        WHERE subscription_id = $1
        """,
        subscription_id
    )

    # Audit
    await log_subscription_event(
        conn, tenant_id, 'DEVICE_ADDED',
        actor_type='user', actor_id=actor_id,
        details={'device_id': device_id, 'subscription_id': subscription_id}
    )

    return {'device_id': device_id, 'subscription_id': subscription_id}
```
