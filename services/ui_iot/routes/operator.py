import os
import json
import logging
import re
import time
from datetime import datetime

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, Form
from starlette.requests import Request
from pydantic import BaseModel, EmailStr
from typing import Optional

from middleware.auth import JWTBearer
from middleware.tenant import (
    inject_tenant_context,
    get_user,
    require_operator,
    require_operator_admin,
)
import httpx
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
from db.influx_queries import fetch_device_telemetry_influx, fetch_device_events_influx
from db.audit import log_operator_access, fetch_operator_audit_log
from db.pool import operator_connection

logger = logging.getLogger(__name__)

PG_HOST = os.getenv("PG_HOST", "iot-postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "iotcloud")
PG_USER = os.getenv("PG_USER", "iot")
PG_PASS = os.getenv("PG_PASS", "iot_dev")
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://iot-influxdb:8181")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "influx-dev-token-change-me")

pool: asyncpg.Pool | None = None
_influx_client: httpx.AsyncClient | None = None


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


def _get_influx_client() -> httpx.AsyncClient:
    global _influx_client
    if _influx_client is None:
        _influx_client = httpx.AsyncClient(timeout=10.0)
    return _influx_client


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
    prefix="/operator",
    tags=["operator"],
    dependencies=[
        Depends(JWTBearer()),
        Depends(inject_tenant_context),
        Depends(require_operator),
    ],
)


async def provision_tenant_influxdb(tenant_id: str) -> bool:
    """
    Create InfluxDB database for tenant.

    InfluxDB 3 auto-creates databases on first write,
    so we write a dummy point to ensure it exists.
    """
    db_name = f"telemetry_{tenant_id}"
    line_protocol = (
        f"_init,tenant={tenant_id} initialized=1i {int(time.time() * 1_000_000_000)}"
    )
    headers = {
        "Authorization": f"Bearer {INFLUXDB_TOKEN}",
        "Content-Type": "text/plain",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{INFLUXDB_URL}/api/v3/write_lp?db={db_name}",
                content=line_protocol,
                headers=headers,
            )

            if resp.status_code < 300:
                logger.info(
                    "Created InfluxDB database %s for tenant %s",
                    db_name,
                    tenant_id,
                )
                return True
            logger.error(
                "Failed to create InfluxDB database %s: %s %s",
                db_name,
                resp.status_code,
                resp.text,
            )
            return False
    except Exception as exc:
        logger.error("InfluxDB provisioning error for %s: %s", tenant_id, exc)
        return False


async def check_tenant_influxdb(tenant_id: str) -> dict:
    """
    Check if tenant InfluxDB database exists.
    Avoids expensive telemetry scans.
    """
    db_name = f"telemetry_{tenant_id}"
    headers = {
        "Authorization": f"Bearer {INFLUXDB_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Check if database exists with a simple query
            resp = await client.post(
                f"{INFLUXDB_URL}/api/v3/query_sql",
                json={
                    "db": db_name,
                    "q": "SELECT 1",
                    "format": "json",
                },
                headers=headers,
            )

            body = resp.text.lower()

            if resp.status_code == 404 or "database" in body:
                return {"exists": False, "telemetry_count": 0}

            if resp.status_code == 400 and ("table" in body or "relation" in body):
                # Database exists but no telemetry table yet
                return {"exists": True, "telemetry_count": 0}

            if resp.status_code == 400 and ("file limit" in body or "parquet" in body):
                return {"exists": True, "telemetry_count": None}

            if resp.status_code == 200:
                return {"exists": True, "telemetry_count": None}

            return {"exists": None, "error": resp.text}
    except Exception as exc:
        return {"exists": None, "error": str(exc)}


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

    influx_ok = await provision_tenant_influxdb(tenant.tenant_id)

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
        "influxdb_provisioned": influx_ok,
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

    influx_status = await check_tenant_influxdb(tenant_id)

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
        "influxdb": influx_status,
    }


@router.post("/tenants/{tenant_id}/provision-influxdb")
async def provision_influxdb(
    request: Request,
    tenant_id: str,
    _: None = Depends(require_operator_admin),
):
    """Manually provision InfluxDB for existing tenant."""
    user = get_user()
    ip, user_agent = get_request_metadata(request)
    pool = await get_pool()

    async with operator_connection(pool) as conn:
        exists = await conn.fetchval(
            "SELECT 1 FROM tenants WHERE tenant_id = $1",
            tenant_id,
        )
        if not exists:
            raise HTTPException(404, "Tenant not found")

    success = await provision_tenant_influxdb(tenant_id)

    async with pool.acquire() as conn:
        await log_operator_access(
            conn,
            user_id=user["sub"],
            action="provision_influxdb",
            tenant_filter=tenant_id,
            ip_address=ip,
            user_agent=user_agent,
            rls_bypassed=True,
        )

    return {
        "tenant_id": tenant_id,
        "influxdb_provisioned": success,
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
            else:
                devices = await fetch_all_devices(conn, limit=limit, offset=offset)
    except Exception:
        logger.exception("Failed to fetch operator devices")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {
        "devices": devices,
        "tenant_filter": tenant_filter,
        "limit": limit,
        "offset": offset,
    }


@router.get("/tenants/{tenant_id}/devices")
async def list_tenant_devices(request: Request, tenant_id: str):
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

            ic = _get_influx_client()
            events = await fetch_device_events_influx(ic, tenant_id, device_id, limit=50)
            telemetry = await fetch_device_telemetry_influx(ic, tenant_id, device_id, limit=120)
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


@router.get("/integrations")
async def list_integrations(
    request: Request,
    tenant_filter: str | None = Query(None),
):
    user = get_user()
    ip, user_agent = get_request_metadata(request)
    try:
        p = await get_pool()
        async with p.acquire() as conn:
            await log_operator_access(
                conn,
                user_id=user["sub"],
                action="list_all_integrations",
                tenant_filter=tenant_filter,
                ip_address=ip,
                user_agent=user_agent,
                rls_bypassed=True,
            )
        async with operator_connection(p) as conn:
            if tenant_filter:
                integrations = await fetch_integrations(conn, tenant_filter, limit=50)
            else:
                integrations = await fetch_all_integrations(conn, limit=50)
    except Exception:
        logger.exception("Failed to fetch operator integrations")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"integrations": integrations, "tenant_filter": tenant_filter}


@router.get("/audit-log", dependencies=[Depends(require_operator_admin)])
async def get_audit_log(
    request: Request,
    user_id: str | None = None,
    action: str | None = None,
    since: str | None = None,
    limit: int = Query(default=100, le=1000),
):
    """View operator audit log (operator_admin only)."""
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
            entries = await fetch_operator_audit_log(
                conn,
                user_id=user_id,
                action=action,
                since=since_dt,
                limit=limit,
            )
    except Exception:
        logger.exception("Failed to fetch operator audit log")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {
        "entries": entries,
        "limit": limit,
        "user_id": user_id,
        "action": action,
        "since": since,
    }


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
