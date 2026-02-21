# 003: Deprecate Duplicate API Surface

## Goal

Mark all `/api/v2/` routes as deprecated with standard HTTP headers, migrate the WebSocket endpoint to `/customer/ws`, and document the migration path from `/api/v2/` to `/customer/`. Full removal planned for Phase 129.

## Current State

### `/api/v2/` endpoints (in `services/ui_iot/routes/api_v2.py`)
- `GET /api/v2/devices` -- list devices with full metric state
- `GET /api/v2/devices/{device_id}` -- device detail
- `GET /api/v2/fleet/summary` -- fleet health summary
- `GET /api/v2/alerts` -- list alerts
- `GET /api/v2/alerts/trend` -- hourly alert trend
- `GET /api/v2/alerts/{alert_id}` -- alert detail
- `GET /api/v2/alert-rules` -- list alert rules
- `GET /api/v2/alert-rules/{rule_id}` -- alert rule detail
- `GET /api/v2/devices/{device_id}/telemetry` -- device telemetry
- `GET /api/v2/devices/{device_id}/telemetry/latest` -- latest telemetry
- `GET /api/v2/telemetry/summary` -- fleet telemetry summary
- `GET /api/v2/telemetry/chart` -- time-series chart data
- `GET /api/v2/metrics/reference` -- raw/normalized metrics reference
- `GET /api/v2/health` -- defined in `app.py` (not in the router)
- `WS /api/v2/ws` -- WebSocket for live telemetry/alerts

### `/customer/` endpoints (in various route files)
The `/customer/` prefix routes provide equivalent (and often richer) functionality:
- Devices: via `routes/customer.py` and `routes/devices.py`
- Alerts: via `routes/alerts.py` and `routes/customer.py`
- Telemetry: via `routes/customer.py`
- Alert rules: via `routes/customer.py`
- Notification channels: via `routes/notifications.py`
- Fleet summary: via `routes/customer.py`

### Existing deprecation middleware in `app.py`
There is already a deprecation middleware for legacy integrations endpoints (lines 159-168):
```python
@app.middleware("http")
async def deprecate_legacy_integrations_middleware(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/customer/integrations") or request.url.path.startswith("/customer/integration-routes"):
        response.headers["X-Deprecated"] = (...)
        response.headers["Sunset"] = "2026-06-01"
    return response
```

## Step-by-Step Changes

### Step 1: Add deprecation middleware for `/api/v2/` endpoints

**File**: `services/ui_iot/app.py`

Add a new middleware right after the existing `deprecate_legacy_integrations_middleware` (after line 168). This middleware adds standard HTTP deprecation headers to all `/api/v2/` responses:

```python
@app.middleware("http")
async def deprecate_api_v2_middleware(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/v2/"):
        response.headers["Deprecation"] = "true"
        response.headers["Sunset"] = "2026-09-01"
        response.headers["Link"] = '</customer/>; rel="successor-version"'
        response.headers["X-Deprecated"] = (
            "true; The /api/v2/ endpoints are deprecated. "
            "Migrate to /customer/ endpoints. "
            "See /docs/api-migration-v2-to-customer for mapping."
        )
    return response
```

**Important**: This middleware uses the standard `Deprecation` header (RFC 8594 draft) and `Sunset` header (RFC 8594). The `X-Deprecated` header is a non-standard addition for human-readable context.

### Step 2: Update the `/api/v2/health` endpoint

**File**: `services/ui_iot/app.py`

Modify the existing `/api/v2/health` handler (around line 388) to include deprecation notice:

Change from:
```python
@app.get("/api/v2/health")
async def api_v2_health():
    return {"status": "ok", "service": "pulse-ui", "api_version": "v2"}
```

To:
```python
@app.get("/api/v2/health")
async def api_v2_health():
    return {
        "status": "ok",
        "service": "pulse-ui",
        "api_version": "v2",
        "deprecated": True,
        "migrate_to": "/customer/",
        "sunset_date": "2026-09-01",
        "migration_guide": "/docs/api-migration-v2-to-customer",
    }
```

### Step 3: Add WebSocket endpoint at `/customer/ws`

**File**: `services/ui_iot/routes/api_v2.py`

The current WebSocket endpoint is at `/api/v2/ws` (line 728). We need to add a new endpoint at `/customer/ws` while keeping the old one working.

Add a new WebSocket endpoint right after the existing one (after line 855). The new endpoint reuses the same handler logic:

```python
@ws_router.websocket("/customer/ws")
async def customer_websocket_endpoint(websocket: WebSocket, token: str | None = None):
    """WebSocket endpoint for live telemetry and alert streaming.

    This is the canonical WebSocket endpoint. /api/v2/ws is deprecated.

    Auth: Pass JWT as query param: ws://host/customer/ws?token=JWT_TOKEN

    Client messages (JSON):
        {"action": "subscribe", "type": "device", "device_id": "dev-0001"}
        {"action": "subscribe", "type": "alerts"}
        {"action": "subscribe", "type": "fleet"}
        {"action": "unsubscribe", "type": "device", "device_id": "dev-0001"}
        {"action": "unsubscribe", "type": "alerts"}
        {"action": "unsubscribe", "type": "fleet"}

    Server messages (JSON):
        {"type": "telemetry", "device_id": "dev-0001", "data": {...}}
        {"type": "alerts", "alerts": [...]}
        {"type": "fleet_summary", "data": {...}}
        {"type": "subscribed", "channel": "device", "device_id": "dev-0001"}
        {"type": "error", "message": "..."}
    """
    # Delegate to the existing handler
    await websocket_endpoint(websocket, token)
```

This approach avoids code duplication. The `/customer/ws` endpoint delegates to the existing `websocket_endpoint` function.

### Step 4: Add deprecation notice to `/api/v2/ws` endpoint

**File**: `services/ui_iot/routes/api_v2.py`

Update the existing `websocket_endpoint` function to send a deprecation message immediately after accepting the connection. Add this right after `conn = await ws_manager.connect(websocket, tenant_id, payload)` (line 784) and before `push_task = asyncio.create_task(...)`:

```python
    conn = await ws_manager.connect(websocket, tenant_id, payload)

    # Send deprecation notice if connecting via /api/v2/ws
    if websocket.scope.get("path", "").startswith("/api/v2/"):
        try:
            await websocket.send_json({
                "type": "deprecation_notice",
                "message": "/api/v2/ws is deprecated. Migrate to /customer/ws by 2026-09-01.",
                "migrate_to": "/customer/ws",
                "sunset_date": "2026-09-01",
            })
        except Exception:
            pass  # Non-fatal

    push_task = asyncio.create_task(_ws_push_loop(conn))
```

### Step 5: Create API migration documentation

**File**: `docs/api-migration-v2-to-customer.md`

Create this file with the following content:

```markdown
# API Migration Guide: /api/v2/ to /customer/

## Timeline

- **Deprecated**: 2026-02-16
- **Sunset date**: 2026-09-01 (endpoints will be removed)
- **Removal phase**: Phase 129

## Endpoint Mapping

| Deprecated `/api/v2/` endpoint | Replacement `/customer/` endpoint | Notes |
|---|---|---|
| `GET /api/v2/devices` | `GET /customer/devices` | Same query params: limit, offset, status, tags, q, site_id |
| `GET /api/v2/devices/{device_id}` | `GET /customer/devices/{device_id}` | |
| `GET /api/v2/fleet/summary` | `GET /customer/fleet-summary` | Response shape may differ slightly |
| `GET /api/v2/alerts` | `GET /customer/alerts` | Same filters: status, alert_type, limit, offset |
| `GET /api/v2/alerts/trend` | `GET /customer/alerts/trend` | |
| `GET /api/v2/alerts/{alert_id}` | `GET /customer/alerts/{alert_id}` | |
| `GET /api/v2/alert-rules` | `GET /customer/alert-rules` | |
| `GET /api/v2/alert-rules/{rule_id}` | `GET /customer/alert-rules/{rule_id}` | |
| `GET /api/v2/devices/{device_id}/telemetry` | `GET /customer/devices/{device_id}/telemetry` | |
| `GET /api/v2/devices/{device_id}/telemetry/latest` | `GET /customer/devices/{device_id}/telemetry/latest` | |
| `GET /api/v2/telemetry/summary` | `GET /customer/telemetry/summary` | |
| `GET /api/v2/telemetry/chart` | `GET /customer/telemetry/chart` | |
| `GET /api/v2/metrics/reference` | `GET /customer/metrics/reference` | |
| `GET /api/v2/health` | `GET /healthz` | Use the main health endpoint |
| `WS /api/v2/ws` | `WS /customer/ws` | Same protocol, same auth (query param token) |

## Authentication

Both `/api/v2/` and `/customer/` use the same JWT authentication via the `JWTBearer` dependency. No auth changes needed.

## Response Format Differences

The `/customer/` endpoints may have slightly different response envelope shapes. Key differences:

1. `/customer/fleet-summary` returns `fleet_summary` object vs `/api/v2/fleet/summary` which returns flat fields
2. `/customer/alerts` may include additional fields like `notification_status`

## Migration Steps

1. Update your API base URL from `/api/v2/` to `/customer/`
2. Update WebSocket URL from `ws://host/api/v2/ws?token=...` to `ws://host/customer/ws?token=...`
3. Review response shapes for any minor differences
4. Test all endpoints before the sunset date

## Deprecation Headers

All `/api/v2/` responses now include:
- `Deprecation: true`
- `Sunset: 2026-09-01`
- `Link: </customer/>; rel="successor-version"`
- `X-Deprecated: true; ...migration instructions...`
```

### Step 6: Verify no `/customer/` equivalents are missing

Before completing this task, verify that every `/api/v2/` endpoint has a corresponding `/customer/` endpoint. Check each one:

```bash
# List all /api/v2/ endpoints
grep -n "@router\." services/ui_iot/routes/api_v2.py | head -20

# List all /customer/ endpoints
grep -rn "@router\.\(get\|post\|put\|delete\)" services/ui_iot/routes/customer.py services/ui_iot/routes/devices.py services/ui_iot/routes/alerts.py services/ui_iot/routes/metrics.py services/ui_iot/routes/notifications.py | head -40
```

If any `/api/v2/` endpoint does NOT have a `/customer/` equivalent, add a note to the migration doc marking it as "coming in Phase 129" rather than blocking this task.

## Verification

```bash
# 1. Verify deprecation headers on /api/v2/ endpoints
curl -sI http://localhost:8080/api/v2/health | grep -i "deprecation"
# Expected: Deprecation: true

curl -sI http://localhost:8080/api/v2/health | grep -i "sunset"
# Expected: Sunset: 2026-09-01

curl -sI http://localhost:8080/api/v2/health | grep -i "x-deprecated"
# Expected: X-Deprecated: true; ...

# 2. Verify deprecation notice in /api/v2/health body
curl -s http://localhost:8080/api/v2/health | python3 -m json.tool
# Expected: {"deprecated": true, "migrate_to": "/customer/", ...}

# 3. Verify /customer/ endpoints do NOT have deprecation headers
curl -sI http://localhost:8080/customer/notification-channels 2>/dev/null | grep -i "deprecation"
# Expected: no output (no deprecation header)

# 4. Verify WebSocket on /customer/ws accepts connections
# (Use wscat or a browser dev tool)
# wscat -c "ws://localhost:8080/customer/ws?token=YOUR_JWT"

# 5. Verify migration doc exists
test -f docs/api-migration-v2-to-customer.md && echo "PASS: migration doc exists"

# 6. Validate compose (unchanged but verify)
cd compose && docker compose config --quiet && echo "PASS"
```

## Commit

```
feat: deprecate /api/v2/ endpoints in favor of /customer/

Add deprecation middleware for all /api/v2/ routes:
- Deprecation: true header (RFC 8594)
- Sunset: 2026-09-01 header
- Link: </customer/>; rel="successor-version"

Update /api/v2/health to include deprecation notice in response body.

Add /customer/ws WebSocket endpoint (delegates to existing handler).
Add deprecation_notice message on /api/v2/ws connections.

Create docs/api-migration-v2-to-customer.md with endpoint mapping
and migration steps. Full removal planned for Phase 129.
```
