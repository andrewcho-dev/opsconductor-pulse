import os
import logging
import re
import datetime
import json
import uuid
from uuid import UUID
import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.requests import Request

from middleware.auth import JWTBearer
from middleware.tenant import inject_tenant_context, get_tenant_id, require_customer, get_user
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
    create_alert_rule,
    create_integration,
    create_integration_route,
    delete_alert_rule,
    delete_integration,
    delete_integration_route,
    fetch_alerts,
    fetch_alert_rule,
    fetch_alert_rules,
    fetch_delivery_attempts,
    fetch_device,
    fetch_devices_v2,
    fetch_integration,
    fetch_integration_route,
    fetch_integration_routes,
    fetch_integrations,
    update_alert_rule,
    update_integration,
    update_integration_route,
)
from db.telemetry_queries import fetch_device_telemetry, fetch_device_events
from services.alert_dispatcher import dispatch_to_integration, AlertPayload
from services.email_sender import send_alert_email
from services.mqtt_sender import publish_alert

# Compatibility shim for tests expecting fetch_devices in this module.
fetch_devices = fetch_devices_v2

logger = logging.getLogger(__name__)

PG_HOST = os.getenv("PG_HOST", "iot-postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "iotcloud")
PG_USER = os.getenv("PG_USER", "iot")
PG_PASS = os.getenv("PG_PASS", "iot_dev")

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


NAME_PATTERN = re.compile(r"^[A-Za-z0-9 _-]+$")
METRIC_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


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


VALID_OPERATORS = {"GT", "LT", "GTE", "LTE"}


class AlertRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    metric_name: str = Field(..., min_length=1, max_length=100)
    operator: str = Field(...)
    threshold: float
    severity: int = Field(default=3, ge=1, le=5)
    description: str | None = None
    site_ids: list[str] | None = None
    enabled: bool = True


class AlertRuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    metric_name: str | None = Field(default=None, min_length=1, max_length=100)
    operator: str | None = None
    threshold: float | None = None
    severity: int | None = Field(default=None, ge=1, le=5)
    description: str | None = None
    site_ids: list[str] | None = None
    enabled: bool | None = None


class MetricCatalogUpsert(BaseModel):
    metric_name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    unit: str | None = None
    expected_min: float | None = None
    expected_max: float | None = None


class NormalizedMetricCreate(BaseModel):
    normalized_name: str = Field(min_length=1, max_length=100)
    display_unit: str | None = None
    description: str | None = None
    expected_min: float | None = None
    expected_max: float | None = None


class NormalizedMetricUpdate(BaseModel):
    display_unit: str | None = None
    description: str | None = None
    expected_min: float | None = None
    expected_max: float | None = None


class MetricMappingCreate(BaseModel):
    raw_metric: str = Field(min_length=1, max_length=100)
    normalized_name: str = Field(min_length=1, max_length=100)
    multiplier: float | None = None
    offset_value: float | None = None

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


ALERT_TYPES = {"NO_HEARTBEAT", "THRESHOLD"}
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


@router.get("/devices")
async def list_devices(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            devices = await fetch_devices_v2(conn, tenant_id, limit=limit, offset=offset)
    except Exception:
        logger.exception("Failed to fetch tenant devices")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {
        "tenant_id": tenant_id,
        "devices": devices,
        "limit": limit,
        "offset": offset,
    }


@router.get("/devices/{device_id}")
async def get_device_detail(device_id: str):
    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            device = await fetch_device(conn, tenant_id, device_id)
            if not device:
                raise HTTPException(status_code=404, detail="Device not found")

            events = await fetch_device_events(conn, tenant_id, device_id, hours=24, limit=50)
            telemetry = await fetch_device_telemetry(conn, tenant_id, device_id, hours=6, limit=120)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch tenant device detail")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {
        "tenant_id": tenant_id,
        "device": device,
        "events": events,
        "telemetry": telemetry,
    }


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
async def list_integrations(type: str | None = Query(None)):
    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            rows = await fetch_integrations(conn, tenant_id, limit=50, integration_type=type)
    except Exception:
        logger.exception("Failed to fetch tenant integrations")
        raise HTTPException(status_code=500, detail="Internal server error")

    integrations = [dict(r) for r in rows]

    return {"tenant_id": tenant_id, "integrations": integrations}


@router.get("/metrics/catalog")
async def list_metric_catalog():
    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            rows = await conn.fetch(
                """
                SELECT metric_name, description, unit, expected_min, expected_max,
                       created_at, updated_at
                FROM metric_catalog
                WHERE tenant_id = $1
                ORDER BY metric_name
                """,
                tenant_id,
            )
    except Exception:
        logger.exception("Failed to fetch metric catalog")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"tenant_id": tenant_id, "metrics": [dict(r) for r in rows]}


@router.post("/metrics/catalog", dependencies=[Depends(require_customer_admin)])
async def upsert_metric_catalog(payload: MetricCatalogUpsert):
    tenant_id = get_tenant_id()
    metric_name = payload.metric_name.strip()
    if not metric_name:
        raise HTTPException(status_code=400, detail="metric_name is required")
    if payload.expected_min is not None and payload.expected_max is not None:
        if payload.expected_min > payload.expected_max:
            raise HTTPException(status_code=400, detail="expected_min must be <= expected_max")

    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO metric_catalog (
                    tenant_id, metric_name, description, unit, expected_min, expected_max
                ) VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (tenant_id, metric_name)
                DO UPDATE SET
                    description = EXCLUDED.description,
                    unit = EXCLUDED.unit,
                    expected_min = EXCLUDED.expected_min,
                    expected_max = EXCLUDED.expected_max,
                    updated_at = NOW()
                RETURNING metric_name, description, unit, expected_min, expected_max,
                          created_at, updated_at
                """,
                tenant_id,
                metric_name,
                payload.description,
                payload.unit,
                payload.expected_min,
                payload.expected_max,
            )
    except Exception:
        logger.exception("Failed to upsert metric catalog entry")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"tenant_id": tenant_id, "metric": dict(row)}


@router.delete("/metrics/catalog/{metric_name}", dependencies=[Depends(require_customer_admin)])
async def delete_metric_catalog(metric_name: str):
    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            result = await conn.execute(
                """
                DELETE FROM metric_catalog
                WHERE tenant_id = $1 AND metric_name = $2
                """,
                tenant_id,
                metric_name,
            )
    except Exception:
        logger.exception("Failed to delete metric catalog entry")
        raise HTTPException(status_code=500, detail="Internal server error")

    if result.endswith("0"):
        raise HTTPException(status_code=404, detail="Metric not found")

    return Response(status_code=204)


@router.get("/normalized-metrics")
async def list_normalized_metrics():
    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            rows = await conn.fetch(
                """
                SELECT normalized_name, display_unit, description, expected_min, expected_max,
                       created_at, updated_at
                FROM normalized_metrics
                WHERE tenant_id = $1
                ORDER BY normalized_name
                """,
                tenant_id,
            )
    except Exception:
        logger.exception("Failed to fetch normalized metrics")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"tenant_id": tenant_id, "metrics": [dict(r) for r in rows]}


@router.post("/normalized-metrics", dependencies=[Depends(require_customer_admin)])
async def create_normalized_metric(payload: NormalizedMetricCreate):
    tenant_id = get_tenant_id()
    normalized_name = _validate_name(payload.normalized_name)
    if payload.expected_min is not None and payload.expected_max is not None:
        if payload.expected_min > payload.expected_max:
            raise HTTPException(status_code=400, detail="expected_min must be <= expected_max")

    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO normalized_metrics (
                    tenant_id, normalized_name, display_unit, description, expected_min, expected_max
                ) VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (tenant_id, normalized_name)
                DO NOTHING
                RETURNING normalized_name, display_unit, description, expected_min, expected_max,
                          created_at, updated_at
                """,
                tenant_id,
                normalized_name,
                payload.display_unit,
                payload.description,
                payload.expected_min,
                payload.expected_max,
            )
    except Exception:
        logger.exception("Failed to create normalized metric")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not row:
        raise HTTPException(status_code=409, detail="Normalized metric already exists")

    return {"tenant_id": tenant_id, "metric": dict(row)}


@router.patch("/normalized-metrics/{name}", dependencies=[Depends(require_customer_admin)])
async def update_normalized_metric(name: str, payload: NormalizedMetricUpdate):
    tenant_id = get_tenant_id()
    normalized_name = _validate_name(name)
    if payload.expected_min is not None and payload.expected_max is not None:
        if payload.expected_min > payload.expected_max:
            raise HTTPException(status_code=400, detail="expected_min must be <= expected_max")
    if (
        payload.display_unit is None
        and payload.description is None
        and payload.expected_min is None
        and payload.expected_max is None
    ):
        raise HTTPException(status_code=400, detail="No fields provided")

    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                UPDATE normalized_metrics
                SET display_unit = $3,
                    description = $4,
                    expected_min = $5,
                    expected_max = $6,
                    updated_at = NOW()
                WHERE tenant_id = $1 AND normalized_name = $2
                RETURNING normalized_name, display_unit, description, expected_min, expected_max,
                          created_at, updated_at
                """,
                tenant_id,
                normalized_name,
                payload.display_unit,
                payload.description,
                payload.expected_min,
                payload.expected_max,
            )
    except Exception:
        logger.exception("Failed to update normalized metric")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not row:
        raise HTTPException(status_code=404, detail="Normalized metric not found")

    return {"tenant_id": tenant_id, "metric": dict(row)}


@router.delete("/normalized-metrics/{name}", dependencies=[Depends(require_customer_admin)])
async def delete_normalized_metric(name: str):
    tenant_id = get_tenant_id()
    normalized_name = _validate_name(name)
    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            result = await conn.execute(
                """
                DELETE FROM normalized_metrics
                WHERE tenant_id = $1 AND normalized_name = $2
                """,
                tenant_id,
                normalized_name,
            )
    except Exception:
        logger.exception("Failed to delete normalized metric")
        raise HTTPException(status_code=500, detail="Internal server error")

    if result.endswith("0"):
        raise HTTPException(status_code=404, detail="Normalized metric not found")

    return Response(status_code=204)


@router.get("/metric-mappings")
async def list_metric_mappings():
    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            rows = await conn.fetch(
                """
                SELECT raw_metric, normalized_name, multiplier, offset_value, created_at
                FROM metric_mappings
                WHERE tenant_id = $1
                ORDER BY raw_metric
                """,
                tenant_id,
            )
    except Exception:
        logger.exception("Failed to fetch metric mappings")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"tenant_id": tenant_id, "mappings": [dict(r) for r in rows]}


@router.post("/metric-mappings", dependencies=[Depends(require_customer_admin)])
async def create_metric_mapping(payload: MetricMappingCreate):
    tenant_id = get_tenant_id()
    raw_metric = payload.raw_metric.strip()
    if not METRIC_NAME_PATTERN.match(raw_metric):
        raise HTTPException(status_code=400, detail="Invalid raw metric name")
    normalized_name = _validate_name(payload.normalized_name)
    multiplier = payload.multiplier if payload.multiplier is not None else 1
    offset_value = payload.offset_value if payload.offset_value is not None else 0

    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            exists = await conn.fetchval(
                """
                SELECT 1 FROM normalized_metrics
                WHERE tenant_id = $1 AND normalized_name = $2
                """,
                tenant_id,
                normalized_name,
            )
            if not exists:
                raise HTTPException(status_code=404, detail="Normalized metric not found")

            row = await conn.fetchrow(
                """
                INSERT INTO metric_mappings (
                    tenant_id, raw_metric, normalized_name, multiplier, offset_value
                ) VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (tenant_id, raw_metric)
                DO UPDATE SET
                    normalized_name = EXCLUDED.normalized_name,
                    multiplier = EXCLUDED.multiplier,
                    offset_value = EXCLUDED.offset_value
                RETURNING raw_metric, normalized_name, multiplier, offset_value, created_at
                """,
                tenant_id,
                raw_metric,
                normalized_name,
                multiplier,
                offset_value,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to create metric mapping")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"tenant_id": tenant_id, "mapping": dict(row)}


@router.delete("/metric-mappings/{raw_metric}", dependencies=[Depends(require_customer_admin)])
async def delete_metric_mapping(raw_metric: str):
    tenant_id = get_tenant_id()
    raw_metric = raw_metric.strip()
    if not METRIC_NAME_PATTERN.match(raw_metric):
        raise HTTPException(status_code=400, detail="Invalid raw metric name")
    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            result = await conn.execute(
                """
                DELETE FROM metric_mappings
                WHERE tenant_id = $1 AND raw_metric = $2
                """,
                tenant_id,
                raw_metric,
            )
    except Exception:
        logger.exception("Failed to delete metric mapping")
        raise HTTPException(status_code=500, detail="Internal server error")

    if result.endswith("0"):
        raise HTTPException(status_code=404, detail="Metric mapping not found")

    return Response(status_code=204)


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


@router.get("/alert-rules")
async def list_alert_rules():
    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            rules = await fetch_alert_rules(conn, tenant_id)
    except Exception:
        logger.exception("Failed to fetch alert rules")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"tenant_id": tenant_id, "rules": rules}


@router.get("/alert-rules/{rule_id}")
async def get_alert_rule(rule_id: str):
    try:
        UUID(rule_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid rule_id format: must be a valid UUID")

    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            rule = await fetch_alert_rule(conn, tenant_id, rule_id)
    except Exception:
        logger.exception("Failed to fetch alert rule")
        raise HTTPException(status_code=500, detail="Internal server error")
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return rule


@router.post("/alert-rules", dependencies=[Depends(require_customer_admin)])
async def create_alert_rule_endpoint(body: AlertRuleCreate):
    tenant_id = get_tenant_id()
    if body.operator not in VALID_OPERATORS:
        raise HTTPException(status_code=400, detail="Invalid operator value")
    if not METRIC_NAME_PATTERN.match(body.metric_name):
        raise HTTPException(status_code=400, detail="Invalid metric_name format")
    if body.site_ids is not None:
        for site_id in body.site_ids:
            if site_id is None or not str(site_id).strip():
                raise HTTPException(status_code=400, detail="Invalid site_id value")
    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            rule = await create_alert_rule(
                conn,
                tenant_id=tenant_id,
                name=body.name,
                metric_name=body.metric_name,
                operator=body.operator,
                threshold=body.threshold,
                severity=body.severity,
                description=body.description,
                site_ids=body.site_ids,
                enabled=body.enabled,
            )
    except Exception:
        logger.exception("Failed to create alert rule")
        raise HTTPException(status_code=500, detail="Internal server error")
    return JSONResponse(status_code=201, content=jsonable_encoder(rule))


@router.patch("/alert-rules/{rule_id}", dependencies=[Depends(require_customer_admin)])
async def update_alert_rule_endpoint(rule_id: str, body: AlertRuleUpdate):
    try:
        UUID(rule_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid rule_id format: must be a valid UUID")

    if (
        body.name is None
        and body.metric_name is None
        and body.operator is None
        and body.threshold is None
        and body.severity is None
        and body.description is None
        and body.site_ids is None
        and body.enabled is None
    ):
        raise HTTPException(status_code=400, detail="No fields to update")

    if body.operator is not None and body.operator not in VALID_OPERATORS:
        raise HTTPException(status_code=400, detail="Invalid operator value")
    if body.metric_name is not None and not METRIC_NAME_PATTERN.match(body.metric_name):
        raise HTTPException(status_code=400, detail="Invalid metric_name format")
    if body.site_ids is not None:
        for site_id in body.site_ids:
            if site_id is None or not str(site_id).strip():
                raise HTTPException(status_code=400, detail="Invalid site_id value")

    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            rule = await update_alert_rule(
                conn,
                tenant_id=tenant_id,
                rule_id=rule_id,
                name=body.name,
                metric_name=body.metric_name,
                operator=body.operator,
                threshold=body.threshold,
                severity=body.severity,
                description=body.description,
                site_ids=body.site_ids,
                enabled=body.enabled,
            )
    except Exception:
        logger.exception("Failed to update alert rule")
        raise HTTPException(status_code=500, detail="Internal server error")
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return rule


@router.delete("/alert-rules/{rule_id}", dependencies=[Depends(require_customer_admin)])
async def delete_alert_rule_endpoint(rule_id: str):
    try:
        UUID(rule_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid rule_id format: must be a valid UUID")

    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            deleted = await delete_alert_rule(conn, tenant_id, rule_id)
    except Exception:
        logger.exception("Failed to delete alert rule")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not deleted:
        raise HTTPException(status_code=404, detail="Alert rule not found")
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
