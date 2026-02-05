import os
import logging
from datetime import datetime

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, Form
from starlette.requests import Request

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

pool: asyncpg.Pool | None = None
_influx_client: httpx.AsyncClient | None = None


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
