import os
import logging
from urllib.parse import urlparse

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from middleware.auth import JWTBearer
from middleware.tenant import inject_tenant_context, get_tenant_id, require_customer
from db.queries import (
    fetch_alerts,
    fetch_delivery_attempts,
    fetch_device,
    fetch_device_count,
    fetch_device_events,
    fetch_device_telemetry,
    fetch_devices,
    fetch_integrations,
)

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


def redact_url(value: str | None) -> str:
    if not value:
        return ""
    try:
        parsed = urlparse(value)
    except Exception:
        return ""
    if not parsed.hostname:
        return ""
    scheme = parsed.scheme or "http"
    port = f":{parsed.port}" if parsed.port else ""
    return f"{scheme}://{parsed.hostname}{port}"


router = APIRouter(
    prefix="/customer",
    tags=["customer"],
    dependencies=[
        Depends(JWTBearer()),
        Depends(inject_tenant_context),
        Depends(require_customer),
    ],
)


@router.get("/dashboard", response_class=HTMLResponse)
async def customer_dashboard(request: Request):
    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with p.acquire() as conn:
            device_counts = await fetch_device_count(conn, tenant_id)
            devices = await fetch_devices(conn, tenant_id, limit=50, offset=0)
            alerts = await fetch_alerts(conn, tenant_id, limit=20)
            delivery_attempts = await fetch_delivery_attempts(conn, tenant_id, limit=10)
    except Exception:
        logger.exception("Failed to load customer dashboard")
        raise HTTPException(status_code=500, detail="Internal server error")

    return templates.TemplateResponse(
        "customer_dashboard.html",
        {
            "request": request,
            "refresh": UI_REFRESH_SECONDS,
            "tenant_id": tenant_id,
            "device_counts": device_counts,
            "devices": devices,
            "alerts": alerts,
            "delivery_attempts": delivery_attempts,
            "user": getattr(request.state, "user", None),
        },
    )


@router.get("/devices")
async def list_devices(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with p.acquire() as conn:
            devices = await fetch_devices(conn, tenant_id, limit=limit, offset=offset)
    except Exception:
        logger.exception("Failed to fetch tenant devices")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {
        "tenant_id": tenant_id,
        "devices": devices,
        "limit": limit,
        "offset": offset,
    }


@router.get("/devices/{device_id}", response_class=HTMLResponse)
async def get_device_detail(
    request: Request,
    device_id: str,
    format: str = Query("html"),
):
    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with p.acquire() as conn:
            device = await fetch_device(conn, tenant_id, device_id)
            if not device:
                raise HTTPException(status_code=404, detail="Device not found")

            events = await fetch_device_events(conn, tenant_id, device_id, limit=50)
            telemetry = await fetch_device_telemetry(conn, tenant_id, device_id, limit=120)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch tenant device detail")
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
        "customer_device.html",
        {
            "request": request,
            "refresh": UI_REFRESH_SECONDS,
            "tenant_id": tenant_id,
            "device_id": device_id,
            "dev": device,
            "events": events,
            "charts": charts,
            "user": getattr(request.state, "user", None),
        },
    )


@router.get("/alerts")
async def list_alerts(
    status: str = Query("OPEN"),
    limit: int = Query(100, ge=1, le=500),
):
    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with p.acquire() as conn:
            alerts = await fetch_alerts(conn, tenant_id, status=status, limit=limit)
    except Exception:
        logger.exception("Failed to fetch tenant alerts")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"tenant_id": tenant_id, "alerts": alerts, "status": status, "limit": limit}


@router.get("/alerts/{alert_id}")
async def get_alert(alert_id: str):
    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with p.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT alert_id, tenant_id, device_id, site_id, alert_type,
                       severity, confidence, summary, status, created_at
                FROM fleet_alert
                WHERE tenant_id = $1 AND alert_id = $2
                """,
                tenant_id,
                alert_id,
            )
    except Exception:
        logger.exception("Failed to fetch tenant alert")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not row:
        raise HTTPException(status_code=404, detail="Alert not found")

    return {"tenant_id": tenant_id, "alert": dict(row)}


@router.get("/integrations")
async def list_integrations():
    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with p.acquire() as conn:
            rows = await fetch_integrations(conn, tenant_id, limit=50)
    except Exception:
        logger.exception("Failed to fetch tenant integrations")
        raise HTTPException(status_code=500, detail="Internal server error")

    integrations = []
    for r in rows:
        item = dict(r)
        item["url"] = redact_url(item.get("url"))
        integrations.append(item)

    return {"tenant_id": tenant_id, "integrations": integrations}


@router.get("/delivery-status")
async def delivery_status(
    limit: int = Query(20, ge=1, le=100),
):
    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with p.acquire() as conn:
            attempts = await fetch_delivery_attempts(conn, tenant_id, limit=limit)
    except Exception:
        logger.exception("Failed to fetch tenant delivery attempts")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"tenant_id": tenant_id, "attempts": attempts}
