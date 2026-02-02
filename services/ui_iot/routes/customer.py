import os
import logging
import re
import datetime
import time
from uuid import UUID
from urllib.parse import urlparse

import asyncpg
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from starlette.requests import Request

from middleware.auth import JWTBearer
from middleware.tenant import inject_tenant_context, get_tenant_id, require_customer, get_user
from db.queries import (
    check_and_increment_rate_limit,
    create_integration,
    create_integration_route,
    delete_integration,
    delete_integration_route,
    fetch_alerts,
    fetch_delivery_attempts,
    fetch_device,
    fetch_device_count,
    fetch_device_events,
    fetch_device_telemetry,
    fetch_devices,
    fetch_integration,
    fetch_integration_route,
    fetch_integration_routes,
    fetch_integrations,
    update_integration,
    update_integration_route,
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


NAME_PATTERN = re.compile(r"^[A-Za-z0-9 _-]+$")


class IntegrationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    webhook_url: str = Field(..., min_length=1)
    enabled: bool = True


class IntegrationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    webhook_url: str | None = None
    enabled: bool | None = None


class RouteCreate(BaseModel):
    integration_id: UUID
    alert_types: list[str]
    severities: list[str]
    enabled: bool = True


class RouteUpdate(BaseModel):
    alert_types: list[str] | None = None
    severities: list[str] | None = None
    enabled: bool | None = None

async def require_customer_admin(request: Request):
    user = get_user()
    if user.get("role") != "customer_admin":
        raise HTTPException(status_code=403, detail="Customer admin role required")


def _validate_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned or len(cleaned) > 100:
        raise HTTPException(status_code=400, detail="Invalid name length")
    if not NAME_PATTERN.match(cleaned):
        raise HTTPException(status_code=400, detail="Invalid name format")
    return cleaned


def _validate_basic_url(value: str) -> None:
    try:
        parsed = urlparse(value)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid URL format")
    if not parsed.scheme or not parsed.netloc:
        raise HTTPException(status_code=400, detail="Invalid URL format")
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Only HTTP/HTTPS URLs are allowed")


ALERT_TYPES = {"STALE_DEVICE", "LOW_BATTERY", "TEMPERATURE_ALERT", "CONNECTIVITY_ISSUE", "DEVICE_OFFLINE"}
SEVERITIES = {"CRITICAL", "WARNING", "INFO"}


def _normalize_list(values: list[str] | None, allowed: set[str], field_name: str) -> list[str] | None:
    if values is None:
        return None
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in values:
        if item is None:
            continue
        trimmed = item.strip()
        if not trimmed:
            continue
        if trimmed not in allowed:
            raise HTTPException(status_code=400, detail=f"Invalid {field_name} value: {trimmed}")
        if trimmed in seen:
            continue
        seen.add(trimmed)
        cleaned.append(trimmed)
    if not cleaned:
        raise HTTPException(status_code=400, detail=f"{field_name} must not be empty")
    return cleaned


def generate_test_payload(tenant_id: str, integration_name: str) -> dict:
    now = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    return {
        "_test": True,
        "_generated_at": now,
        "alert_id": "test-00000000-0000-0000-0000-000000000000",
        "tenant_id": tenant_id,
        "device_id": "TEST-DEVICE-001",
        "site_id": "TEST-SITE",
        "alert_type": "STALE_DEVICE",
        "severity": "WARNING",
        "summary": "Test alert from OpsConductor Pulse",
        "message": "This is a test delivery to verify your webhook integration is working correctly.",
        "integration_name": integration_name,
        "created_at": now,
    }


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


@router.post("/integrations", dependencies=[Depends(require_customer_admin)])
async def create_integration_route(body: IntegrationCreate):
    tenant_id = get_tenant_id()
    name = _validate_name(body.name)
    _validate_basic_url(body.webhook_url)
    try:
        p = await get_pool()
        async with p.acquire() as conn:
            integration = await create_integration(
                conn,
                tenant_id=tenant_id,
                name=name,
                webhook_url=body.webhook_url,
                enabled=body.enabled,
            )
    except Exception:
        logger.exception("Failed to create integration")
        raise HTTPException(status_code=500, detail="Internal server error")

    integration["url"] = redact_url(integration.get("url"))
    return integration


@router.get("/integrations/{integration_id}")
async def get_integration(integration_id: str):
    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with p.acquire() as conn:
            integration = await fetch_integration(conn, tenant_id, integration_id)
    except Exception:
        logger.exception("Failed to fetch integration")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    integration["url"] = redact_url(integration.get("url"))
    return integration


@router.patch("/integrations/{integration_id}", dependencies=[Depends(require_customer_admin)])
async def patch_integration(integration_id: str, body: IntegrationUpdate):
    tenant_id = get_tenant_id()
    if body.name is None and body.webhook_url is None and body.enabled is None:
        raise HTTPException(status_code=400, detail="No fields to update")

    name = _validate_name(body.name) if body.name is not None else None
    if body.webhook_url is not None:
        _validate_basic_url(body.webhook_url)

    try:
        p = await get_pool()
        async with p.acquire() as conn:
            integration = await update_integration(
                conn,
                tenant_id=tenant_id,
                integration_id=integration_id,
                name=name,
                webhook_url=body.webhook_url,
                enabled=body.enabled,
            )
    except Exception:
        logger.exception("Failed to update integration")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    integration["url"] = redact_url(integration.get("url"))
    return integration


@router.delete("/integrations/{integration_id}", dependencies=[Depends(require_customer_admin)])
async def delete_integration_route(integration_id: str):
    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with p.acquire() as conn:
            deleted = await delete_integration(conn, tenant_id, integration_id)
    except Exception:
        logger.exception("Failed to delete integration")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not deleted:
        raise HTTPException(status_code=404, detail="Integration not found")
    return Response(status_code=204)


@router.post("/integrations/{integration_id}/test", dependencies=[Depends(require_customer_admin)])
async def test_integration_delivery(integration_id: str):
    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with p.acquire() as conn:
            allowed, _ = await check_and_increment_rate_limit(
                conn,
                tenant_id=tenant_id,
                action="test_delivery",
                limit=5,
                window_seconds=60,
            )
            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded. Maximum 5 test deliveries per minute.",
                )

            integration = await fetch_integration(conn, tenant_id, integration_id)
            if not integration:
                raise HTTPException(status_code=404, detail="Integration not found")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch integration for test")
        raise HTTPException(status_code=500, detail="Internal server error")

    webhook_url = integration.get("url")
    if not webhook_url:
        raise HTTPException(status_code=400, detail="Integration webhook URL missing")
    payload = generate_test_payload(tenant_id, integration.get("name", "Webhook"))

    start = time.monotonic()
    success = False
    http_status = None
    error = None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(webhook_url, json=payload, headers={"Content-Type": "application/json"})
            http_status = resp.status_code
            if 200 <= resp.status_code < 300:
                success = True
            else:
                error = f"Server returned HTTP {resp.status_code}"
    except httpx.TimeoutException:
        error = "Connection timeout after 10 seconds"
    except httpx.ConnectError as exc:
        msg = str(exc).lower()
        if "name or service not known" in msg or "nodename nor servname" in msg:
            error = "Could not resolve hostname"
        else:
            error = "Connection refused by server"
    except httpx.RequestError:
        error = "Connection refused by server"

    latency_ms = int((time.monotonic() - start) * 1000)
    result = {
        "success": success,
        "http_status": http_status,
        "latency_ms": latency_ms,
        "error": error,
        "payload_sent": payload,
    }

    logger.info(
        "Test delivery",
        extra={
            "tenant_id": tenant_id,
            "integration_id": integration_id,
            "success": success,
            "latency_ms": latency_ms,
        },
    )
    return result


@router.get("/integration-routes")
async def list_integration_routes(limit: int = Query(100, ge=1, le=500)):
    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with p.acquire() as conn:
            routes = await fetch_integration_routes(conn, tenant_id, limit=limit)
    except Exception:
        logger.exception("Failed to fetch integration routes")
        raise HTTPException(status_code=500, detail="Internal server error")
    return {"tenant_id": tenant_id, "routes": routes}


@router.get("/integration-routes/{route_id}")
async def get_integration_route(route_id: str):
    try:
        UUID(route_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid route_id format: must be a valid UUID")

    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with p.acquire() as conn:
            route = await fetch_integration_route(conn, tenant_id, route_id)
    except Exception:
        logger.exception("Failed to fetch integration route")
        raise HTTPException(status_code=500, detail="Internal server error")
    if not route:
        raise HTTPException(status_code=404, detail="Integration route not found")
    return route


@router.post("/integration-routes", dependencies=[Depends(require_customer_admin)])
async def create_integration_route_endpoint(body: RouteCreate):
    tenant_id = get_tenant_id()
    alert_types = _normalize_list(body.alert_types, ALERT_TYPES, "alert_types")
    severities = _normalize_list(body.severities, SEVERITIES, "severities")
    try:
        p = await get_pool()
        async with p.acquire() as conn:
            integration = await fetch_integration(conn, tenant_id, str(body.integration_id))
            if not integration:
                raise HTTPException(
                    status_code=400,
                    detail="Integration not found or belongs to different tenant",
                )
            route = await create_integration_route(
                conn,
                tenant_id=tenant_id,
                integration_id=str(body.integration_id),
                alert_types=alert_types,
                severities=severities,
                enabled=body.enabled,
            )
            route["integration_name"] = integration.get("name")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to create integration route")
        raise HTTPException(status_code=500, detail="Internal server error")

    return route


@router.patch("/integration-routes/{route_id}", dependencies=[Depends(require_customer_admin)])
async def patch_integration_route(route_id: str, body: RouteUpdate):
    try:
        UUID(route_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid route_id format: must be a valid UUID")

    if body.alert_types is None and body.severities is None and body.enabled is None:
        raise HTTPException(status_code=400, detail="No fields to update")

    alert_types = _normalize_list(body.alert_types, ALERT_TYPES, "alert_types") if body.alert_types is not None else None
    severities = _normalize_list(body.severities, SEVERITIES, "severities") if body.severities is not None else None

    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with p.acquire() as conn:
            route = await update_integration_route(
                conn,
                tenant_id=tenant_id,
                route_id=route_id,
                alert_types=alert_types,
                severities=severities,
                enabled=body.enabled,
            )
    except Exception:
        logger.exception("Failed to update integration route")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not route:
        raise HTTPException(status_code=404, detail="Integration route not found")
    return route


@router.delete("/integration-routes/{route_id}", dependencies=[Depends(require_customer_admin)])
async def delete_integration_route_endpoint(route_id: str):
    try:
        UUID(route_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid route_id format: must be a valid UUID")

    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with p.acquire() as conn:
            deleted = await delete_integration_route(conn, tenant_id, route_id)
    except Exception:
        logger.exception("Failed to delete integration route")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not deleted:
        raise HTTPException(status_code=404, detail="Integration route not found")
    return Response(status_code=204)


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
