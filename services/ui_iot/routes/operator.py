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
PG_PASS = os.environ["PG_PASS"]

pool: asyncpg.Pool | None = None


class TenantCreate(BaseModel):
    tenant_id: str  # Must be URL-safe, lowercase
    name: str
    contact_email: Optional[EmailStr] = None
    contact_name: Optional[str] = None
    metadata: dict = {}


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_name: Optional[str] = None
    status: Optional[str] = None  # ACTIVE, SUSPENDED
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

    return dict(row)


@router.post("/subscriptions", status_code=201)
async def create_subscription(data: SubscriptionCreate, request: Request):
    """Create a new subscription for a tenant."""
    user = get_user()
    ip, _ = get_request_metadata(request)

    pool = await get_pool()
    async with operator_connection(pool) as conn:
        tenant = await conn.fetchval(
            "SELECT 1 FROM tenants WHERE tenant_id = $1",
            data.tenant_id,
        )
        if not tenant:
            raise HTTPException(404, "Tenant not found")

        term_start = data.term_start or datetime.now(timezone.utc)
        if data.term_days:
            term_end = term_start + timedelta(days=data.term_days)
        elif data.term_end:
            term_end = data.term_end
        elif data.subscription_type == "TRIAL":
            term_end = term_start + timedelta(days=14)
        else:
            raise HTTPException(400, "term_end or term_days required for non-TRIAL subscriptions")

        if data.subscription_type == "ADDON":
            if not data.parent_subscription_id:
                raise HTTPException(400, "ADDON requires parent_subscription_id")
            parent = await conn.fetchrow(
                "SELECT subscription_type, term_end FROM subscriptions WHERE subscription_id = $1",
                data.parent_subscription_id,
            )
            if not parent:
                raise HTTPException(404, "Parent subscription not found")
            if parent["subscription_type"] != "MAIN":
                raise HTTPException(400, "Parent must be MAIN subscription")
            term_end = parent["term_end"]

        subscription_id = await conn.fetchval("SELECT generate_subscription_id()")

        row = await conn.fetchrow(
            """
            INSERT INTO subscriptions (
                subscription_id, tenant_id, subscription_type, parent_subscription_id,
                device_limit, term_start, term_end, status, plan_id, description, created_by
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, 'ACTIVE', $8, $9, $10)
            RETURNING *
            """,
            subscription_id,
            data.tenant_id,
            data.subscription_type,
            data.parent_subscription_id,
            data.device_limit,
            term_start,
            term_end,
            data.plan_id,
            data.description,
            user.get("sub") if user else None,
        )

        await conn.execute(
            """
            INSERT INTO subscription_audit
                (tenant_id, event_type, actor_type, actor_id, new_state, details, ip_address)
            VALUES ($1, 'SUBSCRIPTION_CREATED', 'admin', $2, $3, $4, $5)
            """,
            data.tenant_id,
            user.get("sub") if user else None,
            json.dumps(dict(row), default=str),
            json.dumps({"notes": data.notes}) if data.notes else None,
            ip,
        )

        return {
            "subscription_id": row["subscription_id"],
            "tenant_id": row["tenant_id"],
            "subscription_type": row["subscription_type"],
            "device_limit": row["device_limit"],
            "term_start": row["term_start"].isoformat(),
            "term_end": row["term_end"].isoformat(),
            "status": row["status"],
        }


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
                    "subscription_id": r["subscription_id"],
                    "tenant_id": r["tenant_id"],
                    "tenant_name": r["tenant_name"],
                    "subscription_type": r["subscription_type"],
                    "parent_subscription_id": r["parent_subscription_id"],
                    "device_limit": r["device_limit"],
                    "active_device_count": r["active_device_count"],
                    "term_start": r["term_start"].isoformat(),
                    "term_end": r["term_end"].isoformat(),
                    "status": r["status"],
                    "description": r["description"],
                }
                for r in rows
            ],
            "count": len(rows),
        }


@router.get("/subscriptions/expiring-notifications")
async def list_expiring_notifications(
    status: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
):
    """List subscription expiry notification records."""
    conditions: list[str] = []
    params: list[str | int] = []

    if status:
        params.append(status.upper())
        conditions.append(f"status = ${len(params)}")
    if tenant_id:
        params.append(tenant_id)
        conditions.append(f"tenant_id = ${len(params)}")

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)

    p = await get_pool()
    async with operator_connection(p) as conn:
        rows = await conn.fetch(
            f"""
            SELECT id, tenant_id, notification_type, scheduled_at, sent_at,
                   channel, status, error
            FROM subscription_notifications
            {where_clause}
            ORDER BY scheduled_at DESC
            LIMIT ${len(params)}
            """,
            *params,
        )
    return {"notifications": [dict(r) for r in rows], "total": len(rows)}


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

        if data.status and data.status != current["status"]:
            event_type = f"STATUS_{data.status}"
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
            json.dumps({"notes": data.notes, "transaction_ref": data.transaction_ref}),
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
    user = get_user()
    ip, _ = get_request_metadata(request)

    pool = await get_pool()
    async with operator_connection(pool) as conn:
        device = await conn.fetchrow(
            "SELECT tenant_id, subscription_id FROM device_registry WHERE device_id = $1",
            device_id,
        )
        if not device:
            raise HTTPException(404, "Device not found")

        old_subscription_id = device["subscription_id"]
        tenant_id = device["tenant_id"]

        new_sub = await conn.fetchrow(
            "SELECT * FROM subscriptions WHERE subscription_id = $1",
            data.subscription_id,
        )
        if not new_sub:
            raise HTTPException(404, "Subscription not found")

        if new_sub["tenant_id"] != tenant_id:
            raise HTTPException(400, "Subscription belongs to different tenant")

        if new_sub["status"] in ("SUSPENDED", "EXPIRED"):
            raise HTTPException(400, f"Cannot assign to {new_sub['status']} subscription")

        if new_sub["active_device_count"] >= new_sub["device_limit"]:
            raise HTTPException(400, "Subscription at device limit")

        await conn.execute(
            "UPDATE device_registry SET subscription_id = $1 WHERE device_id = $2",
            data.subscription_id,
            device_id,
        )

        if old_subscription_id:
            await conn.execute(
                """
                UPDATE subscriptions
                SET active_device_count = GREATEST(0, active_device_count - 1)
                WHERE subscription_id = $1
                """,
                old_subscription_id,
            )
        await conn.execute(
            """
            UPDATE subscriptions
            SET active_device_count = active_device_count + 1
            WHERE subscription_id = $1
            """,
            data.subscription_id,
        )

        await conn.execute(
            """
            INSERT INTO subscription_audit
                (tenant_id, event_type, actor_type, actor_id, details, ip_address)
            VALUES ($1, 'DEVICE_REASSIGNED', 'admin', $2, $3, $4)
            """,
            tenant_id,
            user.get("sub") if user else None,
            json.dumps(
                {
                    "device_id": device_id,
                    "from_subscription": old_subscription_id,
                    "to_subscription": data.subscription_id,
                    "notes": data.notes,
                }
            ),
            ip,
        )

        return {
            "device_id": device_id,
            "subscription_id": data.subscription_id,
            "previous_subscription_id": old_subscription_id,
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
            INSERT INTO tenants (tenant_id, name, contact_email, contact_name, metadata)
            VALUES ($1, $2, $3, $4, $5::jsonb)
            """,
            tenant.tenant_id,
            tenant.name,
            tenant.contact_email,
            tenant.contact_name,
            json.dumps(tenant.metadata),
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
