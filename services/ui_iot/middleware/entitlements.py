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
            "current": 0,
            "limit": 0,
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
            "current": count,
            "limit": max_rules,
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
    # No tenant_users table; count distinct assigned users for this tenant.
    user_count = await conn.fetchval(
        "SELECT COUNT(DISTINCT user_id) FROM user_role_assignments WHERE tenant_id = $1",
        tenant_id,
    )

    return {
        "plan_id": plan_id,
        "usage": {
            "alert_rules": {"current": rule_count, "limit": limits["alert_rules"]},
            "notification_channels": {
                "current": channel_count,
                "limit": limits["notification_channels"],
            },
            "users": {"current": user_count, "limit": limits["users"]},
            "devices": {"current": device_count, "limit": None},  # device limit is per-subscription
        },
    }

