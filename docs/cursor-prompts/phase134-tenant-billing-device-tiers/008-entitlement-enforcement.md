# 008 -- Entitlement Enforcement

## Context

With Stripe billing syncing plan data to `subscriptions` and `subscription_tier_allocations`, and device tier assignment handling slot checks (task 007), we need broader entitlement enforcement:
1. Device creation — clearer error when subscription capacity is reached (402 vs generic 403)
2. Alert rule creation — check rule count against plan limits
3. Entitlement summary endpoint — show plan limits vs current usage

The device creation flow already checks `active_device_count < device_limit` in `routes/devices.py`. We tighten it with user-friendly error messages. Tier slot enforcement is already in task 007.

## Task

### Step 1: Create Entitlement Helper Module

Create `services/ui_iot/middleware/entitlements.py`:

```python
"""Entitlement enforcement helpers for subscription limits.

All plan limits are read from the subscription_plans table — never hardcoded.
If a plan has no limits JSONB entry, we default to 0 (deny by default).
"""
import json
import logging

logger = logging.getLogger("pulse.entitlements")

DEFAULT_LIMITS = {"alert_rules": 0, "notification_channels": 0, "users": 0}


async def _get_plan_limits(conn, plan_id: str) -> dict:
    """Look up plan limits from subscription_plans table."""
    if not plan_id:
        return DEFAULT_LIMITS
    row = await conn.fetchrow(
        "SELECT limits, device_limit FROM subscription_plans WHERE plan_id = $1 AND is_active = true",
        plan_id,
    )
    if not row:
        logger.warning("Unknown or inactive plan_id '%s', using default limits", plan_id)
        return DEFAULT_LIMITS
    limits = row["limits"]
    # PgBouncer compatibility: limits may be a string
    if isinstance(limits, str):
        limits = json.loads(limits)
    return {**DEFAULT_LIMITS, **limits}


async def check_device_limit(conn, tenant_id: str) -> dict:
    """Check if tenant can create another device."""
    sub = await conn.fetchrow(
        """
        SELECT subscription_id, device_limit, active_device_count, plan_id, status
        FROM subscriptions
        WHERE tenant_id = $1 AND subscription_type = 'MAIN'
          AND status IN ('ACTIVE', 'TRIAL')
        ORDER BY created_at DESC LIMIT 1
        """,
        tenant_id,
    )

    if not sub:
        return {
            "allowed": False,
            "current": 0, "limit": 0,
            "message": "No active subscription. Please subscribe to a plan.",
            "status_code": 403,
        }

    if sub["active_device_count"] >= sub["device_limit"]:
        return {
            "allowed": False,
            "current": sub["active_device_count"],
            "limit": sub["device_limit"],
            "message": f"Device limit reached. Current: {sub['active_device_count']}/{sub['device_limit']}. Upgrade your plan.",
            "status_code": 402,
        }

    return {
        "allowed": True,
        "current": sub["active_device_count"],
        "limit": sub["device_limit"],
        "subscription_id": sub["subscription_id"],
    }


async def check_alert_rule_limit(conn, tenant_id: str) -> dict:
    """Check if tenant can create another alert rule."""
    sub = await conn.fetchrow(
        """
        SELECT plan_id FROM subscriptions
        WHERE tenant_id = $1 AND subscription_type = 'MAIN'
          AND status IN ('ACTIVE', 'TRIAL')
        ORDER BY created_at DESC LIMIT 1
        """,
        tenant_id,
    )

    plan_id = sub["plan_id"] if sub else None
    limits = await _get_plan_limits(conn, plan_id)
    max_rules = limits["alert_rules"]

    count = await conn.fetchval(
        "SELECT COUNT(*) FROM alert_rules WHERE tenant_id = $1",
        tenant_id,
    )

    if count >= max_rules:
        return {
            "allowed": False,
            "current": count, "limit": max_rules,
            "message": f"Alert rule limit reached. Current: {count}/{max_rules}. Upgrade your plan.",
            "status_code": 402,
        }

    return {"allowed": True, "current": count, "limit": max_rules}


async def get_plan_usage(conn, tenant_id: str) -> dict:
    """Get all plan limits and current usage for a tenant."""
    sub = await conn.fetchrow(
        """
        SELECT plan_id FROM subscriptions
        WHERE tenant_id = $1 AND subscription_type = 'MAIN'
          AND status IN ('ACTIVE', 'TRIAL')
        ORDER BY created_at DESC LIMIT 1
        """,
        tenant_id,
    )

    plan_id = sub["plan_id"] if sub else None
    limits = await _get_plan_limits(conn, plan_id)

    device_count = await conn.fetchval(
        "SELECT COUNT(*) FROM device_registry WHERE tenant_id = $1", tenant_id
    )
    rule_count = await conn.fetchval(
        "SELECT COUNT(*) FROM alert_rules WHERE tenant_id = $1", tenant_id
    )
    channel_count = await conn.fetchval(
        "SELECT COUNT(*) FROM notification_channels WHERE tenant_id = $1", tenant_id
    )
    user_count = await conn.fetchval(
        "SELECT COUNT(*) FROM tenant_users WHERE tenant_id = $1", tenant_id
    )

    return {
        "plan_id": plan_id,
        "usage": {
            "alert_rules": {"current": rule_count, "limit": limits["alert_rules"]},
            "notification_channels": {"current": channel_count, "limit": limits["notification_channels"]},
            "users": {"current": user_count, "limit": limits["users"]},
            "devices": {"current": device_count, "limit": None},  # device limit is per-subscription
        },
    }
```

### Step 2: Integrate Device Limit Check

In `services/ui_iot/routes/devices.py`, in the `create_device` endpoint (around line 128):

Add import:
```python
from middleware.entitlements import check_device_limit
```

Before the existing subscription lookup query, add the entitlement check:
```python
check = await check_device_limit(conn, tenant_id)
if not check["allowed"]:
    raise HTTPException(check["status_code"], check["message"])
```

This replaces the current generic "No MAIN subscription with available capacity" error with a clear, actionable message.

### Step 3: Integrate Alert Rule Limit Check

In `services/ui_iot/routes/alerts.py`, find the alert rule creation endpoint (POST for creating rules).

Add import:
```python
from middleware.entitlements import check_alert_rule_limit
```

Before the INSERT query:
```python
check = await check_alert_rule_limit(conn, tenant_id)
if not check["allowed"]:
    raise HTTPException(check["status_code"], check["message"])
```

### Step 4: Add Entitlements Summary Endpoint

In `services/ui_iot/routes/billing.py`, add to `customer_router`:

```python
from middleware.entitlements import get_plan_usage

@customer_router.get("/entitlements")
async def get_entitlements(pool=Depends(get_db_pool)):
    """Get plan limits and current usage for display on billing page."""
    tenant_id = get_tenant_id()

    async with tenant_connection(pool, tenant_id) as conn:
        usage = await get_plan_usage(conn, tenant_id)

    return usage
```

## Verify

```bash
# 1. Rebuild
docker compose -f compose/docker-compose.yml up -d --build ui

# 2. Check entitlements
curl -s http://localhost:8080/api/v1/customer/billing/entitlements \
  -H "Authorization: Bearer $TOKEN" | jq .

# 3. Test device creation at limit (set device_limit low for testing)
# Expected: 402 "Device limit reached. Current: X/X. Upgrade your plan."

# 4. Test alert rule creation at limit
# Expected: 402 "Alert rule limit reached. Current: X/X. Upgrade your plan."
```

## Commit

```
feat(phase134): add entitlement enforcement for devices and alert rules

Add middleware/entitlements.py with check_device_limit and
check_alert_rule_limit helpers returning 402 with actionable
upgrade messages. Integrate into device creation and alert rule
creation endpoints. Add GET /billing/entitlements endpoint returning
plan limits vs current usage (rules, channels, users, devices).
```
