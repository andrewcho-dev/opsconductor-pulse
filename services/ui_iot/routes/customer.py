import logging
import os
import re
import secrets
from datetime import datetime, timezone, timedelta
import time
import json
import csv
import io
import uuid
from uuid import UUID
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile, File
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from starlette.requests import Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from passlib.hash import bcrypt

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
    fetch_fleet_summary,
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
from services.subscription import create_device_on_subscription, log_subscription_event
from shared.utils import check_delete_result, validate_uuid
from dependencies import get_db_pool
from shared.utils import check_delete_result, validate_uuid
from dependencies import get_db_pool

# PHASE 44b DIAGNOSIS — Operator Format:
# DB constraint allows: '>', '<', '>=', '<=', '==', '!='
# API VALID_OPERATORS: {'GT', 'LT', 'GTE', 'LTE'}
# Evaluator expects: GT/LT/GTE/LTE (named form) in evaluate_threshold()
# Currently stored in DB: '<' and '>' (from SELECT DISTINCT operator)
# Translation layer: evaluator maps named -> symbols for display/SQL comparisons
#   (OPERATOR_SYMBOLS and check_duration_window op_map), but there is no write-path
#   translation between API payload and alert_rules.operator storage.
# Decision: make named form canonical in DB constraint (prompt 002).


logger = logging.getLogger(__name__)


def get_rate_limit_key(request: Request) -> str:
    tenant_id = getattr(request.state, "tenant_id", None)
    if tenant_id:
        return str(tenant_id)
    return get_remote_address(request)


limiter = Limiter(key_func=get_rate_limit_key, headers_enabled=True)
CUSTOMER_RATE_LIMIT = os.environ.get("RATE_LIMIT_CUSTOMER", "100/minute")



async def geocode_address(address: str) -> tuple[float, float] | None:
    """Convert street address to lat/lng using Nominatim."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": address,
                    "format": "json",
                    "limit": 1,
                },
                headers={
                    "User-Agent": "OpsConductor-Pulse/1.0"
                },
                timeout=5.0,
            )
            if response.status_code == 200:
                data = response.json()
                if data:
                    return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        return None
    return None


NAME_PATTERN = re.compile(r"^[A-Za-z0-9 _-]+$")
METRIC_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class IntegrationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    webhook_url: str = Field(..., min_length=1)
    body_template: str | None = None
    enabled: bool = True


class IntegrationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    webhook_url: str | None = None
    body_template: str | None = None
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
VALID_DEVICE_STATUSES = {"ONLINE", "STALE", "OFFLINE"}
ALERT_RULE_TEMPLATES = [
    {"template_id": "temp_high", "device_type": "temperature", "name": "High Temperature",
     "metric_name": "temperature", "operator": "GT", "threshold": 85.0, "severity": 1,
     "duration_seconds": 60, "description": "Temperature exceeds 85°C for 60s"},
    {"template_id": "temp_low", "device_type": "temperature", "name": "Low Temperature",
     "metric_name": "temperature", "operator": "LT", "threshold": -10.0, "severity": 1,
     "duration_seconds": 60, "description": "Temperature below -10°C for 60s"},
    {"template_id": "humidity_high", "device_type": "humidity", "name": "High Humidity",
     "metric_name": "humidity", "operator": "GT", "threshold": 90.0, "severity": 2,
     "duration_seconds": 120, "description": "Humidity exceeds 90% for 120s"},
    {"template_id": "humidity_low", "device_type": "humidity", "name": "Low Humidity",
     "metric_name": "humidity", "operator": "LT", "threshold": 10.0, "severity": 2,
     "duration_seconds": 120, "description": "Humidity below 10% for 120s"},
    {"template_id": "pressure_high", "device_type": "pressure", "name": "High Pressure",
     "metric_name": "pressure", "operator": "GT", "threshold": 1100.0, "severity": 2,
     "duration_seconds": 0, "description": "Pressure exceeds 1100 hPa"},
    {"template_id": "pressure_low", "device_type": "pressure", "name": "Low Pressure",
     "metric_name": "pressure", "operator": "LT", "threshold": 900.0, "severity": 2,
     "duration_seconds": 0, "description": "Pressure below 900 hPa"},
    {"template_id": "vibration_high", "device_type": "vibration", "name": "High Vibration",
     "metric_name": "vibration", "operator": "GT", "threshold": 5.0, "severity": 1,
     "duration_seconds": 30, "description": "Vibration exceeds 5 m/s² for 30s"},
    {"template_id": "power_high", "device_type": "power", "name": "High Power Usage",
     "metric_name": "power", "operator": "GT", "threshold": 95.0, "severity": 2,
     "duration_seconds": 300, "description": "Power usage >95% for 5 minutes"},
    {"template_id": "power_loss", "device_type": "power", "name": "Power Loss",
     "metric_name": "power", "operator": "LT", "threshold": 5.0, "severity": 3,
     "duration_seconds": 300, "description": "Power below 5% for 5 minutes"},
    {"template_id": "flow_low", "device_type": "flow", "name": "Low Flow Rate",
     "metric_name": "flow", "operator": "LT", "threshold": 1.0, "severity": 2,
     "duration_seconds": 120, "description": "Flow rate below 1 unit for 120s"},
    {"template_id": "level_high", "device_type": "level", "name": "High Level",
     "metric_name": "level", "operator": "GT", "threshold": 90.0, "severity": 1,
     "duration_seconds": 60, "description": "Level exceeds 90% for 60s"},
    {"template_id": "level_low", "device_type": "level", "name": "Low Level",
     "metric_name": "level", "operator": "LT", "threshold": 10.0, "severity": 1,
     "duration_seconds": 60, "description": "Level below 10% for 60s"},
]
TEST_PAYLOAD = {
    "test": True,
    "alert_id": 0,
    "site_id": "test-site",
    "device_id": "test-device",
    "alert_type": "TEST",
    "severity": 3,
    "summary": "This is a test notification from OpsConductor/Pulse",
    "status": "OPEN",
    "created_at": None,
}
VALID_TELEMETRY_RANGES = {
    "1h": ("1 hour", "1 minute"),
    "6h": ("6 hours", "5 minutes"),
    "24h": ("24 hours", "15 minutes"),
    "7d": ("7 days", "1 hour"),
    "30d": ("30 days", "6 hours"),
}
EXPORT_RANGES = {
    "1h": "1 hour",
    "6h": "6 hours",
    "24h": "24 hours",
    "7d": "7 days",
    "30d": "30 days",
}
TEMPLATE_VARIABLES = [
    {"name": "alert_id", "type": "integer", "description": "Numeric alert ID"},
    {"name": "device_id", "type": "string", "description": "Device identifier"},
    {"name": "site_id", "type": "string", "description": "Site identifier"},
    {"name": "tenant_id", "type": "string", "description": "Tenant identifier"},
    {"name": "severity", "type": "integer", "description": "Severity level (0=critical, 3=info)"},
    {"name": "severity_label", "type": "string", "description": "Severity label: CRITICAL, WARNING, INFO"},
    {"name": "alert_type", "type": "string", "description": "Alert type: THRESHOLD, NO_HEARTBEAT, etc."},
    {"name": "summary", "type": "string", "description": "Alert summary text"},
    {"name": "status", "type": "string", "description": "Alert status: OPEN, ACKNOWLEDGED, CLOSED"},
    {"name": "created_at", "type": "string", "description": "ISO 8601 creation timestamp"},
    {"name": "details", "type": "object", "description": "Alert details (JSONB dict)"},
]


class DeviceUpdate(BaseModel):
    name: str | None = None
    site_id: str | None = None
    tags: list[str] | None = None
    latitude: float | None = None
    longitude: float | None = None
    address: str | None = None
    location_source: str | None = None
    mac_address: str | None = None
    imei: str | None = None
    iccid: str | None = None
    serial_number: str | None = None
    model: str | None = None
    manufacturer: str | None = None
    hw_revision: str | None = None
    fw_version: str | None = None
    notes: str | None = None


class DeviceCreate(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=100)
    site_id: str = Field(..., min_length=1, max_length=100)
    subscription_id: str | None = None


class TagListUpdate(BaseModel):
    tags: list[str]


class DeviceGroupCreate(BaseModel):
    group_id: str | None = None
    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = None


class DeviceGroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = None


class MaintenanceWindowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    starts_at: datetime
    ends_at: datetime | None = None
    recurring: dict | None = None
    site_ids: list[str] | None = None
    device_types: list[str] | None = None
    enabled: bool = True


class MaintenanceWindowUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    recurring: dict | None = None
    site_ids: list[str] | None = None
    device_types: list[str] | None = None
    enabled: bool | None = None


class TokenRotateRequest(BaseModel):
    label: str = Field(default="rotated", min_length=1, max_length=100)


class AlertDigestSettingsUpdate(BaseModel):
    frequency: Literal["daily", "weekly", "disabled"]
    email: str = Field(default="", max_length=320)


class RenewalRequest(BaseModel):
    subscription_id: str
    plan_id: Optional[str] = None
    term_days: int = 365
    new_device_limit: Optional[int] = None
    devices_to_deactivate: Optional[List[str]] = None


class ApplyTemplatesRequest(BaseModel):
    template_ids: list[str]
    site_ids: list[str] | None = None


class AlertRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    rule_type: Literal["threshold", "anomaly", "telemetry_gap"] = "threshold"
    metric_name: str | None = Field(default=None, min_length=1, max_length=100)
    operator: str | None = None
    threshold: float | None = None
    severity: int = Field(default=3, ge=1, le=5)
    duration_seconds: int = Field(
        default=0,
        ge=0,
        description="Seconds threshold must be continuously breached before alert fires. 0 = immediate.",
    )
    description: str | None = None
    site_ids: list[str] | None = None
    group_ids: list[str] | None = None
    conditions: "RuleConditions | None" = None
    anomaly_conditions: "AnomalyConditions | None" = None
    gap_conditions: "TelemetryGapConditions | None" = None
    enabled: bool = True


class AlertRuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    rule_type: Literal["threshold", "anomaly", "telemetry_gap"] | None = None
    metric_name: str | None = Field(default=None, min_length=1, max_length=100)
    operator: str | None = None
    threshold: float | None = None
    severity: int | None = Field(default=None, ge=1, le=5)
    duration_seconds: int | None = Field(default=None, ge=0)
    description: str | None = None
    site_ids: list[str] | None = None
    group_ids: list[str] | None = None
    conditions: "RuleConditions | None" = None
    anomaly_conditions: "AnomalyConditions | None" = None
    gap_conditions: "TelemetryGapConditions | None" = None
    enabled: bool | None = None


class RuleCondition(BaseModel):
    metric_name: str
    operator: Literal["GT", "LT", "GTE", "LTE"]
    threshold: float


class RuleConditions(BaseModel):
    combinator: Literal["AND", "OR"] = "AND"
    conditions: List[RuleCondition] = Field(..., min_length=1, max_length=10)


class AnomalyConditions(BaseModel):
    metric_name: str
    window_minutes: int = Field(60, ge=5, le=1440)
    z_threshold: float = Field(3.0, ge=1.0, le=10.0)
    min_samples: int = Field(10, ge=3, le=1000)


class TelemetryGapConditions(BaseModel):
    metric_name: str
    gap_minutes: int = Field(10, ge=1, le=1440)
    min_expected_per_hour: int | None = Field(default=None, ge=1)


AlertRuleCreate.model_rebuild()
AlertRuleUpdate.model_rebuild()


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


class MetricMappingUpdate(BaseModel):
    multiplier: float | None = None
    offset_value: float | None = None


class SilenceRequest(BaseModel):
    minutes: int = Field(..., ge=1, le=1440)


async def require_customer_admin(request: Request):
    user = get_user()
    realm_access = user.get("realm_access", {}) or {}
    roles = set(realm_access.get("roles", []) or [])
    # Operators retain global admin behavior.
    if "operator-admin" in roles or "operator" in roles:
        return
    if "tenant-admin" not in roles:
        raise HTTPException(status_code=403, detail="Customer admin role required")


def _validate_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned or len(cleaned) > 100:
        raise HTTPException(status_code=400, detail="Invalid name length")
    if not NAME_PATTERN.match(cleaned):
        raise HTTPException(status_code=400, detail="Invalid name format")
    return cleaned


ALERT_TYPES = {"NO_HEARTBEAT", "THRESHOLD", "ANOMALY", "NO_TELEMETRY"}
SEVERITIES = {"CRITICAL", "WARNING", "INFO"}
SUPPORTED_DEVICE_TYPES = {
    "temperature",
    "humidity",
    "pressure",
    "vibration",
    "power",
    "flow",
    "level",
    "gateway",
}

UPTIME_RANGES_SECONDS = {
    "24h": 24 * 60 * 60,
    "7d": 7 * 24 * 60 * 60,
    "30d": 30 * 24 * 60 * 60,
}


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


def _normalize_optional_ids(values: list[str] | None, field_name: str) -> list[str] | None:
    if values is None:
        return None
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        item = str(value).strip()
        if not item:
            continue
        if item in seen:
            continue
        seen.add(item)
        cleaned.append(item)
    if not cleaned:
        raise HTTPException(status_code=400, detail=f"{field_name} must not be empty")
    return cleaned


def _with_rule_conditions(rule: dict) -> dict:
    result = dict(rule)
    if result.get("rule_type") == "anomaly":
        result["anomaly_conditions"] = result.get("conditions")
        result["gap_conditions"] = None
    elif result.get("rule_type") == "telemetry_gap":
        result["anomaly_conditions"] = None
        result["gap_conditions"] = result.get("conditions")
    else:
        result["anomaly_conditions"] = None
        result["gap_conditions"] = None
    return result


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


router = APIRouter(
    prefix="/customer",
    tags=["customer"],
    dependencies=[
        Depends(JWTBearer()),
        Depends(inject_tenant_context),
        Depends(require_customer),
    ],
)


@router.post("/devices", status_code=201)
async def create_device(device: DeviceCreate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    user = get_user()

    p = pool
    async with tenant_connection(p, tenant_id) as conn:
        subscription_id = device.subscription_id
        if not subscription_id:
            sub = await conn.fetchrow(
                """
                SELECT subscription_id
                FROM subscriptions
                WHERE tenant_id = $1
                  AND subscription_type = 'MAIN'
                  AND status = 'ACTIVE'
                  AND active_device_count < device_limit
                ORDER BY created_at
                LIMIT 1
                """,
                tenant_id,
            )
            if not sub:
                raise HTTPException(403, "No MAIN subscription with available capacity")
            subscription_id = sub["subscription_id"]

        try:
            await create_device_on_subscription(
                conn,
                tenant_id,
                device.device_id,
                device.site_id,
                subscription_id,
                actor_id=user.get("sub") if user else None,
            )
        except ValueError as exc:
            message = str(exc)
            status_code = 403 if "limit" in message.lower() else 400
            raise HTTPException(status_code, message)

    return {
        "device_id": device.device_id,
        "subscription_id": subscription_id,
        "status": "created",
    }


@router.get("/devices/{device_id}/tokens")
async def list_device_tokens(device_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            exists = await conn.fetchval(
                "SELECT 1 FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
                tenant_id,
                device_id,
            )
            if not exists:
                raise HTTPException(status_code=404, detail="Device not found")
            rows = await conn.fetch(
                """
                SELECT id, client_id, label, created_at, revoked_at
                FROM device_api_tokens
                WHERE tenant_id = $1 AND device_id = $2 AND revoked_at IS NULL
                ORDER BY created_at DESC
                """,
                tenant_id,
                device_id,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to list device tokens")
        raise HTTPException(status_code=500, detail="Internal server error")

    tokens = []
    for row in rows:
        token = dict(row)
        if token.get("revoked_at") is not None:
            continue
        token["id"] = str(token["id"])
        tokens.append(token)
    return {"device_id": device_id, "tokens": tokens, "total": len(tokens)}


@router.delete("/devices/{device_id}/tokens/{token_id}", status_code=204)
async def revoke_device_token(device_id: str, token_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                UPDATE device_api_tokens
                SET revoked_at = now()
                WHERE tenant_id = $1
                  AND device_id = $2
                  AND id = $3::uuid
                  AND revoked_at IS NULL
                RETURNING id
                """,
                tenant_id,
                device_id,
                token_id,
            )
    except Exception:
        logger.exception("Failed to revoke device token")
        raise HTTPException(status_code=500, detail="Internal server error")
    if not row:
        raise HTTPException(status_code=404, detail="Token not found")
    return Response(status_code=204)


@router.post("/devices/{device_id}/tokens/rotate", status_code=201)
async def rotate_device_token(
    device_id: str,
    body: TokenRotateRequest,
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            exists = await conn.fetchval(
                "SELECT 1 FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
                tenant_id,
                device_id,
            )
            if not exists:
                raise HTTPException(status_code=404, detail="Device not found")

            await conn.execute(
                """
                UPDATE device_api_tokens
                SET revoked_at = now()
                WHERE tenant_id = $1 AND device_id = $2 AND revoked_at IS NULL
                """,
                tenant_id,
                device_id,
            )

            client_id = f"{tenant_id[:8]}-{device_id[:8]}-{uuid.uuid4().hex[:8]}"
            password = secrets.token_urlsafe(32)
            token_hash = bcrypt.hash(password)
            await conn.execute(
                """
                INSERT INTO device_api_tokens (tenant_id, device_id, client_id, token_hash, label)
                VALUES ($1, $2, $3, $4, $5)
                """,
                tenant_id,
                device_id,
                client_id,
                token_hash,
                body.label.strip() or "rotated",
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to rotate device token")
        raise HTTPException(status_code=500, detail="Internal server error")

    broker_url = os.environ.get("MQTT_BROKER_URL", "mqtt://localhost:1883")
    return {"client_id": client_id, "password": password, "broker_url": broker_url}


@router.post("/devices/import")
async def import_devices_csv(file: UploadFile = File(...), pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    user = get_user()
    raw = await file.read()
    if len(raw) > 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 1 MB)")

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded")

    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    required_columns = {"name", "device_type"}
    if not required_columns.issubset(set(headers)):
        raise HTTPException(status_code=400, detail="Missing required CSV columns: name, device_type")

    rows = list(reader)
    if len(rows) > 500:
        raise HTTPException(status_code=400, detail="CSV row limit exceeded (max 500)")

    results: list[dict] = []
    imported = 0
    failed = 0

    async with tenant_connection(pool, tenant_id) as conn:
        for idx, row in enumerate(rows, start=1):
            name = (row.get("name") or "").strip()
            device_type = (row.get("device_type") or "").strip().lower()
            site_id = (row.get("site_id") or "").strip() or "default-site"
            tags_value = (row.get("tags") or "").strip()
            tags = _normalize_tags(tags_value.split(",")) if tags_value else []

            if not name:
                failed += 1
                results.append(
                    {"row": idx, "name": name, "status": "error", "message": "name is required"}
                )
                continue
            if device_type not in SUPPORTED_DEVICE_TYPES:
                failed += 1
                results.append(
                    {
                        "row": idx,
                        "name": name,
                        "status": "error",
                        "message": f"unsupported device_type: {device_type}",
                    }
                )
                continue

            subscription_id = await conn.fetchval(
                """
                SELECT subscription_id
                FROM subscriptions
                WHERE tenant_id = $1
                  AND subscription_type = 'MAIN'
                  AND status = 'ACTIVE'
                  AND active_device_count < device_limit
                ORDER BY created_at
                LIMIT 1
                """,
                tenant_id,
            )
            if not subscription_id:
                failed += 1
                results.append(
                    {
                        "row": idx,
                        "name": name,
                        "status": "error",
                        "message": "No active subscription capacity",
                    }
                )
                continue

            base_id = re.sub(r"[^A-Za-z0-9-]+", "-", name).strip("-").upper() or "DEVICE"
            device_id = f"{base_id}-{uuid.uuid4().hex[:6]}"
            try:
                await create_device_on_subscription(
                    conn,
                    tenant_id,
                    device_id,
                    site_id,
                    subscription_id,
                    actor_id=user.get("sub") if user else None,
                )

                if tags:
                    await conn.executemany(
                        """
                        INSERT INTO device_tags (tenant_id, device_id, tag)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (tenant_id, device_id, tag) DO NOTHING
                        """,
                        [(tenant_id, device_id, tag) for tag in tags],
                    )

                client_id = f"{tenant_id[:8]}-{device_id[:8]}-{uuid.uuid4().hex[:8]}"
                password = secrets.token_urlsafe(32)
                await conn.execute(
                    """
                    INSERT INTO device_api_tokens (tenant_id, device_id, client_id, token_hash, label)
                    VALUES ($1, $2, $3, $4, 'default')
                    """,
                    tenant_id,
                    device_id,
                    client_id,
                    bcrypt.hash(password),
                )
            except Exception as exc:
                failed += 1
                results.append(
                    {"row": idx, "name": name, "status": "error", "message": str(exc)}
                )
                continue

            imported += 1
            results.append({"row": idx, "name": name, "status": "ok", "device_id": device_id})

    return {
        "total": len(rows),
        "imported": imported,
        "failed": failed,
        "results": results,
    }


@router.get("/alert-digest-settings")
async def get_alert_digest_settings(pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                SELECT frequency, email, last_sent_at
                FROM alert_digest_settings
                WHERE tenant_id = $1
                """,
                tenant_id,
            )
    except Exception:
        logger.exception("Failed to fetch alert digest settings")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not row:
        return {"frequency": "daily", "email": "", "last_sent_at": None}
    return {
        "frequency": row["frequency"],
        "email": row["email"],
        "last_sent_at": row["last_sent_at"],
    }


@router.put("/alert-digest-settings")
async def put_alert_digest_settings(
    body: AlertDigestSettingsUpdate,
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            await conn.execute(
                """
                INSERT INTO alert_digest_settings (tenant_id, frequency, email)
                VALUES ($1, $2, $3)
                ON CONFLICT (tenant_id)
                DO UPDATE SET
                    frequency = EXCLUDED.frequency,
                    email = EXCLUDED.email,
                    updated_at = now()
                """,
                tenant_id,
                body.frequency,
                body.email.strip(),
            )
    except Exception:
        logger.exception("Failed to upsert alert digest settings")
        raise HTTPException(status_code=500, detail="Internal server error")
    return {"ok": True}


@router.get("/devices/{device_id}/uptime")
async def get_device_uptime(
    device_id: str,
    range: Literal["24h", "7d", "30d"] = Query("24h"),
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()
    range_seconds = UPTIME_RANGES_SECONDS[range]
    range_start = datetime.now(timezone.utc) - timedelta(seconds=range_seconds)
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            exists = await conn.fetchval(
                "SELECT 1 FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
                tenant_id,
                device_id,
            )
            if not exists:
                raise HTTPException(status_code=404, detail="Device not found")

            row = await conn.fetchrow(
                """
                SELECT COALESCE(SUM(
                    EXTRACT(EPOCH FROM (LEAST(COALESCE(closed_at, now()), now()) - GREATEST(created_at, $3)))
                ), 0) AS offline_seconds
                FROM fleet_alert
                WHERE tenant_id = $1
                  AND device_id = $2
                  AND alert_type = 'NO_TELEMETRY'
                  AND created_at < now()
                  AND COALESCE(closed_at, now()) > $3
                """,
                tenant_id,
                device_id,
                range_start,
            )
            is_offline = await conn.fetchval(
                """
                SELECT 1
                FROM fleet_alert
                WHERE tenant_id = $1
                  AND device_id = $2
                  AND alert_type = 'NO_TELEMETRY'
                  AND status = 'OPEN'
                LIMIT 1
                """,
                tenant_id,
                device_id,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to compute device uptime")
        raise HTTPException(status_code=500, detail="Internal server error")

    offline_seconds = max(0, int(float(row["offline_seconds"] or 0)))
    offline_seconds = min(offline_seconds, range_seconds)
    uptime_pct = round(((range_seconds - offline_seconds) / range_seconds) * 100, 1)
    return {
        "device_id": device_id,
        "range": range,
        "uptime_pct": uptime_pct,
        "offline_seconds": offline_seconds,
        "range_seconds": range_seconds,
        "status": "offline" if is_offline else "online",
    }


@router.get("/fleet/uptime-summary")
async def get_fleet_uptime_summary(pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    range_seconds = UPTIME_RANGES_SECONDS["24h"]
    range_start = datetime.now(timezone.utc) - timedelta(seconds=range_seconds)
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            counts = await conn.fetchrow(
                """
                WITH open_gap AS (
                    SELECT DISTINCT device_id
                    FROM fleet_alert
                    WHERE tenant_id = $1
                      AND alert_type = 'NO_TELEMETRY'
                      AND status = 'OPEN'
                )
                SELECT
                    COUNT(*) AS total_devices,
                    COUNT(*) FILTER (WHERE og.device_id IS NULL) AS online,
                    COUNT(*) FILTER (WHERE og.device_id IS NOT NULL) AS offline
                FROM device_registry dr
                LEFT JOIN open_gap og
                  ON og.device_id = dr.device_id
                WHERE dr.tenant_id = $1
                """,
                tenant_id,
            )
            avg_row = await conn.fetchrow(
                """
                WITH device_offline AS (
                    SELECT
                        dr.device_id,
                        COALESCE(SUM(
                            EXTRACT(EPOCH FROM (
                                LEAST(COALESCE(fa.closed_at, now()), now()) - GREATEST(fa.created_at, $2)
                            ))
                        ), 0) AS offline_seconds
                    FROM device_registry dr
                    LEFT JOIN fleet_alert fa
                      ON fa.tenant_id = dr.tenant_id
                     AND fa.device_id = dr.device_id
                     AND fa.alert_type = 'NO_TELEMETRY'
                     AND fa.created_at < now()
                     AND COALESCE(fa.closed_at, now()) > $2
                    WHERE dr.tenant_id = $1
                    GROUP BY dr.device_id
                )
                SELECT COALESCE(AVG(
                    (( $3 - LEAST(offline_seconds, $3) ) / $3::numeric) * 100
                ), 100) AS avg_uptime_pct
                FROM device_offline
                """,
                tenant_id,
                range_start,
                range_seconds,
            )
    except Exception:
        logger.exception("Failed to compute fleet uptime summary")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {
        "total_devices": int(counts["total_devices"] or 0),
        "online": int(counts["online"] or 0),
        "offline": int(counts["offline"] or 0),
        "avg_uptime_pct": round(float(avg_row["avg_uptime_pct"] or 100), 1),
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/devices")
@limiter.limit(CUSTOMER_RATE_LIMIT)
async def list_devices(
    request: Request,
    response: Response,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None),
    tags: str | None = Query(None),
    q: str | None = Query(None, max_length=100),
    site_id: str | None = Query(None),
    include_decommissioned: bool = Query(False),
    pool=Depends(get_db_pool),
):
    if status is not None and status.upper() not in VALID_DEVICE_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status value")
    status = status.upper() if status else None
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None

    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            result = await fetch_devices_v2(
                conn,
                tenant_id,
                limit=limit,
                offset=offset,
                status=status,
                tags=tag_list,
                q=q,
                site_id=site_id,
                include_decommissioned=include_decommissioned,
            )
            devices = result["devices"]
            if devices:
                device_ids = [device["device_id"] for device in devices]
                rows = await conn.fetch(
                    """
                    SELECT
                        d.device_id,
                        d.subscription_id,
                        s.subscription_type,
                        s.status as subscription_status
                    FROM device_registry d
                    LEFT JOIN subscriptions s ON d.subscription_id = s.subscription_id
                    WHERE d.tenant_id = $1 AND d.device_id = ANY($2::text[])
                    """,
                    tenant_id,
                    device_ids,
                )
                subscription_map = {row["device_id"]: dict(row) for row in rows}
                for device in devices:
                    subscription = subscription_map.get(device["device_id"])
                    if subscription:
                        device["subscription_id"] = subscription["subscription_id"]
                        device["subscription_type"] = subscription["subscription_type"]
                        device["subscription_status"] = subscription["subscription_status"]
    except Exception:
        logger.exception("Failed to fetch tenant devices")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {
        "tenant_id": tenant_id,
        "devices": devices,
        "total": result["total"],
        "limit": limit,
        "offset": offset,
    }


@router.get("/sites", dependencies=[Depends(require_customer)])
async def list_sites(pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        rows = await conn.fetch(
            """
            SELECT
                s.site_id,
                s.name,
                s.location,
                s.latitude,
                s.longitude,
                COUNT(DISTINCT dr.device_id) AS device_count,
                COUNT(DISTINCT dr.device_id) FILTER (WHERE COALESCE(ds.status, 'OFFLINE') = 'ONLINE') AS online_count,
                COUNT(DISTINCT dr.device_id) FILTER (WHERE COALESCE(ds.status, 'OFFLINE') = 'STALE') AS stale_count,
                COUNT(DISTINCT dr.device_id) FILTER (WHERE COALESCE(ds.status, 'OFFLINE') = 'OFFLINE') AS offline_count,
                COUNT(DISTINCT a.id) FILTER (WHERE a.status IN ('OPEN', 'ACKNOWLEDGED')) AS active_alert_count
            FROM sites s
            LEFT JOIN device_registry dr
              ON dr.site_id = s.site_id AND dr.tenant_id = s.tenant_id
            LEFT JOIN device_state ds
              ON ds.device_id = dr.device_id AND ds.tenant_id = dr.tenant_id
            LEFT JOIN fleet_alert a
              ON a.site_id = s.site_id AND a.tenant_id = s.tenant_id
            WHERE s.tenant_id = $1
            GROUP BY s.site_id, s.name, s.location, s.latitude, s.longitude
            ORDER BY s.name
            """,
            tenant_id,
        )
    return {"sites": [dict(row) for row in rows], "total": len(rows)}


@router.get("/sites/{site_id}/summary", dependencies=[Depends(require_customer)])
async def get_site_summary(site_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        site = await conn.fetchrow(
            "SELECT site_id, name, location FROM sites WHERE tenant_id = $1 AND site_id = $2",
            tenant_id,
            site_id,
        )
        if not site:
            raise HTTPException(status_code=404, detail="Site not found")

        devices = await conn.fetch(
            """
            SELECT
                dr.device_id,
                COALESCE(dr.model, dr.device_id) AS name,
                COALESCE(ds.status, 'OFFLINE') AS status,
                dr.device_type,
                ds.last_seen_at
            FROM device_registry dr
            LEFT JOIN device_state ds
              ON ds.tenant_id = dr.tenant_id AND ds.device_id = dr.device_id
            WHERE dr.tenant_id = $1 AND dr.site_id = $2
              AND dr.decommissioned_at IS NULL
            ORDER BY name
            """,
            tenant_id,
            site_id,
        )

        alerts = await conn.fetch(
            """
            SELECT id, alert_type, severity, summary, status, created_at
            FROM fleet_alert
            WHERE tenant_id = $1 AND site_id = $2 AND status IN ('OPEN', 'ACKNOWLEDGED')
            ORDER BY severity ASC, created_at DESC
            LIMIT 20
            """,
            tenant_id,
            site_id,
        )

    return {
        "site": dict(site),
        "devices": [dict(device) for device in devices],
        "active_alerts": [dict(alert) for alert in alerts],
        "device_count": len(devices),
        "active_alert_count": len(alerts),
    }


@router.get("/devices/summary")
async def get_fleet_summary(pool=Depends(get_db_pool)):
    """Fleet status summary: counts of ONLINE/STALE/OFFLINE devices."""
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            summary = await fetch_fleet_summary(conn, tenant_id)
    except Exception:
        logger.exception("Failed to fetch fleet summary")
        raise HTTPException(status_code=500, detail="Internal server error")
    return summary


@router.delete("/devices/{device_id}")
async def delete_device(device_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    user = get_user()

    p = pool
    async with tenant_connection(p, tenant_id) as conn:
        device = await conn.fetchrow(
            """
            SELECT subscription_id
            FROM device_registry
            WHERE tenant_id = $1 AND device_id = $2
            """,
            tenant_id,
            device_id,
        )
        if not device:
            raise HTTPException(404, "Device not found")

        await conn.execute(
            """
            UPDATE device_registry
            SET status = 'DELETED'
            WHERE tenant_id = $1 AND device_id = $2
            """,
            tenant_id,
            device_id,
        )

        subscription_id = device["subscription_id"]
        if subscription_id:
            await conn.execute(
                """
                UPDATE subscriptions
                SET active_device_count = GREATEST(0, active_device_count - 1), updated_at = now()
                WHERE subscription_id = $1
                """,
                subscription_id,
            )

        await log_subscription_event(
            conn,
            tenant_id,
            event_type="DEVICE_REMOVED",
            actor_type="user",
            actor_id=user.get("sub") if user else None,
            details={"device_id": device_id, "subscription_id": subscription_id},
        )

    return {"device_id": device_id, "status": "deleted"}


@router.get("/devices/{device_id}")
async def get_device_detail(device_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        p = pool
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


@router.get("/devices/{device_id}/telemetry/history", dependencies=[Depends(require_customer)])
async def get_telemetry_history(
    device_id: str,
    metric: str = Query(...),
    range: str = Query("24h"),
    pool=Depends(get_db_pool),
):
    if range not in VALID_TELEMETRY_RANGES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid range. Must be one of: {list(VALID_TELEMETRY_RANGES.keys())}",
        )

    tenant_id = get_tenant_id()
    lookback, bucket = VALID_TELEMETRY_RANGES[range]

    async with tenant_connection(pool, tenant_id) as conn:
        rows = await conn.fetch(
            """
            SELECT
                time_bucket($1::interval, time) AS bucket,
                AVG((metrics->>$2)::numeric) AS avg_val,
                MIN((metrics->>$2)::numeric) AS min_val,
                MAX((metrics->>$2)::numeric) AS max_val,
                COUNT(*) AS sample_count
            FROM telemetry
            WHERE tenant_id = $3
              AND device_id = $4
              AND time > now() - $5::interval
              AND metrics ? $2
            GROUP BY bucket
            ORDER BY bucket ASC
            """,
            bucket,
            metric,
            tenant_id,
            device_id,
            lookback,
        )

    return {
        "device_id": device_id,
        "metric": metric,
        "range": range,
        "bucket_size": bucket,
        "points": [
            {
                "time": row["bucket"].isoformat(),
                "avg": float(row["avg_val"]) if row["avg_val"] is not None else None,
                "min": float(row["min_val"]) if row["min_val"] is not None else None,
                "max": float(row["max_val"]) if row["max_val"] is not None else None,
                "count": row["sample_count"],
            }
            for row in rows
        ],
    }


@router.get("/devices/{device_id}/telemetry/export", dependencies=[Depends(require_customer)])
async def export_telemetry_csv(
    device_id: str,
    range: str = Query("24h"),
    limit: int = Query(5000, ge=1, le=10000),
    pool=Depends(get_db_pool),
):
    if range not in EXPORT_RANGES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid range. Must be one of: {list(EXPORT_RANGES.keys())}",
        )

    tenant_id = get_tenant_id()
    lookback = EXPORT_RANGES[range]
    async with tenant_connection(pool, tenant_id) as conn:
        rows = await conn.fetch(
            """
            SELECT time, device_id, site_id, seq, metrics
            FROM telemetry
            WHERE tenant_id = $1
              AND device_id = $2
              AND time > now() - $3::interval
            ORDER BY time ASC
            LIMIT $4
            """,
            tenant_id,
            device_id,
            lookback,
            limit,
        )

    output = io.StringIO()
    writer = csv.writer(output)
    if not rows:
        writer.writerow(["time", "device_id", "site_id", "seq"])
    else:
        metric_keys = sorted(
            {
                key
                for row in rows
                for key in ((row["metrics"] or {}).keys())
            }
        )
        headers = ["time", "device_id", "site_id", "seq", *metric_keys]
        writer.writerow(headers)
        for row in rows:
            metrics = row["metrics"] or {}
            writer.writerow(
                [
                    row["time"].isoformat(),
                    row["device_id"],
                    row["site_id"] or "",
                    row["seq"],
                    *[metrics.get(k, "") for k in metric_keys],
                ]
            )
    output.seek(0)
    filename = f"{device_id}_telemetry_{range}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/subscriptions")
async def list_subscriptions(
    include_expired: bool = Query(False),
):
    """List all subscriptions for the tenant."""
    tenant_id = get_tenant_id()

    p = pool
    async with tenant_connection(p, tenant_id) as conn:
        if include_expired:
            rows = await conn.fetch(
                """
                SELECT
                    subscription_id, subscription_type, parent_subscription_id,
                    device_limit, active_device_count, term_start, term_end,
                    status, plan_id, description, created_at
                FROM subscriptions
                WHERE tenant_id = $1
                ORDER BY
                    CASE subscription_type
                        WHEN 'MAIN' THEN 1
                        WHEN 'ADDON' THEN 2
                        WHEN 'TRIAL' THEN 3
                        WHEN 'TEMPORARY' THEN 4
                    END,
                    term_end DESC
                """,
                tenant_id,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT
                    subscription_id, subscription_type, parent_subscription_id,
                    device_limit, active_device_count, term_start, term_end,
                    status, plan_id, description, created_at
                FROM subscriptions
                WHERE tenant_id = $1 AND status != 'EXPIRED'
                ORDER BY
                    CASE subscription_type
                        WHEN 'MAIN' THEN 1
                        WHEN 'ADDON' THEN 2
                        WHEN 'TRIAL' THEN 3
                        WHEN 'TEMPORARY' THEN 4
                    END,
                    term_end DESC
                """,
                tenant_id,
            )

        total_limit = sum(
            r["device_limit"] for r in rows if r["status"] not in ("SUSPENDED", "EXPIRED")
        )
        total_active = sum(
            r["active_device_count"]
            for r in rows
            if r["status"] not in ("SUSPENDED", "EXPIRED")
        )

        return {
            "subscriptions": [
                {
                    "subscription_id": r["subscription_id"],
                    "subscription_type": r["subscription_type"],
                    "parent_subscription_id": r["parent_subscription_id"],
                    "device_limit": r["device_limit"],
                    "active_device_count": r["active_device_count"],
                    "devices_available": r["device_limit"] - r["active_device_count"],
                    "term_start": r["term_start"].isoformat() if r["term_start"] else None,
                    "term_end": r["term_end"].isoformat() if r["term_end"] else None,
                    "status": r["status"],
                    "plan_id": r["plan_id"],
                    "description": r["description"],
                }
                for r in rows
            ],
            "summary": {
                "total_device_limit": total_limit,
                "total_active_devices": total_active,
                "total_available": total_limit - total_active,
            },
        }


@router.get("/subscriptions/{subscription_id}")
async def get_subscription_detail(subscription_id: str, pool=Depends(get_db_pool)):
    """Get details of a specific subscription."""
    tenant_id = get_tenant_id()

    p = pool
    async with tenant_connection(p, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            SELECT * FROM subscriptions
            WHERE subscription_id = $1 AND tenant_id = $2
            """,
            subscription_id,
            tenant_id,
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
            LIMIT 100
            """,
            subscription_id,
        )

        device_count = await conn.fetchval(
            "SELECT COUNT(*) FROM device_registry WHERE subscription_id = $1",
            subscription_id,
        )

        days_until_expiry = None
        if row["term_end"]:
            delta = row["term_end"] - datetime.now(timezone.utc)
            days_until_expiry = max(0, delta.days)

        return {
            "subscription_id": row["subscription_id"],
            "subscription_type": row["subscription_type"],
            "parent_subscription_id": row["parent_subscription_id"],
            "device_limit": row["device_limit"],
            "active_device_count": row["active_device_count"],
            "devices_available": row["device_limit"] - row["active_device_count"],
            "term_start": row["term_start"].isoformat() if row["term_start"] else None,
            "term_end": row["term_end"].isoformat() if row["term_end"] else None,
            "days_until_expiry": days_until_expiry,
            "status": row["status"],
            "plan_id": row["plan_id"],
            "description": row["description"],
            "devices": [
                {
                    "device_id": d["device_id"],
                    "site_id": d["site_id"],
                    "status": d["status"],
                    "last_seen_at": d["last_seen_at"].isoformat()
                    if d["last_seen_at"]
                    else None,
                }
                for d in devices
            ],
            "total_devices": device_count,
        }


@router.get("/subscription/audit")
async def get_subscription_audit(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Get subscription audit history for tenant."""
    tenant_id = get_tenant_id()

    p = pool
    async with tenant_connection(p, tenant_id) as conn:
        rows = await conn.fetch(
            """
            SELECT
                id,
                event_type,
                event_timestamp,
                actor_type,
                actor_id,
                previous_state,
                new_state,
                details
            FROM subscription_audit
            WHERE tenant_id = $1
            ORDER BY event_timestamp DESC
            LIMIT $2 OFFSET $3
            """,
            tenant_id,
            limit,
            offset,
        )

        count = await conn.fetchval(
            "SELECT COUNT(*) FROM subscription_audit WHERE tenant_id = $1",
            tenant_id,
        )

        return {
            "events": [
                {
                    "id": row["id"],
                    "event_type": row["event_type"],
                    "event_timestamp": row["event_timestamp"].isoformat(),
                    "actor_type": row["actor_type"],
                    "actor_id": row["actor_id"],
                    "previous_state": row["previous_state"],
                    "new_state": row["new_state"],
                    "details": row["details"],
                }
                for row in rows
            ],
            "total": count,
            "limit": limit,
            "offset": offset,
        }


@router.post("/subscription/renew")
async def request_renewal(data: RenewalRequest, request: Request, pool=Depends(get_db_pool)):
    """
    Request subscription renewal.
    If downsizing, deactivates specified devices first.
    """
    tenant_id = get_tenant_id()
    user = get_user()
    ip = request.client.host if request.client else None

    async with tenant_connection(pool, tenant_id) as conn:
        async with conn.transaction():
            sub = await conn.fetchrow(
                """
                SELECT * FROM subscriptions
                WHERE subscription_id = $1 AND tenant_id = $2
                FOR UPDATE
                """,
                data.subscription_id,
                tenant_id,
            )
            if not sub:
                raise HTTPException(404, "Subscription not found")

            if sub["status"] == "ACTIVE" and sub["term_end"] > (
                datetime.now(timezone.utc) + timedelta(days=30)
            ):
                return {
                    "subscription_id": data.subscription_id,
                    "renewed": True,
                    "note": "Already active",
                }

            if data.devices_to_deactivate:
                required_reduction = sub["active_device_count"] - (
                    data.new_device_limit or sub["device_limit"]
                )
                if len(data.devices_to_deactivate) != required_reduction:
                    raise HTTPException(
                        400,
                        f"Must select exactly {required_reduction} devices to deactivate",
                    )

                devices = await conn.fetch(
                    """
                    SELECT device_id FROM device_registry
                    WHERE subscription_id = $1 AND device_id = ANY($2)
                    """,
                    data.subscription_id,
                    data.devices_to_deactivate,
                )
                if len(devices) != len(data.devices_to_deactivate):
                    raise HTTPException(400, "Some devices not found on this subscription")

                await conn.execute(
                    """
                    UPDATE device_registry
                    SET status = 'INACTIVE', subscription_id = NULL, updated_at = now()
                    WHERE device_id = ANY($1)
                    """,
                    data.devices_to_deactivate,
                )

                await conn.execute(
                    """
                    UPDATE subscriptions
                    SET active_device_count = active_device_count - $1
                    WHERE subscription_id = $2
                    """,
                    len(data.devices_to_deactivate),
                    data.subscription_id,
                )

            new_term_end = datetime.now(timezone.utc) + timedelta(days=data.term_days)

            await conn.execute(
                """
                UPDATE subscriptions
                SET term_end = $1,
                    device_limit = COALESCE($2, device_limit),
                    plan_id = COALESCE($3, plan_id),
                    status = 'ACTIVE',
                    grace_end = NULL,
                    updated_at = now()
                WHERE subscription_id = $4
                """,
                new_term_end,
                data.new_device_limit,
                data.plan_id,
                data.subscription_id,
            )

            await conn.execute(
                """
                INSERT INTO subscription_audit
                    (tenant_id, event_type, actor_type, actor_id, details, ip_address)
                VALUES ($1, 'RENEWED', 'user', $2, $3, $4)
                """,
                tenant_id,
                user.get("sub") if user else None,
                json.dumps(
                    {
                        "subscription_id": data.subscription_id,
                        "plan_id": data.plan_id,
                        "term_days": data.term_days,
                        "new_device_limit": data.new_device_limit,
                        "devices_deactivated": data.devices_to_deactivate,
                    }
                ),
                ip,
            )

            return {
                "subscription_id": data.subscription_id,
                "renewed": True,
                "new_term_end": new_term_end.isoformat(),
                "devices_deactivated": len(data.devices_to_deactivate)
                if data.devices_to_deactivate
                else 0,
            }


@router.patch("/devices/{device_id}")
async def update_device(device_id: str, body: DeviceUpdate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided")

    tags_update = update_data.pop("tags", None)
    if "name" in update_data:
        update_data["model"] = update_data.pop("name")

    if update_data.get("address") and not (
        update_data.get("latitude") is not None and update_data.get("longitude") is not None
    ):
        coords = await geocode_address(update_data["address"])
        if coords:
            update_data["latitude"], update_data["longitude"] = coords

    if any(key in update_data for key in ("latitude", "longitude", "address")):
        update_data["location_source"] = "manual"

    fields = [
        "site_id",
        "latitude",
        "longitude",
        "address",
        "location_source",
        "mac_address",
        "imei",
        "iccid",
        "serial_number",
        "model",
        "manufacturer",
        "hw_revision",
        "fw_version",
        "notes",
    ]
    allowed_fields = set(fields)
    unknown_fields = [
        key for key, value in update_data.items()
        if value is not None and key not in allowed_fields
    ]
    if unknown_fields:
        raise HTTPException(status_code=400, detail="Invalid fields provided")

    sets: list[str] = []
    params: list[object] = [tenant_id, device_id]
    idx = 3

    for field in fields:
        if field in update_data:
            sets.append(f"{field} = ${idx}")
            params.append(update_data[field])
            idx += 1

    if not sets:
        raise HTTPException(status_code=400, detail="No fields provided")

    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            row = await conn.fetchrow(
                f"""
                UPDATE device_registry
                SET {", ".join(sets)}
                WHERE tenant_id = $1 AND device_id = $2
                RETURNING tenant_id, device_id
                """,
                *params,
            )
            if not row:
                raise HTTPException(status_code=404, detail="Device not found")

            if tags_update is not None:
                normalized_tags = _normalize_tags(tags_update)
                await conn.execute(
                    "DELETE FROM device_tags WHERE tenant_id = $1 AND device_id = $2",
                    tenant_id,
                    device_id,
                )
                if normalized_tags:
                    await conn.executemany(
                        """
                        INSERT INTO device_tags (tenant_id, device_id, tag)
                        VALUES ($1, $2, $3)
                        ON CONFLICT DO NOTHING
                        """,
                        [(tenant_id, device_id, tag) for tag in normalized_tags],
                    )

            device = await fetch_device(conn, tenant_id, device_id)
            if not device:
                raise HTTPException(status_code=404, detail="Device not found")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to update device attributes")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"tenant_id": tenant_id, "device": device}


@router.patch("/devices/{device_id}/decommission", dependencies=[Depends(require_customer)])
async def decommission_device(device_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                UPDATE device_registry
                SET decommissioned_at = now(), status = 'REVOKED'
                WHERE tenant_id = $1 AND device_id = $2 AND decommissioned_at IS NULL
                RETURNING device_id, decommissioned_at
                """,
                tenant_id,
                device_id,
            )
    except Exception:
        logger.exception("Failed to decommission device")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not row:
        raise HTTPException(status_code=404, detail="Device not found or already decommissioned")
    return {"device_id": row["device_id"], "decommissioned_at": row["decommissioned_at"].isoformat()}


def _normalize_tags(tags: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        if tag is None:
            continue
        trimmed = str(tag).strip()
        if not trimmed or trimmed in seen:
            continue
        seen.add(trimmed)
        cleaned.append(trimmed)
    return cleaned



@router.get("/devices/{device_id}/tags")
async def get_device_tags(device_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            exists = await conn.fetchval(
                "SELECT 1 FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
                tenant_id,
                device_id,
            )
            if not exists:
                raise HTTPException(status_code=404, detail="Device not found")

            rows = await conn.fetch(
                """
                SELECT tag
                FROM device_tags
                WHERE tenant_id = $1 AND device_id = $2
                ORDER BY tag
                """,
                tenant_id,
                device_id,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch device tags")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"tenant_id": tenant_id, "device_id": device_id, "tags": [r["tag"] for r in rows]}


@router.put("/devices/{device_id}/tags")
async def set_device_tags(device_id: str, body: TagListUpdate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    tags = _normalize_tags(body.tags)
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            exists = await conn.fetchval(
                "SELECT 1 FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
                tenant_id,
                device_id,
            )
            if not exists:
                raise HTTPException(status_code=404, detail="Device not found")

            await conn.execute(
                "DELETE FROM device_tags WHERE tenant_id = $1 AND device_id = $2",
                tenant_id,
                device_id,
            )
            if tags:
                await conn.executemany(
                    """
                    INSERT INTO device_tags (tenant_id, device_id, tag)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (tenant_id, device_id, tag) DO NOTHING
                    """,
                    [(tenant_id, device_id, tag) for tag in tags],
                )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to update device tags")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"tenant_id": tenant_id, "device_id": device_id, "tags": tags}


@router.post("/devices/{device_id}/tags/{tag}")
async def add_device_tag(device_id: str, tag: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    tags = _normalize_tags([tag])
    if not tags:
        raise HTTPException(status_code=400, detail="Invalid tag")
    tag_value = tags[0]
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            exists = await conn.fetchval(
                "SELECT 1 FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
                tenant_id,
                device_id,
            )
            if not exists:
                raise HTTPException(status_code=404, detail="Device not found")

            await conn.execute(
                """
                INSERT INTO device_tags (tenant_id, device_id, tag)
                VALUES ($1, $2, $3)
                ON CONFLICT (tenant_id, device_id, tag) DO NOTHING
                """,
                tenant_id,
                device_id,
                tag_value,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to add device tag")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"tenant_id": tenant_id, "device_id": device_id, "tag": tag_value}


@router.delete("/devices/{device_id}/tags/{tag}")
async def remove_device_tag(device_id: str, tag: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    tags = _normalize_tags([tag])
    if not tags:
        raise HTTPException(status_code=400, detail="Invalid tag")
    tag_value = tags[0]
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            exists = await conn.fetchval(
                "SELECT 1 FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
                tenant_id,
                device_id,
            )
            if not exists:
                raise HTTPException(status_code=404, detail="Device not found")

            await conn.execute(
                """
                DELETE FROM device_tags
                WHERE tenant_id = $1 AND device_id = $2 AND tag = $3
                """,
                tenant_id,
                device_id,
                tag_value,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to remove device tag")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"tenant_id": tenant_id, "device_id": device_id, "tag": tag_value}


@router.get("/tags")
async def list_tags(pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            rows = await conn.fetch(
                """
                SELECT DISTINCT tag
                FROM device_tags
                WHERE tenant_id = $1
                ORDER BY tag
                """,
                tenant_id,
            )
    except Exception:
        logger.exception("Failed to fetch tags")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"tenant_id": tenant_id, "tags": [r["tag"] for r in rows]}


@router.get("/device-groups")
async def list_device_groups(pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            rows = await conn.fetch(
                """
                SELECT g.group_id, g.name, g.description, g.created_at,
                       COUNT(m.device_id)::int AS member_count
                FROM device_groups g
                LEFT JOIN device_group_members m
                    ON m.tenant_id = g.tenant_id AND m.group_id = g.group_id
                WHERE g.tenant_id = $1
                GROUP BY g.group_id, g.name, g.description, g.created_at
                ORDER BY g.name
                """,
                tenant_id,
            )
    except Exception:
        logger.exception("Failed to fetch device groups")
        raise HTTPException(status_code=500, detail="Internal server error")
    return {"groups": [dict(r) for r in rows], "total": len(rows)}


@router.post("/device-groups", status_code=201)
async def create_device_group(body: DeviceGroupCreate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    group_id = (body.group_id or f"grp-{uuid.uuid4().hex[:8]}").strip()
    if not group_id:
        raise HTTPException(status_code=400, detail="Invalid group_id")
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO device_groups (tenant_id, group_id, name, description)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (tenant_id, group_id) DO NOTHING
                RETURNING group_id, name, description, created_at, updated_at
                """,
                tenant_id,
                group_id,
                body.name.strip(),
                body.description,
            )
    except Exception:
        logger.exception("Failed to create device group")
        raise HTTPException(status_code=500, detail="Internal server error")
    if not row:
        raise HTTPException(status_code=409, detail="Group ID already exists")
    return dict(row)


@router.patch("/device-groups/{group_id}")
async def update_device_group(group_id: str, body: DeviceGroupUpdate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    if "name" in updates:
        updates["name"] = str(updates["name"]).strip()
        if not updates["name"]:
            raise HTTPException(status_code=400, detail="Invalid name")

    set_parts = [f"{field} = ${idx + 2}" for idx, field in enumerate(updates.keys())]
    params = [tenant_id] + list(updates.values()) + [group_id]
    set_clause = ", ".join(set_parts) + ", updated_at = now()"
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            row = await conn.fetchrow(
                f"""
                UPDATE device_groups
                SET {set_clause}
                WHERE tenant_id = $1 AND group_id = ${len(params)}
                RETURNING group_id, tenant_id, name, description, created_at, updated_at
                """,
                *params,
            )
    except Exception:
        logger.exception("Failed to update device group")
        raise HTTPException(status_code=500, detail="Internal server error")
    if not row:
        raise HTTPException(status_code=404, detail="Group not found")
    return dict(row)


@router.delete("/device-groups/{group_id}")
async def delete_device_group(group_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                DELETE FROM device_groups
                WHERE tenant_id = $1 AND group_id = $2
                RETURNING group_id
                """,
                tenant_id,
                group_id,
            )
    except Exception:
        logger.exception("Failed to delete device group")
        raise HTTPException(status_code=500, detail="Internal server error")
    if not row:
        raise HTTPException(status_code=404, detail="Group not found")
    return {"group_id": group_id, "deleted": True}


@router.get("/device-groups/{group_id}/devices")
async def list_group_members(group_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            rows = await conn.fetch(
                """
                SELECT
                    dr.device_id,
                    COALESCE(dr.metadata->>'name', dr.device_id) AS name,
                    COALESCE(ds.status, 'UNKNOWN') AS status,
                    dr.site_id,
                    m.added_at
                FROM device_group_members m
                JOIN device_registry dr
                    ON dr.tenant_id = m.tenant_id AND dr.device_id = m.device_id
                LEFT JOIN device_state ds
                    ON ds.tenant_id = m.tenant_id AND ds.device_id = m.device_id
                WHERE m.tenant_id = $1 AND m.group_id = $2
                ORDER BY name, dr.device_id
                """,
                tenant_id,
                group_id,
            )
    except Exception:
        logger.exception("Failed to fetch group members")
        raise HTTPException(status_code=500, detail="Internal server error")
    return {"group_id": group_id, "members": [dict(r) for r in rows], "total": len(rows)}


@router.put("/device-groups/{group_id}/devices/{device_id}")
async def add_group_member(group_id: str, device_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            group = await conn.fetchrow(
                "SELECT group_id FROM device_groups WHERE tenant_id = $1 AND group_id = $2",
                tenant_id,
                group_id,
            )
            if not group:
                raise HTTPException(status_code=404, detail="Group not found")
            device_exists = await conn.fetchval(
                "SELECT 1 FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
                tenant_id,
                device_id,
            )
            if not device_exists:
                raise HTTPException(status_code=404, detail="Device not found")
            await conn.execute(
                """
                INSERT INTO device_group_members (tenant_id, group_id, device_id)
                VALUES ($1, $2, $3)
                ON CONFLICT DO NOTHING
                """,
                tenant_id,
                group_id,
                device_id,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to add group member")
        raise HTTPException(status_code=500, detail="Internal server error")
    return {"group_id": group_id, "device_id": device_id, "action": "added"}


@router.delete("/device-groups/{group_id}/devices/{device_id}")
async def remove_group_member(group_id: str, device_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                DELETE FROM device_group_members
                WHERE tenant_id = $1 AND group_id = $2 AND device_id = $3
                RETURNING device_id
                """,
                tenant_id,
                group_id,
                device_id,
            )
    except Exception:
        logger.exception("Failed to remove group member")
        raise HTTPException(status_code=500, detail="Internal server error")
    if not row:
        raise HTTPException(status_code=404, detail="Device not in group")
    return {"group_id": group_id, "device_id": device_id, "action": "removed"}


@router.get("/maintenance-windows")
async def list_maintenance_windows(pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            rows = await conn.fetch(
                """
                SELECT *
                FROM alert_maintenance_windows
                WHERE tenant_id = $1
                ORDER BY starts_at DESC
                """,
                tenant_id,
            )
    except Exception:
        logger.exception("Failed to fetch maintenance windows")
        raise HTTPException(status_code=500, detail="Internal server error")
    return {"windows": [dict(r) for r in rows], "total": len(rows)}


@router.post("/maintenance-windows", status_code=201)
async def create_maintenance_window(body: MaintenanceWindowCreate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    window_id = f"mw-{uuid.uuid4().hex[:8]}"
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO alert_maintenance_windows
                    (tenant_id, window_id, name, starts_at, ends_at, recurring, site_ids, device_types, enabled)
                VALUES ($1,$2,$3,$4,$5,$6::jsonb,$7,$8,$9)
                RETURNING *
                """,
                tenant_id,
                window_id,
                body.name,
                body.starts_at,
                body.ends_at,
                json.dumps(body.recurring) if body.recurring is not None else None,
                _normalize_optional_ids(body.site_ids, "site_ids"),
                _normalize_optional_ids(body.device_types, "device_types"),
                body.enabled,
            )
    except Exception:
        logger.exception("Failed to create maintenance window")
        raise HTTPException(status_code=500, detail="Internal server error")
    return dict(row)


@router.patch("/maintenance-windows/{window_id}")
async def update_maintenance_window(
    window_id: str,
    body: MaintenanceWindowUpdate,
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    if "site_ids" in updates:
        updates["site_ids"] = _normalize_optional_ids(updates["site_ids"], "site_ids")
    if "device_types" in updates:
        updates["device_types"] = _normalize_optional_ids(updates["device_types"], "device_types")
    if "recurring" in updates:
        updates["recurring"] = json.dumps(updates["recurring"])

    set_parts: list[str] = []
    params: list = [tenant_id]
    idx = 2
    for key, value in updates.items():
        cast = "::jsonb" if key == "recurring" else ""
        set_parts.append(f"{key} = ${idx}{cast}")
        params.append(value)
        idx += 1
    params.append(window_id)
    set_clause = ", ".join(set_parts)
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            row = await conn.fetchrow(
                f"""
                UPDATE alert_maintenance_windows
                SET {set_clause}
                WHERE tenant_id = $1 AND window_id = ${len(params)}
                RETURNING *
                """,
                *params,
            )
    except Exception:
        logger.exception("Failed to update maintenance window")
        raise HTTPException(status_code=500, detail="Internal server error")
    if not row:
        raise HTTPException(status_code=404, detail="Window not found")
    return dict(row)


@router.delete("/maintenance-windows/{window_id}")
async def delete_maintenance_window(window_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                DELETE FROM alert_maintenance_windows
                WHERE tenant_id = $1 AND window_id = $2
                RETURNING window_id
                """,
                tenant_id,
                window_id,
            )
    except Exception:
        logger.exception("Failed to delete maintenance window")
        raise HTTPException(status_code=500, detail="Internal server error")
    if not row:
        raise HTTPException(status_code=404, detail="Window not found")
    return {"window_id": window_id, "deleted": True}


@router.get("/geocode")
async def geocode_address_endpoint(address: str = Query(..., min_length=3)):
    """Geocode an address using Nominatim (proxied to avoid CORS)."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": address,
                    "format": "json",
                    "limit": 1,
                },
                headers={
                    "User-Agent": "OpsConductor-Pulse/1.0"
                },
                timeout=10.0
            )
            if response.status_code == 200:
                data = response.json()
                if data:
                    return {
                        "latitude": float(data[0]["lat"]),
                        "longitude": float(data[0]["lon"]),
                        "display_name": data[0].get("display_name", "")
                    }
                return {"error": "Address not found"}
            return {"error": f"Geocoding service returned {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}


@router.get("/alerts")
@limiter.limit(CUSTOMER_RATE_LIMIT)
async def list_alerts(
    request: Request,
    response: Response,
    status: str = Query("OPEN"),  # OPEN | ACKNOWLEDGED | CLOSED | ALL
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    pool=Depends(get_db_pool),
):
    valid = {"OPEN", "ACKNOWLEDGED", "CLOSED", "ALL"}
    status_filter = status.upper()
    if status_filter not in valid:
        raise HTTPException(status_code=400, detail="Invalid status")

    tenant_id = get_tenant_id()
    try:
        where = "tenant_id = $1" if status_filter == "ALL" else "tenant_id = $1 AND status = $2"
        params = [tenant_id] if status_filter == "ALL" else [tenant_id, status_filter]
        async with tenant_connection(pool, tenant_id) as conn:
            rows = await conn.fetch(
                f"""
                SELECT id AS alert_id, tenant_id, created_at, closed_at, device_id, site_id, alert_type,
                       fingerprint, status, severity, confidence, summary, details,
                       silenced_until, acknowledged_by, acknowledged_at,
                       escalation_level, escalated_at
                FROM fleet_alert
                WHERE {where}
                ORDER BY created_at DESC
                LIMIT {limit} OFFSET {offset}
                """,
                *params,
            )
            total = await conn.fetchval(
                f"SELECT COUNT(*) FROM fleet_alert WHERE {where}",
                *params,
            )
    except Exception:
        logger.exception("Failed to fetch tenant alerts")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {
        "tenant_id": tenant_id,
        "alerts": [dict(r) for r in rows],
        "total": int(total or 0),
        "status_filter": status_filter,
        "limit": limit,
        "offset": offset,
    }


@router.get("/alerts/{alert_id}")
async def get_alert(alert_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                SELECT id AS alert_id, tenant_id, device_id, site_id, alert_type,
                       severity, confidence, summary, status, created_at
                FROM fleet_alert
                WHERE tenant_id = $1 AND id = $2
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


@router.patch("/alerts/{alert_id}/acknowledge", dependencies=[Depends(require_customer)])
async def acknowledge_alert(alert_id: str, request: Request, pool=Depends(get_db_pool)):
    try:
        alert_id_int = int(alert_id)
        if alert_id_int <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid alert_id")

    tenant_id = get_tenant_id()
    user = get_user() or {}
    user_ref = user.get("email") or user.get("preferred_username") or user.get("sub", "unknown")
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            UPDATE fleet_alert
            SET status = 'ACKNOWLEDGED',
                acknowledged_by = $3,
                acknowledged_at = now()
            WHERE tenant_id = $1 AND id = $2 AND status = 'OPEN'
            RETURNING id, status
            """,
            tenant_id,
            alert_id_int,
            user_ref,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found or not OPEN")

    logger.info(
        "alert acknowledged",
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "tenant_id": tenant_id,
            "alert_id": alert_id_int,
            "acknowledged_by": user_ref,
        },
    )
    return {"alert_id": alert_id, "status": "ACKNOWLEDGED", "acknowledged_by": user_ref}


@router.patch("/alerts/{alert_id}/close", dependencies=[Depends(require_customer)])
async def close_alert_endpoint(alert_id: str, request: Request, pool=Depends(get_db_pool)):
    try:
        alert_id_int = int(alert_id)
        if alert_id_int <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid alert_id")

    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            UPDATE fleet_alert
            SET status = 'CLOSED', closed_at = now()
            WHERE tenant_id = $1 AND id = $2 AND status IN ('OPEN', 'ACKNOWLEDGED')
            RETURNING id, status
            """,
            tenant_id,
            alert_id_int,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found or already closed")

    logger.info(
        "alert closed",
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "tenant_id": tenant_id,
            "alert_id": alert_id_int,
        },
    )
    return {"alert_id": alert_id, "status": "CLOSED"}


@router.patch("/alerts/{alert_id}/silence", dependencies=[Depends(require_customer)])
async def silence_alert(
    alert_id: str,
    body: SilenceRequest,
    request: Request,
    pool=Depends(get_db_pool),
):
    try:
        alert_id_int = int(alert_id)
        if alert_id_int <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid alert_id")

    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            UPDATE fleet_alert
            SET silenced_until = now() + ($3 || ' minutes')::interval
            WHERE tenant_id = $1 AND id = $2 AND status IN ('OPEN', 'ACKNOWLEDGED')
            RETURNING id, silenced_until
            """,
            tenant_id,
            alert_id_int,
            str(body.minutes),
        )
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found or closed")

    silenced_until = row["silenced_until"]
    logger.info(
        "alert silenced",
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "tenant_id": tenant_id,
            "alert_id": alert_id_int,
            "minutes": body.minutes,
            "silenced_until": silenced_until.isoformat() if silenced_until else None,
        },
    )
    return {"alert_id": alert_id, "silenced_until": silenced_until.isoformat()}


@router.get("/integrations")
async def list_integrations(type: str | None = Query(None), pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            rows = await fetch_integrations(conn, tenant_id, limit=50, integration_type=type)
    except Exception:
        logger.exception("Failed to fetch tenant integrations")
        raise HTTPException(status_code=500, detail="Internal server error")

    integrations = [dict(r) for r in rows]

    return {"tenant_id": tenant_id, "integrations": integrations}


@router.get("/metrics/catalog")
async def list_metric_catalog(pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        p = pool
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
async def upsert_metric_catalog(payload: MetricCatalogUpsert, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    metric_name = payload.metric_name.strip()
    if not metric_name:
        raise HTTPException(status_code=400, detail="metric_name is required")
    if payload.expected_min is not None and payload.expected_max is not None:
        if payload.expected_min > payload.expected_max:
            raise HTTPException(status_code=400, detail="expected_min must be <= expected_max")

    try:
        p = pool
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
async def delete_metric_catalog(metric_name: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        p = pool
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

    if not check_delete_result(result):
        raise HTTPException(status_code=404, detail="Metric not found")

    return Response(status_code=204)


@router.get("/normalized-metrics")
async def list_normalized_metrics(pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        p = pool
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
async def create_normalized_metric(payload: NormalizedMetricCreate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    normalized_name = _validate_name(payload.normalized_name)
    if payload.expected_min is not None and payload.expected_max is not None:
        if payload.expected_min > payload.expected_max:
            raise HTTPException(status_code=400, detail="expected_min must be <= expected_max")

    try:
        p = pool
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
async def update_normalized_metric(name: str, payload: NormalizedMetricUpdate, pool=Depends(get_db_pool)):
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
        p = pool
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
async def delete_normalized_metric(name: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    normalized_name = _validate_name(name)
    try:
        p = pool
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

    if not check_delete_result(result):
        raise HTTPException(status_code=404, detail="Normalized metric not found")

    return Response(status_code=204)


@router.get("/metric-mappings")
async def list_metric_mappings(normalized_name: str | None = Query(None), pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            if normalized_name:
                normalized_name = _validate_name(normalized_name)
                rows = await conn.fetch(
                    """
                    SELECT raw_metric, normalized_name, multiplier, offset_value, created_at
                    FROM metric_mappings
                    WHERE tenant_id = $1 AND normalized_name = $2
                    ORDER BY raw_metric
                    """,
                    tenant_id,
                    normalized_name,
                )
            else:
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
async def create_metric_mapping(payload: MetricMappingCreate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    raw_metric = payload.raw_metric.strip()
    if not METRIC_NAME_PATTERN.match(raw_metric):
        raise HTTPException(status_code=400, detail="Invalid raw metric name")
    normalized_name = _validate_name(payload.normalized_name)
    multiplier = payload.multiplier if payload.multiplier is not None else 1
    offset_value = payload.offset_value if payload.offset_value is not None else 0

    try:
        p = pool
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


@router.patch("/metric-mappings/{raw_metric}", dependencies=[Depends(require_customer_admin)])
async def update_metric_mapping(raw_metric: str, payload: MetricMappingUpdate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    raw_metric = raw_metric.strip()
    if not METRIC_NAME_PATTERN.match(raw_metric):
        raise HTTPException(status_code=400, detail="Invalid raw metric name")
    if payload.multiplier is None and payload.offset_value is None:
        raise HTTPException(status_code=400, detail="No fields provided")

    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                UPDATE metric_mappings
                SET multiplier = COALESCE($3, multiplier),
                    offset_value = COALESCE($4, offset_value)
                WHERE tenant_id = $1 AND raw_metric = $2
                RETURNING raw_metric, normalized_name, multiplier, offset_value, created_at
                """,
                tenant_id,
                raw_metric,
                payload.multiplier,
                payload.offset_value,
            )
    except Exception:
        logger.exception("Failed to update metric mapping")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not row:
        raise HTTPException(status_code=404, detail="Metric mapping not found")

    return {"tenant_id": tenant_id, "mapping": dict(row)}


@router.delete("/metric-mappings/{raw_metric}", dependencies=[Depends(require_customer_admin)])
async def delete_metric_mapping(raw_metric: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    raw_metric = raw_metric.strip()
    if not METRIC_NAME_PATTERN.match(raw_metric):
        raise HTTPException(status_code=400, detail="Invalid raw metric name")
    try:
        p = pool
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
async def list_snmp_integrations(pool=Depends(get_db_pool)):
    """List all SNMP integrations for this tenant."""
    tenant_id = get_tenant_id()
    try:
        p = pool
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
async def get_snmp_integration(integration_id: str, pool=Depends(get_db_pool)):
    """Get a specific SNMP integration."""
    tenant_id = get_tenant_id()
    if not validate_uuid(integration_id):
        raise HTTPException(status_code=404, detail="Integration not found")

    try:
        p = pool
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
async def create_snmp_integration(data: SNMPIntegrationCreate, pool=Depends(get_db_pool)):
    """Create a new SNMP integration."""
    tenant_id = get_tenant_id()
    name = _validate_name(data.name)
    validation = validate_snmp_host(data.snmp_host, data.snmp_port)
    if not validation.valid:
        raise HTTPException(status_code=400, detail=f"Invalid SNMP destination: {validation.error}")
    integration_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    snmp_config = data.snmp_config.model_dump()

    try:
        p = pool
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
async def update_snmp_integration(integration_id: str, data: SNMPIntegrationUpdate, pool=Depends(get_db_pool)):
    """Update an SNMP integration."""
    tenant_id = get_tenant_id()
    if not validate_uuid(integration_id):
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

    allowed_fields = {"name", "snmp_host", "snmp_port", "snmp_oid_prefix", "enabled", "snmp_config"}
    unknown_fields = [
        key for key, value in update_data.items()
        if value is not None and key not in allowed_fields
    ]
    if unknown_fields:
        raise HTTPException(status_code=400, detail="Invalid fields provided")

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
    values.append(datetime.now(timezone.utc))
    param_idx += 1

    values.extend([integration_id, tenant_id])

    try:
        p = pool
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
async def delete_snmp_integration(integration_id: str, pool=Depends(get_db_pool)):
    """Delete an SNMP integration."""
    tenant_id = get_tenant_id()
    if not validate_uuid(integration_id):
        raise HTTPException(status_code=404, detail="Integration not found")

    try:
        p = pool
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
async def list_email_integrations(pool=Depends(get_db_pool)):
    """List all email integrations for this tenant."""
    tenant_id = get_tenant_id()
    try:
        p = pool
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
                subject_template=email_template.get("subject_template"),
                body_template=email_template.get("body_template"),
                enabled=row["enabled"],
                created_at=row["created_at"].isoformat(),
                updated_at=row["updated_at"].isoformat(),
            )
        )
    return results


@router.get("/integrations/email/{integration_id}", response_model=EmailIntegrationResponse)
async def get_email_integration(integration_id: str, pool=Depends(get_db_pool)):
    """Get a specific email integration."""
    tenant_id = get_tenant_id()
    if not validate_uuid(integration_id):
        raise HTTPException(status_code=404, detail="Integration not found")

    try:
        p = pool
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
        subject_template=email_template.get("subject_template"),
        body_template=email_template.get("body_template"),
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
async def create_email_integration(data: EmailIntegrationCreate, pool=Depends(get_db_pool)):
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
    now = datetime.now(timezone.utc)

    email_config = data.smtp_config.model_dump()
    email_recipients = data.recipients.model_dump()
    email_template = data.template.model_dump() if data.template else {
        "subject_template": "[{severity}] {alert_type}: {device_id}",
        "format": "html",
    }

    try:
        p = pool
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
        subject_template=email_template.get("subject_template"),
        body_template=email_template.get("body_template"),
        enabled=row["enabled"],
        created_at=row["created_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
    )


@router.patch(
    "/integrations/email/{integration_id}",
    response_model=EmailIntegrationResponse,
    dependencies=[Depends(require_customer_admin)],
)
async def update_email_integration(integration_id: str, data: EmailIntegrationUpdate, pool=Depends(get_db_pool)):
    """Update an email integration."""
    tenant_id = get_tenant_id()
    if not validate_uuid(integration_id):
        raise HTTPException(status_code=404, detail="Integration not found")

    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    if "smtp_config" in update_data or "recipients" in update_data:
        try:
            p = pool
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
    values.append(datetime.now(timezone.utc))
    param_idx += 1

    values.extend([integration_id, tenant_id])

    try:
        p = pool
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
        subject_template=email_template.get("subject_template"),
        body_template=email_template.get("body_template"),
        enabled=row["enabled"],
        created_at=row["created_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
    )


@router.delete(
    "/integrations/email/{integration_id}",
    status_code=204,
    dependencies=[Depends(require_customer_admin)],
)
async def delete_email_integration(integration_id: str, pool=Depends(get_db_pool)):
    """Delete an email integration."""
    tenant_id = get_tenant_id()
    if not validate_uuid(integration_id):
        raise HTTPException(status_code=404, detail="Integration not found")

    try:
        p = pool
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
async def list_mqtt_integrations(pool=Depends(get_db_pool)):
    """List all MQTT integrations for this tenant."""
    tenant_id = get_tenant_id()
    try:
        p = pool
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
async def get_mqtt_integration(integration_id: str, pool=Depends(get_db_pool)):
    """Get a specific MQTT integration."""
    tenant_id = get_tenant_id()
    if not validate_uuid(integration_id):
        raise HTTPException(status_code=404, detail="Integration not found")

    try:
        p = pool
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
async def create_mqtt_integration(data: MQTTIntegrationCreate, pool=Depends(get_db_pool)):
    """Create a new MQTT integration."""
    tenant_id = get_tenant_id()
    name = _validate_name(data.name)
    validation = validate_mqtt_topic(data.mqtt_topic, tenant_id)
    if not validation.valid:
        raise HTTPException(status_code=400, detail=f"Invalid MQTT topic: {validation.error}")

    integration_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    try:
        p = pool
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
async def update_mqtt_integration(integration_id: str, data: MQTTIntegrationUpdate, pool=Depends(get_db_pool)):
    """Update a MQTT integration."""
    tenant_id = get_tenant_id()
    if not validate_uuid(integration_id):
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
    values.append(datetime.now(timezone.utc))
    param_idx += 1

    values.extend([integration_id, tenant_id])

    try:
        p = pool
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
async def delete_mqtt_integration(integration_id: str, pool=Depends(get_db_pool)):
    """Delete a MQTT integration."""
    tenant_id = get_tenant_id()
    if not validate_uuid(integration_id):
        raise HTTPException(status_code=404, detail="Integration not found")

    try:
        p = pool
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
async def test_mqtt_integration(integration_id: str, pool=Depends(get_db_pool)):
    """Send a test MQTT message."""
    tenant_id = get_tenant_id()
    if not validate_uuid(integration_id):
        raise HTTPException(status_code=404, detail="Integration not found")

    try:
        p = pool
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

    now = datetime.now(timezone.utc).replace(microsecond=0)
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
async def create_integration_route(body: IntegrationCreate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    name = _validate_name(body.name)
    valid, error = await validate_webhook_url(body.webhook_url)
    if not valid:
        raise HTTPException(status_code=400, detail=f"Invalid webhook URL: {error}")
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            integration = await create_integration(
                conn,
                tenant_id=tenant_id,
                name=name,
                webhook_url=body.webhook_url,
                body_template=body.body_template,
                enabled=body.enabled,
            )
    except Exception:
        logger.exception("Failed to create integration")
        raise HTTPException(status_code=500, detail="Internal server error")

    return integration


@router.get("/integrations/{integration_id}")
async def get_integration(integration_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            integration = await fetch_integration(conn, tenant_id, integration_id)
    except Exception:
        logger.exception("Failed to fetch integration")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    return integration


@router.patch("/integrations/{integration_id}", dependencies=[Depends(require_customer_admin)])
async def patch_integration(integration_id: str, body: IntegrationUpdate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    if body.name is None and body.webhook_url is None and body.body_template is None and body.enabled is None:
        raise HTTPException(status_code=400, detail="No fields to update")

    name = _validate_name(body.name) if body.name is not None else None
    if body.webhook_url is not None:
        valid, error = await validate_webhook_url(body.webhook_url)
        if not valid:
            raise HTTPException(status_code=400, detail=f"Invalid webhook URL: {error}")

    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            integration = await update_integration(
                conn,
                tenant_id=tenant_id,
                integration_id=integration_id,
                name=name,
                webhook_url=body.webhook_url,
                body_template=body.body_template,
                enabled=body.enabled,
            )
    except Exception:
        logger.exception("Failed to update integration")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    return integration


@router.get("/integrations/{integration_id}/template-variables", dependencies=[Depends(require_customer)])
async def get_template_variables(integration_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            "SELECT integration_id, type FROM integrations WHERE tenant_id=$1 AND integration_id=$2",
            tenant_id,
            integration_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Integration not found")
    return {
        "integration_id": integration_id,
        "type": row["type"],
        "variables": TEMPLATE_VARIABLES,
        "syntax": "Jinja2 - use {{ variable_name }} syntax",
        "example": "Alert {{ alert_id }}: {{ severity_label }} - {{ summary }}",
    }


@router.delete("/integrations/{integration_id}", dependencies=[Depends(require_customer_admin)])
async def delete_integration_route(integration_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        p = pool
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
async def test_snmp_integration(integration_id: str, pool=Depends(get_db_pool)):
    """Send a test SNMP trap."""
    tenant_id = get_tenant_id()
    try:
        p = pool
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
        alert_id=f"test-{int(datetime.now(timezone.utc).timestamp())}",
        device_id="test-device",
        tenant_id=tenant_id,
        severity="info",
        message="Test trap from OpsConductor Pulse",
        timestamp=datetime.now(timezone.utc),
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
async def test_email_integration(integration_id: str, pool=Depends(get_db_pool)):
    """Send a test email."""
    tenant_id = get_tenant_id()
    if not validate_uuid(integration_id):
        raise HTTPException(status_code=404, detail="Integration not found")

    try:
        p = pool
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
        alert_id=f"test-{int(datetime.now(timezone.utc).timestamp())}",
        device_id="test-device",
        tenant_id=tenant_id,
        severity="info",
        message="This is a test email from OpsConductor Pulse. If you received this, your email integration is working correctly.",
        alert_type="TEST_ALERT",
        timestamp=datetime.now(timezone.utc),
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
async def test_integration_delivery(integration_id: str, pool=Depends(get_db_pool)):
    """Send a test delivery to any integration type."""
    tenant_id = get_tenant_id()
    if not validate_uuid(integration_id):
        raise HTTPException(status_code=404, detail="Integration not found")

    try:
        p = pool
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
    now = datetime.now(timezone.utc)

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


@router.post("/integrations/{integration_id}/test-send", dependencies=[Depends(require_customer)])
async def test_send_integration(integration_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            SELECT integration_id, type, config_json, enabled
            FROM integrations
            WHERE tenant_id = $1 AND integration_id = $2
            """,
            tenant_id,
            integration_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Integration not found")
    if row["type"] != "webhook":
        raise HTTPException(status_code=400, detail="Test send only supported for webhook integrations")
    if not row["enabled"]:
        raise HTTPException(status_code=400, detail="Integration is disabled")

    config = row["config_json"] or {}
    if isinstance(config, str):
        try:
            config = json.loads(config)
        except Exception:
            config = {}
    url = config.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="Webhook URL not configured")

    valid, reason = await validate_webhook_url(url, allow_http=True)
    if not valid:
        raise HTTPException(status_code=400, detail=f"Webhook URL blocked: {reason}")

    headers = config.get("headers", {})
    payload = {**TEST_PAYLOAD, "created_at": datetime.now(timezone.utc).isoformat()}

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
        latency_ms = int((time.monotonic() - start) * 1000)
        return {
            "success": resp.status_code < 400,
            "http_status": resp.status_code,
            "latency_ms": latency_ms,
        }
    except Exception as exc:
        latency_ms = int((time.monotonic() - start) * 1000)
        return {
            "success": False,
            "http_status": None,
            "latency_ms": latency_ms,
            "error": str(exc),
        }


@router.get("/integration-routes")
async def list_integration_routes(limit: int = Query(100, ge=1, le=500), pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            routes = await fetch_integration_routes(conn, tenant_id, limit=limit)
    except Exception:
        logger.exception("Failed to fetch integration routes")
        raise HTTPException(status_code=500, detail="Internal server error")
    return {"tenant_id": tenant_id, "routes": routes}


@router.get("/integration-routes/{route_id}")
async def get_integration_route(route_id: str, pool=Depends(get_db_pool)):
    if not validate_uuid(route_id):
        raise HTTPException(status_code=400, detail="Invalid route_id format: must be a valid UUID")

    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            route = await fetch_integration_route(conn, tenant_id, route_id)
    except Exception:
        logger.exception("Failed to fetch integration route")
        raise HTTPException(status_code=500, detail="Internal server error")
    if not route:
        raise HTTPException(status_code=404, detail="Integration route not found")
    return route


@router.post("/integration-routes", dependencies=[Depends(require_customer_admin)])
async def create_integration_route_endpoint(body: RouteCreate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    alert_types = _normalize_list(body.alert_types, ALERT_TYPES, "alert_types")
    severities = _normalize_list(body.severities, SEVERITIES, "severities")
    try:
        p = pool
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
async def patch_integration_route(route_id: str, body: RouteUpdate, pool=Depends(get_db_pool)):
    if not validate_uuid(route_id):
        raise HTTPException(status_code=400, detail="Invalid route_id format: must be a valid UUID")

    if body.alert_types is None and body.severities is None and body.enabled is None:
        raise HTTPException(status_code=400, detail="No fields to update")

    alert_types = _normalize_list(body.alert_types, ALERT_TYPES, "alert_types") if body.alert_types is not None else None
    severities = _normalize_list(body.severities, SEVERITIES, "severities") if body.severities is not None else None

    tenant_id = get_tenant_id()
    try:
        p = pool
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
async def delete_integration_route_endpoint(route_id: str, pool=Depends(get_db_pool)):
    if not validate_uuid(route_id):
        raise HTTPException(status_code=400, detail="Invalid route_id format: must be a valid UUID")

    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            deleted = await delete_integration_route(conn, tenant_id, route_id)
    except Exception:
        logger.exception("Failed to delete integration route")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not deleted:
        raise HTTPException(status_code=404, detail="Integration route not found")
    return Response(status_code=204)


@router.get("/alert-rule-templates", dependencies=[Depends(require_customer)])
async def list_alert_rule_templates(device_type: str | None = Query(None)):
    templates = ALERT_RULE_TEMPLATES
    if device_type:
        templates = [tmpl for tmpl in templates if tmpl["device_type"] == device_type]
    return {"templates": templates, "total": len(templates)}


@router.post("/alert-rule-templates/apply", dependencies=[Depends(require_customer)])
@limiter.limit(CUSTOMER_RATE_LIMIT)
async def apply_alert_rule_templates(
    request: Request,
    response: Response,
    body: ApplyTemplatesRequest,
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()
    template_map = {tmpl["template_id"]: tmpl for tmpl in ALERT_RULE_TEMPLATES}

    requested = [template_map[tid] for tid in body.template_ids if tid in template_map]
    if not requested:
        raise HTTPException(status_code=400, detail="No valid template_ids provided")

    created = []
    skipped = []

    async with tenant_connection(pool, tenant_id) as conn:
        for tmpl in requested:
            existing = await conn.fetchval(
                "SELECT id FROM alert_rules WHERE tenant_id = $1 AND name = $2",
                tenant_id,
                tmpl["name"],
            )
            if existing:
                skipped.append(tmpl["template_id"])
                continue

            row = await conn.fetchrow(
                """
                INSERT INTO alert_rules
                    (tenant_id, name, description, metric_name, operator, threshold,
                     severity, duration_seconds, device_type, site_ids, enabled)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,true)
                RETURNING id, name
                """,
                tenant_id,
                tmpl["name"],
                tmpl["description"],
                tmpl["metric_name"],
                tmpl["operator"],
                tmpl["threshold"],
                tmpl["severity"],
                tmpl["duration_seconds"],
                tmpl["device_type"],
                body.site_ids or None,
            )
            created.append(
                {"id": row["id"], "name": row["name"], "template_id": tmpl["template_id"]}
            )

    return {"created": created, "skipped": skipped}


@router.get("/alert-rules")
async def list_alert_rules(pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            rules = await fetch_alert_rules(conn, tenant_id)
    except Exception:
        logger.exception("Failed to fetch alert rules")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"tenant_id": tenant_id, "rules": [_with_rule_conditions(rule) for rule in rules]}


@router.get("/alert-rules/{rule_id}")
async def get_alert_rule(rule_id: str, pool=Depends(get_db_pool)):
    if not validate_uuid(rule_id):
        raise HTTPException(status_code=400, detail="Invalid rule_id format: must be a valid UUID")

    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            rule = await fetch_alert_rule(conn, tenant_id, rule_id)
    except Exception:
        logger.exception("Failed to fetch alert rule")
        raise HTTPException(status_code=500, detail="Internal server error")
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return _with_rule_conditions(rule)


@router.post("/alert-rules", dependencies=[Depends(require_customer_admin)])
async def create_alert_rule_endpoint(request: Request, body: AlertRuleCreate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    conditions_json = body.conditions.model_dump() if body.conditions else None
    anomaly_conditions_json = (
        body.anomaly_conditions.model_dump() if body.anomaly_conditions else None
    )
    gap_conditions_json = body.gap_conditions.model_dump() if body.gap_conditions else None
    rule_type = body.rule_type

    if rule_type == "anomaly":
        if anomaly_conditions_json is None:
            raise HTTPException(status_code=422, detail="anomaly_conditions is required")
        metric_name = anomaly_conditions_json["metric_name"]
        if not METRIC_NAME_PATTERN.match(metric_name):
            raise HTTPException(status_code=400, detail="Invalid metric_name format")
        operator = "GT"
        threshold = float(anomaly_conditions_json["z_threshold"])
        conditions_payload = anomaly_conditions_json
    elif rule_type == "telemetry_gap":
        if gap_conditions_json is None:
            raise HTTPException(status_code=422, detail="gap_conditions is required")
        metric_name = gap_conditions_json["metric_name"]
        if not METRIC_NAME_PATTERN.match(metric_name):
            raise HTTPException(status_code=400, detail="Invalid metric_name format")
        operator = "GT"
        threshold = float(gap_conditions_json["gap_minutes"])
        conditions_payload = gap_conditions_json
    elif conditions_json:
        first_condition = conditions_json["conditions"][0]
        metric_name = first_condition["metric_name"]
        operator = first_condition["operator"]
        threshold = first_condition["threshold"]
        for cond in conditions_json["conditions"]:
            if cond["operator"] not in VALID_OPERATORS:
                raise HTTPException(status_code=400, detail="Invalid operator value")
            if not METRIC_NAME_PATTERN.match(cond["metric_name"]):
                raise HTTPException(status_code=400, detail="Invalid metric_name format")
        conditions_payload = conditions_json
    else:
        if body.operator not in VALID_OPERATORS:
            raise HTTPException(status_code=400, detail="Invalid operator value")
        if body.metric_name is None or not METRIC_NAME_PATTERN.match(body.metric_name):
            raise HTTPException(status_code=400, detail="Invalid metric_name format")
        if body.threshold is None:
            raise HTTPException(status_code=400, detail="threshold is required")
        metric_name = body.metric_name
        operator = body.operator
        threshold = body.threshold
        conditions_payload = None

    if body.site_ids is not None:
        for site_id in body.site_ids:
            if site_id is None or not str(site_id).strip():
                raise HTTPException(status_code=400, detail="Invalid site_id value")
    group_ids = _normalize_optional_ids(body.group_ids, "group_ids")
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            rule = await create_alert_rule(
                conn,
                tenant_id=tenant_id,
                name=body.name,
                rule_type=rule_type,
                metric_name=metric_name,
                operator=operator,
                threshold=threshold,
                severity=body.severity,
                duration_seconds=body.duration_seconds,
                description=body.description,
                site_ids=body.site_ids,
                group_ids=group_ids,
                conditions=conditions_payload,
                enabled=body.enabled,
            )
    except Exception:
        logger.exception("Failed to create alert rule")
        raise HTTPException(status_code=500, detail="Internal server error")
    audit = getattr(request.app.state, "audit", None)
    if audit:
        user = get_user()
        username = (
            user.get("preferred_username")
            or user.get("email")
            or user.get("sub")
            or "unknown"
        )
        audit.config_changed(
            tenant_id,
            "rule",
            rule.get("rule_id"),
            "create",
            body.name,
            user_id=user.get("sub") or "unknown",
            username=username,
            ip_address=request.client.host if request.client else None,
            details={"metric": metric_name, "threshold": threshold},
        )
    return JSONResponse(status_code=201, content=jsonable_encoder(_with_rule_conditions(rule)))


@router.patch("/alert-rules/{rule_id}", dependencies=[Depends(require_customer_admin)])
async def update_alert_rule_endpoint(rule_id: str, body: AlertRuleUpdate, pool=Depends(get_db_pool)):
    if not validate_uuid(rule_id):
        raise HTTPException(status_code=400, detail="Invalid rule_id format: must be a valid UUID")

    if (
        body.name is None
        and body.rule_type is None
        and body.metric_name is None
        and body.operator is None
        and body.threshold is None
        and body.severity is None
        and body.duration_seconds is None
        and body.description is None
        and body.site_ids is None
        and body.group_ids is None
        and body.conditions is None
        and body.anomaly_conditions is None
        and body.gap_conditions is None
        and body.enabled is None
    ):
        raise HTTPException(status_code=400, detail="No fields to update")

    conditions_json = body.conditions.model_dump() if body.conditions else None
    anomaly_conditions_json = (
        body.anomaly_conditions.model_dump() if body.anomaly_conditions else None
    )
    gap_conditions_json = body.gap_conditions.model_dump() if body.gap_conditions else None
    if body.rule_type == "anomaly":
        if anomaly_conditions_json is None:
            raise HTTPException(status_code=422, detail="anomaly_conditions is required")
        metric_name = anomaly_conditions_json["metric_name"]
        if not METRIC_NAME_PATTERN.match(metric_name):
            raise HTTPException(status_code=400, detail="Invalid metric_name format")
        operator = "GT"
        threshold = float(anomaly_conditions_json["z_threshold"])
        conditions_payload = anomaly_conditions_json
    elif body.rule_type == "telemetry_gap":
        if gap_conditions_json is None:
            raise HTTPException(status_code=422, detail="gap_conditions is required")
        metric_name = gap_conditions_json["metric_name"]
        if not METRIC_NAME_PATTERN.match(metric_name):
            raise HTTPException(status_code=400, detail="Invalid metric_name format")
        operator = "GT"
        threshold = float(gap_conditions_json["gap_minutes"])
        conditions_payload = gap_conditions_json
    elif conditions_json:
        for cond in conditions_json["conditions"]:
            if cond["operator"] not in VALID_OPERATORS:
                raise HTTPException(status_code=400, detail="Invalid operator value")
            if not METRIC_NAME_PATTERN.match(cond["metric_name"]):
                raise HTTPException(status_code=400, detail="Invalid metric_name format")
        first_condition = conditions_json["conditions"][0]
        metric_name = first_condition["metric_name"]
        operator = first_condition["operator"]
        threshold = first_condition["threshold"]
        conditions_payload = conditions_json
    else:
        metric_name = body.metric_name
        operator = body.operator
        threshold = body.threshold
        conditions_payload = None
        if operator is not None and operator not in VALID_OPERATORS:
            raise HTTPException(status_code=400, detail="Invalid operator value")
        if metric_name is not None and not METRIC_NAME_PATTERN.match(metric_name):
            raise HTTPException(status_code=400, detail="Invalid metric_name format")
    if body.site_ids is not None:
        for site_id in body.site_ids:
            if site_id is None or not str(site_id).strip():
                raise HTTPException(status_code=400, detail="Invalid site_id value")
    group_ids = _normalize_optional_ids(body.group_ids, "group_ids")

    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            rule = await update_alert_rule(
                conn,
                tenant_id=tenant_id,
                rule_id=rule_id,
                name=body.name,
                rule_type=body.rule_type,
                metric_name=metric_name,
                operator=operator,
                threshold=threshold,
                severity=body.severity,
                duration_seconds=body.duration_seconds,
                description=body.description,
                site_ids=body.site_ids,
                group_ids=group_ids,
                conditions=conditions_payload,
                enabled=body.enabled,
            )
    except Exception:
        logger.exception("Failed to update alert rule")
        raise HTTPException(status_code=500, detail="Internal server error")
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return _with_rule_conditions(rule)


@router.delete("/alert-rules/{rule_id}", dependencies=[Depends(require_customer_admin)])
async def delete_alert_rule_endpoint(rule_id: str, pool=Depends(get_db_pool)):
    if not validate_uuid(rule_id):
        raise HTTPException(status_code=400, detail="Invalid rule_id format: must be a valid UUID")

    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            deleted = await delete_alert_rule(conn, tenant_id, rule_id)
    except Exception:
        logger.exception("Failed to delete alert rule")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not deleted:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return Response(status_code=204)


@router.get("/delivery-jobs", dependencies=[Depends(require_customer)])
async def list_delivery_jobs(
    status: str | None = Query(None),
    integration_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()
    conditions = ["tenant_id = $1"]
    params: list[object] = [tenant_id]

    if status:
        valid_statuses = {"PENDING", "PROCESSING", "COMPLETED", "FAILED"}
        normalized = status.upper()
        if normalized not in valid_statuses:
            raise HTTPException(status_code=400, detail="Invalid status")
        params.append(normalized)
        conditions.append(f"status = ${len(params)}")

    if integration_id:
        params.append(integration_id)
        conditions.append(f"integration_id = ${len(params)}")

    where = " AND ".join(conditions)
    async with tenant_connection(pool, tenant_id) as conn:
        rows = await conn.fetch(
            f"""
            SELECT job_id, alert_id, integration_id, route_id, status,
                   attempts, last_error, deliver_on_event, created_at, updated_at
            FROM delivery_jobs
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT {limit} OFFSET {offset}
            """,
            *params,
        )
        total = await conn.fetchval(
            f"SELECT COUNT(*) FROM delivery_jobs WHERE {where}",
            *params,
        )

    return {"jobs": [dict(row) for row in rows], "total": int(total or 0)}


@router.get("/delivery-jobs/{job_id}/attempts", dependencies=[Depends(require_customer)])
async def get_delivery_job_attempts(job_id: int, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        job = await conn.fetchrow(
            "SELECT job_id FROM delivery_jobs WHERE tenant_id = $1 AND job_id = $2",
            tenant_id,
            job_id,
        )
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        attempts = await conn.fetch(
            """
            SELECT attempt_no, ok, http_status, latency_ms, error, started_at, finished_at
            FROM delivery_attempts
            WHERE job_id = $1
            ORDER BY attempt_no ASC
            """,
            job_id,
        )
    return {"job_id": job_id, "attempts": [dict(a) for a in attempts]}


@router.get("/delivery-status")
async def delivery_status(
    limit: int = Query(20, ge=1, le=100),
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            attempts = await fetch_delivery_attempts(conn, tenant_id, limit=limit)
    except Exception:
        logger.exception("Failed to fetch tenant delivery attempts")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"tenant_id": tenant_id, "attempts": attempts}


@router.get("/audit-log")
async def get_audit_log(
    request: Request,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    category: str | None = Query(None),
    severity: str | None = Query(None),
    entity_type: str | None = Query(None),
    entity_id: str | None = Query(None),
    start: str | None = Query(None),
    end: str | None = Query(None),
    search: str | None = Query(None),
):
    tenant_id = get_tenant_id()
    pool = request.app.state.pool

    async with tenant_connection(pool, tenant_id) as conn:

        where = ["tenant_id = $1"]
        params = [tenant_id]
        idx = 2

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

        where_clause = " AND ".join(where)

        total = await conn.fetchval(
            f"SELECT COUNT(*) FROM audit_log WHERE {where_clause}",
            *params
        )

        rows = await conn.fetch(
            f"""
            SELECT timestamp, event_type, category, severity,
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
        "offset": offset
    }