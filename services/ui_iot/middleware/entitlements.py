"""
Entitlement checks for the two-tier subscription model.

- Account Tier (per tenant): shared resource limits + account-level features
- Device Plan (per device): per-device capability limits + device-level features

All plan limits are read from the DB — never hardcoded.
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


# ─── Account Tier Checks (tenant-level) ──────────────────────────

async def get_account_tier(conn, tenant_id: str) -> dict | None:
    """Load the tenant's account tier definition."""
    row = await conn.fetchrow(
        """
        SELECT at.*
        FROM tenants t
        JOIN account_tiers at ON at.tier_id = t.account_tier_id
        WHERE t.tenant_id = $1 AND at.is_active = true
        """,
        tenant_id,
    )
    if not row:
        return None
    result = dict(row)
    # Handle PgBouncer JSONB-as-string
    for col in ("limits", "features", "support"):
        if isinstance(result.get(col), str):
            result[col] = json.loads(result[col])
    return result


async def check_account_limit(conn, tenant_id: str, resource: str, current_count: int) -> dict:
    """
    Check if tenant is at or over their account tier limit for a shared resource.

    resource: one of 'users', 'alert_rules', 'notification_channels', etc.
    current_count: current number of that resource the tenant has.

    Returns: {"allowed": bool, "current": int, "limit": int, "message": str, "status_code": int}
    """
    tier = await get_account_tier(conn, tenant_id)
    if not tier:
        return {
            "allowed": False,
            "current": current_count,
            "limit": 0,
            "message": "No account tier assigned. Contact support.",
            "status_code": 403,
        }

    limits = tier.get("limits", {})
    limit_value = limits.get(resource)

    if limit_value is None:
        # No limit defined for this resource — allow by default
        return {"allowed": True, "current": current_count, "limit": None, "message": "", "status_code": 200}

    limit_value = int(limit_value)
    if current_count >= limit_value:
        tier_name = tier.get("name", tier.get("tier_id", "unknown"))
        return {
            "allowed": False,
            "current": current_count,
            "limit": limit_value,
            "message": f"{resource.replace('_', ' ').title()} limit reached ({current_count}/{limit_value}). Upgrade your account tier to add more.",
            "status_code": 402,
        }

    return {"allowed": True, "current": current_count, "limit": limit_value, "message": "", "status_code": 200}


async def check_account_feature(conn, tenant_id: str, feature: str) -> dict:
    """
    Check if tenant's account tier includes a specific feature.

    feature: one of 'sso', 'carrier_self_service', 'bulk_device_import', etc.

    Returns: {"allowed": bool, "message": str}
    """
    tier = await get_account_tier(conn, tenant_id)
    if not tier:
        return {"allowed": False, "message": "No account tier assigned. Contact support."}

    features = tier.get("features", {})
    allowed = bool(features.get(feature, False))

    if not allowed:
        tier_name = tier.get("name", tier.get("tier_id", "unknown"))
        return {
            "allowed": False,
            "message": f"This feature requires an upgraded account tier. Current tier: {tier_name}.",
        }

    return {"allowed": True, "message": ""}


# ─── Convenience: Specific Account Limit Checks ─────────────────

async def check_alert_rule_limit(conn, tenant_id: str) -> dict:
    """Check if tenant can create another alert rule."""
    count = await conn.fetchval(
        "SELECT COUNT(*) FROM alert_rules WHERE tenant_id = $1", tenant_id
    )
    return await check_account_limit(conn, tenant_id, "alert_rules", count)


async def check_notification_channel_limit(conn, tenant_id: str) -> dict:
    """Check if tenant can create another notification channel."""
    count = await conn.fetchval(
        "SELECT COUNT(*) FROM notification_channels WHERE tenant_id = $1", tenant_id
    )
    return await check_account_limit(conn, tenant_id, "notification_channels", count)


async def check_user_limit(conn, tenant_id: str) -> dict:
    """Check if tenant can invite another user."""
    count = await conn.fetchval(
        "SELECT COUNT(DISTINCT user_id) FROM user_role_assignments WHERE tenant_id = $1",
        tenant_id,
    )
    return await check_account_limit(conn, tenant_id, "users", count)


# ─── Device Plan Checks (per-device) ────────────────────────────

async def get_device_plan(conn, device_id: str) -> dict | None:
    """Load the device's plan definition."""
    row = await conn.fetchrow(
        """
        SELECT dp.*
        FROM device_registry dr
        JOIN device_plans dp ON dp.plan_id = dr.plan_id
        WHERE dr.device_id = $1 AND dp.is_active = true
        """,
        device_id,
    )
    if not row:
        return None
    result = dict(row)
    for col in ("limits", "features"):
        if isinstance(result.get(col), str):
            result[col] = json.loads(result[col])
    return result


async def check_device_limit(conn, device_id: str, resource: str, current_count: int) -> dict:
    """
    Check if device is at or over its plan limit for a resource.

    resource: one of 'sensors', etc.
    current_count: current number of that resource on this device.
    """
    plan = await get_device_plan(conn, device_id)
    if not plan:
        return {
            "allowed": False,
            "current": current_count,
            "limit": 0,
            "message": "No device plan assigned. Assign a plan to this device.",
            "status_code": 403,
        }

    limits = plan.get("limits", {})
    limit_value = limits.get(resource)

    if limit_value is None:
        return {"allowed": True, "current": current_count, "limit": None, "message": "", "status_code": 200}

    limit_value = int(limit_value)
    if current_count >= limit_value:
        plan_name = plan.get("name", plan.get("plan_id", "unknown"))
        return {
            "allowed": False,
            "current": current_count,
            "limit": limit_value,
            "message": f"Sensor limit reached ({current_count}/{limit_value}). Upgrade this device's plan to add more.",
            "status_code": 402,
        }

    return {"allowed": True, "current": current_count, "limit": limit_value, "message": "", "status_code": 200}


async def check_device_feature(conn, device_id: str, feature: str) -> dict:
    """
    Check if device's plan includes a specific feature.

    feature: one of 'ota_updates', 'x509_auth', 'streaming_export', etc.
    """
    plan = await get_device_plan(conn, device_id)
    if not plan:
        return {"allowed": False, "message": "No device plan assigned."}

    features = plan.get("features", {})
    allowed = bool(features.get(feature, False))

    if not allowed:
        plan_name = plan.get("name", plan.get("plan_id", "unknown"))
        return {
            "allowed": False,
            "message": f"This feature requires an upgraded device plan. Current plan: {plan_name}.",
        }

    return {"allowed": True, "message": ""}


async def check_sensor_limit(conn, tenant_id: str, device_id: str) -> dict:
    """Check if device can add another sensor (convenience wrapper)."""
    count = await conn.fetchval(
        "SELECT COUNT(*) FROM sensors WHERE tenant_id = $1 AND device_id = $2",
        tenant_id, device_id,
    )
    return await check_device_limit(conn, device_id, "sensors", count)


# ─── Usage Reporting (for billing/entitlements UI) ───────────────

async def get_account_usage(conn, tenant_id: str) -> dict:
    """
    Get current usage vs limits for the tenant's account tier.
    Used by GET /billing/entitlements.
    """
    tier = await get_account_tier(conn, tenant_id)
    if not tier:
        return {
            "tier_id": None,
            "tier_name": None,
            "limits": {},
            "features": {},
            "support": {},
            "usage": {},
        }

    limits = tier.get("limits", {})

    # Count current usage for each limited resource
    alert_count = await conn.fetchval(
        "SELECT COUNT(*) FROM alert_rules WHERE tenant_id = $1", tenant_id
    )
    channel_count = await conn.fetchval(
        "SELECT COUNT(*) FROM notification_channels WHERE tenant_id = $1", tenant_id
    )
    user_count = await conn.fetchval(
        "SELECT COUNT(DISTINCT user_id) FROM user_role_assignments WHERE tenant_id = $1",
        tenant_id,
    )
    device_count = await conn.fetchval(
        "SELECT COUNT(*) FROM device_registry WHERE tenant_id = $1 AND status = 'ACTIVE'", tenant_id
    )

    usage: dict[str, Any] = {}
    for key, count in [
        ("alert_rules", alert_count),
        ("notification_channels", channel_count),
        ("users", user_count),
    ]:
        limit = limits.get(key)
        usage[key] = {
            "current": count,
            "limit": int(limit) if limit is not None else None,
        }

    # Device count isn't an account-tier limit anymore (each device has its own subscription)
    # but we include it for display
    usage["devices"] = {"current": device_count, "limit": None}

    return {
        "tier_id": tier["tier_id"],
        "tier_name": tier["name"],
        "limits": limits,
        "features": tier.get("features", {}),
        "support": tier.get("support", {}),
        "usage": usage,
    }


async def get_device_usage(conn, tenant_id: str, device_id: str) -> dict:
    """
    Get current usage vs limits for a specific device's plan.
    Used by device detail pages.
    """
    plan = await get_device_plan(conn, device_id)
    if not plan:
        return {"plan_id": None, "plan_name": None, "limits": {}, "features": {}, "usage": {}}

    limits = plan.get("limits", {})

    sensor_count = await conn.fetchval(
        "SELECT COUNT(*) FROM sensors WHERE tenant_id = $1 AND device_id = $2",
        tenant_id, device_id,
    )

    usage = {
        "sensors": {
            "current": sensor_count,
            "limit": int(limits["sensors"]) if "sensors" in limits else None,
        },
    }

    return {
        "plan_id": plan["plan_id"],
        "plan_name": plan["name"],
        "limits": limits,
        "features": plan.get("features", {}),
        "usage": usage,
    }

