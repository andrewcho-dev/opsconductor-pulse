import os
import json
import logging
import re
import time
from datetime import datetime, timezone, timedelta

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, Form
from starlette.requests import Request
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

from middleware.auth import JWTBearer
from middleware.tenant import (
    inject_tenant_context,
    get_user,
    require_operator,
    require_operator_admin,
)
from db.queries import (
    fetch_alerts,
    fetch_all_alerts,
    fetch_all_devices,
    fetch_all_integrations,
    fetch_delivery_attempts,
    fetch_device,
    fetch_devices,
    fetch_integrations,
    fetch_quarantine_events,
)
from db.telemetry_queries import fetch_device_telemetry, fetch_device_events
from db.audit import log_operator_access, fetch_operator_audit_log
from db.pool import operator_connection
from dependencies import get_db_pool

logger = logging.getLogger(__name__)

PG_HOST = os.getenv("PG_HOST", "iot-postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "iotcloud")
PG_USER = os.getenv("PG_USER", "iot")
PG_PASS = os.getenv("PG_PASS", "iot_dev")

pool: asyncpg.Pool | None = None


class TenantCreate(BaseModel):
    tenant_id: str  # Must be URL-safe, lowercase
    name: str
    contact_email: Optional[EmailStr] = None
    contact_name: Optional[str] = None
    legal_name: Optional[str] = Field(None, max_length=200)
    phone: Optional[str] = Field(None, max_length=50)
    industry: Optional[str] = Field(None, max_length=100)
    company_size: Optional[str] = Field(None, max_length=50)
    address_line1: Optional[str] = Field(None, max_length=200)
    address_line2: Optional[str] = Field(None, max_length=200)
    city: Optional[str] = Field(None, max_length=100)
    state_province: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=2)
    data_residency_region: Optional[str] = Field(None, max_length=50)
    support_tier: Optional[str] = Field(None, max_length=20)
    sla_level: Optional[float] = None
    billing_email: Optional[str] = Field(None, max_length=255)
    metadata: Optional[dict] = None


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_name: Optional[str] = None
    status: Optional[str] = None  # ACTIVE, SUSPENDED
    legal_name: Optional[str] = Field(None, max_length=200)
    phone: Optional[str] = Field(None, max_length=50)
    industry: Optional[str] = Field(None, max_length=100)
    company_size: Optional[str] = Field(None, max_length=50)
    address_line1: Optional[str] = Field(None, max_length=200)
    address_line2: Optional[str] = Field(None, max_length=200)
    city: Optional[str] = Field(None, max_length=100)
    state_province: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=2)
    data_residency_region: Optional[str] = Field(None, max_length=50)
    support_tier: Optional[str] = Field(None, max_length=20)
    sla_level: Optional[float] = None
    billing_email: Optional[str] = Field(None, max_length=255)
    stripe_customer_id: Optional[str] = Field(None, max_length=100)  # operator can manually link
    metadata: Optional[dict] = None


class TenantResponse(BaseModel):
    tenant_id: str
    name: str
    status: str
    contact_email: Optional[EmailStr]
    contact_name: Optional[str]
    metadata: dict
    created_at: datetime
    updated_at: datetime


# ── Device Tier Management ────────────────────────────────────

class DeviceTierCreate(BaseModel):
    name: str = Field(..., max_length=50, pattern="^[a-z][a-z0-9_-]*$")
    display_name: str = Field(..., max_length=100)
    description: Optional[str] = ""
    features: dict = Field(default_factory=dict)
    sort_order: int = Field(default=0)


class DeviceTierUpdate(BaseModel):
    display_name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    features: Optional[dict] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class SubscriptionCreate(BaseModel):
    tenant_id: str
    subscription_type: str = Field(..., pattern="^(MAIN|ADDON|TRIAL|TEMPORARY)$")
    device_limit: int = Field(..., ge=1)
    term_start: Optional[datetime] = None
    term_end: Optional[datetime] = None
    term_days: Optional[int] = None
    parent_subscription_id: Optional[str] = None
    plan_id: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None


class SubscriptionUpdate(BaseModel):
    device_limit: Optional[int] = Field(None, ge=0)
    plan_id: Optional[str] = None
    term_end: Optional[datetime] = None
    status: Optional[str] = Field(None, pattern="^(TRIAL|ACTIVE|GRACE|SUSPENDED|EXPIRED)$")
    description: Optional[str] = None
    notes: Optional[str] = None
    transaction_ref: Optional[str] = None


class DeviceSubscriptionAssign(BaseModel):
    subscription_id: str
    notes: Optional[str] = None




async def get_pool() -> asyncpg.Pool:
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(
            host=PG_HOST,
            port=PG_PORT,
            database=PG_DB,
            user=PG_USER,
            password=PG_PASS,
            min_size=1,
            max_size=5,
        )
    return pool


def get_request_metadata(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return ip, user_agent


async def get_settings(conn):
    rows = await conn.fetch(
        "SELECT key, value FROM app_settings WHERE key IN "
        "('MODE','STORE_REJECTS','MIRROR_REJECTS_TO_RAW','RATE_LIMIT_RPS','RATE_LIMIT_BURST','MAX_PAYLOAD_BYTES')"
    )
    kv = {r["key"]: r["value"] for r in rows}

    mode = (kv.get("MODE", "PROD") or "PROD").upper()
    if mode not in ("PROD", "DEV"):
        mode = "PROD"

    store_rejects = kv.get("STORE_REJECTS", "0")
    mirror_rejects = kv.get("MIRROR_REJECTS_TO_RAW", "0")

    if mode == "PROD":
        store_rejects = "0"
        mirror_rejects = "0"

    rate_rps = kv.get("RATE_LIMIT_RPS", "5")
    rate_burst = kv.get("RATE_LIMIT_BURST", "20")
    max_payload_bytes = kv.get("MAX_PAYLOAD_BYTES", "8192")

    return mode, store_rejects, mirror_rejects, rate_rps, rate_burst, max_payload_bytes


router = APIRouter(
    prefix="/api/v1/operator",
    tags=["operator"],
    dependencies=[
        Depends(JWTBearer()),
        Depends(inject_tenant_context),
        Depends(require_operator),
    ],
)


# ── Account Tiers + Device Plans (Phase 156) ──────────────────────

class AccountTierCreate(BaseModel):
    tier_id: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    description: str = ""
    limits: dict = Field(default_factory=dict)
    features: dict = Field(default_factory=dict)
    support: dict = Field(default_factory=dict)
    monthly_price_cents: int = Field(default=0, ge=0)
    annual_price_cents: int = Field(default=0, ge=0)
    sort_order: int = Field(default=0)


class AccountTierUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    limits: Optional[dict] = None
    features: Optional[dict] = None
    support: Optional[dict] = None
    monthly_price_cents: Optional[int] = Field(None, ge=0)
    annual_price_cents: Optional[int] = Field(None, ge=0)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class DevicePlanCreate(BaseModel):
    plan_id: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    description: str = ""
    limits: dict = Field(default_factory=dict)
    features: dict = Field(default_factory=dict)
    monthly_price_cents: int = Field(default=0, ge=0)
    annual_price_cents: int = Field(default=0, ge=0)
    sort_order: int = Field(default=0)


class DevicePlanUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    limits: Optional[dict] = None
    features: Optional[dict] = None
    monthly_price_cents: Optional[int] = Field(None, ge=0)
    annual_price_cents: Optional[int] = Field(None, ge=0)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class TenantTierAssign(BaseModel):
    tier_id: str = Field(..., max_length=50)


class DeviceSubscriptionCreateV2(BaseModel):
    tenant_id: str
    device_id: str
    plan_id: str = Field(..., max_length=50)
    status: str = Field(default="ACTIVE", pattern="^(TRIAL|ACTIVE|GRACE|SUSPENDED|EXPIRED|CANCELLED)$")
    term_start: Optional[datetime] = None
    term_end: Optional[datetime] = None


class DeviceSubscriptionUpdateV2(BaseModel):
    plan_id: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = Field(None, pattern="^(TRIAL|ACTIVE|GRACE|SUSPENDED|EXPIRED|CANCELLED)$")
    term_end: Optional[datetime] = None


@router.get("/account-tiers")
async def operator_list_account_tiers():
    pool = await get_pool()
    async with operator_connection(pool) as conn:
        rows = await conn.fetch("SELECT * FROM account_tiers ORDER BY sort_order")
    return {"tiers": [dict(r) for r in rows]}


@router.post("/account-tiers", status_code=201)
async def operator_create_account_tier(
    data: AccountTierCreate,
    _: None = Depends(require_operator_admin),
):
    pool = await get_pool()
    async with operator_connection(pool) as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO account_tiers (
                tier_id, name, description, limits, features, support,
                monthly_price_cents, annual_price_cents, sort_order
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING *
            """,
            data.tier_id,
            data.name,
            data.description,
            json.dumps(data.limits),
            json.dumps(data.features),
            json.dumps(data.support),
            data.monthly_price_cents,
            data.annual_price_cents,
            data.sort_order,
        )
    return dict(row)


@router.put("/account-tiers/{tier_id}")
async def operator_update_account_tier(
    tier_id: str,
    data: AccountTierUpdate,
    _: None = Depends(require_operator_admin),
):
    updates = []
    params = []
    idx = 1
    for key, value in [
        ("name", data.name),
        ("description", data.description),
        ("monthly_price_cents", data.monthly_price_cents),
        ("annual_price_cents", data.annual_price_cents),
        ("sort_order", data.sort_order),
        ("is_active", data.is_active),
    ]:
        if value is not None:
            updates.append(f"{key} = ${idx}")
            params.append(value)
            idx += 1

    if data.limits is not None:
        updates.append(f"limits = ${idx}")
        params.append(json.dumps(data.limits))
        idx += 1
    if data.features is not None:
        updates.append(f"features = ${idx}")
        params.append(json.dumps(data.features))
        idx += 1
    if data.support is not None:
        updates.append(f"support = ${idx}")
        params.append(json.dumps(data.support))
        idx += 1

    if not updates:
        raise HTTPException(400, "No fields to update")

    pool = await get_pool()
    async with operator_connection(pool) as conn:
        row = await conn.fetchrow(
            f"UPDATE account_tiers SET {', '.join(updates)}, updated_at = NOW() WHERE tier_id = ${idx} RETURNING *",
            *params,
            tier_id,
        )
    if not row:
        raise HTTPException(404, "Account tier not found")
    return dict(row)


@router.delete("/account-tiers/{tier_id}")
async def operator_deactivate_account_tier(
    tier_id: str,
    _: None = Depends(require_operator_admin),
):
    pool = await get_pool()
    async with operator_connection(pool) as conn:
        row = await conn.fetchrow(
            "UPDATE account_tiers SET is_active = false, updated_at = NOW() WHERE tier_id = $1 RETURNING *",
            tier_id,
        )
    if not row:
        raise HTTPException(404, "Account tier not found")
    return dict(row)


@router.get("/device-plans")
async def operator_list_device_plans():
    pool = await get_pool()
    async with operator_connection(pool) as conn:
        rows = await conn.fetch("SELECT * FROM device_plans ORDER BY sort_order")
    return {"plans": [dict(r) for r in rows]}


@router.post("/device-plans", status_code=201)
async def operator_create_device_plan(
    data: DevicePlanCreate,
    _: None = Depends(require_operator_admin),
):
    pool = await get_pool()
    async with operator_connection(pool) as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO device_plans (
                plan_id, name, description, limits, features,
                monthly_price_cents, annual_price_cents, sort_order
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING *
            """,
            data.plan_id,
            data.name,
            data.description,
            json.dumps(data.limits),
            json.dumps(data.features),
            data.monthly_price_cents,
            data.annual_price_cents,
            data.sort_order,
        )
    return dict(row)


@router.put("/device-plans/{plan_id}")
async def operator_update_device_plan(
    plan_id: str,
    data: DevicePlanUpdate,
    _: None = Depends(require_operator_admin),
):
    updates = []
    params = []
    idx = 1
    for key, value in [
        ("name", data.name),
        ("description", data.description),
        ("monthly_price_cents", data.monthly_price_cents),
        ("annual_price_cents", data.annual_price_cents),
        ("sort_order", data.sort_order),
        ("is_active", data.is_active),
    ]:
        if value is not None:
            updates.append(f"{key} = ${idx}")
            params.append(value)
            idx += 1

    if data.limits is not None:
        updates.append(f"limits = ${idx}")
        params.append(json.dumps(data.limits))
        idx += 1
    if data.features is not None:
        updates.append(f"features = ${idx}")
        params.append(json.dumps(data.features))
        idx += 1

    if not updates:
        raise HTTPException(400, "No fields to update")

    pool = await get_pool()
    async with operator_connection(pool) as conn:
        row = await conn.fetchrow(
            f"UPDATE device_plans SET {', '.join(updates)}, updated_at = NOW() WHERE plan_id = ${idx} RETURNING *",
            *params,
            plan_id,
        )
    if not row:
        raise HTTPException(404, "Device plan not found")
    return dict(row)


@router.delete("/device-plans/{plan_id}")
async def operator_deactivate_device_plan(
    plan_id: str,
    _: None = Depends(require_operator_admin),
):
    pool = await get_pool()
    async with operator_connection(pool) as conn:
        row = await conn.fetchrow(
            "UPDATE device_plans SET is_active = false, updated_at = NOW() WHERE plan_id = $1 RETURNING *",
            plan_id,
        )
    if not row:
        raise HTTPException(404, "Device plan not found")
    return dict(row)


@router.patch("/tenants/{tenant_id}/tier")
async def operator_assign_tenant_tier(
    tenant_id: str,
    data: TenantTierAssign,
    _: None = Depends(require_operator_admin),
):
    pool = await get_pool()
    async with operator_connection(pool) as conn:
        tier_exists = await conn.fetchval(
            "SELECT 1 FROM account_tiers WHERE tier_id = $1 AND is_active = true",
            data.tier_id,
        )
        if not tier_exists:
            raise HTTPException(404, "Account tier not found")
        row = await conn.fetchrow(
            """
            UPDATE tenants SET account_tier_id = $2, updated_at = NOW()
            WHERE tenant_id = $1
            RETURNING tenant_id, account_tier_id
            """,
            tenant_id,
            data.tier_id,
        )
    if not row:
        raise HTTPException(404, "Tenant not found")
    return dict(row)


@router.get("/device-subscriptions")
async def operator_list_device_subscriptions(
    tenant_id: Optional[str] = None,
    device_id: Optional[str] = None,
    status: Optional[str] = None,
):
    pool = await get_pool()
    where = ["1=1"]
    params = []
    idx = 1
    for col, value in [("tenant_id", tenant_id), ("device_id", device_id), ("status", status)]:
        if value:
            where.append(f"{col} = ${idx}")
            params.append(value)
            idx += 1

    sql = f"SELECT * FROM device_subscriptions WHERE {' AND '.join(where)} ORDER BY created_at DESC"
    async with operator_connection(pool) as conn:
        rows = await conn.fetch(sql, *params)
    return {"subscriptions": [dict(r) for r in rows]}


@router.post("/device-subscriptions", status_code=201)
async def operator_create_device_subscription(
    data: DeviceSubscriptionCreateV2,
    _: None = Depends(require_operator_admin),
):
    pool = await get_pool()
    async with operator_connection(pool) as conn:
        plan_exists = await conn.fetchval(
            "SELECT 1 FROM device_plans WHERE plan_id = $1 AND is_active = true",
            data.plan_id,
        )
        if not plan_exists:
            raise HTTPException(404, "Device plan not found")

        device_exists = await conn.fetchval(
            "SELECT 1 FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
            data.tenant_id,
            data.device_id,
        )
        if not device_exists:
            raise HTTPException(404, "Device not found for tenant")

        # Keep device_registry in sync with the authoritative subscription plan.
        await conn.execute(
            """
            UPDATE device_registry SET plan_id = $1, updated_at = NOW()
            WHERE tenant_id = $2 AND device_id = $3
            """,
            data.plan_id,
            data.tenant_id,
            data.device_id,
        )

        subscription_id = await conn.fetchval("SELECT generate_subscription_id()")
        term_start = data.term_start or datetime.now(timezone.utc)
        term_end = data.term_end
        row = await conn.fetchrow(
            """
            INSERT INTO device_subscriptions (
                subscription_id, tenant_id, device_id, plan_id, status, term_start, term_end
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
            """,
            subscription_id,
            data.tenant_id,
            data.device_id,
            data.plan_id,
            data.status,
            term_start,
            term_end,
        )
    return dict(row)


@router.patch("/device-subscriptions/{subscription_id}")
async def operator_update_device_subscription(
    subscription_id: str,
    data: DeviceSubscriptionUpdateV2,
    _: None = Depends(require_operator_admin),
):
    updates = []
    params = []
    idx = 1
    if data.plan_id is not None:
        updates.append(f"plan_id = ${idx}")
        params.append(data.plan_id)
        idx += 1
    if data.status is not None:
        updates.append(f"status = ${idx}")
        params.append(data.status)
        idx += 1
    if data.term_end is not None:
        updates.append(f"term_end = ${idx}")
        params.append(data.term_end)
        idx += 1
    if not updates:
        raise HTTPException(400, "No fields to update")

    pool = await get_pool()
    async with operator_connection(pool) as conn:
        if data.plan_id is not None:
            plan_exists = await conn.fetchval(
                "SELECT 1 FROM device_plans WHERE plan_id = $1 AND is_active = true",
                data.plan_id,
            )
            if not plan_exists:
                raise HTTPException(404, "Device plan not found")

        row = await conn.fetchrow(
            f"UPDATE device_subscriptions SET {', '.join(updates)}, updated_at = NOW() WHERE subscription_id = ${idx} RETURNING *",
            *params,
            subscription_id,
        )
        if not row:
            raise HTTPException(404, "Device subscription not found")

        if data.plan_id is not None:
            await conn.execute(
                """
                UPDATE device_registry SET plan_id = $1, updated_at = NOW()
                WHERE tenant_id = $2 AND device_id = $3
                """,
                data.plan_id,
                row["tenant_id"],
                row["device_id"],
            )

    return dict(row)


@router.delete("/device-subscriptions/{subscription_id}")
async def operator_cancel_device_subscription(
    subscription_id: str,
    _: None = Depends(require_operator_admin),
):
    pool = await get_pool()
    async with operator_connection(pool) as conn:
        row = await conn.fetchrow(
            """
            UPDATE device_subscriptions
            SET status = 'CANCELLED', cancelled_at = NOW(), updated_at = NOW()
            WHERE subscription_id = $1
            RETURNING *
            """,
            subscription_id,
        )
    if not row:
        raise HTTPException(404, "Device subscription not found")
    return dict(row)


@router.get("/device-tiers")
async def list_device_tiers():
    """List all device tiers (operator view — includes inactive)."""
    raise HTTPException(
        410,
        "Device tiers are deprecated. Use /operator/device-plans (Phase 156).",
    )


@router.post("/device-tiers", status_code=201)
async def create_device_tier(
    data: DeviceTierCreate,
    _: None = Depends(require_operator_admin),
):
    """Create a new device tier (operator_admin only)."""
    raise HTTPException(
        410,
        "Device tiers are deprecated. Use /operator/device-plans (Phase 156).",
    )


@router.put("/device-tiers/{tier_id}")
async def update_device_tier(
    tier_id: int,
    data: DeviceTierUpdate,
    _: None = Depends(require_operator_admin),
):
    """Update a device tier (operator_admin only)."""
    raise HTTPException(
        410,
        "Device tiers are deprecated. Use /operator/device-plans (Phase 156).",
    )


@router.get("/migration/integration-status")
async def integration_migration_status(
    pool=Depends(get_db_pool),
    claims=Depends(require_operator),
):
    async with pool.acquire() as conn:
        old_count = await conn.fetchval(
            "SELECT COUNT(DISTINCT tenant_id) FROM integrations WHERE enabled = TRUE"
        )
        new_count = await conn.fetchval(
            "SELECT COUNT(DISTINCT tenant_id) FROM notification_channels WHERE is_enabled = TRUE"
        )
        total_old_integrations = await conn.fetchval(
            "SELECT COUNT(*) FROM integrations WHERE enabled = TRUE"
        )
        total_new_channels = await conn.fetchval(
            "SELECT COUNT(*) FROM notification_channels WHERE is_enabled = TRUE"
        )
    return {
        "tenants_on_old_system": old_count or 0,
        "tenants_on_new_system": new_count or 0,
        "total_old_integrations": total_old_integrations or 0,
        "total_new_channels": total_new_channels or 0,
        "migration_complete": (old_count or 0) == 0,
    }




@router.get("/tenants")
async def list_tenants(
    request: Request,
    status: str = Query("ACTIVE"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List all tenants (operator only)."""
    user = get_user()
    ip, user_agent = get_request_metadata(request)
    pool = await get_pool()

    async with operator_connection(pool) as conn:
        rows = await conn.fetch(
            """
            SELECT tenant_id, name, status, contact_email, contact_name,
                   metadata, created_at, updated_at
            FROM tenants
            WHERE ($1 = 'ALL' OR status = $1)
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            """,
            status,
            limit,
            offset,
        )

        total = await conn.fetchval(
            "SELECT COUNT(*) FROM tenants WHERE ($1 = 'ALL' OR status = $1)",
            status,
        )

    async with pool.acquire() as conn:
        await log_operator_access(
            conn,
            user_id=user["sub"],
            action="list_tenants",
            tenant_filter=None,
            ip_address=ip,
            user_agent=user_agent,
            rls_bypassed=True,
        )

    return {
        "tenants": [dict(r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/tenants/stats/summary")
async def get_all_tenants_stats(request: Request):
    """Get summary stats for all active tenants (operator only)."""
    user = get_user()
    ip, user_agent = get_request_metadata(request)
    pool = await get_pool()

    async with operator_connection(pool) as conn:
        rows = await conn.fetch(
            """
            SELECT
                t.tenant_id,
                t.name,
                t.status,
                t.created_at,
                COALESCE(d.device_count, 0) AS device_count,
                COALESCE(d.online_count, 0) AS online_count,
                COALESCE(a.open_alerts, 0) AS open_alerts,
                d.last_activity
            FROM tenants t
            LEFT JOIN (
                SELECT
                    tenant_id,
                    COUNT(*) AS device_count,
                    COUNT(*) FILTER (WHERE status = 'ONLINE') AS online_count,
                    MAX(last_seen_at) AS last_activity
                FROM device_state
                GROUP BY tenant_id
            ) d ON d.tenant_id = t.tenant_id
            LEFT JOIN (
                SELECT tenant_id, COUNT(*) AS open_alerts
                FROM fleet_alert
                WHERE status = 'OPEN'
                GROUP BY tenant_id
            ) a ON a.tenant_id = t.tenant_id
            WHERE t.status != 'DELETED'
            ORDER BY t.created_at DESC
            """
        )

    async with pool.acquire() as conn:
        await log_operator_access(
            conn,
            user_id=user["sub"],
            action="get_all_tenants_stats",
            tenant_filter=None,
            ip_address=ip,
            user_agent=user_agent,
            rls_bypassed=True,
        )

    return {
        "tenants": [
            {
                "tenant_id": r["tenant_id"],
                "name": r["name"],
                "status": r["status"],
                "device_count": r["device_count"],
                "online_count": r["online_count"],
                "open_alerts": r["open_alerts"],
                "last_activity": r["last_activity"].isoformat()
                if r["last_activity"]
                else None,
                "created_at": r["created_at"].isoformat(),
            }
            for r in rows
        ]
    }


@router.get("/tenants/{tenant_id}")
async def get_tenant(request: Request, tenant_id: str):
    """Get tenant details (operator only)."""
    user = get_user()
    ip, user_agent = get_request_metadata(request)
    pool = await get_pool()

    async with operator_connection(pool) as conn:
        row = await conn.fetchrow(
            """
            SELECT tenant_id, name, status, contact_email, contact_name,
                   legal_name, phone, industry, company_size,
                   address_line1, address_line2, city, state_province, postal_code, country,
                   data_residency_region, support_tier, sla_level,
                   stripe_customer_id, billing_email,
                   metadata, created_at, updated_at
            FROM tenants
            WHERE tenant_id = $1
            """,
            tenant_id,
        )

    if not row:
        raise HTTPException(404, "Tenant not found")

    async with pool.acquire() as conn:
        await log_operator_access(
            conn,
            user_id=user["sub"],
            action="get_tenant",
            tenant_filter=tenant_id,
            ip_address=ip,
            user_agent=user_agent,
            rls_bypassed=True,
        )

    result = dict(row)
    if isinstance(result.get("metadata"), str):
        result["metadata"] = json.loads(result["metadata"])
    if result.get("sla_level") is not None:
        result["sla_level"] = float(result["sla_level"])
    return result


@router.post("/subscriptions", status_code=201)
async def create_subscription(data: SubscriptionCreate, request: Request):
    """Create a new subscription for a tenant."""
    raise HTTPException(
        410,
        "Legacy subscriptions are deprecated. Use /operator/device-subscriptions and /operator/tenants/{tenant_id}/tier (Phase 156).",
    )


@router.get("/subscriptions")
async def list_subscriptions(
    request: Request,
    tenant_id: Optional[str] = None,
    subscription_type: Optional[str] = None,
    status: Optional[str] = None,
    expiring_days: Optional[int] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List subscriptions with optional filters."""
    raise HTTPException(
        410,
        "Legacy subscriptions are deprecated. Use /operator/device-subscriptions (Phase 156).",
    )


@router.get("/subscriptions/expiring-notifications")
async def list_expiring_notifications(
    status: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
):
    """List subscription expiry notification records."""
    raise HTTPException(
        410,
        "Legacy subscription notifications are deprecated in the Phase 156 model.",
    )


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
            subscription_id,
        )

        if not row:
            raise HTTPException(404, "Subscription not found")

        devices = await conn.fetch(
            """
            SELECT d.device_id, d.site_id, d.status, ds.last_seen_at
            FROM device_registry d
            LEFT JOIN device_state ds ON d.tenant_id = ds.tenant_id AND d.device_id = ds.device_id
            WHERE d.subscription_id = $1
            ORDER BY d.device_id
            """,
            subscription_id,
        )

        children = []
        if row["subscription_type"] == "MAIN":
            child_rows = await conn.fetch(
                """
                SELECT subscription_id, device_limit, active_device_count, status
                FROM subscriptions
                WHERE parent_subscription_id = $1
                """,
                subscription_id,
            )
            children = [dict(r) for r in child_rows]

        return {
            **dict(row),
            "term_start": row["term_start"].isoformat() if row["term_start"] else None,
            "term_end": row["term_end"].isoformat() if row["term_end"] else None,
            "devices": [
                {
                    "device_id": d["device_id"],
                    "site_id": d["site_id"],
                    "status": d["status"],
                    "last_seen_at": d["last_seen_at"].isoformat() if d["last_seen_at"] else None,
                }
                for d in devices
            ],
            "child_subscriptions": children,
        }


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
        current = await conn.fetchrow(
            "SELECT * FROM subscriptions WHERE subscription_id = $1",
            subscription_id,
        )
        if not current:
            raise HTTPException(404, "Subscription not found")

        previous_state = dict(current)
        existing_plan_id = current.get("plan_id")

        updates = []
        params = []
        param_idx = 1

        if data.device_limit is not None:
            updates.append(f"device_limit = ${param_idx}")
            params.append(data.device_limit)
            param_idx += 1

        if data.plan_id is not None:
            updates.append(f"plan_id = ${param_idx}")
            params.append(data.plan_id)
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

        allocations_synced: list[dict] = []
        async with conn.transaction():
            row = await conn.fetchrow(query, *params)
            new_state = dict(row)

            # If plan_id changed, auto-sync tier allocations from plan defaults.
            if (
                data.plan_id
                and data.plan_id != existing_plan_id
                and isinstance(data.plan_id, str)
                and data.plan_id.strip()
            ):
                defaults = await conn.fetch(
                    "SELECT tier_id, slot_limit FROM plan_tier_defaults WHERE plan_id = $1",
                    data.plan_id,
                )
                for default in defaults:
                    await conn.execute(
                        """
                        INSERT INTO subscription_tier_allocations (subscription_id, tier_id, slot_limit)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (subscription_id, tier_id)
                        DO UPDATE SET slot_limit = EXCLUDED.slot_limit, updated_at = NOW()
                        """,
                        subscription_id,
                        default["tier_id"],
                        default["slot_limit"],
                    )
                    allocations_synced.append(
                        {"tier_id": default["tier_id"], "slot_limit": default["slot_limit"]}
                    )

        if data.status and data.status != current["status"]:
            event_type = f"STATUS_{data.status}"
        elif data.plan_id is not None and data.plan_id != existing_plan_id:
            event_type = "PLAN_CHANGED"
        elif data.device_limit is not None and data.device_limit != current["device_limit"]:
            event_type = "LIMIT_CHANGED"
        elif data.term_end is not None and data.term_end != current["term_end"]:
            event_type = "TERM_EXTENDED"
        else:
            event_type = "UPDATED"

        await conn.execute(
            """
            INSERT INTO subscription_audit
                (tenant_id, event_type, actor_type, actor_id, previous_state, new_state, details, ip_address)
            VALUES ($1, $2, 'admin', $3, $4, $5, $6, $7)
            """,
            current["tenant_id"],
            event_type,
            user.get("sub") if user else None,
            json.dumps(previous_state, default=str),
            json.dumps(new_state, default=str),
            json.dumps(
                {
                    "notes": data.notes,
                    "transaction_ref": data.transaction_ref,
                    "previous_plan_id": existing_plan_id,
                    "new_plan_id": data.plan_id,
                    "allocations_synced": allocations_synced,
                }
            ),
            ip,
        )

        return {"subscription_id": subscription_id, "updated": True, "event_type": event_type}


@router.post("/devices/{device_id}/subscription")
async def assign_device_subscription(
    device_id: str,
    data: DeviceSubscriptionAssign,
    request: Request,
):
    """Assign a device to a subscription."""
    raise HTTPException(
        410,
        "Legacy subscription assignment is deprecated. Use /operator/device-subscriptions and update device plan_id (Phase 156).",
    )


# ── Manual Provisioning Workflow (for offline-payment customers) ──
#
# 1. POST /operator/tenants                                → Create tenant
# 2. POST /operator/users                                  → Create Keycloak admin user
# 3. POST /operator/users/{id}/send-welcome-email           → Send password-set email
# 4. POST /operator/subscriptions                           → Create subscription (set plan_id)
# 5. POST /operator/subscriptions/{id}/sync-tier-allocations → Seed tier slot limits
#    OR POST /operator/subscriptions/{id}/tier-allocations   → Set custom allocations
# 6. Customer logs in → assigns devices to tiers
#
# Plan management workflow:
# - GET  /operator/plans                                   → List all plans
# - POST /operator/plans                                   → Create new plan
# - PUT  /operator/plans/{plan_id}                          → Update plan name/limits/pricing
# - GET  /operator/plans/{plan_id}/tier-defaults            → View plan's default tier allocations
# - PUT  /operator/plans/{plan_id}/tier-defaults            → Replace plan's default tier allocations
#
# Adjustment workflow:
# - PATCH /operator/subscriptions/{id} {plan_id: "pro"}      → Changes plan + auto-syncs tiers
# - PUT /operator/subscriptions/{id}/tier-allocations/{tier_id} → Adjust slot limit
# - POST /operator/subscriptions/{id}/reconcile-tiers        → Fix drifted slot counts
# - PUT /operator/devices/tier                               → Override device tier (bypass slot limits)
#
# ── Subscription Tier Allocations ─────────────────────────────


class TierAllocationCreate(BaseModel):
    tier_id: int
    slot_limit: int = Field(..., ge=0)


class TierAllocationUpdate(BaseModel):
    slot_limit: Optional[int] = Field(None, ge=0)
    slots_used: Optional[int] = Field(None, ge=0)  # manual override for reconciliation


@router.get("/subscriptions/{subscription_id}/tier-allocations")
async def list_tier_allocations(subscription_id: str):
    """List all tier allocations for a subscription."""
    pool = await get_pool()
    async with operator_connection(pool) as conn:
        sub = await conn.fetchrow(
            "SELECT subscription_id, tenant_id, plan_id FROM subscriptions WHERE subscription_id = $1",
            subscription_id,
        )
        if not sub:
            raise HTTPException(404, "Subscription not found")

        rows = await conn.fetch(
            """
            SELECT sta.id, sta.subscription_id, sta.tier_id, dt.name, dt.display_name,
                   sta.slot_limit, sta.slots_used, sta.created_at, sta.updated_at
            FROM subscription_tier_allocations sta
            JOIN device_tiers dt ON dt.tier_id = sta.tier_id
            WHERE sta.subscription_id = $1
            ORDER BY dt.sort_order
            """,
            subscription_id,
        )

    return {
        "subscription_id": subscription_id,
        "tenant_id": sub["tenant_id"],
        "plan_id": sub["plan_id"],
        "allocations": [
            {
                **dict(r),
                "slots_available": r["slot_limit"] - r["slots_used"],
                "created_at": r["created_at"].isoformat() + "Z" if r["created_at"] else None,
                "updated_at": r["updated_at"].isoformat() + "Z" if r["updated_at"] else None,
            }
            for r in rows
        ],
    }


@router.post("/subscriptions/{subscription_id}/tier-allocations", status_code=201)
async def create_tier_allocation(
    subscription_id: str,
    data: TierAllocationCreate,
    request: Request,
    _: None = Depends(require_operator_admin),
):
    """Manually add a tier allocation to a subscription."""
    pool = await get_pool()
    user = get_user()
    ip, _ = get_request_metadata(request)

    async with operator_connection(pool) as conn:
        sub = await conn.fetchrow(
            "SELECT subscription_id, tenant_id FROM subscriptions WHERE subscription_id = $1",
            subscription_id,
        )
        if not sub:
            raise HTTPException(404, "Subscription not found")

        tier = await conn.fetchrow(
            "SELECT tier_id, display_name FROM device_tiers WHERE tier_id = $1",
            data.tier_id,
        )
        if not tier:
            raise HTTPException(404, "Device tier not found")

        try:
            row = await conn.fetchrow(
                """
                INSERT INTO subscription_tier_allocations (subscription_id, tier_id, slot_limit)
                VALUES ($1, $2, $3)
                RETURNING id, subscription_id, tier_id, slot_limit, slots_used, created_at, updated_at
                """,
                subscription_id,
                data.tier_id,
                data.slot_limit,
            )
        except Exception as exc:
            if "unique" in str(exc).lower():
                raise HTTPException(
                    409,
                    f"Tier allocation already exists for tier {tier['display_name']}. Use PUT to update.",
                )
            raise

        await conn.execute(
            """
            INSERT INTO subscription_audit
                (tenant_id, event_type, actor_type, actor_id, details, ip_address)
            VALUES ($1, 'TIER_ALLOCATION_CREATED', 'admin', $2, $3, $4)
            """,
            sub["tenant_id"],
            user.get("sub") if user else None,
            json.dumps(
                {
                    "subscription_id": subscription_id,
                    "tier_id": data.tier_id,
                    "tier_name": tier["display_name"],
                    "slot_limit": data.slot_limit,
                }
            ),
            ip,
        )

    return {
        **dict(row),
        "created_at": row["created_at"].isoformat() + "Z" if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() + "Z" if row["updated_at"] else None,
    }


@router.put("/subscriptions/{subscription_id}/tier-allocations/{tier_id}")
async def update_tier_allocation(
    subscription_id: str,
    tier_id: int,
    data: TierAllocationUpdate,
    request: Request,
    _: None = Depends(require_operator_admin),
):
    """Manually adjust a tier allocation (slot limit or slots_used for reconciliation)."""
    pool = await get_pool()
    user = get_user()
    ip, _ = get_request_metadata(request)

    async with operator_connection(pool) as conn:
        existing = await conn.fetchrow(
            """
            SELECT sta.id, sta.slot_limit, sta.slots_used, s.tenant_id, dt.display_name
            FROM subscription_tier_allocations sta
            JOIN subscriptions s ON s.subscription_id = sta.subscription_id
            JOIN device_tiers dt ON dt.tier_id = sta.tier_id
            WHERE sta.subscription_id = $1 AND sta.tier_id = $2
            """,
            subscription_id,
            tier_id,
        )
        if not existing:
            raise HTTPException(404, "Tier allocation not found")

        updates = []
        params = []
        idx = 1
        changes = {}

        if data.slot_limit is not None:
            updates.append(f"slot_limit = ${idx}")
            params.append(data.slot_limit)
            changes["slot_limit"] = {
                "old": existing["slot_limit"],
                "new": data.slot_limit,
            }
            idx += 1

        if data.slots_used is not None:
            updates.append(f"slots_used = ${idx}")
            params.append(data.slots_used)
            changes["slots_used"] = {
                "old": existing["slots_used"],
                "new": data.slots_used,
            }
            idx += 1

        if not updates:
            raise HTTPException(400, "No fields to update")

        updates.append("updated_at = NOW()")
        params.extend([subscription_id, tier_id])

        await conn.execute(
            f"UPDATE subscription_tier_allocations SET {', '.join(updates)} WHERE subscription_id = ${idx} AND tier_id = ${idx + 1}",
            *params,
        )

        await conn.execute(
            """
            INSERT INTO subscription_audit
                (tenant_id, event_type, actor_type, actor_id, details, ip_address)
            VALUES ($1, 'TIER_ALLOCATION_UPDATED', 'admin', $2, $3, $4)
            """,
            existing["tenant_id"],
            user.get("sub") if user else None,
            json.dumps(
                {
                    "subscription_id": subscription_id,
                    "tier_id": tier_id,
                    "tier_name": existing["display_name"],
                    "changes": changes,
                }
            ),
            ip,
        )

    return {"status": "ok", "changes": changes}


@router.delete("/subscriptions/{subscription_id}/tier-allocations/{tier_id}")
async def delete_tier_allocation(
    subscription_id: str,
    tier_id: int,
    request: Request,
    _: None = Depends(require_operator_admin),
):
    """Remove a tier allocation from a subscription."""
    pool = await get_pool()
    user = get_user()
    ip, _ = get_request_metadata(request)

    async with operator_connection(pool) as conn:
        existing = await conn.fetchrow(
            """
            SELECT sta.slots_used, s.tenant_id, dt.display_name
            FROM subscription_tier_allocations sta
            JOIN subscriptions s ON s.subscription_id = sta.subscription_id
            JOIN device_tiers dt ON dt.tier_id = sta.tier_id
            WHERE sta.subscription_id = $1 AND sta.tier_id = $2
            """,
            subscription_id,
            tier_id,
        )
        if not existing:
            raise HTTPException(404, "Tier allocation not found")

        if existing["slots_used"] > 0:
            raise HTTPException(
                409,
                f"Cannot delete: {existing['slots_used']} devices are still assigned to {existing['display_name']} tier. Reassign them first.",
            )

        await conn.execute(
            "DELETE FROM subscription_tier_allocations WHERE subscription_id = $1 AND tier_id = $2",
            subscription_id,
            tier_id,
        )

        await conn.execute(
            """
            INSERT INTO subscription_audit
                (tenant_id, event_type, actor_type, actor_id, details, ip_address)
            VALUES ($1, 'TIER_ALLOCATION_DELETED', 'admin', $2, $3, $4)
            """,
            existing["tenant_id"],
            user.get("sub") if user else None,
            json.dumps(
                {
                    "subscription_id": subscription_id,
                    "tier_id": tier_id,
                    "tier_name": existing["display_name"],
                }
            ),
            ip,
        )

    return {"status": "ok"}


# ── Subscription Plan Management ─────────────────────────────


class PlanCreate(BaseModel):
    plan_id: str = Field(..., max_length=50, pattern=r"^[a-z0-9_-]+$")
    name: str = Field(..., max_length=100)
    description: str = ""
    device_limit: int = Field(0, ge=0)
    limits: dict = Field(default_factory=dict)
    stripe_price_id: Optional[str] = None
    stripe_annual_price_id: Optional[str] = None
    monthly_price_cents: Optional[int] = None
    annual_price_cents: Optional[int] = None
    is_active: bool = True
    sort_order: int = 0


class PlanUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    device_limit: Optional[int] = Field(None, ge=0)
    limits: Optional[dict] = None
    stripe_price_id: Optional[str] = None
    stripe_annual_price_id: Optional[str] = None
    monthly_price_cents: Optional[int] = None
    annual_price_cents: Optional[int] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class PlanTierDefaultEntry(BaseModel):
    tier_id: int
    slot_limit: int = Field(..., ge=0)


@router.get("/plans")
async def list_plans():
    """List all subscription plans (including inactive)."""
    pool = await get_pool()
    async with operator_connection(pool) as conn:
        rows = await conn.fetch("SELECT * FROM subscription_plans ORDER BY sort_order, plan_id")
    out = []
    for r in rows:
        d = dict(r)
        limits_val = d.get("limits")
        if isinstance(limits_val, str):
            try:
                d["limits"] = json.loads(limits_val)
            except Exception:
                d["limits"] = {}
        out.append(d)
    return {"plans": out}


@router.post("/plans", status_code=201)
async def create_plan(
    data: PlanCreate,
    _: None = Depends(require_operator_admin),
):
    """Create a new subscription plan."""
    pool = await get_pool()
    async with operator_connection(pool) as conn:
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO subscription_plans
                    (plan_id, name, description, device_limit, limits,
                     stripe_price_id, stripe_annual_price_id,
                     monthly_price_cents, annual_price_cents,
                     is_active, sort_order)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING *
                """,
                data.plan_id,
                data.name,
                data.description,
                data.device_limit,
                json.dumps(data.limits),
                data.stripe_price_id,
                data.stripe_annual_price_id,
                data.monthly_price_cents,
                data.annual_price_cents,
                data.is_active,
                data.sort_order,
            )
        except Exception as exc:
            if "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
                raise HTTPException(409, f"Plan '{data.plan_id}' already exists")
            raise
    d = dict(row)
    if isinstance(d.get("limits"), str):
        try:
            d["limits"] = json.loads(d["limits"])
        except Exception:
            d["limits"] = {}
    return d


@router.put("/plans/{plan_id}")
async def update_plan(
    plan_id: str,
    data: PlanUpdate,
    _: None = Depends(require_operator_admin),
):
    """Update a subscription plan.

    Changing limits or device_limit here does NOT retroactively affect existing
    subscriptions. To cascade: PATCH the subscription's plan_id or use
    POST /subscriptions/{id}/sync-tier-allocations.
    """
    pool = await get_pool()
    async with operator_connection(pool) as conn:
        existing = await conn.fetchrow(
            "SELECT plan_id FROM subscription_plans WHERE plan_id = $1", plan_id
        )
        if not existing:
            raise HTTPException(404, "Plan not found")

        updates = []
        params = []
        idx = 1

        dumped = data.model_dump(exclude_unset=True)
        for field in [
            "name",
            "description",
            "device_limit",
            "stripe_price_id",
            "stripe_annual_price_id",
            "monthly_price_cents",
            "annual_price_cents",
            "is_active",
            "sort_order",
        ]:
            if field in dumped:
                updates.append(f"{field} = ${idx}")
                params.append(dumped[field])
                idx += 1

        if "limits" in dumped:
            updates.append(f"limits = ${idx}")
            params.append(json.dumps(dumped["limits"]))
            idx += 1

        if not updates:
            raise HTTPException(400, "No fields to update")

        updates.append("updated_at = NOW()")
        params.append(plan_id)

        await conn.execute(
            f"UPDATE subscription_plans SET {', '.join(updates)} WHERE plan_id = ${idx}",
            *params,
        )

    return {"status": "ok", "plan_id": plan_id}


@router.get("/plans/{plan_id}/tier-defaults")
async def list_plan_tier_defaults(plan_id: str):
    """List the default tier allocations for a plan."""
    pool = await get_pool()
    async with operator_connection(pool) as conn:
        plan = await conn.fetchrow(
            "SELECT plan_id FROM subscription_plans WHERE plan_id = $1", plan_id
        )
        if not plan:
            raise HTTPException(404, "Plan not found")

        rows = await conn.fetch(
            """
            SELECT ptd.id, ptd.plan_id, ptd.tier_id, dt.name, dt.display_name, ptd.slot_limit
            FROM plan_tier_defaults ptd
            JOIN device_tiers dt ON dt.tier_id = ptd.tier_id
            WHERE ptd.plan_id = $1
            ORDER BY dt.sort_order
            """,
            plan_id,
        )
    return {"plan_id": plan_id, "tier_defaults": [dict(r) for r in rows]}


@router.put("/plans/{plan_id}/tier-defaults")
async def set_plan_tier_defaults(
    plan_id: str,
    data: list[PlanTierDefaultEntry],
    _: None = Depends(require_operator_admin),
):
    """Replace all tier defaults for a plan.

    Accepts a list of {tier_id, slot_limit} entries. Existing defaults
    for this plan are deleted and replaced.
    This does NOT affect existing subscriptions — only new subscriptions
    or manual sync operations will use the updated defaults.
    """
    pool = await get_pool()
    async with operator_connection(pool) as conn:
        plan = await conn.fetchrow(
            "SELECT plan_id FROM subscription_plans WHERE plan_id = $1", plan_id
        )
        if not plan:
            raise HTTPException(404, "Plan not found")

        async with conn.transaction():
            await conn.execute("DELETE FROM plan_tier_defaults WHERE plan_id = $1", plan_id)
            for entry in data:
                await conn.execute(
                    """
                    INSERT INTO plan_tier_defaults (plan_id, tier_id, slot_limit)
                    VALUES ($1, $2, $3)
                    """,
                    plan_id,
                    entry.tier_id,
                    entry.slot_limit,
                )

    return {
        "status": "ok",
        "plan_id": plan_id,
        "tier_defaults": [e.model_dump() for e in data],
    }


@router.post("/subscriptions/{subscription_id}/sync-tier-allocations")
async def sync_tier_allocations_from_plan(
    subscription_id: str,
    request: Request,
    _: None = Depends(require_operator_admin),
):
    """Sync tier allocations from plan_tier_defaults for this subscription's plan_id.

    Manual equivalent of the Stripe webhook tier allocation sync.
    Creates new allocations or updates slot_limit on existing ones.
    Does NOT reduce slots_used (preserves current device assignments).
    """
    pool = await get_pool()
    user = get_user()
    ip, _ = get_request_metadata(request)

    async with operator_connection(pool) as conn:
        sub = await conn.fetchrow(
            "SELECT subscription_id, tenant_id, plan_id FROM subscriptions WHERE subscription_id = $1",
            subscription_id,
        )
        if not sub:
            raise HTTPException(404, "Subscription not found")
        if not sub["plan_id"]:
            raise HTTPException(400, "Subscription has no plan_id set. Set plan_id first via PATCH.")

        defaults = await conn.fetch(
            "SELECT tier_id, slot_limit FROM plan_tier_defaults WHERE plan_id = $1",
            sub["plan_id"],
        )
        if not defaults:
            raise HTTPException(404, f"No tier defaults found for plan '{sub['plan_id']}'")

        synced: list[dict] = []
        async with conn.transaction():
            for default in defaults:
                await conn.execute(
                    """
                    INSERT INTO subscription_tier_allocations (subscription_id, tier_id, slot_limit)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (subscription_id, tier_id)
                    DO UPDATE SET slot_limit = EXCLUDED.slot_limit, updated_at = NOW()
                    """,
                    subscription_id,
                    default["tier_id"],
                    default["slot_limit"],
                )
                synced.append({"tier_id": default["tier_id"], "slot_limit": default["slot_limit"]})

            await conn.execute(
                """
                INSERT INTO subscription_audit
                    (tenant_id, event_type, actor_type, actor_id, details, ip_address)
                VALUES ($1, 'TIER_ALLOCATIONS_SYNCED', 'admin', $2, $3, $4)
                """,
                sub["tenant_id"],
                user.get("sub") if user else None,
                json.dumps(
                    {
                        "subscription_id": subscription_id,
                        "plan_id": sub["plan_id"],
                        "allocations_synced": synced,
                    }
                ),
                ip,
            )

    return {"status": "ok", "plan_id": sub["plan_id"], "allocations_synced": synced}


@router.post("/subscriptions/{subscription_id}/reconcile-tiers")
async def reconcile_tier_slots(
    subscription_id: str,
    request: Request,
    _: None = Depends(require_operator_admin),
):
    """Recount actual devices per tier and fix slots_used."""
    pool = await get_pool()
    user = get_user()
    ip, _ = get_request_metadata(request)

    async with operator_connection(pool) as conn:
        sub = await conn.fetchrow(
            "SELECT subscription_id, tenant_id FROM subscriptions WHERE subscription_id = $1",
            subscription_id,
        )
        if not sub:
            raise HTTPException(404, "Subscription not found")

        actual_counts = await conn.fetch(
            """
            SELECT tier_id, COUNT(*) as actual_count
            FROM device_registry
            WHERE subscription_id = $1 AND tier_id IS NOT NULL
            GROUP BY tier_id
            """,
            subscription_id,
        )
        count_map = {r["tier_id"]: r["actual_count"] for r in actual_counts}

        allocations = await conn.fetch(
            "SELECT tier_id, slots_used FROM subscription_tier_allocations WHERE subscription_id = $1",
            subscription_id,
        )

        corrections: list[dict] = []
        async with conn.transaction():
            for alloc in allocations:
                actual = count_map.get(alloc["tier_id"], 0)
                if actual != alloc["slots_used"]:
                    await conn.execute(
                        """
                        UPDATE subscription_tier_allocations
                        SET slots_used = $1, updated_at = NOW()
                        WHERE subscription_id = $2 AND tier_id = $3
                        """,
                        actual,
                        subscription_id,
                        alloc["tier_id"],
                    )
                    corrections.append(
                        {
                            "tier_id": alloc["tier_id"],
                            "old_slots_used": alloc["slots_used"],
                            "actual_count": actual,
                        }
                    )

            if corrections:
                await conn.execute(
                    """
                    INSERT INTO subscription_audit
                        (tenant_id, event_type, actor_type, actor_id, details, ip_address)
                    VALUES ($1, 'TIER_SLOTS_RECONCILED', 'admin', $2, $3, $4)
                    """,
                    sub["tenant_id"],
                    user.get("sub") if user else None,
                    json.dumps({"subscription_id": subscription_id, "corrections": corrections}),
                    ip,
                )

    return {
        "status": "ok",
        "corrections": corrections,
        "message": f"Reconciled {len(corrections)} tier(s)" if corrections else "All slot counts are accurate",
    }


class OperatorTierAssignment(BaseModel):
    device_id: str
    tenant_id: str
    tier_id: Optional[int] = None  # None = remove tier


@router.put("/devices/tier")
async def operator_assign_device_tier(
    data: OperatorTierAssignment,
    request: Request,
    _: None = Depends(require_operator_admin),
):
    """Assign or remove a device tier as operator (bypasses slot limit checks)."""
    pool = await get_pool()
    user = get_user()
    ip, _ = get_request_metadata(request)

    async with operator_connection(pool) as conn:
        device = await conn.fetchrow(
            """
            SELECT device_id, subscription_id, tier_id
            FROM device_registry
            WHERE device_id = $1 AND tenant_id = $2
            """,
            data.device_id,
            data.tenant_id,
        )
        if not device:
            raise HTTPException(404, "Device not found")

        old_tier_id = device["tier_id"]
        subscription_id = device["subscription_id"]

        # No-op assignment should not drift slot counts.
        if old_tier_id == data.tier_id:
            return {
                "status": "ok",
                "device_id": data.device_id,
                "old_tier_id": old_tier_id,
                "new_tier_id": data.tier_id,
            }

        async with conn.transaction():
            if old_tier_id is not None and subscription_id:
                await conn.execute(
                    """
                    UPDATE subscription_tier_allocations
                    SET slots_used = GREATEST(slots_used - 1, 0), updated_at = NOW()
                    WHERE subscription_id = $1 AND tier_id = $2
                    """,
                    subscription_id,
                    old_tier_id,
                )

            await conn.execute(
                "UPDATE device_registry SET tier_id = $1 WHERE device_id = $2 AND tenant_id = $3",
                data.tier_id,
                data.device_id,
                data.tenant_id,
            )

            if data.tier_id is not None and subscription_id:
                await conn.execute(
                    """
                    INSERT INTO subscription_tier_allocations (subscription_id, tier_id, slot_limit, slots_used)
                    VALUES ($1, $2, 0, 1)
                    ON CONFLICT (subscription_id, tier_id)
                    DO UPDATE SET slots_used = subscription_tier_allocations.slots_used + 1, updated_at = NOW()
                    """,
                    subscription_id,
                    data.tier_id,
                )

            await conn.execute(
                """
                INSERT INTO subscription_audit
                    (tenant_id, event_type, actor_type, actor_id, details, ip_address)
                VALUES ($1, 'OPERATOR_TIER_ASSIGNMENT', 'admin', $2, $3, $4)
                """,
                data.tenant_id,
                user.get("sub") if user else None,
                json.dumps(
                    {
                        "device_id": data.device_id,
                        "old_tier_id": old_tier_id,
                        "new_tier_id": data.tier_id,
                    }
                ),
                ip,
            )

    return {
        "status": "ok",
        "device_id": data.device_id,
        "old_tier_id": old_tier_id,
        "new_tier_id": data.tier_id,
    }


@router.get("/subscriptions/expiring")
async def list_expiring_subscriptions(
    request: Request,
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(50, ge=1, le=200),
):
    """List subscriptions expiring within N days (operator only)."""
    user = get_user()
    ip, user_agent = get_request_metadata(request)

    pool = await get_pool()
    async with operator_connection(pool) as conn:
        rows = await conn.fetch(
            """
            SELECT
                s.tenant_id,
                t.name as tenant_name,
                t.contact_email,
                s.device_limit,
                s.active_device_count,
                s.term_end,
                s.status,
                EXTRACT(DAY FROM s.term_end - now()) as days_remaining
            FROM subscriptions s
            JOIN tenants t ON t.tenant_id = s.tenant_id
            WHERE s.status = 'ACTIVE'
              AND s.term_end <= now() + ($1 || ' days')::interval
              AND s.term_end > now()
            ORDER BY s.term_end ASC
            LIMIT $2
            """,
            str(days),
            limit,
        )

    async with pool.acquire() as conn:
        await log_operator_access(
            conn,
            user_id=user["sub"],
            action="list_expiring_subscriptions",
            tenant_filter=None,
            ip_address=ip,
            user_agent=user_agent,
            rls_bypassed=True,
        )

    return {
        "subscriptions": [
            {
                "tenant_id": row["tenant_id"],
                "tenant_name": row["tenant_name"],
                "contact_email": row["contact_email"],
                "device_limit": row["device_limit"],
                "active_device_count": row["active_device_count"],
                "term_end": row["term_end"].isoformat(),
                "days_remaining": int(row["days_remaining"]),
            }
            for row in rows
        ],
        "count": len(rows),
    }


@router.get("/subscriptions/summary")
async def get_subscriptions_summary(request: Request):
    """Get subscription summary statistics (operator only)."""
    user = get_user()
    ip, user_agent = get_request_metadata(request)
    pool = await get_pool()
    async with operator_connection(pool) as conn:
        status_counts = await conn.fetch(
            """
            SELECT status, COUNT(*) as count
            FROM subscriptions
            GROUP BY status
            """
        )

        totals = await conn.fetchrow(
            """
            SELECT
                SUM(device_limit) as total_limit,
                SUM(active_device_count) as total_devices
            FROM subscriptions
            WHERE status IN ('TRIAL', 'ACTIVE', 'GRACE')
            """
        )

        expiring_count = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM subscriptions
            WHERE status = 'ACTIVE'
              AND term_end <= now() + interval '30 days'
              AND term_end > now()
            """
        )

    async with pool.acquire() as conn:
        await log_operator_access(
            conn,
            user_id=user["sub"],
            action="get_subscriptions_summary",
            tenant_filter=None,
            ip_address=ip,
            user_agent=user_agent,
            rls_bypassed=True,
        )

    return {
        "by_status": {row["status"]: row["count"] for row in status_counts},
        "total_device_limit": totals["total_limit"] or 0,
        "total_active_devices": totals["total_devices"] or 0,
        "expiring_30_days": expiring_count,
    }


@router.post("/tenants", status_code=201)
async def create_tenant(
    request: Request,
    tenant: TenantCreate,
    _: None = Depends(require_operator_admin),
):
    """Create a new tenant (operator_admin only)."""
    user = get_user()
    ip, user_agent = get_request_metadata(request)
    pool = await get_pool()

    if not re.match(r"^[a-z0-9]([a-z0-9\-]*[a-z0-9])?$", tenant.tenant_id):
        raise HTTPException(
            400,
            "tenant_id must be lowercase alphanumeric with hyphens, cannot start/end with hyphen",
        )
    if len(tenant.tenant_id) > 64:
        raise HTTPException(400, "tenant_id must be 64 characters or less")

    async with operator_connection(pool) as conn:
        exists = await conn.fetchval(
            "SELECT 1 FROM tenants WHERE tenant_id = $1",
            tenant.tenant_id,
        )
        if exists:
            raise HTTPException(409, "Tenant already exists")

        await conn.execute(
            """
            INSERT INTO tenants (
                tenant_id, name, contact_email, contact_name,
                legal_name, phone, industry, company_size,
                address_line1, address_line2, city, state_province, postal_code, country,
                data_residency_region, support_tier, sla_level, billing_email,
                metadata
            )
            VALUES (
                $1, $2, $3, $4,
                $5, $6, $7, $8,
                $9, $10, $11, $12, $13, $14,
                $15, $16, $17, $18,
                $19::jsonb
            )
            """,
            tenant.tenant_id,
            tenant.name,
            tenant.contact_email,
            tenant.contact_name,
            tenant.legal_name,
            tenant.phone,
            tenant.industry,
            tenant.company_size,
            tenant.address_line1,
            tenant.address_line2,
            tenant.city,
            tenant.state_province,
            tenant.postal_code,
            tenant.country,
            tenant.data_residency_region,
            tenant.support_tier,
            tenant.sla_level,
            tenant.billing_email,
            json.dumps(tenant.metadata or {}),
        )

    async with pool.acquire() as conn:
        await log_operator_access(
            conn,
            user_id=user["sub"],
            action="create_tenant",
            tenant_filter=tenant.tenant_id,
            ip_address=ip,
            user_agent=user_agent,
            rls_bypassed=True,
        )

    return {
        "tenant_id": tenant.tenant_id,
        "status": "created",
    }


@router.patch("/tenants/{tenant_id}")
async def update_tenant(
    request: Request,
    tenant_id: str,
    update: TenantUpdate,
    _: None = Depends(require_operator_admin),
):
    """Update tenant (operator_admin only)."""
    user = get_user()
    ip, user_agent = get_request_metadata(request)
    pool = await get_pool()

    updates = []
    params = [tenant_id]
    param_num = 2

    for field in [
        "name",
        "contact_email",
        "contact_name",
        "status",
        "legal_name",
        "phone",
        "industry",
        "company_size",
        "address_line1",
        "address_line2",
        "city",
        "state_province",
        "postal_code",
        "country",
        "data_residency_region",
        "support_tier",
        "sla_level",
        "billing_email",
        "stripe_customer_id",
    ]:
        value = getattr(update, field, None)
        if value is not None:
            updates.append(f"{field} = ${param_num}")
            params.append(value)
            param_num += 1

    if update.metadata is not None:
        updates.append(f"metadata = ${param_num}::jsonb")
        params.append(json.dumps(update.metadata))
        param_num += 1

    if not updates:
        raise HTTPException(400, "No fields to update")

    updates.append("updated_at = now()")

    async with operator_connection(pool) as conn:
        result = await conn.execute(
            f"""
            UPDATE tenants SET {", ".join(updates)}
            WHERE tenant_id = $1 AND status != 'DELETED'
            """,
            *params,
        )

        if result == "UPDATE 0":
            raise HTTPException(404, "Tenant not found")

    async with pool.acquire() as conn:
        await log_operator_access(
            conn,
            user_id=user["sub"],
            action="update_tenant",
            tenant_filter=tenant_id,
            ip_address=ip,
            user_agent=user_agent,
            rls_bypassed=True,
        )

    return {"tenant_id": tenant_id, "status": "updated"}


@router.delete("/tenants/{tenant_id}")
async def delete_tenant(
    request: Request,
    tenant_id: str,
    _: None = Depends(require_operator_admin),
):
    """Soft delete tenant (operator_admin only)."""
    user = get_user()
    ip, user_agent = get_request_metadata(request)
    pool = await get_pool()

    async with operator_connection(pool) as conn:
        result = await conn.execute(
            """
            UPDATE tenants
            SET status = 'DELETED', deleted_at = now(), updated_at = now()
            WHERE tenant_id = $1 AND status != 'DELETED'
            """,
            tenant_id,
        )

        if result == "UPDATE 0":
            raise HTTPException(404, "Tenant not found or already deleted")

    async with pool.acquire() as conn:
        await log_operator_access(
            conn,
            user_id=user["sub"],
            action="delete_tenant",
            tenant_filter=tenant_id,
            ip_address=ip,
            user_agent=user_agent,
            rls_bypassed=True,
        )

    return {"tenant_id": tenant_id, "status": "deleted"}


@router.get("/tenants/{tenant_id}/stats")
async def get_tenant_stats(request: Request, tenant_id: str):
    """Get comprehensive tenant statistics (operator only)."""
    user = get_user()
    ip, user_agent = get_request_metadata(request)
    pool = await get_pool()

    async with operator_connection(pool) as conn:
        tenant = await conn.fetchrow(
            "SELECT tenant_id, name, status FROM tenants WHERE tenant_id = $1",
            tenant_id,
        )
        if not tenant:
            raise HTTPException(404, "Tenant not found")

        stats = await conn.fetchrow(
            """
            SELECT
                (SELECT COUNT(*) FROM device_registry WHERE tenant_id = $1) AS total_devices,
                (SELECT COUNT(*) FROM device_registry WHERE tenant_id = $1 AND status = 'ACTIVE') AS active_devices,
                (SELECT COUNT(*) FROM device_state WHERE tenant_id = $1 AND status = 'ONLINE') AS online_devices,
                (SELECT COUNT(*) FROM device_state WHERE tenant_id = $1 AND status = 'STALE') AS stale_devices,
                (SELECT COUNT(*) FROM fleet_alert WHERE tenant_id = $1 AND status = 'OPEN') AS open_alerts,
                (SELECT COUNT(*) FROM fleet_alert WHERE tenant_id = $1 AND status = 'CLOSED') AS closed_alerts,
                (SELECT COUNT(*) FROM fleet_alert WHERE tenant_id = $1
                 AND created_at >= now() - interval '24 hours') AS alerts_24h,
                (SELECT COUNT(*) FROM integrations WHERE tenant_id = $1) AS total_integrations,
                (SELECT COUNT(*) FROM integrations WHERE tenant_id = $1 AND enabled = true) AS active_integrations,
                (SELECT COUNT(*) FROM alert_rules WHERE tenant_id = $1) AS total_rules,
                (SELECT COUNT(*) FROM alert_rules WHERE tenant_id = $1 AND enabled = true) AS active_rules,
                (SELECT MAX(last_seen_at) FROM device_state WHERE tenant_id = $1) AS last_device_activity,
                (SELECT MAX(created_at) FROM fleet_alert WHERE tenant_id = $1) AS last_alert_created,
                (SELECT COUNT(DISTINCT site_id) FROM device_registry WHERE tenant_id = $1) AS site_count
            """,
            tenant_id,
        )

    async with pool.acquire() as conn:
        await log_operator_access(
            conn,
            user_id=user["sub"],
            action="get_tenant_stats",
            tenant_filter=tenant_id,
            ip_address=ip,
            user_agent=user_agent,
            rls_bypassed=True,
        )

    return {
        "tenant_id": tenant_id,
        "name": tenant["name"],
        "status": tenant["status"],
        "stats": {
            "devices": {
                "total": stats["total_devices"] or 0,
                "active": stats["active_devices"] or 0,
                "online": stats["online_devices"] or 0,
                "stale": stats["stale_devices"] or 0,
            },
            "alerts": {
                "open": stats["open_alerts"] or 0,
                "closed": stats["closed_alerts"] or 0,
                "last_24h": stats["alerts_24h"] or 0,
            },
            "integrations": {
                "total": stats["total_integrations"] or 0,
                "active": stats["active_integrations"] or 0,
            },
            "rules": {
                "total": stats["total_rules"] or 0,
                "active": stats["active_rules"] or 0,
            },
            "sites": stats["site_count"] or 0,
            "last_device_activity": stats["last_device_activity"].isoformat()
            if stats["last_device_activity"]
            else None,
            "last_alert": stats["last_alert_created"].isoformat()
            if stats["last_alert_created"]
            else None,
        },
    }


@router.get("/devices")
async def list_devices(
    request: Request,
    tenant_filter: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    user = get_user()
    ip, user_agent = get_request_metadata(request)
    try:
        p = await get_pool()
        async with p.acquire() as conn:
            await log_operator_access(
                conn,
                user_id=user["sub"],
                action="list_all_devices",
                tenant_filter=tenant_filter,
                ip_address=ip,
                user_agent=user_agent,
                rls_bypassed=True,
            )
        async with operator_connection(p) as conn:
            if tenant_filter:
                devices = await fetch_devices(conn, tenant_filter, limit=limit, offset=offset)
                total = await conn.fetchval(
                    "SELECT COUNT(*) FROM device_state WHERE tenant_id = $1",
                    tenant_filter,
                )
            else:
                devices = await fetch_all_devices(conn, limit=limit, offset=offset)
                total = await conn.fetchval("SELECT COUNT(*) FROM device_state")
    except Exception:
        logger.exception("Failed to fetch operator devices")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {
        "devices": devices,
        "tenant_filter": tenant_filter,
        "limit": limit,
        "offset": offset,
        "total": total or 0,
    }


@router.get("/tenants/{tenant_id}/devices")
async def list_tenant_devices(
    request: Request,
    tenant_id: str,
    unassigned: bool = Query(False),
):
    user = get_user()
    ip, user_agent = get_request_metadata(request)
    try:
        p = await get_pool()
        async with p.acquire() as conn:
            await log_operator_access(
                conn,
                user_id=user["sub"],
                action="list_tenant_devices",
                tenant_filter=tenant_id,
                ip_address=ip,
                user_agent=user_agent,
                rls_bypassed=True,
            )
        async with operator_connection(p) as conn:
            if unassigned:
                devices = await conn.fetch(
                    """
                    SELECT ds.tenant_id, ds.device_id, ds.site_id, ds.status, ds.last_seen_at,
                           ds.state->>'battery_pct' AS battery_pct,
                           ds.state->>'temp_c' AS temp_c,
                           ds.state->>'rssi_dbm' AS rssi_dbm,
                           ds.state->>'snr_db' AS snr_db,
                           dr.subscription_id
                    FROM device_state ds
                    LEFT JOIN device_registry dr
                      ON dr.tenant_id = ds.tenant_id AND dr.device_id = ds.device_id
                    WHERE ds.tenant_id = $1
                      AND dr.subscription_id IS NULL
                    ORDER BY ds.site_id, ds.device_id
                    LIMIT 200
                    """,
                    tenant_id,
                )
                devices = [dict(r) for r in devices]
            else:
                devices = await fetch_devices(conn, tenant_id, limit=100, offset=0)
    except Exception:
        logger.exception("Failed to fetch operator tenant devices")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"tenant_id": tenant_id, "devices": devices}


@router.get("/tenants/{tenant_id}/devices/{device_id}")
async def view_device(
    request: Request,
    tenant_id: str,
    device_id: str,
):
    user = get_user()
    ip, user_agent = get_request_metadata(request)
    try:
        p = await get_pool()
        async with p.acquire() as conn:
            await log_operator_access(
                conn,
                user_id=user["sub"],
                action="view_device",
                tenant_filter=tenant_id,
                resource_type="device",
                resource_id=device_id,
                ip_address=ip,
                user_agent=user_agent,
                rls_bypassed=True,
            )
        async with operator_connection(p) as conn:
            device = await fetch_device(conn, tenant_id, device_id)
            if not device:
                raise HTTPException(status_code=404, detail="Device not found")

            events = await fetch_device_events(conn, tenant_id, device_id, hours=24, limit=50)
            telemetry = await fetch_device_telemetry(conn, tenant_id, device_id, hours=6, limit=120)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch operator device detail")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {
        "tenant_id": tenant_id,
        "device": device,
        "events": events,
        "telemetry": telemetry,
    }


@router.get("/alerts")
async def list_alerts(
    request: Request,
    tenant_filter: str | None = Query(None),
    status: str = Query("OPEN"),
    limit: int = Query(100, ge=1, le=500),
):
    user = get_user()
    ip, user_agent = get_request_metadata(request)
    try:
        p = await get_pool()
        async with p.acquire() as conn:
            await log_operator_access(
                conn,
                user_id=user["sub"],
                action="list_all_alerts",
                tenant_filter=tenant_filter,
                ip_address=ip,
                user_agent=user_agent,
                rls_bypassed=True,
            )
        async with operator_connection(p) as conn:
            if tenant_filter:
                alerts = await fetch_alerts(conn, tenant_filter, status=status, limit=limit)
            else:
                alerts = await fetch_all_alerts(conn, status=status, limit=limit)
    except Exception:
        logger.exception("Failed to fetch operator alerts")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"alerts": alerts, "tenant_filter": tenant_filter, "status": status, "limit": limit}


@router.get("/quarantine")
async def list_quarantine(
    request: Request,
    minutes: int = Query(60, ge=1, le=1440),
    limit: int = Query(100, ge=1, le=500),
):
    user = get_user()
    ip, user_agent = get_request_metadata(request)
    try:
        p = await get_pool()
        async with p.acquire() as conn:
            await log_operator_access(
                conn,
                user_id=user["sub"],
                action="view_quarantine",
                ip_address=ip,
                user_agent=user_agent,
                rls_bypassed=True,
            )
        async with operator_connection(p) as conn:
            events = await fetch_quarantine_events(conn, minutes=minutes, limit=limit)
    except Exception:
        logger.exception("Failed to fetch operator quarantine events")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"minutes": minutes, "events": events, "limit": limit}




@router.get("/audit-log")
async def get_audit_log(
    request: Request,
    source: str | None = Query(None, description="'operator' for operator access only, otherwise system activity"),
    user_id: str | None = None,
    action: str | None = None,
    since: str | None = None,
    limit: int = Query(default=100, le=1000),
    offset: int = Query(0, ge=0),
    tenant_id: str | None = None,
    category: str | None = None,
    severity: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    start: str | None = None,
    end: str | None = None,
    search: str | None = None,
):
    """View audit log - system activity events by default, or operator access with source=operator."""
    user = get_user()
    ip, user_agent = get_request_metadata(request)
    since_dt = None
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid since value; use ISO 8601")

    try:
        p = await get_pool()

        # If source=operator, return operator access log
        if source == "operator":
            async with p.acquire() as conn:
                await log_operator_access(
                    conn,
                    user_id=user["sub"],
                    action="view_audit_log",
                    ip_address=ip,
                    user_agent=user_agent,
                    rls_bypassed=True,
                )
            async with operator_connection(p) as conn:
                entries, total = await fetch_operator_audit_log(
                    conn,
                    user_id=user_id,
                    action=action,
                    since=since_dt,
                    limit=limit,
                    offset=offset,
                )
            return {
                "entries": entries,
                "total": total,
                "limit": limit,
                "offset": offset,
                "user_id": user_id,
                "action": action,
                "since": since,
            }

        # Default: return system activity events from audit_log table
        async with p.acquire() as conn:
            await log_operator_access(
                conn,
                user_id=user["sub"],
                action="view_system_audit_log",
                ip_address=ip,
                user_agent=user_agent,
                rls_bypassed=True,
            )
        async with operator_connection(p) as conn:
            where = []
            params = []
            idx = 1

            if tenant_id:
                where.append(f"tenant_id = ${idx}")
                params.append(tenant_id)
                idx += 1

            if category:
                where.append(f"category = ${idx}")
                params.append(category)
                idx += 1

            if severity:
                where.append(f"severity = ${idx}")
                params.append(severity)
                idx += 1

            if entity_type:
                where.append(f"entity_type = ${idx}")
                params.append(entity_type)
                idx += 1

            if entity_id:
                where.append(f"entity_id = ${idx}")
                params.append(entity_id)
                idx += 1

            if start:
                where.append(f"timestamp >= ${idx}")
                params.append(start)
                idx += 1

            if end:
                where.append(f"timestamp <= ${idx}")
                params.append(end)
                idx += 1

            if search:
                where.append(f"message ILIKE ${idx}")
                params.append(f"%{search}%")
                idx += 1

            where_clause = " AND ".join(where) if where else "TRUE"

            total = await conn.fetchval(
                f"SELECT COUNT(*) FROM audit_log WHERE {where_clause}",
                *params
            )

            rows = await conn.fetch(
                f"""
                SELECT timestamp, tenant_id, event_type, category, severity,
                       entity_type, entity_id, entity_name,
                       action, message, details,
                       source_service, actor_type, actor_id, actor_name
                FROM audit_log
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT ${idx} OFFSET ${idx + 1}
                """,
                *params, limit, offset
            )

        return {
            "events": [dict(r) for r in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    except Exception:
        logger.exception("Failed to fetch audit log")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/settings")
async def update_settings(
    request: Request,
    mode: str = Form("PROD"),
    store_rejects: str = Form("0"),
    mirror_rejects: str = Form("0"),
    _: None = Depends(require_operator_admin),
):
    user = get_user()
    ip, user_agent = get_request_metadata(request)
    mode = (mode or "PROD").upper()
    if mode not in ("PROD", "DEV"):
        mode = "PROD"

    if mode == "PROD":
        store_rejects = "0"
        mirror_rejects = "0"

    try:
        p = await get_pool()
        async with p.acquire() as conn:
            await log_operator_access(
                conn,
                user_id=user["sub"],
                action="update_settings",
                ip_address=ip,
                user_agent=user_agent,
                rls_bypassed=True,
            )
        async with operator_connection(p) as conn:
            await conn.execute(
                """
                INSERT INTO app_settings (key, value, updated_at)
                VALUES ('MODE', $1, now())
                ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=now();
                """,
                mode,
            )
            await conn.execute(
                """
                INSERT INTO app_settings (key, value, updated_at)
                VALUES ('STORE_REJECTS', $1, now())
                ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=now();
                """,
                "1" if store_rejects == "1" else "0",
            )
            await conn.execute(
                """
                INSERT INTO app_settings (key, value, updated_at)
                VALUES ('MIRROR_REJECTS_TO_RAW', $1, now())
                ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=now();
                """,
                "1" if mirror_rejects == "1" else "0",
            )
    except Exception:
        logger.exception("Failed to update operator settings")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"status": "ok"}
