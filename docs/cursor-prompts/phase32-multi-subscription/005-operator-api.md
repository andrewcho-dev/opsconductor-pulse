# 005: Operator API for Multi-Subscription Management

## Task

Add operator endpoints to create and manage multiple subscriptions, and assign devices to subscriptions.

## File to Modify

`services/ui_iot/routes/operator.py`

## New Endpoints

### 1. POST /operator/subscriptions (CREATE)

Create a new subscription for a tenant.

```python
class SubscriptionCreate(BaseModel):
    tenant_id: str
    subscription_type: str = Field(..., pattern="^(MAIN|ADDON|TRIAL|TEMPORARY)$")
    device_limit: int = Field(..., ge=1)
    term_start: Optional[datetime] = None  # Defaults to now
    term_end: Optional[datetime] = None  # Required for MAIN/TEMPORARY
    term_days: Optional[int] = None  # Alternative to term_end
    parent_subscription_id: Optional[str] = None  # Required for ADDON
    plan_id: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None  # Audit notes


@router.post("/subscriptions", status_code=201)
async def create_subscription(data: SubscriptionCreate, request: Request):
    """Create a new subscription for a tenant."""
    user = get_user()
    ip, _ = get_request_metadata(request)

    pool = await get_pool()
    async with operator_connection(pool) as conn:
        # Validate tenant exists
        tenant = await conn.fetchval(
            "SELECT 1 FROM tenants WHERE tenant_id = $1",
            data.tenant_id
        )
        if not tenant:
            raise HTTPException(404, "Tenant not found")

        # Calculate term dates
        term_start = data.term_start or datetime.now(timezone.utc)
        if data.term_days:
            term_end = term_start + timedelta(days=data.term_days)
        elif data.term_end:
            term_end = data.term_end
        elif data.subscription_type == 'TRIAL':
            term_end = term_start + timedelta(days=14)
        else:
            raise HTTPException(400, "term_end or term_days required for non-TRIAL subscriptions")

        # Validate ADDON requirements
        if data.subscription_type == 'ADDON':
            if not data.parent_subscription_id:
                raise HTTPException(400, "ADDON requires parent_subscription_id")
            parent = await conn.fetchrow(
                "SELECT subscription_type, term_end FROM subscriptions WHERE subscription_id = $1",
                data.parent_subscription_id
            )
            if not parent:
                raise HTTPException(404, "Parent subscription not found")
            if parent['subscription_type'] != 'MAIN':
                raise HTTPException(400, "Parent must be MAIN subscription")
            # ADDON inherits term_end from parent
            term_end = parent['term_end']

        # Generate subscription ID
        subscription_id = await conn.fetchval("SELECT generate_subscription_id()")

        # Create subscription
        row = await conn.fetchrow(
            """
            INSERT INTO subscriptions (
                subscription_id, tenant_id, subscription_type, parent_subscription_id,
                device_limit, term_start, term_end, status, plan_id, description, created_by
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, 'ACTIVE', $8, $9, $10)
            RETURNING *
            """,
            subscription_id, data.tenant_id, data.subscription_type, data.parent_subscription_id,
            data.device_limit, term_start, term_end, data.plan_id, data.description,
            user.get('sub') if user else None
        )

        # Audit log
        await conn.execute(
            """
            INSERT INTO subscription_audit
                (tenant_id, event_type, actor_type, actor_id, new_state, details, ip_address)
            VALUES ($1, 'SUBSCRIPTION_CREATED', 'admin', $2, $3, $4, $5)
            """,
            data.tenant_id,
            user.get('sub') if user else None,
            json.dumps(dict(row), default=str),
            json.dumps({'notes': data.notes}) if data.notes else None,
            ip
        )

        return {
            "subscription_id": row['subscription_id'],
            "tenant_id": row['tenant_id'],
            "subscription_type": row['subscription_type'],
            "device_limit": row['device_limit'],
            "term_start": row['term_start'].isoformat(),
            "term_end": row['term_end'].isoformat(),
            "status": row['status'],
        }
```

### 2. GET /operator/subscriptions (LIST)

List subscriptions with filtering.

```python
@router.get("/subscriptions")
async def list_subscriptions(
    request: Request,
    tenant_id: Optional[str] = None,
    subscription_type: Optional[str] = None,
    status: Optional[str] = None,
    expiring_days: Optional[int] = None,  # Show expiring within N days
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List subscriptions with optional filters."""
    pool = await get_pool()
    async with operator_connection(pool) as conn:
        conditions = []
        params = []
        param_idx = 1

        if tenant_id:
            conditions.append(f"s.tenant_id = ${param_idx}")
            params.append(tenant_id)
            param_idx += 1

        if subscription_type:
            conditions.append(f"s.subscription_type = ${param_idx}")
            params.append(subscription_type)
            param_idx += 1

        if status:
            conditions.append(f"s.status = ${param_idx}")
            params.append(status)
            param_idx += 1

        if expiring_days:
            conditions.append(f"s.term_end <= now() + (${param_idx} || ' days')::interval")
            conditions.append("s.status = 'ACTIVE'")
            params.append(str(expiring_days))
            param_idx += 1

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        query = f"""
            SELECT
                s.subscription_id, s.tenant_id, t.name as tenant_name,
                s.subscription_type, s.parent_subscription_id,
                s.device_limit, s.active_device_count, s.term_start, s.term_end,
                s.status, s.plan_id, s.description
            FROM subscriptions s
            JOIN tenants t ON t.tenant_id = s.tenant_id
            {where_clause}
            ORDER BY s.term_end ASC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """
        params.extend([limit, offset])

        rows = await conn.fetch(query, *params)

        return {
            "subscriptions": [
                {
                    "subscription_id": r['subscription_id'],
                    "tenant_id": r['tenant_id'],
                    "tenant_name": r['tenant_name'],
                    "subscription_type": r['subscription_type'],
                    "parent_subscription_id": r['parent_subscription_id'],
                    "device_limit": r['device_limit'],
                    "active_device_count": r['active_device_count'],
                    "term_start": r['term_start'].isoformat(),
                    "term_end": r['term_end'].isoformat(),
                    "status": r['status'],
                    "description": r['description'],
                }
                for r in rows
            ],
            "count": len(rows),
        }
```

### 3. GET /operator/subscriptions/{subscription_id} (DETAIL)

Get subscription details with devices.

```python
@router.get("/subscriptions/{subscription_id}")
async def get_subscription(subscription_id: str, request: Request):
    """Get subscription details including devices."""
    pool = await get_pool()
    async with operator_connection(pool) as conn:
        row = await conn.fetchrow(
            """
            SELECT s.*, t.name as tenant_name
            FROM subscriptions s
            JOIN tenants t ON t.tenant_id = s.tenant_id
            WHERE s.subscription_id = $1
            """,
            subscription_id
        )

        if not row:
            raise HTTPException(404, "Subscription not found")

        # Get devices
        devices = await conn.fetch(
            """
            SELECT d.device_id, d.site_id, d.status, ds.last_seen_at
            FROM device_registry d
            LEFT JOIN device_state ds ON d.tenant_id = ds.tenant_id AND d.device_id = ds.device_id
            WHERE d.subscription_id = $1
            ORDER BY d.device_id
            """,
            subscription_id
        )

        # Get child subscriptions (for MAIN)
        children = []
        if row['subscription_type'] == 'MAIN':
            child_rows = await conn.fetch(
                "SELECT subscription_id, device_limit, active_device_count, status FROM subscriptions WHERE parent_subscription_id = $1",
                subscription_id
            )
            children = [dict(r) for r in child_rows]

        return {
            **dict(row),
            "term_start": row['term_start'].isoformat() if row['term_start'] else None,
            "term_end": row['term_end'].isoformat() if row['term_end'] else None,
            "devices": [
                {
                    "device_id": d['device_id'],
                    "site_id": d['site_id'],
                    "status": d['status'],
                    "last_seen_at": d['last_seen_at'].isoformat() if d['last_seen_at'] else None,
                }
                for d in devices
            ],
            "child_subscriptions": children,
        }
```

### 4. PATCH /operator/subscriptions/{subscription_id} (UPDATE)

Update subscription details.

```python
class SubscriptionUpdate(BaseModel):
    device_limit: Optional[int] = Field(None, ge=0)
    term_end: Optional[datetime] = None
    status: Optional[str] = Field(None, pattern="^(TRIAL|ACTIVE|GRACE|SUSPENDED|EXPIRED)$")
    description: Optional[str] = None
    notes: Optional[str] = None  # Audit notes
    transaction_ref: Optional[str] = None


@router.patch("/subscriptions/{subscription_id}")
async def update_subscription(
    subscription_id: str,
    data: SubscriptionUpdate,
    request: Request,
):
    """Update subscription details."""
    user = get_user()
    ip, _ = get_request_metadata(request)

    pool = await get_pool()
    async with operator_connection(pool) as conn:
        # Get current state
        current = await conn.fetchrow(
            "SELECT * FROM subscriptions WHERE subscription_id = $1",
            subscription_id
        )
        if not current:
            raise HTTPException(404, "Subscription not found")

        previous_state = dict(current)

        # Build update
        updates = []
        params = []
        param_idx = 1

        if data.device_limit is not None:
            updates.append(f"device_limit = ${param_idx}")
            params.append(data.device_limit)
            param_idx += 1

        if data.term_end is not None:
            updates.append(f"term_end = ${param_idx}")
            params.append(data.term_end)
            param_idx += 1

        if data.status is not None:
            updates.append(f"status = ${param_idx}")
            params.append(data.status)
            param_idx += 1

        if data.description is not None:
            updates.append(f"description = ${param_idx}")
            params.append(data.description)
            param_idx += 1

        if not updates:
            raise HTTPException(400, "No updates provided")

        updates.append("updated_at = now()")

        query = f"""
            UPDATE subscriptions
            SET {', '.join(updates)}
            WHERE subscription_id = ${param_idx}
            RETURNING *
        """
        params.append(subscription_id)

        row = await conn.fetchrow(query, *params)
        new_state = dict(row)

        # Determine event type
        if data.status and data.status != current['status']:
            event_type = f"STATUS_{data.status}"
        elif data.device_limit and data.device_limit != current['device_limit']:
            event_type = "LIMIT_CHANGED"
        elif data.term_end and data.term_end != current['term_end']:
            event_type = "TERM_EXTENDED"
        else:
            event_type = "UPDATED"

        # Audit log
        await conn.execute(
            """
            INSERT INTO subscription_audit
                (tenant_id, event_type, actor_type, actor_id, previous_state, new_state, details, ip_address)
            VALUES ($1, $2, 'admin', $3, $4, $5, $6, $7)
            """,
            current['tenant_id'],
            event_type,
            user.get('sub') if user else None,
            json.dumps(previous_state, default=str),
            json.dumps(new_state, default=str),
            json.dumps({'notes': data.notes, 'transaction_ref': data.transaction_ref}),
            ip
        )

        return {"subscription_id": subscription_id, "updated": True, "event_type": event_type}
```

### 5. POST /operator/devices/{device_id}/subscription (ASSIGN)

Assign a device to a subscription.

```python
class DeviceSubscriptionAssign(BaseModel):
    subscription_id: str
    notes: Optional[str] = None


@router.post("/devices/{device_id}/subscription")
async def assign_device_subscription(
    device_id: str,
    data: DeviceSubscriptionAssign,
    request: Request,
):
    """Assign a device to a subscription."""
    user = get_user()
    ip, _ = get_request_metadata(request)

    pool = await get_pool()
    async with operator_connection(pool) as conn:
        # Get device
        device = await conn.fetchrow(
            "SELECT tenant_id, subscription_id FROM device_registry WHERE device_id = $1",
            device_id
        )
        if not device:
            raise HTTPException(404, "Device not found")

        old_subscription_id = device['subscription_id']
        tenant_id = device['tenant_id']

        # Validate new subscription
        new_sub = await conn.fetchrow(
            "SELECT * FROM subscriptions WHERE subscription_id = $1",
            data.subscription_id
        )
        if not new_sub:
            raise HTTPException(404, "Subscription not found")

        if new_sub['tenant_id'] != tenant_id:
            raise HTTPException(400, "Subscription belongs to different tenant")

        if new_sub['status'] in ('SUSPENDED', 'EXPIRED'):
            raise HTTPException(400, f"Cannot assign to {new_sub['status']} subscription")

        if new_sub['active_device_count'] >= new_sub['device_limit']:
            raise HTTPException(400, "Subscription at device limit")

        # Update device
        await conn.execute(
            "UPDATE device_registry SET subscription_id = $1 WHERE device_id = $2",
            data.subscription_id, device_id
        )

        # Update counts
        if old_subscription_id:
            await conn.execute(
                "UPDATE subscriptions SET active_device_count = GREATEST(0, active_device_count - 1) WHERE subscription_id = $1",
                old_subscription_id
            )
        await conn.execute(
            "UPDATE subscriptions SET active_device_count = active_device_count + 1 WHERE subscription_id = $1",
            data.subscription_id
        )

        # Audit
        await conn.execute(
            """
            INSERT INTO subscription_audit
                (tenant_id, event_type, actor_type, actor_id, details, ip_address)
            VALUES ($1, 'DEVICE_REASSIGNED', 'admin', $2, $3, $4)
            """,
            tenant_id,
            user.get('sub') if user else None,
            json.dumps({
                'device_id': device_id,
                'from_subscription': old_subscription_id,
                'to_subscription': data.subscription_id,
                'notes': data.notes,
            }),
            ip
        )

        return {
            "device_id": device_id,
            "subscription_id": data.subscription_id,
            "previous_subscription_id": old_subscription_id,
        }
```

## Required Imports

```python
from datetime import datetime, timezone, timedelta
```
