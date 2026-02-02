import os
import logging

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from middleware.auth import JWTBearer
from middleware.tenant import (
    inject_tenant_context,
    get_tenant_id_or_none,
    get_user,
    require_operator,
    require_operator_admin,
    is_operator,
)
from db.queries import (
    fetch_alerts,
    fetch_all_alerts,
    fetch_all_delivery_attempts,
    fetch_all_devices,
    fetch_all_integrations,
    fetch_delivery_attempts,
    fetch_device,
    fetch_device_events,
    fetch_device_telemetry,
    fetch_devices,
    fetch_integrations,
    fetch_quarantine_events,
)
from db.audit import log_operator_access
from db.pool import operator_connection

logger = logging.getLogger(__name__)

PG_HOST = os.getenv("PG_HOST", "iot-postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "iotcloud")
PG_USER = os.getenv("PG_USER", "iot")
PG_PASS = os.getenv("PG_PASS", "iot_dev")

UI_REFRESH_SECONDS = int(os.getenv("UI_REFRESH_SECONDS", "5"))

templates = Jinja2Templates(directory="/app/templates")
pool: asyncpg.Pool | None = None


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


def to_float(v):
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def to_int(v):
    try:
        if v is None:
            return None
        return int(v)
    except Exception:
        return None


def sparkline_points(values, width=520, height=60, pad=4):
    vals = [v for v in values if v is not None]
    if len(vals) < 2:
        return ""
    vmin = min(vals)
    vmax = max(vals)
    if vmax == vmin:
        vmax = vmin + 1.0

    n = len(values)

    def x(i):
        return pad + (i * (width - 2 * pad) / max(1, n - 1))

    pts = []
    for i, v in enumerate(values):
        if v is None:
            continue
        y = pad + (height - 2 * pad) * (1.0 - ((v - vmin) / (vmax - vmin)))
        pts.append(f"{x(i):.1f},{y:.1f}")
    return " ".join(pts)


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


async def _load_dashboard_context(conn):
    mode, store_rejects, mirror_rejects, rate_rps, rate_burst, max_payload_bytes = await get_settings(conn)

    last_create = await conn.fetchval("SELECT value FROM app_settings WHERE key='LAST_ADMIN_CREATE'") or ""
    last_activate = await conn.fetchval("SELECT value FROM app_settings WHERE key='LAST_DEVICE_ACTIVATE'") or ""

    devices = await fetch_all_devices(conn, limit=100, offset=0)
    open_alerts = await fetch_all_alerts(conn, status="OPEN", limit=50)
    integrations = await fetch_all_integrations(conn, limit=50)
    delivery_attempts = await fetch_all_delivery_attempts(conn, limit=20)

    quarantine = await conn.fetch(
        """
        SELECT ingested_at, tenant_id, site_id, device_id, msg_type, reason
        FROM quarantine_events
        ORDER BY ingested_at DESC
        LIMIT 50
        """
    )

    counts = await conn.fetchrow(
        """
        SELECT
          (SELECT COUNT(*) FROM device_state) AS devices_total,
          (SELECT COUNT(*) FROM device_state WHERE status='ONLINE') AS devices_online,
          (SELECT COUNT(*) FROM device_state WHERE status='STALE') AS devices_stale,
          (SELECT COUNT(*) FROM fleet_alert WHERE status='OPEN') AS alerts_open,
          (SELECT COUNT(*) FROM quarantine_events WHERE ingested_at > (now() - interval '10 minutes')) AS quarantined_10m
        """
    )

    rate_limited_10m = await conn.fetchval(
        """
        SELECT COALESCE(SUM(cnt),0)
        FROM quarantine_counters_minute
        WHERE reason='RATE_LIMITED'
          AND bucket_minute > (date_trunc('minute', now()) - interval '10 minutes')
        """
    )

    rate_limited_5m = await conn.fetchval(
        """
        SELECT COALESCE(SUM(cnt),0)
        FROM quarantine_counters_minute
        WHERE reason='RATE_LIMITED'
          AND bucket_minute > (date_trunc('minute', now()) - interval '5 minutes')
        """
    )

    reason_counts_10m = await conn.fetch(
        """
        SELECT reason, SUM(cnt) AS cnt
        FROM quarantine_counters_minute
        WHERE bucket_minute > (date_trunc('minute', now()) - interval '10 minutes')
        GROUP BY reason
        ORDER BY cnt DESC, reason ASC
        LIMIT 20
        """
    )

    rate_series = await conn.fetch(
        """
        SELECT bucket_minute, SUM(cnt) AS total_cnt,
               COALESCE(SUM(cnt) FILTER (WHERE reason='RATE_LIMITED'),0) AS rate_limited_cnt
        FROM quarantine_counters_minute
        WHERE bucket_minute > (date_trunc('minute', now()) - interval '60 minutes')
        GROUP BY bucket_minute
        ORDER BY bucket_minute ASC
        """
    )
    series = [
        {"t": str(r["bucket_minute"]), "cnt": int(r["total_cnt"]), "rl": int(r["rate_limited_cnt"])}
        for r in rate_series
    ]
    max_cnt = max([x["cnt"] for x in series], default=0)

    return {
        "mode": mode,
        "store_rejects": store_rejects,
        "mirror_rejects": mirror_rejects,
        "rate_rps": rate_rps,
        "rate_burst": rate_burst,
        "max_payload_bytes": max_payload_bytes,
        "rate_limited_10m": int(rate_limited_10m or 0),
        "rate_limited_5m": int(rate_limited_5m or 0),
        "counts": counts,
        "devices": devices,
        "open_alerts": open_alerts,
        "integrations": integrations,
        "delivery_attempts": delivery_attempts,
        "quarantine": quarantine,
        "reason_counts_10m": reason_counts_10m,
        "rate_series": series,
        "rate_max": max_cnt,
        "last_create": last_create,
        "last_activate": last_activate,
    }


router = APIRouter(
    prefix="/operator",
    tags=["operator"],
    dependencies=[
        Depends(JWTBearer()),
        Depends(inject_tenant_context),
        Depends(require_operator),
    ],
)


@router.get("/dashboard", response_class=HTMLResponse)
async def operator_dashboard(request: Request):
    user = get_user()
    ip, user_agent = get_request_metadata(request)
    tenant_hint = get_tenant_id_or_none()

    try:
        p = await get_pool()
        async with operator_connection(p) as conn:
            await log_operator_access(
                conn,
                user_id=user["sub"],
                action="view_dashboard",
                tenant_filter=tenant_hint,
                ip_address=ip,
                user_agent=user_agent,
            )

            context = await _load_dashboard_context(conn)
    except Exception:
        logger.exception("Failed to load operator dashboard")
        raise HTTPException(status_code=500, detail="Internal server error")

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "refresh": UI_REFRESH_SECONDS,
            "user": user,
            "operator": True,
            **context,
        },
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
        async with operator_connection(p) as conn:
            await log_operator_access(
                conn,
                user_id=user["sub"],
                action="list_devices",
                tenant_filter=tenant_filter,
                ip_address=ip,
                user_agent=user_agent,
            )

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
        async with operator_connection(p) as conn:
            await log_operator_access(
                conn,
                user_id=user["sub"],
                action="list_tenant_devices",
                tenant_filter=tenant_id,
                ip_address=ip,
                user_agent=user_agent,
            )
            devices = await fetch_devices(conn, tenant_id, limit=100, offset=0)
    except Exception:
        logger.exception("Failed to fetch operator tenant devices")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"tenant_id": tenant_id, "devices": devices}


@router.get("/tenants/{tenant_id}/devices/{device_id}", response_class=HTMLResponse)
async def view_device(
    request: Request,
    tenant_id: str,
    device_id: str,
    format: str = Query("json"),
):
    user = get_user()
    ip, user_agent = get_request_metadata(request)
    try:
        p = await get_pool()
        async with operator_connection(p) as conn:
            await log_operator_access(
                conn,
                user_id=user["sub"],
                action="view_device",
                tenant_filter=tenant_id,
                resource_type="device",
                resource_id=device_id,
                ip_address=ip,
                user_agent=user_agent,
            )

            device = await fetch_device(conn, tenant_id, device_id)
            if not device:
                raise HTTPException(status_code=404, detail="Device not found")

            events = await fetch_device_events(conn, tenant_id, device_id, limit=50)
            telemetry = await fetch_device_telemetry(conn, tenant_id, device_id, limit=120)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch operator device detail")
        raise HTTPException(status_code=500, detail="Internal server error")

    if format == "json":
        return {
            "tenant_id": tenant_id,
            "device": device,
            "events": events,
            "telemetry": telemetry,
        }

    series = list(reversed(telemetry))
    bat = [to_float(r["battery_pct"]) for r in series]
    tmp = [to_float(r["temp_c"]) for r in series]
    rssi = [to_int(r["rssi_dbm"]) for r in series]
    rssi_f = [float(x) if x is not None else None for x in rssi]

    charts = {
        "battery_pts": sparkline_points(bat),
        "temp_pts": sparkline_points(tmp),
        "rssi_pts": sparkline_points(rssi_f),
    }

    return templates.TemplateResponse(
        "device.html",
        {
            "request": request,
            "refresh": UI_REFRESH_SECONDS,
            "device_id": device_id,
            "tenant_id": tenant_id,
            "dev": device,
            "events": events,
            "charts": charts,
            "user": user,
            "operator": True,
        },
    )


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
        async with operator_connection(p) as conn:
            await log_operator_access(
                conn,
                user_id=user["sub"],
                action="list_alerts",
                tenant_filter=tenant_filter,
                ip_address=ip,
                user_agent=user_agent,
            )

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
        async with operator_connection(p) as conn:
            await log_operator_access(
                conn,
                user_id=user["sub"],
                action="view_quarantine",
                ip_address=ip,
                user_agent=user_agent,
            )
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
        async with operator_connection(p) as conn:
            await log_operator_access(
                conn,
                user_id=user["sub"],
                action="list_integrations",
                tenant_filter=tenant_filter,
                ip_address=ip,
                user_agent=user_agent,
            )
            if tenant_filter:
                integrations = await fetch_integrations(conn, tenant_filter, limit=50)
            else:
                integrations = await fetch_all_integrations(conn, limit=50)
    except Exception:
        logger.exception("Failed to fetch operator integrations")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"integrations": integrations, "tenant_filter": tenant_filter}


@router.get("/settings", response_class=HTMLResponse)
async def settings(request: Request, _: None = Depends(require_operator_admin)):
    user = get_user()
    ip, user_agent = get_request_metadata(request)
    try:
        p = await get_pool()
        async with operator_connection(p) as conn:
            await log_operator_access(
                conn,
                user_id=user["sub"],
                action="view_settings",
                ip_address=ip,
                user_agent=user_agent,
            )
            context = await _load_dashboard_context(conn)
    except Exception:
        logger.exception("Failed to load operator settings")
        raise HTTPException(status_code=500, detail="Internal server error")

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "refresh": UI_REFRESH_SECONDS,
            "user": user,
            "operator": True,
            **context,
        },
    )


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
        async with operator_connection(p) as conn:
            await log_operator_access(
                conn,
                user_id=user["sub"],
                action="update_settings",
                ip_address=ip,
                user_agent=user_agent,
            )
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

    return RedirectResponse(url="/operator/dashboard", status_code=303)
