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
from reports.sla_report import generate_sla_report
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
    rule_type: Literal["threshold", "anomaly", "telemetry_gap", "window"] = "threshold"
    metric_name: str | None = Field(default=None, min_length=1, max_length=100)
    operator: str | None = None
    threshold: float | None = None
    severity: int = Field(default=3, ge=1, le=5)
    duration_seconds: int = Field(
        default=0,
        ge=0,
        description="Seconds threshold must be continuously breached before alert fires. 0 = immediate.",
    )
    duration_minutes: int | None = Field(
        default=None,
        ge=1,
        description="If set, alert fires only after condition holds for this many minutes.",
    )
    description: str | None = None
    site_ids: list[str] | None = None
    group_ids: list[str] | None = None
    device_group_id: str | None = Field(
        default=None,
        description="Scope rule to a single device group",
    )
    conditions: List["RuleCondition"] | "RuleConditions" | None = None
    match_mode: Literal["all", "any"] = "all"
    anomaly_conditions: "AnomalyConditions | None" = None
    gap_conditions: "TelemetryGapConditions | None" = None
    enabled: bool = True
    aggregation: str | None = Field(
        default=None,
        description="Aggregation function for WINDOW rules: avg, min, max, count, sum",
    )
    window_seconds: int | None = Field(
        default=None,
        ge=60,
        le=3600,
        description="Sliding window in seconds for WINDOW rules",
    )


class AlertRuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    rule_type: Literal["threshold", "anomaly", "telemetry_gap", "window"] | None = None
    metric_name: str | None = Field(default=None, min_length=1, max_length=100)
    operator: str | None = None
    threshold: float | None = None
    severity: int | None = Field(default=None, ge=1, le=5)
    duration_seconds: int | None = Field(default=None, ge=0)
    duration_minutes: int | None = Field(default=None, ge=1)
    description: str | None = None
    site_ids: list[str] | None = None
    group_ids: list[str] | None = None
    device_group_id: str | None = None
    conditions: List["RuleCondition"] | "RuleConditions" | None = None
    match_mode: Literal["all", "any"] | None = None
    anomaly_conditions: "AnomalyConditions | None" = None
    gap_conditions: "TelemetryGapConditions | None" = None
    enabled: bool | None = None
    aggregation: str | None = None
    window_seconds: int | None = Field(default=None, ge=60, le=3600)


class RuleCondition(BaseModel):
    metric_name: str
    operator: Literal["GT", "LT", "GTE", "LTE"]
    threshold: float
    duration_minutes: int | None = Field(default=None, ge=1)


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
    if not result.get("match_mode"):
        result["match_mode"] = "all"
    result["device_group_id"] = result.get("device_group_id")
    raw_conditions = result.get("conditions")
    if isinstance(raw_conditions, str):
        try:
            raw_conditions = json.loads(raw_conditions)
        except Exception:
            raw_conditions = None
    if result.get("duration_minutes") is None:
        secs = result.get("duration_seconds")
        if isinstance(secs, int) and secs > 0 and secs % 60 == 0:
            result["duration_minutes"] = secs // 60
    if result.get("rule_type") == "anomaly":
        result["conditions"] = raw_conditions if isinstance(raw_conditions, dict) else {}
        result["anomaly_conditions"] = result.get("conditions")
        result["gap_conditions"] = None
    elif result.get("rule_type") == "telemetry_gap":
        result["conditions"] = raw_conditions if isinstance(raw_conditions, dict) else {}
        result["anomaly_conditions"] = None
        result["gap_conditions"] = result.get("conditions")
    else:
        if isinstance(raw_conditions, dict) and isinstance(raw_conditions.get("conditions"), list):
            result["conditions"] = raw_conditions["conditions"]
            if result.get("match_mode") not in {"all", "any"}:
                result["match_mode"] = "any" if raw_conditions.get("combinator") == "OR" else "all"
        elif isinstance(raw_conditions, list):
            result["conditions"] = raw_conditions
        else:
            result["conditions"] = []
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












@router.get("/subscriptions")
async def list_subscriptions(
    include_expired: bool = Query(False),
    pool=Depends(get_db_pool),
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
    pool=Depends(get_db_pool),
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












