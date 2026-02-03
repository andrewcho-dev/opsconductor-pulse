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
from utils.url_validator import validate_webhook_url
from utils.snmp_validator import validate_snmp_host
from utils.email_validator import validate_email_integration
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
from services.alert_dispatcher import dispatch_to_integration, AlertPayload

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
        async with tenant_connection(p, tenant_id) as conn:
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


@router.get("/snmp-integrations", include_in_schema=False)
async def snmp_integrations_page(request: Request):
    """Render SNMP integrations page."""
    tenant_id = get_tenant_id()
    return templates.TemplateResponse(
        "customer/snmp_integrations.html",
        {"request": request, "tenant_id": tenant_id, "user": getattr(request.state, "user", None)},
    )


@router.get("/devices")
async def list_devices(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
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
        async with tenant_connection(p, tenant_id) as conn:
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
        async with tenant_connection(p, tenant_id) as conn:
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

    return [
        SNMPIntegrationResponse(
            id=row["integration_id"],
            tenant_id=row["tenant_id"],
            name=row["name"],
            snmp_host=row["snmp_host"],
            snmp_port=row["snmp_port"],
            snmp_version=(row["snmp_config"] or {}).get("version", "2c"),
            snmp_oid_prefix=row["snmp_oid_prefix"],
            enabled=row["enabled"],
            created_at=row["created_at"].isoformat(),
            updated_at=row["updated_at"].isoformat(),
        )
        for row in rows
    ]


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

    return SNMPIntegrationResponse(
        id=row["integration_id"],
        tenant_id=row["tenant_id"],
        name=row["name"],
        snmp_host=row["snmp_host"],
        snmp_port=row["snmp_port"],
        snmp_version=(row["snmp_config"] or {}).get("version", "2c"),
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
        id=row["integration_id"],
        tenant_id=row["tenant_id"],
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

    return SNMPIntegrationResponse(
        id=row["integration_id"],
        tenant_id=row["tenant_id"],
        name=row["name"],
        snmp_host=row["snmp_host"],
        snmp_port=row["snmp_port"],
        snmp_version=(row["snmp_config"] or {}).get("version", "2c"),
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

    return [
        EmailIntegrationResponse(
            id=str(row["integration_id"]),
            tenant_id=row["tenant_id"],
            name=row["name"],
            smtp_host=(row["email_config"] or {}).get("smtp_host", ""),
            smtp_port=(row["email_config"] or {}).get("smtp_port", 587),
            smtp_tls=(row["email_config"] or {}).get("smtp_tls", True),
            from_address=(row["email_config"] or {}).get("from_address", ""),
            recipient_count=len((row["email_recipients"] or {}).get("to", [])),
            template_format=(row["email_template"] or {}).get("format", "html"),
            enabled=row["enabled"],
            created_at=row["created_at"].isoformat(),
            updated_at=row["updated_at"].isoformat(),
        )
        for row in rows
    ]


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

    return EmailIntegrationResponse(
        id=str(row["integration_id"]),
        tenant_id=row["tenant_id"],
        name=row["name"],
        smtp_host=(row["email_config"] or {}).get("smtp_host", ""),
        smtp_port=(row["email_config"] or {}).get("smtp_port", 587),
        smtp_tls=(row["email_config"] or {}).get("smtp_tls", True),
        from_address=(row["email_config"] or {}).get("from_address", ""),
        recipient_count=len((row["email_recipients"] or {}).get("to", [])),
        template_format=(row["email_template"] or {}).get("format", "html"),
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

        smtp_config = data.smtp_config.model_dump() if data.smtp_config else (existing["email_config"] or {})
        recipients = data.recipients.model_dump() if data.recipients else (existing["email_recipients"] or {})
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

    email_config = row["email_config"] or {}
    email_recipients = row["email_recipients"] or {}
    email_template = row["email_template"] or {}

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
                action="test_delivery",
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
        "snmp_config": row["snmp_config"],
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
    }


@router.post("/integrations/{integration_id}/test", dependencies=[Depends(require_customer_admin)])
async def test_integration_delivery(integration_id: str):
    """Send a test delivery to any integration type."""
    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
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

            row = await conn.fetchrow(
                """
                SELECT integration_id, tenant_id, name, type,
                       config_json->>'url' AS webhook_url,
                       snmp_host, snmp_port, snmp_config, snmp_oid_prefix, enabled
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

    test_alert = AlertPayload(
        alert_id=f"test-{int(datetime.datetime.utcnow().timestamp())}",
        device_id="test-device",
        tenant_id=tenant_id,
        severity="info",
        message="Test delivery from OpsConductor Pulse",
        timestamp=datetime.datetime.utcnow(),
    )

    integration = dict(row)
    integration["enabled"] = True
    integration["webhook_url"] = row["webhook_url"]

    result = await dispatch_to_integration(test_alert, integration)

    response = {
        "success": result.success,
        "integration_id": integration_id,
        "integration_name": row["name"],
        "integration_type": row["type"],
        "error": result.error,
        "duration_ms": result.duration_ms,
    }

    if row["type"] == "webhook":
        response["destination"] = row["webhook_url"]
    elif row["type"] == "snmp":
        response["destination"] = f"{row['snmp_host']}:{row['snmp_port']}"

    return response


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
