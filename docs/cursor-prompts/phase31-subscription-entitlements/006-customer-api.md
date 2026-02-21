# 006: Customer Subscription API Endpoints

## Task

Add customer-facing subscription endpoints to view their subscription status and audit history.

## File to Modify

`services/ui_iot/routes/customer.py`

## Endpoints to Add

### 1. GET /customer/subscription

Returns the current subscription status for the tenant.

```python
@router.get("/subscription")
async def get_subscription_status():
    """Get current subscription status for tenant."""
    tenant_id = get_tenant_id()

    p = await get_pool()
    async with tenant_connection(p, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            SELECT
                ts.device_limit,
                ts.active_device_count,
                ts.term_start,
                ts.term_end,
                ts.plan_id,
                ts.status,
                ts.grace_end,
                ts.created_at,
                ts.updated_at,
                t.name as tenant_name
            FROM tenant_subscription ts
            JOIN tenants t ON t.tenant_id = ts.tenant_id
            WHERE ts.tenant_id = $1
            """,
            tenant_id
        )

        if not row:
            raise HTTPException(404, "No subscription found")

        # Calculate days until expiry
        days_until_expiry = None
        if row['term_end']:
            delta = row['term_end'] - datetime.now(timezone.utc)
            days_until_expiry = max(0, delta.days)

        return {
            "tenant_id": tenant_id,
            "tenant_name": row['tenant_name'],
            "device_limit": row['device_limit'],
            "active_device_count": row['active_device_count'],
            "devices_available": row['device_limit'] - row['active_device_count'],
            "term_start": row['term_start'].isoformat() if row['term_start'] else None,
            "term_end": row['term_end'].isoformat() if row['term_end'] else None,
            "days_until_expiry": days_until_expiry,
            "plan_id": row['plan_id'],
            "status": row['status'],
            "grace_end": row['grace_end'].isoformat() if row['grace_end'] else None,
        }
```

### 2. GET /customer/subscription/audit

Returns subscription audit history for the tenant.

```python
@router.get("/subscription/audit")
async def get_subscription_audit(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Get subscription audit history for tenant."""
    tenant_id = get_tenant_id()

    p = await get_pool()
    async with tenant_connection(p, tenant_id) as conn:
        rows = await conn.fetch(
            """
            SELECT
                id,
                event_type,
                event_timestamp,
                actor_type,
                actor_id,
                previous_state,
                new_state,
                details
            FROM subscription_audit
            WHERE tenant_id = $1
            ORDER BY event_timestamp DESC
            LIMIT $2 OFFSET $3
            """,
            tenant_id,
            limit,
            offset
        )

        count = await conn.fetchval(
            "SELECT COUNT(*) FROM subscription_audit WHERE tenant_id = $1",
            tenant_id
        )

        return {
            "events": [
                {
                    "id": row['id'],
                    "event_type": row['event_type'],
                    "event_timestamp": row['event_timestamp'].isoformat(),
                    "actor_type": row['actor_type'],
                    "actor_id": row['actor_id'],
                    "previous_state": row['previous_state'],
                    "new_state": row['new_state'],
                    "details": row['details'],
                }
                for row in rows
            ],
            "total": count,
            "limit": limit,
            "offset": offset,
        }
```

### 3. GET /customer/subscription/usage

Returns detailed device usage breakdown.

```python
@router.get("/subscription/usage")
async def get_subscription_usage():
    """Get device usage breakdown for subscription."""
    tenant_id = get_tenant_id()

    p = await get_pool()
    async with tenant_connection(p, tenant_id) as conn:
        # Get subscription
        sub = await conn.fetchrow(
            """
            SELECT device_limit, active_device_count, status
            FROM tenant_subscription
            WHERE tenant_id = $1
            """,
            tenant_id
        )

        if not sub:
            raise HTTPException(404, "No subscription found")

        # Get device status breakdown
        status_counts = await conn.fetch(
            """
            SELECT status, COUNT(*) as count
            FROM device_registry
            WHERE tenant_id = $1
            GROUP BY status
            """,
            tenant_id
        )

        # Get devices by site
        site_counts = await conn.fetch(
            """
            SELECT site_id, COUNT(*) as count
            FROM device_registry
            WHERE tenant_id = $1 AND status = 'ACTIVE'
            GROUP BY site_id
            ORDER BY count DESC
            LIMIT 10
            """,
            tenant_id
        )

        return {
            "device_limit": sub['device_limit'],
            "active_device_count": sub['active_device_count'],
            "usage_percent": round(sub['active_device_count'] / max(sub['device_limit'], 1) * 100, 1),
            "subscription_status": sub['status'],
            "by_status": {row['status']: row['count'] for row in status_counts},
            "by_site": [{"site_id": row['site_id'], "count": row['count']} for row in site_counts],
        }
```

## Required Imports

Add at the top of the file:

```python
from datetime import datetime, timezone
```

## Response Types (Pydantic Models)

Optionally add response models for better documentation:

```python
class SubscriptionResponse(BaseModel):
    tenant_id: str
    tenant_name: str
    device_limit: int
    active_device_count: int
    devices_available: int
    term_start: str | None
    term_end: str | None
    days_until_expiry: int | None
    plan_id: str | None
    status: str
    grace_end: str | None


class SubscriptionAuditEvent(BaseModel):
    id: int
    event_type: str
    event_timestamp: str
    actor_type: str | None
    actor_id: str | None
    previous_state: dict | None
    new_state: dict | None
    details: dict | None
```

## Testing

```bash
# Get subscription status
curl -X GET /customer/subscription \
  -H "Authorization: Bearer $TOKEN"

# Get audit history
curl -X GET "/customer/subscription/audit?limit=10" \
  -H "Authorization: Bearer $TOKEN"

# Get usage breakdown
curl -X GET /customer/subscription/usage \
  -H "Authorization: Bearer $TOKEN"
```
