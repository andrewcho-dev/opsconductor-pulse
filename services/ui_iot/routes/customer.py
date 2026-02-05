import os
import logging
import re
import datetime
import json
import uuid
from uuid import UUID
from urllib.parse import urlparse

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from starlette.requests import Request

from middleware.auth import JWTBearer
from middleware.tenant import inject_tenant_context, get_tenant_id, require_customer, get_user
import httpx
INFLUXDB_READ_ENABLED = os.getenv("INFLUXDB_READ_ENABLED", "1") == "1"
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://iot-influxdb:8181")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "influx-dev-token-change-me")
from utils.url_validator import validate_webhook_url
from utils.snmp_validator import validate_snmp_host
from utils.email_validator import validate_email_integration
from utils.mqtt_validator import validate_mqtt_topic
from schemas.snmp import (
    SNMPIntegrationCreate,
    SNMPIntegrationUpdate,
    SNMPIntegrationResponse,
)
from schemas.email import (
    EmailIntegrationCreate,
    EmailIntegrationUpdate,
    EmailIntegrationResponse,
)
from schemas.mqtt import (
    MQTTIntegrationCreate,
    MQTTIntegrationUpdate,
    MQTTIntegrationResponse,
)
from db.pool import tenant_connection
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
from db.influx_queries import fetch_device_telemetry_influx, fetch_device_events_influx
from services.alert_dispatcher import dispatch_to_integration, AlertPayload
from services.email_sender import send_alert_email
from services.mqtt_sender import publish_alert

logger = logging.getLogger(__name__)

PG_HOST = os.getenv("PG_HOST", "iot-postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "iotcloud")
PG_USER = os.getenv("PG_USER", "iot")
PG_PASS = os.getenv("PG_PASS", "iot_dev")

UI_REFRESH_SECONDS = int(os.getenv("UI_REFRESH_SECONDS", "5"))

templates = Jinja2Templates(directory="/app/templates")
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


def _normalize_json(value) -> dict:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, (bytes, bytearray)):
        try:
            value = value.decode("utf-8")
        except Exception:
            return {}
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except Exception:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


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
        async with tenant_connection(p, tenant_id) as conn:
            device_counts = await fetch_device_count(conn, tenant_id)
            devices = await fetch_devices(conn, tenant_id, limit=50, offset=0)
            alerts = await fetch_alerts(conn, tenant_id, limit=20)
            delivery_attempts = await fetch_delivery_attempts(conn, tenant_id, limit=10)
    except Exception:
        logger.exception("Failed to load customer dashboard")
        raise HTTPException(status_code=500, detail="Internal server error")

    return templates.TemplateResponse(
        "customer/dashboard.html",
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


@router.get("/snmp-integrations", include_in_schema=False)
async def snmp_integrations_page(request: Request):
    """Render SNMP integrations page."""
    tenant_id = get_tenant_id()
    return templates.TemplateResponse(
        "customer/snmp_integrations.html",
        {"request": request, "tenant_id": tenant_id, "user": getattr(request.state, "user", None)},
    )


@router.get("/email-integrations", include_in_schema=False)
async def email_integrations_page(request: Request):
    """Render email integrations page."""
    tenant_id = get_tenant_id()
    return templates.TemplateResponse(
        "customer/email_integrations.html",
        {"request": request, "tenant_id": tenant_id, "user": getattr(request.state, "user", None)},
    )


@router.get("/mqtt-integrations", include_in_schema=False)
async def mqtt_integrations_page(request: Request):
    """Render MQTT integrations page."""
    tenant_id = get_tenant_id()
    return templates.TemplateResponse(
        "customer/mqtt_integrations.html",
        {"request": request, "tenant_id": tenant_id, "user": getattr(request.state, "user", None)},
    )


@router.get("/webhooks", include_in_schema=False)
async def webhooks_page(request: Request):
    """Render webhook integrations page."""
    tenant_id = get_tenant_id()
    return templates.TemplateResponse(
        "customer/webhook_integrations.html",
        {"request": request, "tenant_id": tenant_id, "user": getattr(request.state, "user", None)},
    )


@router.get("/devices", response_class=HTMLResponse)
async def list_devices(
    request: Request,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    format: str = Query("html"),
):
    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            devices = await fetch_devices(conn, tenant_id, limit=limit, offset=offset)
    except Exception:
        logger.exception("Failed to fetch tenant devices")
        raise HTTPException(status_code=500, detail="Internal server error")

    if format == "json":
        payload = {
            "tenant_id": tenant_id,
            "devices": devices,
            "limit": limit,
            "offset": offset,
        }
        return JSONResponse(jsonable_encoder(payload))

    return templates.TemplateResponse(
        "customer/devices.html",
        {
            "request": request,
            "tenant_id": tenant_id,
            "devices": devices,
            "user": getattr(request.state, "user", None),
        },
    )


@router.get("/devices/{device_id}", response_class=HTMLResponse)
async def get_device_detail(
    request: Request,
    device_id: str,
    format: str = Query("html"),
):
    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            device = await fetch_device(conn, tenant_id, device_id)
            if not device:
                raise HTTPException(status_code=404, detail="Device not found")

            if INFLUXDB_READ_ENABLED:
                ic = _get_influx_client()
                events = await fetch_device_events_influx(ic, tenant_id, device_id, limit=50)
                telemetry = await fetch_device_telemetry_influx(ic, tenant_id, device_id, limit=120)
            else:
                events = await fetch_device_events(conn, tenant_id, device_id, limit=50)
                telemetry = await fetch_device_telemetry(conn, tenant_id, device_id, limit=120)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch tenant device detail")
        raise HTTPException(status_code=500, detail="Internal server error")

    if format == "json":
        payload = {
            "tenant_id": tenant_id,
            "device": device,
            "events": events,
            "telemetry": telemetry,
        }
        return JSONResponse(jsonable_encoder(payload))

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
        "customer/device.html",
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


@router.get("/alerts", response_class=HTMLResponse)
async def list_alerts(
    request: Request,
    status: str = Query("OPEN"),
    limit: int = Query(100, ge=1, le=500),
    format: str = Query("html"),
):
    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            alerts = await fetch_alerts(conn, tenant_id, status=status, limit=limit)
    except Exception:
        logger.exception("Failed to fetch tenant alerts")
        raise HTTPException(status_code=500, detail="Internal server error")

    if format == "json":
        payload = {"tenant_id": tenant_id, "alerts": alerts, "status": status, "limit": limit}
        return JSONResponse(jsonable_encoder(payload))

    return templates.TemplateResponse(
        "customer/alerts.html",
        {
            "request": request,
            "tenant_id": tenant_id,
            "alerts": alerts,
            "status": status,
            "user": getattr(request.state, "user", None),
        },
    )


@router.get("/alerts/{alert_id}")
async def get_alert(alert_id: str):
    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
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
        async with tenant_connection(p, tenant_id) as conn:
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


@router.get("/integrations/snmp", response_model=list[SNMPIntegrationResponse])
async def list_snmp_integrations():
    """List all SNMP integrations for this tenant."""
    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            rows = await conn.fetch(
                """
                SELECT integration_id, tenant_id, name, snmp_host, snmp_port, snmp_config,
                       snmp_oid_prefix, enabled, created_at, updated_at
                FROM integrations
                WHERE tenant_id = $1 AND type = 'snmp'
                ORDER BY created_at DESC
                """,
                tenant_id,
            )
    except Exception:
        logger.exception("Failed to fetch SNMP integrations")
        raise HTTPException(status_code=500, detail="Internal server error")

    integrations: list[SNMPIntegrationResponse] = []
    for row in rows:
        snmp_config = _normalize_json(row["snmp_config"])
        integrations.append(
            SNMPIntegrationResponse(
                id=str(row["integration_id"]),
                tenant_id=str(row["tenant_id"]),
                name=row["name"],
                snmp_host=row["snmp_host"],
                snmp_port=row["snmp_port"],
                snmp_version=snmp_config.get("version", "2c"),
                snmp_oid_prefix=row["snmp_oid_prefix"],
                enabled=row["enabled"],
                created_at=row["created_at"].isoformat(),
                updated_at=row["updated_at"].isoformat(),
            )
        )
    return integrations


@router.get("/integrations/snmp/{integration_id}", response_model=SNMPIntegrationResponse)
async def get_snmp_integration(integration_id: str):
    """Get a specific SNMP integration."""
    tenant_id = get_tenant_id()
    try:
        UUID(integration_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Integration not found")

    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                SELECT integration_id, tenant_id, name, snmp_host, snmp_port, snmp_config,
                       snmp_oid_prefix, enabled, created_at, updated_at
                FROM integrations
                WHERE integration_id = $1 AND tenant_id = $2 AND type = 'snmp'
                """,
                integration_id,
                tenant_id,
            )
    except Exception:
        logger.exception("Failed to fetch SNMP integration")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not row:
        raise HTTPException(status_code=404, detail="Integration not found")

    snmp_config = _normalize_json(row["snmp_config"])
    return SNMPIntegrationResponse(
        id=str(row["integration_id"]),
        tenant_id=str(row["tenant_id"]),
        name=row["name"],
        snmp_host=row["snmp_host"],
        snmp_port=row["snmp_port"],
        snmp_version=snmp_config.get("version", "2c"),
        snmp_oid_prefix=row["snmp_oid_prefix"],
        enabled=row["enabled"],
        created_at=row["created_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
    )


@router.post(
    "/integrations/snmp",
    response_model=SNMPIntegrationResponse,
    status_code=201,
    dependencies=[Depends(require_customer_admin)],
)
async def create_snmp_integration(data: SNMPIntegrationCreate):
    """Create a new SNMP integration."""
    tenant_id = get_tenant_id()
    name = _validate_name(data.name)
    validation = validate_snmp_host(data.snmp_host, data.snmp_port)
    if not validation.valid:
        raise HTTPException(status_code=400, detail=f"Invalid SNMP destination: {validation.error}")
    integration_id = str(uuid.uuid4())
    now = datetime.datetime.utcnow()
    snmp_config = data.snmp_config.model_dump()

    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO integrations (
                    integration_id, tenant_id, name, type, snmp_host, snmp_port,
                    snmp_config, snmp_oid_prefix, enabled, created_at, updated_at
                )
                VALUES ($1, $2, $3, 'snmp', $4, $5, $6, $7, $8, $9, $10)
                RETURNING integration_id, tenant_id, name, snmp_host, snmp_port, snmp_config,
                          snmp_oid_prefix, enabled, created_at, updated_at
                """,
                integration_id,
                tenant_id,
                name,
                data.snmp_host,
                data.snmp_port,
                json.dumps(snmp_config),
                data.snmp_oid_prefix,
                data.enabled,
                now,
                now,
            )
    except Exception:
        logger.exception("Failed to create SNMP integration")
        raise HTTPException(status_code=500, detail="Internal server error")

    return SNMPIntegrationResponse(
        id=str(row["integration_id"]),
        tenant_id=str(row["tenant_id"]),
        name=row["name"],
        snmp_host=row["snmp_host"],
        snmp_port=row["snmp_port"],
        snmp_version=snmp_config.get("version", "2c"),
        snmp_oid_prefix=row["snmp_oid_prefix"],
        enabled=row["enabled"],
        created_at=row["created_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
    )


@router.patch(
    "/integrations/snmp/{integration_id}",
    response_model=SNMPIntegrationResponse,
    dependencies=[Depends(require_customer_admin)],
)
async def update_snmp_integration(integration_id: str, data: SNMPIntegrationUpdate):
    """Update an SNMP integration."""
    tenant_id = get_tenant_id()
    try:
        UUID(integration_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Integration not found")

    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    if data.snmp_host is not None:
        port = data.snmp_port if data.snmp_port is not None else 162
        validation = validate_snmp_host(data.snmp_host, port)
        if not validation.valid:
            raise HTTPException(status_code=400, detail=f"Invalid SNMP destination: {validation.error}")


    updates = []
    values = []
    param_idx = 1

    if "name" in update_data and update_data["name"] is not None:
        update_data["name"] = _validate_name(update_data["name"])

    for field in ["name", "snmp_host", "snmp_port", "snmp_oid_prefix", "enabled"]:
        if field in update_data and update_data[field] is not None:
            updates.append(f"{field} = ${param_idx}")
            values.append(update_data[field])
            param_idx += 1

    if "snmp_config" in update_data and update_data["snmp_config"] is not None:
        updates.append(f"snmp_config = ${param_idx}")
        values.append(json.dumps(data.snmp_config.model_dump()))
        param_idx += 1

    updates.append(f"updated_at = ${param_idx}")
    values.append(datetime.datetime.utcnow())
    param_idx += 1

    values.extend([integration_id, tenant_id])

    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            row = await conn.fetchrow(
                f"""
                UPDATE integrations
                SET {", ".join(updates)}
                WHERE integration_id = ${param_idx} AND tenant_id = ${param_idx + 1} AND type = 'snmp'
                RETURNING integration_id, tenant_id, name, snmp_host, snmp_port, snmp_config,
                          snmp_oid_prefix, enabled, created_at, updated_at
                """,
                *values,
            )
    except Exception:
        logger.exception("Failed to update SNMP integration")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not row:
        raise HTTPException(status_code=404, detail="Integration not found")

    snmp_config = _normalize_json(row["snmp_config"])
    return SNMPIntegrationResponse(
        id=str(row["integration_id"]),
        tenant_id=str(row["tenant_id"]),
        name=row["name"],
        snmp_host=row["snmp_host"],
        snmp_port=row["snmp_port"],
        snmp_version=snmp_config.get("version", "2c"),
        snmp_oid_prefix=row["snmp_oid_prefix"],
        enabled=row["enabled"],
        created_at=row["created_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
    )


@router.delete(
    "/integrations/snmp/{integration_id}",
    status_code=204,
    dependencies=[Depends(require_customer_admin)],
)
async def delete_snmp_integration(integration_id: str):
    """Delete an SNMP integration."""
    tenant_id = get_tenant_id()
    try:
        UUID(integration_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Integration not found")

    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            result = await conn.execute(
                """
                DELETE FROM integrations
                WHERE integration_id = $1 AND tenant_id = $2 AND type = 'snmp'
                """,
                integration_id,
                tenant_id,
            )
    except Exception:
        logger.exception("Failed to delete SNMP integration")
        raise HTTPException(status_code=500, detail="Internal server error")

    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Integration not found")

    return Response(status_code=204)


# ============================================================================
# EMAIL INTEGRATION ROUTES
# ============================================================================

@router.get("/integrations/email", response_model=list[EmailIntegrationResponse])
async def list_email_integrations():
    """List all email integrations for this tenant."""
    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            rows = await conn.fetch(
                """
                SELECT integration_id, tenant_id, name, email_config, email_recipients,
                       email_template, enabled, created_at, updated_at
                FROM integrations
                WHERE tenant_id = $1 AND type = 'email'
                ORDER BY created_at DESC
                """,
                tenant_id,
            )
    except Exception:
        logger.exception("Failed to fetch email integrations")
        raise HTTPException(status_code=500, detail="Internal server error")

    results = []
    for row in rows:
        email_config = _normalize_json(row["email_config"])
        email_recipients = _normalize_json(row["email_recipients"])
        email_template = _normalize_json(row["email_template"])
        results.append(
            EmailIntegrationResponse(
                id=str(row["integration_id"]),
                tenant_id=row["tenant_id"],
                name=row["name"],
                smtp_host=email_config.get("smtp_host", ""),
                smtp_port=email_config.get("smtp_port", 587),
                smtp_tls=email_config.get("smtp_tls", True),
                from_address=email_config.get("from_address", ""),
                recipient_count=len(email_recipients.get("to", [])),
                template_format=email_template.get("format", "html"),
                enabled=row["enabled"],
                created_at=row["created_at"].isoformat(),
                updated_at=row["updated_at"].isoformat(),
            )
        )
    return results


@router.get("/integrations/email/{integration_id}", response_model=EmailIntegrationResponse)
async def get_email_integration(integration_id: str):
    """Get a specific email integration."""
    tenant_id = get_tenant_id()
    try:
        UUID(integration_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Integration not found")

    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                SELECT integration_id, tenant_id, name, email_config, email_recipients,
                       email_template, enabled, created_at, updated_at
                FROM integrations
                WHERE integration_id = $1 AND tenant_id = $2 AND type = 'email'
                """,
                integration_id,
                tenant_id,
            )
    except Exception:
        logger.exception("Failed to fetch email integration")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not row:
        raise HTTPException(status_code=404, detail="Integration not found")

    email_config = _normalize_json(row["email_config"])
    email_recipients = _normalize_json(row["email_recipients"])
    email_template = _normalize_json(row["email_template"])
    return EmailIntegrationResponse(
        id=str(row["integration_id"]),
        tenant_id=row["tenant_id"],
        name=row["name"],
        smtp_host=email_config.get("smtp_host", ""),
        smtp_port=email_config.get("smtp_port", 587),
        smtp_tls=email_config.get("smtp_tls", True),
        from_address=email_config.get("from_address", ""),
        recipient_count=len(email_recipients.get("to", [])),
        template_format=email_template.get("format", "html"),
        enabled=row["enabled"],
        created_at=row["created_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
    )


@router.post(
    "/integrations/email",
    response_model=EmailIntegrationResponse,
    status_code=201,
    dependencies=[Depends(require_customer_admin)],
)
async def create_email_integration(data: EmailIntegrationCreate):
    """Create a new email integration."""
    tenant_id = get_tenant_id()
    name = _validate_name(data.name)
    validation = validate_email_integration(
        smtp_host=data.smtp_config.smtp_host,
        smtp_port=data.smtp_config.smtp_port,
        from_address=data.smtp_config.from_address,
        recipients=data.recipients.model_dump(),
    )
    if not validation.valid:
        raise HTTPException(status_code=400, detail=f"Invalid email configuration: {validation.error}")

    integration_id = str(uuid.uuid4())
    now = datetime.datetime.utcnow()

    email_config = data.smtp_config.model_dump()
    email_recipients = data.recipients.model_dump()
    email_template = data.template.model_dump() if data.template else {
        "subject_template": "[{severity}] {alert_type}: {device_id}",
        "format": "html",
    }

    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO integrations (
                    integration_id, tenant_id, name, type, email_config,
                    email_recipients, email_template, enabled, created_at, updated_at
                )
                VALUES ($1, $2, $3, 'email', $4, $5, $6, $7, $8, $9)
                RETURNING integration_id, tenant_id, name, email_config, email_recipients,
                          email_template, enabled, created_at, updated_at
                """,
                integration_id,
                tenant_id,
                name,
                json.dumps(email_config),
                json.dumps(email_recipients),
                json.dumps(email_template),
                data.enabled,
                now,
                now,
            )
    except Exception:
        logger.exception("Failed to create email integration")
        raise HTTPException(status_code=500, detail="Internal server error")

    return EmailIntegrationResponse(
        id=str(row["integration_id"]),
        tenant_id=row["tenant_id"],
        name=row["name"],
        smtp_host=email_config.get("smtp_host", ""),
        smtp_port=email_config.get("smtp_port", 587),
        smtp_tls=email_config.get("smtp_tls", True),
        from_address=email_config.get("from_address", ""),
        recipient_count=len(email_recipients.get("to", [])),
        template_format=email_template.get("format", "html"),
        enabled=row["enabled"],
        created_at=row["created_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
    )


@router.patch(
    "/integrations/email/{integration_id}",
    response_model=EmailIntegrationResponse,
    dependencies=[Depends(require_customer_admin)],
)
async def update_email_integration(integration_id: str, data: EmailIntegrationUpdate):
    """Update an email integration."""
    tenant_id = get_tenant_id()
    try:
        UUID(integration_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Integration not found")

    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    if "smtp_config" in update_data or "recipients" in update_data:
        try:
            p = await get_pool()
            async with tenant_connection(p, tenant_id) as conn:
                existing = await conn.fetchrow(
                    """
                    SELECT email_config, email_recipients
                    FROM integrations
                    WHERE integration_id = $1 AND tenant_id = $2 AND type = 'email'
                    """,
                    integration_id,
                    tenant_id,
                )
        except Exception:
            logger.exception("Failed to load email integration for validation")
            raise HTTPException(status_code=500, detail="Internal server error")

        if not existing:
            raise HTTPException(status_code=404, detail="Integration not found")

        smtp_config = data.smtp_config.model_dump() if data.smtp_config else _normalize_json(existing["email_config"])
        recipients = data.recipients.model_dump() if data.recipients else _normalize_json(existing["email_recipients"])
        validation = validate_email_integration(
            smtp_host=smtp_config.get("smtp_host", ""),
            smtp_port=smtp_config.get("smtp_port", 587),
            from_address=smtp_config.get("from_address", ""),
            recipients=recipients,
        )
        if not validation.valid:
            raise HTTPException(status_code=400, detail=f"Invalid email configuration: {validation.error}")

    updates = []
    values = []
    param_idx = 1

    if "name" in update_data and update_data["name"] is not None:
        update_data["name"] = _validate_name(update_data["name"])
        updates.append(f"name = ${param_idx}")
        values.append(update_data["name"])
        param_idx += 1

    if "smtp_config" in update_data and update_data["smtp_config"] is not None:
        updates.append(f"email_config = ${param_idx}")
        values.append(json.dumps(data.smtp_config.model_dump()))
        param_idx += 1

    if "recipients" in update_data and update_data["recipients"] is not None:
        updates.append(f"email_recipients = ${param_idx}")
        values.append(json.dumps(data.recipients.model_dump()))
        param_idx += 1

    if "template" in update_data and update_data["template"] is not None:
        updates.append(f"email_template = ${param_idx}")
        values.append(json.dumps(data.template.model_dump()))
        param_idx += 1

    if "enabled" in update_data and update_data["enabled"] is not None:
        updates.append(f"enabled = ${param_idx}")
        values.append(update_data["enabled"])
        param_idx += 1

    updates.append(f"updated_at = ${param_idx}")
    values.append(datetime.datetime.utcnow())
    param_idx += 1

    values.extend([integration_id, tenant_id])

    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            row = await conn.fetchrow(
                f"""
                UPDATE integrations
                SET {", ".join(updates)}
                WHERE integration_id = ${param_idx} AND tenant_id = ${param_idx + 1} AND type = 'email'
                RETURNING integration_id, tenant_id, name, email_config, email_recipients,
                          email_template, enabled, created_at, updated_at
                """,
                *values,
            )
    except Exception:
        logger.exception("Failed to update email integration")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not row:
        raise HTTPException(status_code=404, detail="Integration not found")

    email_config = _normalize_json(row["email_config"])
    email_recipients = _normalize_json(row["email_recipients"])
    email_template = _normalize_json(row["email_template"])

    return EmailIntegrationResponse(
        id=str(row["integration_id"]),
        tenant_id=row["tenant_id"],
        name=row["name"],
        smtp_host=email_config.get("smtp_host", ""),
        smtp_port=email_config.get("smtp_port", 587),
        smtp_tls=email_config.get("smtp_tls", True),
        from_address=email_config.get("from_address", ""),
        recipient_count=len(email_recipients.get("to", [])),
        template_format=email_template.get("format", "html"),
        enabled=row["enabled"],
        created_at=row["created_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
    )


@router.delete(
    "/integrations/email/{integration_id}",
    status_code=204,
    dependencies=[Depends(require_customer_admin)],
)
async def delete_email_integration(integration_id: str):
    """Delete an email integration."""
    tenant_id = get_tenant_id()
    try:
        UUID(integration_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Integration not found")

    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            result = await conn.execute(
                """
                DELETE FROM integrations
                WHERE integration_id = $1 AND tenant_id = $2 AND type = 'email'
                """,
                integration_id,
                tenant_id,
            )
    except Exception:
        logger.exception("Failed to delete email integration")
        raise HTTPException(status_code=500, detail="Internal server error")

    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Integration not found")

    return Response(status_code=204)


@router.get("/integrations/mqtt", response_model=list[MQTTIntegrationResponse])
async def list_mqtt_integrations():
    """List all MQTT integrations for this tenant."""
    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            rows = await conn.fetch(
                """
                SELECT integration_id, tenant_id, name, mqtt_topic, mqtt_qos,
                       mqtt_retain, enabled, created_at, updated_at
                FROM integrations
                WHERE tenant_id = $1 AND type = 'mqtt'
                ORDER BY created_at DESC
                """,
                tenant_id,
            )
    except Exception:
        logger.exception("Failed to fetch MQTT integrations")
        raise HTTPException(status_code=500, detail="Internal server error")

    results = []
    for row in rows:
        results.append(
            MQTTIntegrationResponse(
                id=str(row["integration_id"]),
                tenant_id=str(row["tenant_id"]),
                name=row["name"],
                mqtt_topic=row["mqtt_topic"],
                mqtt_qos=row["mqtt_qos"],
                mqtt_retain=row["mqtt_retain"],
                enabled=row["enabled"],
                created_at=row["created_at"].isoformat(),
                updated_at=row["updated_at"].isoformat(),
            )
        )
    return results


@router.get("/integrations/mqtt/{integration_id}", response_model=MQTTIntegrationResponse)
async def get_mqtt_integration(integration_id: str):
    """Get a specific MQTT integration."""
    tenant_id = get_tenant_id()
    try:
        UUID(integration_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Integration not found")

    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                SELECT integration_id, tenant_id, name, mqtt_topic, mqtt_qos,
                       mqtt_retain, enabled, created_at, updated_at
                FROM integrations
                WHERE integration_id = $1 AND tenant_id = $2 AND type = 'mqtt'
                """,
                integration_id,
                tenant_id,
            )
    except Exception:
        logger.exception("Failed to fetch MQTT integration")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not row:
        raise HTTPException(status_code=404, detail="Integration not found")

    return MQTTIntegrationResponse(
        id=str(row["integration_id"]),
        tenant_id=str(row["tenant_id"]),
        name=row["name"],
        mqtt_topic=row["mqtt_topic"],
        mqtt_qos=row["mqtt_qos"],
        mqtt_retain=row["mqtt_retain"],
        enabled=row["enabled"],
        created_at=row["created_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
    )


@router.post(
    "/integrations/mqtt",
    response_model=MQTTIntegrationResponse,
    status_code=201,
    dependencies=[Depends(require_customer_admin)],
)
async def create_mqtt_integration(data: MQTTIntegrationCreate):
    """Create a new MQTT integration."""
    tenant_id = get_tenant_id()
    name = _validate_name(data.name)
    validation = validate_mqtt_topic(data.mqtt_topic, tenant_id)
    if not validation.valid:
        raise HTTPException(status_code=400, detail=f"Invalid MQTT topic: {validation.error}")

    integration_id = str(uuid.uuid4())
    now = datetime.datetime.utcnow()

    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO integrations (
                    integration_id, tenant_id, name, type, mqtt_topic,
                    mqtt_qos, mqtt_retain, enabled, created_at, updated_at
                )
                VALUES ($1, $2, $3, 'mqtt', $4, $5, $6, $7, $8, $9)
                RETURNING integration_id, tenant_id, name, mqtt_topic, mqtt_qos,
                          mqtt_retain, enabled, created_at, updated_at
                """,
                integration_id,
                tenant_id,
                name,
                data.mqtt_topic,
                data.mqtt_qos,
                data.mqtt_retain,
                data.enabled,
                now,
                now,
            )
    except Exception:
        logger.exception("Failed to create MQTT integration")
        raise HTTPException(status_code=500, detail="Internal server error")

    return MQTTIntegrationResponse(
        id=str(row["integration_id"]),
        tenant_id=str(row["tenant_id"]),
        name=row["name"],
        mqtt_topic=row["mqtt_topic"],
        mqtt_qos=row["mqtt_qos"],
        mqtt_retain=row["mqtt_retain"],
        enabled=row["enabled"],
        created_at=row["created_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
    )


@router.patch(
    "/integrations/mqtt/{integration_id}",
    response_model=MQTTIntegrationResponse,
    dependencies=[Depends(require_customer_admin)],
)
async def update_mqtt_integration(integration_id: str, data: MQTTIntegrationUpdate):
    """Update a MQTT integration."""
    tenant_id = get_tenant_id()
    try:
        UUID(integration_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Integration not found")

    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    if "mqtt_topic" in update_data and update_data["mqtt_topic"] is not None:
        validation = validate_mqtt_topic(update_data["mqtt_topic"], tenant_id)
        if not validation.valid:
            raise HTTPException(status_code=400, detail=f"Invalid MQTT topic: {validation.error}")

    updates = []
    values = []
    param_idx = 1

    if "name" in update_data and update_data["name"] is not None:
        update_data["name"] = _validate_name(update_data["name"])

    for field in ["name", "mqtt_topic", "mqtt_qos", "mqtt_retain", "enabled"]:
        if field in update_data and update_data[field] is not None:
            updates.append(f"{field} = ${param_idx}")
            values.append(update_data[field])
            param_idx += 1

    updates.append(f"updated_at = ${param_idx}")
    values.append(datetime.datetime.utcnow())
    param_idx += 1

    values.extend([integration_id, tenant_id])

    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            row = await conn.fetchrow(
                f"""
                UPDATE integrations
                SET {", ".join(updates)}
                WHERE integration_id = ${param_idx} AND tenant_id = ${param_idx + 1} AND type = 'mqtt'
                RETURNING integration_id, tenant_id, name, mqtt_topic, mqtt_qos,
                          mqtt_retain, enabled, created_at, updated_at
                """,
                *values,
            )
    except Exception:
        logger.exception("Failed to update MQTT integration")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not row:
        raise HTTPException(status_code=404, detail="Integration not found")

    return MQTTIntegrationResponse(
        id=str(row["integration_id"]),
        tenant_id=str(row["tenant_id"]),
        name=row["name"],
        mqtt_topic=row["mqtt_topic"],
        mqtt_qos=row["mqtt_qos"],
        mqtt_retain=row["mqtt_retain"],
        enabled=row["enabled"],
        created_at=row["created_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
    )


@router.delete(
    "/integrations/mqtt/{integration_id}",
    status_code=204,
    dependencies=[Depends(require_customer_admin)],
)
async def delete_mqtt_integration(integration_id: str):
    """Delete a MQTT integration."""
    tenant_id = get_tenant_id()
    try:
        UUID(integration_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Integration not found")

    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            result = await conn.execute(
                """
                DELETE FROM integrations
                WHERE integration_id = $1 AND tenant_id = $2 AND type = 'mqtt'
                """,
                integration_id,
                tenant_id,
            )
    except Exception:
        logger.exception("Failed to delete MQTT integration")
        raise HTTPException(status_code=500, detail="Internal server error")

    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Integration not found")

    return Response(status_code=204)


@router.post(
    "/integrations/mqtt/{integration_id}/test",
    dependencies=[Depends(require_customer_admin)],
)
async def test_mqtt_integration(integration_id: str):
    """Send a test MQTT message."""
    tenant_id = get_tenant_id()

    try:
        UUID(integration_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Integration not found")

    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            allowed, _ = await check_and_increment_rate_limit(
                conn,
                tenant_id=tenant_id,
                action=f"test_delivery:{integration_id}",
                limit=5,
                window_seconds=60,
            )
            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded. Maximum 5 test deliveries per minute.",
                )

            row = await conn.fetchrow(
                """
                SELECT integration_id, tenant_id, name, type, mqtt_topic,
                       mqtt_qos, mqtt_retain, mqtt_config, enabled
                FROM integrations
                WHERE integration_id = $1 AND tenant_id = $2 AND type = 'mqtt'
                """,
                integration_id,
                tenant_id,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch MQTT integration for test")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not row:
        raise HTTPException(status_code=404, detail="Integration not found")

    now = datetime.datetime.utcnow().replace(microsecond=0)
    timestamp = now.isoformat() + "Z"
    test_values = {
        "tenant_id": tenant_id,
        "severity": "INFO",
        "site_id": "test-site",
        "device_id": "test-device",
        "alert_id": "test-alert-001",
        "alert_type": "test",
    }

    resolved_topic = row["mqtt_topic"]
    for key, value in test_values.items():
        resolved_topic = resolved_topic.replace(f"{{{key}}}", value)

    payload = {
        **test_values,
        "message": "Test MQTT delivery from OpsConductor Pulse",
        "timestamp": timestamp,
    }

    mqtt_config = _normalize_json(row["mqtt_config"])
    broker_url = mqtt_config.get("broker_url") or "mqtt://iot-mqtt:1883"

    result = await publish_alert(
        broker_url=broker_url,
        topic=resolved_topic,
        payload=json.dumps(payload),
        qos=row["mqtt_qos"] if row["mqtt_qos"] is not None else 1,
        retain=row["mqtt_retain"] if row["mqtt_retain"] is not None else False,
    )

    return {
        "success": result.success,
        "error": result.error,
        "duration_ms": result.duration_ms,
    }


@router.post("/integrations", dependencies=[Depends(require_customer_admin)])
async def create_integration_route(body: IntegrationCreate):
    tenant_id = get_tenant_id()
    name = _validate_name(body.name)
    valid, error = await validate_webhook_url(body.webhook_url)
    if not valid:
        raise HTTPException(status_code=400, detail=f"Invalid webhook URL: {error}")
    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
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
        async with tenant_connection(p, tenant_id) as conn:
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
        valid, error = await validate_webhook_url(body.webhook_url)
        if not valid:
            raise HTTPException(status_code=400, detail=f"Invalid webhook URL: {error}")

    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
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
        async with tenant_connection(p, tenant_id) as conn:
            deleted = await delete_integration(conn, tenant_id, integration_id)
    except Exception:
        logger.exception("Failed to delete integration")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not deleted:
        raise HTTPException(status_code=404, detail="Integration not found")
    return Response(status_code=204)


@router.post(
    "/integrations/snmp/{integration_id}/test",
    dependencies=[Depends(require_customer_admin)],
)
async def test_snmp_integration(integration_id: str):
    """Send a test SNMP trap."""
    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            allowed, _ = await check_and_increment_rate_limit(
                conn,
                tenant_id=tenant_id,
                action=f"test_delivery:{integration_id}",
                limit=5,
                window_seconds=60,
            )
            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded. Maximum 5 test deliveries per minute.",
                )

            row = await conn.fetchrow(
                """
                SELECT integration_id, tenant_id, name, type, snmp_host, snmp_port,
                       snmp_config, snmp_oid_prefix, enabled
                FROM integrations
                WHERE integration_id = $1 AND tenant_id = $2 AND type = 'snmp'
                """,
                integration_id,
                tenant_id,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch SNMP integration for test")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not row:
        raise HTTPException(status_code=404, detail="Integration not found")

    test_alert = AlertPayload(
        alert_id=f"test-{int(datetime.datetime.utcnow().timestamp())}",
        device_id="test-device",
        tenant_id=tenant_id,
        severity="info",
        message="Test trap from OpsConductor Pulse",
        timestamp=datetime.datetime.utcnow(),
    )

    integration = {
        "integration_id": row["integration_id"],
        "name": row["name"],
        "type": row["type"],
        "snmp_host": row["snmp_host"],
        "snmp_port": row["snmp_port"],
        "snmp_config": _normalize_json(row["snmp_config"]),
        "snmp_oid_prefix": row["snmp_oid_prefix"],
        "enabled": True,
    }

    result = await dispatch_to_integration(test_alert, integration)

    return {
        "success": result.success,
        "integration_id": integration_id,
        "integration_name": row["name"],
        "destination": f"{row['snmp_host']}:{row['snmp_port']}",
        "error": result.error,
        "duration_ms": result.duration_ms,
        "latency_ms": result.duration_ms,
    }


@router.post(
    "/integrations/email/{integration_id}/test",
    dependencies=[Depends(require_customer_admin)],
)
async def test_email_integration(integration_id: str):
    """Send a test email."""
    tenant_id = get_tenant_id()

    try:
        UUID(integration_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Integration not found")

    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            # Rate limit
            allowed, _ = await check_and_increment_rate_limit(
                conn,
                tenant_id=tenant_id,
                action=f"test_delivery:{integration_id}",
                limit=5,
                window_seconds=60,
            )
            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded. Maximum 5 test deliveries per minute.",
                )

            row = await conn.fetchrow(
                """
                SELECT integration_id, tenant_id, name, type, email_config,
                       email_recipients, email_template, enabled
                FROM integrations
                WHERE integration_id = $1 AND tenant_id = $2 AND type = 'email'
                """,
                integration_id,
                tenant_id,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch email integration for test")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not row:
        raise HTTPException(status_code=404, detail="Integration not found")

    email_config = _normalize_json(row["email_config"])
    email_recipients = _normalize_json(row["email_recipients"])
    email_template = _normalize_json(row["email_template"])

    # Send test email
    result = await send_alert_email(
        smtp_host=email_config.get("smtp_host", ""),
        smtp_port=email_config.get("smtp_port", 587),
        smtp_user=email_config.get("smtp_user"),
        smtp_password=email_config.get("smtp_password"),
        smtp_tls=email_config.get("smtp_tls", True),
        from_address=email_config.get("from_address", ""),
        from_name=email_config.get("from_name", "OpsConductor Alerts"),
        recipients=email_recipients,
        alert_id=f"test-{int(datetime.datetime.utcnow().timestamp())}",
        device_id="test-device",
        tenant_id=tenant_id,
        severity="info",
        message="This is a test email from OpsConductor Pulse. If you received this, your email integration is working correctly.",
        alert_type="TEST_ALERT",
        timestamp=datetime.datetime.utcnow(),
        subject_template=email_template.get("subject_template"),
        body_template=email_template.get("body_template"),
        body_format=email_template.get("format", "html"),
    )

    return {
        "success": result.success,
        "integration_id": integration_id,
        "integration_name": row["name"],
        "recipients_count": result.recipients_count,
        "error": result.error,
        "duration_ms": result.duration_ms,
    }


@router.post("/integrations/{integration_id}/test", dependencies=[Depends(require_customer_admin)])
async def test_integration_delivery(integration_id: str):
    """Send a test delivery to any integration type."""
    tenant_id = get_tenant_id()
    try:
        UUID(integration_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Integration not found")

    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            allowed, _ = await check_and_increment_rate_limit(
                conn,
                tenant_id=tenant_id,
                action=f"test_delivery:{integration_id}",
                limit=5,
                window_seconds=60,
            )
            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded. Maximum 5 test deliveries per minute.",
                )

            row = await conn.fetchrow(
                """
                SELECT integration_id, tenant_id, name, type,
                       config_json->>'url' AS webhook_url,
                       snmp_host, snmp_port, snmp_config, snmp_oid_prefix,
                       email_config, email_recipients, email_template,
                       enabled
                FROM integrations
                WHERE integration_id = $1 AND tenant_id = $2
                """,
                integration_id,
                tenant_id,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch integration for test")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not row:
        raise HTTPException(status_code=404, detail="Integration not found")

    integration_type = row["type"]
    now = datetime.datetime.utcnow()

    if integration_type == "email":
        # Email delivery
        email_config = _normalize_json(row["email_config"])
        email_recipients = _normalize_json(row["email_recipients"])
        email_template = _normalize_json(row["email_template"])

        result = await send_alert_email(
            smtp_host=email_config.get("smtp_host", ""),
            smtp_port=email_config.get("smtp_port", 587),
            smtp_user=email_config.get("smtp_user"),
            smtp_password=email_config.get("smtp_password"),
            smtp_tls=email_config.get("smtp_tls", True),
            from_address=email_config.get("from_address", ""),
            from_name=email_config.get("from_name", "OpsConductor Alerts"),
            recipients=email_recipients,
            alert_id=f"test-{int(now.timestamp())}",
            device_id="test-device",
            tenant_id=tenant_id,
            severity="info",
            message="Test delivery from OpsConductor Pulse",
            alert_type="TEST_ALERT",
            timestamp=now,
            subject_template=email_template.get("subject_template"),
            body_template=email_template.get("body_template"),
            body_format=email_template.get("format", "html"),
        )

        return {
            "success": result.success,
            "integration_id": integration_id,
            "integration_name": row["name"],
            "integration_type": "email",
            "destination": f"{len((email_recipients.get('to', [])))} recipients",
            "error": result.error,
            "duration_ms": result.duration_ms,
            "latency_ms": result.duration_ms,
        }

    elif integration_type == "snmp":
        # SNMP delivery (existing code)
        test_alert = AlertPayload(
            alert_id=f"test-{int(now.timestamp())}",
            device_id="test-device",
            tenant_id=tenant_id,
            severity="info",
            message="Test delivery from OpsConductor Pulse",
            timestamp=now,
        )

        integration_dict = dict(row)
        integration_dict["enabled"] = True

        result = await dispatch_to_integration(test_alert, integration_dict)

        return {
            "success": result.success,
            "integration_id": integration_id,
            "integration_name": row["name"],
            "integration_type": "snmp",
            "destination": f"{row['snmp_host']}:{row['snmp_port']}",
            "error": result.error,
            "duration_ms": result.duration_ms,
            "latency_ms": result.duration_ms,
        }

    else:
        # Webhook delivery (existing code)
        test_alert = AlertPayload(
            alert_id=f"test-{int(now.timestamp())}",
            device_id="test-device",
            tenant_id=tenant_id,
            severity="info",
            message="Test delivery from OpsConductor Pulse",
            timestamp=now,
        )

        integration_dict = dict(row)
        integration_dict["enabled"] = True
        integration_dict["webhook_url"] = row["webhook_url"]

        result = await dispatch_to_integration(test_alert, integration_dict)

        return {
            "success": result.success,
            "integration_id": integration_id,
            "integration_name": row["name"],
            "integration_type": "webhook",
            "destination": row["webhook_url"],
            "error": result.error,
            "duration_ms": result.duration_ms,
            "latency_ms": result.duration_ms,
        }


@router.get("/integration-routes")
async def list_integration_routes(limit: int = Query(100, ge=1, le=500)):
    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
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
        async with tenant_connection(p, tenant_id) as conn:
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
        async with tenant_connection(p, tenant_id) as conn:
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
        async with tenant_connection(p, tenant_id) as conn:
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
        async with tenant_connection(p, tenant_id) as conn:
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
        async with tenant_connection(p, tenant_id) as conn:
            attempts = await fetch_delivery_attempts(conn, tenant_id, limit=limit)
    except Exception:
        logger.exception("Failed to fetch tenant delivery attempts")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"tenant_id": tenant_id, "attempts": attempts}
