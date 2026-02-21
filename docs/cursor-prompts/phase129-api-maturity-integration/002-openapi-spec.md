# Task 002 -- OpenAPI Spec: Response Models, Tags, Swagger UI

## Commit Message
```
feat: add OpenAPI metadata, response models, and Swagger UI access control
```

## Context

FastAPI auto-generates OpenAPI from route signatures, but our endpoints mostly return raw dicts, have no docstrings, and use default OpenAPI metadata. This task adds proper response models, tags, and controlled access to Swagger UI.

## Step 1: Configure FastAPI OpenAPI metadata

In `services/ui_iot/app.py`, update the `FastAPI()` constructor:

```python
# BEFORE:
app = FastAPI()

# AFTER:
tags_metadata = [
    {
        "name": "devices",
        "description": "Device management: CRUD, tokens, tags, groups, maintenance windows, device twin, commands",
    },
    {
        "name": "alerts",
        "description": "Alert management: list, acknowledge, close, silence, alert rules, digest settings",
    },
    {
        "name": "notifications",
        "description": "Notification channels and routing rules for alert delivery",
    },
    {
        "name": "escalation",
        "description": "Escalation policies with multi-level notification chains",
    },
    {
        "name": "oncall",
        "description": "On-call schedules, layers, and override management",
    },
    {
        "name": "exports",
        "description": "Data exports: device lists, alert history, SLA reports, telemetry CSV",
    },
    {
        "name": "metrics",
        "description": "Metric catalog, normalized metrics, and metric mappings",
    },
    {
        "name": "jobs",
        "description": "Scheduled and one-time job management",
    },
    {
        "name": "customer",
        "description": "Customer tenant operations: sites, subscriptions, fleet summary",
    },
    {
        "name": "operator",
        "description": "Operator-only: cross-tenant management, tenant CRUD, system settings",
    },
    {
        "name": "system",
        "description": "System health, metrics, capacity, and error monitoring (operator)",
    },
    {
        "name": "roles",
        "description": "Role-based access control and permission management",
    },
    {
        "name": "users",
        "description": "User management for operators and tenant admins",
    },
]

app = FastAPI(
    title="OpsConductor Pulse API",
    description=(
        "IoT fleet management platform API. Provides device monitoring, "
        "alerting, notification delivery, and operational tooling for "
        "multi-tenant IoT deployments."
    ),
    version="1.0.0",
    openapi_tags=tags_metadata,
    docs_url=None,   # We will serve conditionally below
    redoc_url=None,  # We will serve conditionally below
)
```

## Step 2: Add conditional Swagger UI and ReDoc endpoints

Add endpoints that serve docs based on role or dev mode. Place these after the `app` creation but before route includes:

```python
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi


def _is_dev_mode() -> bool:
    return os.getenv("MODE", "DEV").upper() == "DEV"


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui(request: Request):
    """Serve Swagger UI. In PROD, requires operator role."""
    if not _is_dev_mode():
        # Check for operator auth
        session_token = request.cookies.get("pulse_session")
        auth_header = request.headers.get("authorization", "")
        token = None
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        elif session_token:
            token = session_token

        if not token:
            raise HTTPException(status_code=401, detail="Authentication required")
        try:
            payload = await validate_token(token)
            realm_access = payload.get("realm_access", {}) or {}
            roles = set(realm_access.get("roles", []) or [])
            if not roles.intersection({"operator", "operator-admin"}):
                raise HTTPException(status_code=403, detail="Operator role required")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")

    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="OpsConductor Pulse API - Swagger UI",
    )


@app.get("/redoc", include_in_schema=False)
async def custom_redoc(request: Request):
    """Serve ReDoc. Available in DEV mode, restricted in PROD."""
    if not _is_dev_mode():
        session_token = request.cookies.get("pulse_session")
        auth_header = request.headers.get("authorization", "")
        token = None
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        elif session_token:
            token = session_token

        if not token:
            raise HTTPException(status_code=401, detail="Authentication required")
        try:
            payload = await validate_token(token)
            realm_access = payload.get("realm_access", {}) or {}
            roles = set(realm_access.get("roles", []) or [])
            if not roles.intersection({"operator", "operator-admin"}):
                raise HTTPException(status_code=403, detail="Operator role required")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")

    return get_redoc_html(
        openapi_url="/openapi.json",
        title="OpsConductor Pulse API - ReDoc",
    )
```

Note: By setting `docs_url=None` and `redoc_url=None` in the FastAPI constructor, we disable the default docs endpoints. The `/openapi.json` endpoint is still auto-generated and always accessible (this is fine -- the spec itself does not leak secrets).

## Step 3: Create shared response models

Create a new file `services/ui_iot/schemas/responses.py`:

```python
"""Shared Pydantic response models for OpenAPI documentation."""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


# --- Pagination ---

class PaginatedMeta(BaseModel):
    total: int
    limit: int
    offset: int


# --- Device responses ---

class DeviceSummary(BaseModel):
    device_id: str
    name: Optional[str] = None
    site_id: Optional[str] = None
    status: str = "OFFLINE"
    device_type: Optional[str] = None
    last_seen_at: Optional[datetime] = None
    tags: list[str] = []
    subscription_id: Optional[str] = None
    subscription_type: Optional[str] = None
    subscription_status: Optional[str] = None


class DeviceListResponse(BaseModel):
    tenant_id: str
    devices: list[DeviceSummary]
    total: int
    limit: int
    offset: int


class DeviceDetailResponse(BaseModel):
    tenant_id: str
    device: dict[str, Any]
    events: list[dict[str, Any]] = []
    telemetry: list[dict[str, Any]] = []


# --- Alert responses ---

class AlertSummary(BaseModel):
    alert_id: int
    tenant_id: str
    device_id: Optional[str] = None
    site_id: Optional[str] = None
    alert_type: str
    severity: int
    status: str
    summary: Optional[str] = None
    created_at: datetime
    closed_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    silenced_until: Optional[datetime] = None
    escalation_level: Optional[int] = None


class AlertListResponse(BaseModel):
    tenant_id: str
    alerts: list[AlertSummary]
    total: int
    status_filter: str
    limit: int
    offset: int


class AlertDetailResponse(BaseModel):
    tenant_id: str
    alert: dict[str, Any]


# --- Fleet responses ---

class FleetSummaryResponse(BaseModel):
    ONLINE: int = 0
    STALE: int = 0
    OFFLINE: int = 0
    total: int = 0
    active_alerts: int = 0


class FleetHealthResponse(BaseModel):
    total_devices: int = 0
    online: int = 0
    stale: int = 0
    offline: int = 0
    avg_uptime_pct: float = 100.0
    as_of: str


# --- Notification channel responses ---

class NotificationChannelSummary(BaseModel):
    channel_id: int
    tenant_id: str
    name: str
    channel_type: str
    is_enabled: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class NotificationChannelListResponse(BaseModel):
    channels: list[NotificationChannelSummary]
    total: int


# --- Generic responses ---

class SuccessResponse(BaseModel):
    ok: bool = True


class DeletedResponse(BaseModel):
    deleted: bool = True


class StatusResponse(BaseModel):
    status: str
    service: str
    api_version: str
```

## Step 4: Add response_model to key endpoints

Apply `response_model` to the most important endpoints. This is the highest-impact change for OpenAPI quality. Do NOT apply to every endpoint at once -- focus on the primary list/detail endpoints.

### devices.py -- list_devices endpoint

```python
from schemas.responses import DeviceListResponse

@router.get("/devices", response_model=DeviceListResponse)
@limiter.limit(CUSTOMER_RATE_LIMIT)
async def list_devices(
    request: Request,
    response: Response,
    ...
):
    """List all devices for the authenticated tenant.

    Supports filtering by status, tags, site, and free-text search.
    Returns paginated results with subscription info.
    """
    ...
```

### devices.py -- get_device_detail endpoint

```python
from schemas.responses import DeviceDetailResponse

@router.get("/devices/{device_id}", response_model=DeviceDetailResponse)
async def get_device_detail(device_id: str, pool=Depends(get_db_pool)):
    """Get detailed device information including recent events and telemetry.

    Returns the device record, last 50 events (24h), and last 120 telemetry points (6h).
    """
    ...
```

### devices.py -- get_fleet_summary endpoint

```python
@router.get("/devices/summary")
async def get_fleet_summary(pool=Depends(get_db_pool)):
    """Fleet device status summary.

    Returns counts of ONLINE, STALE, and OFFLINE devices for the tenant.
    """
    ...
```

### devices.py -- get_fleet_uptime_summary endpoint

```python
from schemas.responses import FleetHealthResponse

@router.get("/fleet/uptime-summary", response_model=FleetHealthResponse)
async def get_fleet_uptime_summary(pool=Depends(get_db_pool)):
    """Fleet-wide uptime summary over the last 24 hours.

    Calculates average uptime percentage across all devices.
    """
    ...
```

### alerts.py -- list_alerts endpoint

```python
from schemas.responses import AlertListResponse

@router.get("/alerts", response_model=AlertListResponse)
@limiter.limit(CUSTOMER_RATE_LIMIT)
async def list_alerts(
    request: Request,
    response: Response,
    status: str = Query("OPEN"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    pool=Depends(get_db_pool),
):
    """List alerts for the authenticated tenant.

    Filter by status: OPEN, ACKNOWLEDGED, CLOSED, or ALL.
    Returns paginated results sorted by creation time (newest first).
    """
    ...
```

### alerts.py -- get_alert endpoint

```python
from schemas.responses import AlertDetailResponse

@router.get("/alerts/{alert_id}", response_model=AlertDetailResponse)
async def get_alert(alert_id: str, pool=Depends(get_db_pool)):
    """Get a single alert by ID.

    Returns full alert details including severity, summary, and status history.
    """
    ...
```

## Step 5: Add docstrings to all endpoints that lack them

Go through every route file and add a one-line docstring to endpoints that have none. FastAPI uses the first line of the docstring as the OpenAPI `summary` and subsequent lines as the `description`.

**Pattern to follow:**

```python
@router.get("/some-endpoint")
async def some_endpoint(...):
    """Short summary of what this endpoint does.

    Longer description with details about parameters, filtering behavior,
    and any important notes about authorization or side effects.
    """
```

Key endpoints that currently lack docstrings (add them):
- `customer.py`: `list_sites`, `get_site_summary`, `geocode_address_endpoint`
- `devices.py`: `list_devices`, `get_device_detail`, `update_device`, `delete_device`
- `alerts.py`: `list_alerts`, `get_alert`
- `exports.py`: `delivery_status`, `export_devices`, `export_alerts`
- `notifications.py`: `list_channels`, `create_channel`, `test_channel`
- `escalation.py`: all endpoints
- `oncall.py`: all endpoints

## Step 6: Add /openapi.json link to health endpoint

Update the `/healthz` endpoint in `app.py` to include the OpenAPI spec URL:

```python
@app.get("/healthz")
async def healthz():
    # ... existing checks ...
    return {
        "status": overall,
        "checks": checks,
        "api_version": "v1",
        "openapi_url": "/openapi.json",
    }
```

And update the `/api/v1/health` endpoint (created in task 001):
```python
@app.get("/api/v1/health")
async def api_v1_health():
    return {
        "status": "ok",
        "service": "pulse-ui",
        "api_version": "v1",
        "docs_url": "/docs",
        "openapi_url": "/openapi.json",
    }
```

## Verification

```bash
# 1. OpenAPI JSON is served
curl -s http://localhost:8080/openapi.json | jq '.info'
# Expected: {"title": "OpsConductor Pulse API", "version": "1.0.0", "description": "..."}

# 2. Tags are present
curl -s http://localhost:8080/openapi.json | jq '.tags | length'
# Expected: 13+ tags

# 3. Response models are in spec
curl -s http://localhost:8080/openapi.json | jq '.components.schemas | keys' | grep -i "DeviceListResponse"
# Expected: "DeviceListResponse"

curl -s http://localhost:8080/openapi.json | jq '.components.schemas | keys' | grep -i "AlertListResponse"
# Expected: "AlertListResponse"

# 4. Swagger UI works in DEV mode
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/docs
# Expected: 200 (in DEV mode)

# 5. ReDoc works
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/redoc
# Expected: 200 (in DEV mode)

# 6. Endpoints have summaries
curl -s http://localhost:8080/openapi.json | jq '.paths["/api/v1/customer/devices"]["get"]["summary"]'
# Expected: non-null string

# 7. Health endpoint includes openapi_url
curl -s http://localhost:8080/healthz | jq .openapi_url
# Expected: "/openapi.json"
```

## Notes

- Do NOT add `response_model` to every single endpoint in this task. Focus on the 6-8 most important ones listed above. The rest can be added incrementally.
- Using `response_model` will cause FastAPI to validate and filter the response data. Make sure the models match what the endpoints actually return. If an endpoint returns extra fields, use `model_config = ConfigDict(extra="allow")` in the response model or widen the model.
- The `dict[str, Any]` type in some response models (like `DeviceDetailResponse.device`) is intentional -- these fields have complex nested structures that vary per device and are not worth modeling in full.
