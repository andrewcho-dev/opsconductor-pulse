# 007: Operator Subscription Management API

## Task

Add operator endpoints for managing tenant subscriptions.

## File to Modify

`services/ui_iot/routes/operator.py`

## Endpoints to Add

### 1. GET /operator/tenants/{tenant_id}/subscription

Get subscription details for a specific tenant.

```python
@router.get("/tenants/{tenant_id}/subscription")
async def get_tenant_subscription(tenant_id: str, request: Request):
    """Get subscription details for a tenant (operator only)."""
    user = get_user()
    ip, user_agent = get_request_metadata(request)

    pool = await get_pool()
    async with operator_connection(pool) as conn:
        row = await conn.fetchrow(
            """
            SELECT
                ts.tenant_id,
                ts.device_limit,
                ts.active_device_count,
                ts.term_start,
                ts.term_end,
                ts.plan_id,
                ts.status,
                ts.grace_end,
                ts.created_at,
                ts.updated_at,
                t.name as tenant_name,
                t.contact_email
            FROM tenant_subscription ts
            JOIN tenants t ON t.tenant_id = ts.tenant_id
            WHERE ts.tenant_id = $1
            """,
            tenant_id
        )

        if not row:
            raise HTTPException(404, "Subscription not found")

        # Log operator access
        await log_operator_access(conn, user, 'view_subscription', tenant_id, ip)

        return {
            "tenant_id": row['tenant_id'],
            "tenant_name": row['tenant_name'],
            "contact_email": row['contact_email'],
            "device_limit": row['device_limit'],
            "active_device_count": row['active_device_count'],
            "term_start": row['term_start'].isoformat() if row['term_start'] else None,
            "term_end": row['term_end'].isoformat() if row['term_end'] else None,
            "plan_id": row['plan_id'],
            "status": row['status'],
            "grace_end": row['grace_end'].isoformat() if row['grace_end'] else None,
            "created_at": row['created_at'].isoformat(),
            "updated_at": row['updated_at'].isoformat(),
        }
```

### 2. POST /operator/tenants/{tenant_id}/subscription

Create or update subscription for a tenant.

```python
class SubscriptionUpsert(BaseModel):
    device_limit: int = Field(..., ge=0)
    term_start: Optional[datetime] = None
    term_end: Optional[datetime] = None
    plan_id: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(TRIAL|ACTIVE|GRACE|SUSPENDED|EXPIRED)$")


@router.post("/tenants/{tenant_id}/subscription")
async def upsert_tenant_subscription(
    tenant_id: str,
    data: SubscriptionUpsert,
    request: Request
):
    """Create or update subscription for a tenant (operator only)."""
    user = get_user()
    ip, user_agent = get_request_metadata(request)

    pool = await get_pool()
    async with operator_connection(pool) as conn:
        # Check tenant exists
        tenant = await conn.fetchval(
            "SELECT 1 FROM tenants WHERE tenant_id = $1",
            tenant_id
        )
        if not tenant:
            raise HTTPException(404, "Tenant not found")

        # Get current subscription for audit
        current = await conn.fetchrow(
            "SELECT * FROM tenant_subscription WHERE tenant_id = $1",
            tenant_id
        )

        previous_state = dict(current) if current else None

        # Upsert subscription
        row = await conn.fetchrow(
            """
            INSERT INTO tenant_subscription (
                tenant_id, device_limit, term_start, term_end, plan_id, status
            ) VALUES ($1, $2, $3, $4, $5, COALESCE($6, 'ACTIVE'))
            ON CONFLICT (tenant_id) DO UPDATE SET
                device_limit = COALESCE($2, tenant_subscription.device_limit),
                term_start = COALESCE($3, tenant_subscription.term_start),
                term_end = COALESCE($4, tenant_subscription.term_end),
                plan_id = COALESCE($5, tenant_subscription.plan_id),
                status = COALESCE($6, tenant_subscription.status),
                updated_at = now()
            RETURNING *
            """,
            tenant_id,
            data.device_limit,
            data.term_start,
            data.term_end,
            data.plan_id,
            data.status
        )

        new_state = dict(row)

        # Determine event type
        event_type = 'CREATED' if not current else 'UPDATED'
        if current and data.device_limit and data.device_limit != current['device_limit']:
            event_type = 'LIMIT_CHANGED'
        if current and data.status and data.status != current['status']:
            if data.status == 'ACTIVE' and current['status'] in ('SUSPENDED', 'EXPIRED'):
                event_type = 'REACTIVATED'

        # Audit log
        await conn.execute(
            """
            INSERT INTO subscription_audit
                (tenant_id, event_type, actor_type, actor_id, previous_state, new_state, ip_address)
            VALUES ($1, $2, 'admin', $3, $4, $5, $6)
            """,
            tenant_id,
            event_type,
            user.get('sub') if user else None,
            json.dumps(previous_state, default=str) if previous_state else None,
            json.dumps(new_state, default=str),
            ip
        )

        await log_operator_access(conn, user, 'modify_subscription', tenant_id, ip)

        return {
            "tenant_id": row['tenant_id'],
            "device_limit": row['device_limit'],
            "status": row['status'],
            "updated": True,
        }
```

### 3. GET /operator/subscriptions/expiring

List subscriptions expiring soon.

```python
@router.get("/subscriptions/expiring")
async def list_expiring_subscriptions(
    request: Request,
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(50, ge=1, le=200),
):
    """List subscriptions expiring within N days (operator only)."""
    user = get_user()

    pool = await get_pool()
    async with operator_connection(pool) as conn:
        rows = await conn.fetch(
            """
            SELECT
                ts.tenant_id,
                t.name as tenant_name,
                t.contact_email,
                ts.device_limit,
                ts.active_device_count,
                ts.term_end,
                ts.status,
                EXTRACT(DAY FROM ts.term_end - now()) as days_remaining
            FROM tenant_subscription ts
            JOIN tenants t ON t.tenant_id = ts.tenant_id
            WHERE ts.status = 'ACTIVE'
              AND ts.term_end <= now() + ($1 || ' days')::interval
              AND ts.term_end > now()
            ORDER BY ts.term_end ASC
            LIMIT $2
            """,
            str(days),
            limit
        )

        return {
            "subscriptions": [
                {
                    "tenant_id": row['tenant_id'],
                    "tenant_name": row['tenant_name'],
                    "contact_email": row['contact_email'],
                    "device_limit": row['device_limit'],
                    "active_device_count": row['active_device_count'],
                    "term_end": row['term_end'].isoformat(),
                    "days_remaining": int(row['days_remaining']),
                }
                for row in rows
            ],
            "count": len(rows),
        }
```

### 4. GET /operator/subscriptions/summary

Get summary statistics for all subscriptions.

```python
@router.get("/subscriptions/summary")
async def get_subscriptions_summary(request: Request):
    """Get subscription summary statistics (operator only)."""
    pool = await get_pool()
    async with operator_connection(pool) as conn:
        # Status breakdown
        status_counts = await conn.fetch(
            """
            SELECT status, COUNT(*) as count
            FROM tenant_subscription
            GROUP BY status
            """
        )

        # Total devices vs limits
        totals = await conn.fetchrow(
            """
            SELECT
                SUM(device_limit) as total_limit,
                SUM(active_device_count) as total_devices
            FROM tenant_subscription
            WHERE status IN ('TRIAL', 'ACTIVE', 'GRACE')
            """
        )

        # Expiring soon (next 30 days)
        expiring_count = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM tenant_subscription
            WHERE status = 'ACTIVE'
              AND term_end <= now() + interval '30 days'
              AND term_end > now()
            """
        )

        return {
            "by_status": {row['status']: row['count'] for row in status_counts},
            "total_device_limit": totals['total_limit'] or 0,
            "total_active_devices": totals['total_devices'] or 0,
            "expiring_30_days": expiring_count,
        }
```

## Required Imports

Add at top of file:

```python
import json
from datetime import datetime
```

## Testing

```bash
# Get tenant subscription
curl -X GET /operator/tenants/acme-corp/subscription \
  -H "Authorization: Bearer $OPERATOR_TOKEN"

# Create/update subscription
curl -X POST /operator/tenants/acme-corp/subscription \
  -H "Authorization: Bearer $OPERATOR_TOKEN" \
  -d '{"device_limit": 100, "status": "ACTIVE"}'

# List expiring subscriptions
curl -X GET "/operator/subscriptions/expiring?days=30" \
  -H "Authorization: Bearer $OPERATOR_TOKEN"

# Get summary
curl -X GET /operator/subscriptions/summary \
  -H "Authorization: Bearer $OPERATOR_TOKEN"
```
