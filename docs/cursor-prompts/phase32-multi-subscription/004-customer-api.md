# 004: Customer API for Multi-Subscription

## Task

Update customer API endpoints to support viewing multiple subscriptions and device assignments.

## File to Modify

`services/ui_iot/routes/customer.py`

## Endpoints to Update/Add

### 1. GET /customer/subscriptions (NEW)

List all subscriptions for the tenant.

```python
@router.get("/subscriptions")
async def list_subscriptions(
    include_expired: bool = Query(False),
):
    """List all subscriptions for the tenant."""
    tenant_id = get_tenant_id()

    p = await get_pool()
    async with tenant_connection(p, tenant_id) as conn:
        if include_expired:
            rows = await conn.fetch(
                """
                SELECT
                    subscription_id, subscription_type, parent_subscription_id,
                    device_limit, active_device_count, term_start, term_end,
                    status, plan_id, description, created_at
                FROM subscriptions
                WHERE tenant_id = $1
                ORDER BY
                    CASE subscription_type
                        WHEN 'MAIN' THEN 1
                        WHEN 'ADDON' THEN 2
                        WHEN 'TRIAL' THEN 3
                        WHEN 'TEMPORARY' THEN 4
                    END,
                    term_end DESC
                """,
                tenant_id
            )
        else:
            rows = await conn.fetch(
                """
                SELECT
                    subscription_id, subscription_type, parent_subscription_id,
                    device_limit, active_device_count, term_start, term_end,
                    status, plan_id, description, created_at
                FROM subscriptions
                WHERE tenant_id = $1 AND status != 'EXPIRED'
                ORDER BY
                    CASE subscription_type
                        WHEN 'MAIN' THEN 1
                        WHEN 'ADDON' THEN 2
                        WHEN 'TRIAL' THEN 3
                        WHEN 'TEMPORARY' THEN 4
                    END,
                    term_end DESC
                """,
                tenant_id
            )

        # Calculate totals
        total_limit = sum(r['device_limit'] for r in rows if r['status'] not in ('SUSPENDED', 'EXPIRED'))
        total_active = sum(r['active_device_count'] for r in rows if r['status'] not in ('SUSPENDED', 'EXPIRED'))

        return {
            "subscriptions": [
                {
                    "subscription_id": r['subscription_id'],
                    "subscription_type": r['subscription_type'],
                    "parent_subscription_id": r['parent_subscription_id'],
                    "device_limit": r['device_limit'],
                    "active_device_count": r['active_device_count'],
                    "devices_available": r['device_limit'] - r['active_device_count'],
                    "term_start": r['term_start'].isoformat() if r['term_start'] else None,
                    "term_end": r['term_end'].isoformat() if r['term_end'] else None,
                    "status": r['status'],
                    "plan_id": r['plan_id'],
                    "description": r['description'],
                }
                for r in rows
            ],
            "summary": {
                "total_device_limit": total_limit,
                "total_active_devices": total_active,
                "total_available": total_limit - total_active,
            },
        }
```

### 2. GET /customer/subscriptions/{subscription_id} (NEW)

Get details of a specific subscription.

```python
@router.get("/subscriptions/{subscription_id}")
async def get_subscription_detail(subscription_id: str):
    """Get details of a specific subscription."""
    tenant_id = get_tenant_id()

    p = await get_pool()
    async with tenant_connection(p, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            SELECT * FROM subscriptions
            WHERE subscription_id = $1 AND tenant_id = $2
            """,
            subscription_id, tenant_id
        )

        if not row:
            raise HTTPException(404, "Subscription not found")

        # Get devices on this subscription
        devices = await conn.fetch(
            """
            SELECT d.device_id, d.site_id, d.status, ds.last_seen_at
            FROM device_registry d
            LEFT JOIN device_state ds ON d.tenant_id = ds.tenant_id AND d.device_id = ds.device_id
            WHERE d.subscription_id = $1
            ORDER BY d.device_id
            LIMIT 100
            """,
            subscription_id
        )

        device_count = await conn.fetchval(
            "SELECT COUNT(*) FROM device_registry WHERE subscription_id = $1",
            subscription_id
        )

        # Calculate days until expiry
        days_until_expiry = None
        if row['term_end']:
            delta = row['term_end'] - datetime.now(timezone.utc)
            days_until_expiry = max(0, delta.days)

        return {
            "subscription_id": row['subscription_id'],
            "subscription_type": row['subscription_type'],
            "parent_subscription_id": row['parent_subscription_id'],
            "device_limit": row['device_limit'],
            "active_device_count": row['active_device_count'],
            "devices_available": row['device_limit'] - row['active_device_count'],
            "term_start": row['term_start'].isoformat() if row['term_start'] else None,
            "term_end": row['term_end'].isoformat() if row['term_end'] else None,
            "days_until_expiry": days_until_expiry,
            "status": row['status'],
            "plan_id": row['plan_id'],
            "description": row['description'],
            "devices": [
                {
                    "device_id": d['device_id'],
                    "site_id": d['site_id'],
                    "status": d['status'],
                    "last_seen_at": d['last_seen_at'].isoformat() if d['last_seen_at'] else None,
                }
                for d in devices
            ],
            "total_devices": device_count,
        }
```

### 3. GET /customer/subscription (UPDATE existing)

Update the existing endpoint to return summary across all subscriptions:

```python
@router.get("/subscription")
async def get_subscription_summary():
    """Get overall subscription summary for the tenant (backward compatible)."""
    tenant_id = get_tenant_id()

    p = await get_pool()
    async with tenant_connection(p, tenant_id) as conn:
        rows = await conn.fetch(
            """
            SELECT device_limit, active_device_count, term_end, status
            FROM subscriptions
            WHERE tenant_id = $1 AND status NOT IN ('EXPIRED')
            """,
            tenant_id
        )

        if not rows:
            raise HTTPException(404, "No active subscriptions found")

        # Aggregate across all active subscriptions
        total_limit = sum(r['device_limit'] for r in rows if r['status'] != 'SUSPENDED')
        total_active = sum(r['active_device_count'] for r in rows if r['status'] != 'SUSPENDED')

        # Find earliest expiring active subscription
        active_subs = [r for r in rows if r['status'] == 'ACTIVE']
        earliest_expiry = min((r['term_end'] for r in active_subs), default=None)

        days_until_expiry = None
        if earliest_expiry:
            delta = earliest_expiry - datetime.now(timezone.utc)
            days_until_expiry = max(0, delta.days)

        # Overall status (worst case)
        statuses = [r['status'] for r in rows]
        if 'SUSPENDED' in statuses:
            overall_status = 'SUSPENDED'
        elif 'GRACE' in statuses:
            overall_status = 'GRACE'
        elif 'TRIAL' in statuses and 'ACTIVE' not in statuses:
            overall_status = 'TRIAL'
        else:
            overall_status = 'ACTIVE'

        tenant = await conn.fetchrow(
            "SELECT name FROM tenants WHERE tenant_id = $1", tenant_id
        )

        return {
            "tenant_id": tenant_id,
            "tenant_name": tenant['name'] if tenant else tenant_id,
            "device_limit": total_limit,
            "active_device_count": total_active,
            "devices_available": total_limit - total_active,
            "days_until_expiry": days_until_expiry,
            "status": overall_status,
            "subscription_count": len(rows),
        }
```

### 4. GET /customer/devices (UPDATE)

Add subscription_id to device list response:

Find the existing devices endpoint and add subscription info to the response:

```python
# In the SELECT query, add:
# d.subscription_id, s.subscription_type, s.status as subscription_status

# In the response, add to each device:
# "subscription_id": d['subscription_id'],
# "subscription_type": d['subscription_type'],
# "subscription_status": d['subscription_status'],
```

## Required Imports

```python
from datetime import datetime, timezone
```

## Testing

```bash
# List all subscriptions
curl -X GET /customer/subscriptions \
  -H "Authorization: Bearer $TOKEN"

# Get specific subscription with devices
curl -X GET /customer/subscriptions/SUB-20240101-00001 \
  -H "Authorization: Bearer $TOKEN"

# Get summary (backward compatible)
curl -X GET /customer/subscription \
  -H "Authorization: Bearer $TOKEN"
```
