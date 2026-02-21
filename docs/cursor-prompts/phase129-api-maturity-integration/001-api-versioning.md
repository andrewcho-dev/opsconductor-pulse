# Task 001 -- API Versioning: Restructure Routes to /api/v1/

## Commit Message
```
feat: restructure routes to /api/v1/, add backward-compat redirects, remove /api/v2/
```

## Context

The current API surface uses bare `/customer/...` and `/operator/...` prefixes with no version namespace. The deprecated `/api/v2/` routes from Phase 128 still exist. This task creates a clean `/api/v1/` namespace, adds redirect middleware for backward compatibility, and removes the deprecated v2 REST endpoints.

## Step 1: Change all customer route prefixes

In every file listed below, find the `APIRouter(prefix="/customer", ...)` declaration and change the prefix to `/api/v1/customer`.

**Files to modify (all in `services/ui_iot/routes/`):**

### customer.py (line ~574)
```python
# BEFORE:
router = APIRouter(
    prefix="/customer",
    tags=["customer"],
    ...
)

# AFTER:
router = APIRouter(
    prefix="/api/v1/customer",
    tags=["customer"],
    ...
)
```

### devices.py (line ~12)
```python
# BEFORE:
router = APIRouter(
    prefix="/customer",
    tags=["devices"],
    ...
)

# AFTER:
router = APIRouter(
    prefix="/api/v1/customer",
    tags=["devices"],
    ...
)
```

### alerts.py (line ~8)
```python
# Same pattern -- change prefix="/customer" to prefix="/api/v1/customer"
```

### notifications.py (line ~93)
```python
# Same pattern -- change prefix="/customer" to prefix="/api/v1/customer"
```

### escalation.py (line ~47)
```python
# Same pattern -- change prefix="/customer" to prefix="/api/v1/customer"
```

### oncall.py (line ~39)
```python
# Same pattern -- change prefix="/customer" to prefix="/api/v1/customer"
```

### jobs.py (line ~12)
```python
# Same pattern -- change prefix="/customer" to prefix="/api/v1/customer"
```

### exports.py (line ~6)
```python
# Same pattern -- change prefix="/customer" to prefix="/api/v1/customer"
```

### metrics.py (line ~6)
```python
# Same pattern -- change prefix="/customer" to prefix="/api/v1/customer"
```

## Step 2: Change operator route prefixes

### operator.py (line ~150)
```python
# BEFORE:
router = APIRouter(
    prefix="/operator",
    tags=["operator"],
    ...
)

# AFTER:
router = APIRouter(
    prefix="/api/v1/operator",
    tags=["operator"],
    ...
)
```

### system.py (line ~34)
```python
# BEFORE:
router = APIRouter(
    prefix="/operator/system",
    tags=["system"],
    ...
)

# AFTER:
router = APIRouter(
    prefix="/api/v1/operator/system",
    tags=["system"],
    ...
)
```

## Step 3: Handle roles.py and users.py

Check these files -- `roles.py` currently has `tags=["roles"]` with NO prefix. Determine:
- If it has endpoints that should be under `/api/v1/customer/` or `/api/v1/operator/`, add the appropriate prefix.
- `users.py` similarly -- check its current prefix and update.

If `roles.py` has no prefix:
```python
# Add prefix based on where its routes should live. If it serves customer-facing RBAC:
router = APIRouter(
    prefix="/api/v1/customer",
    tags=["roles"],
    ...
)
```

## Step 4: Add backward-compatibility redirect middleware

In `services/ui_iot/app.py`, add a middleware BEFORE route registration that redirects old paths:

```python
class LegacyPathRedirectMiddleware(BaseHTTPMiddleware):
    """Redirect legacy /customer/ and /operator/ paths to /api/v1/ equivalents."""

    LEGACY_PREFIXES = [
        ("/customer/", "/api/v1/customer/"),
        ("/operator/", "/api/v1/operator/"),
    ]

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        for old_prefix, new_prefix in self.LEGACY_PREFIXES:
            if path.startswith(old_prefix):
                new_path = new_prefix + path[len(old_prefix):]
                query = str(request.url.query)
                redirect_url = new_path + ("?" + query if query else "")
                return RedirectResponse(
                    url=redirect_url,
                    status_code=308,  # Permanent Redirect, preserves method
                    headers={"X-Deprecated-Path": path},
                )

        return await call_next(request)


# Add BEFORE other middleware:
app.add_middleware(LegacyPathRedirectMiddleware)
```

**Important:** Place this middleware addition AFTER the `app = FastAPI()` line but BEFORE `app.include_router(...)` calls. Because Starlette middleware executes in reverse registration order, adding it last means it runs first (before route matching). Alternatively, add it as a raw `@app.middleware("http")` function to ensure correct ordering:

```python
@app.middleware("http")
async def legacy_path_redirect(request: Request, call_next):
    """Redirect legacy /customer/ and /operator/ paths to /api/v1/ equivalents."""
    path = request.url.path

    # Only redirect if NOT already under /api/
    if not path.startswith("/api/"):
        legacy_prefixes = [
            ("/customer/", "/api/v1/customer/"),
            ("/operator/", "/api/v1/operator/"),
        ]
        for old_prefix, new_prefix in legacy_prefixes:
            if path.startswith(old_prefix):
                new_path = new_prefix + path[len(old_prefix):]
                query = str(request.url.query)
                redirect_url = new_path + ("?" + query if query else "")
                return RedirectResponse(
                    url=redirect_url,
                    status_code=308,
                    headers={"X-Deprecated-Path": path},
                )

    return await call_next(request)
```

## Step 5: Remove deprecated /api/v2/ REST endpoints

### In `services/ui_iot/routes/api_v2.py`:

1. **Keep** the WebSocket endpoint (`ws_router` and `websocket_endpoint`) and its supporting code (`setup_ws_listener`, `shutdown_ws_listener`, `_ws_push_loop`, `fetch_fleet_summary_for_tenant`, etc.).
2. **Delete** all REST endpoint functions decorated with `@router.get(...)` or `@router.post(...)`:
   - `list_devices` (GET /api/v2/devices)
   - `get_fleet_summary` (GET /api/v2/fleet/summary)
   - `get_device` (GET /api/v2/devices/{device_id})
   - `list_alerts` (GET /api/v2/alerts)
   - `get_alert_trend` (GET /api/v2/alerts/trend)
   - `get_alert` (GET /api/v2/alerts/{alert_id})
   - `list_alert_rules` (GET /api/v2/alert-rules)
   - `get_alert_rule` (GET /api/v2/alert-rules/{rule_id})
   - `get_device_telemetry` (GET /api/v2/devices/{device_id}/telemetry)
   - `get_device_telemetry_latest` (GET /api/v2/devices/{device_id}/telemetry/latest)
   - `get_fleet_telemetry_summary` (GET /api/v2/telemetry/summary)
   - `get_telemetry_chart` (GET /api/v2/telemetry/chart)
   - `get_metrics_reference` (GET /api/v2/metrics/reference)
3. **Delete** the `router` variable (the APIRouter with prefix="/api/v2") and its `enforce_rate_limit` dependency. Keep `ws_router`.
4. **Delete** the `_rate_buckets`, `_check_rate_limit`, `enforce_rate_limit` code (only used by v2 REST).

### In `services/ui_iot/app.py`:

Update the import and router registration:

```python
# BEFORE:
from routes.api_v2 import (
    router as api_v2_router,
    ws_router as api_v2_ws_router,
    setup_ws_listener,
    shutdown_ws_listener,
)
...
app.include_router(api_v2_router)
app.include_router(api_v2_ws_router)

# AFTER:
from routes.api_v2 import (
    ws_router as api_v2_ws_router,
    setup_ws_listener,
    shutdown_ws_listener,
)
...
# REMOVE: app.include_router(api_v2_router)
app.include_router(api_v2_ws_router)
```

Also remove or update the `/api/v2/health` endpoint in `app.py` (line ~388):
```python
# BEFORE:
@app.get("/api/v2/health")
async def api_v2_health():
    return {"status": "ok", "service": "pulse-ui", "api_version": "v2"}

# AFTER: Either remove or convert to /api/v1/health:
@app.get("/api/v1/health")
async def api_v1_health():
    return {"status": "ok", "service": "pulse-ui", "api_version": "v1"}
```

## Step 6: Update deprecation middleware

In `services/ui_iot/app.py`, update the `deprecate_legacy_integrations_middleware`:

```python
# BEFORE:
if request.url.path.startswith("/customer/integrations") or request.url.path.startswith("/customer/integration-routes"):

# AFTER:
if request.url.path.startswith("/api/v1/customer/integrations") or request.url.path.startswith("/api/v1/customer/integration-routes"):
```

## Step 7: Update frontend API client paths

In every frontend API file under `frontend/src/services/api/`, change all path strings:

- `/customer/` -> `/api/v1/customer/`
- `/operator/` -> `/api/v1/operator/`

**Specific files and patterns:**

### alerts.ts
```typescript
// BEFORE:
"/customer/alerts?status=..."
"/customer/alerts/${alertId}/acknowledge"
"/customer/maintenance-windows"
"/customer/alert-digest-settings"

// AFTER:
"/api/v1/customer/alerts?status=..."
"/api/v1/customer/alerts/${alertId}/acknowledge"
"/api/v1/customer/maintenance-windows"
"/api/v1/customer/alert-digest-settings"
```

### devices.ts
```typescript
// All "/customer/devices..." -> "/api/v1/customer/devices..."
```

### operator.ts
```typescript
// All "/operator/..." -> "/api/v1/operator/..."
```

### system.ts
```typescript
// All "/operator/system/..." -> "/api/v1/operator/system/..."
```

### tenants.ts
```typescript
// All "/operator/tenants..." -> "/api/v1/operator/tenants..."
```

### reports.ts
```typescript
// All "/customer/export/..." -> "/api/v1/customer/export/..."
// All "/customer/reports/..." -> "/api/v1/customer/reports/..."
```

### subscription.ts
```typescript
// All "/customer/subscriptions..." -> "/api/v1/customer/subscriptions..."
// All "/customer/subscription/..." -> "/api/v1/customer/subscription/..."
```

### audit.ts
```typescript
// "/customer/audit-log" -> "/api/v1/customer/audit-log"
```

### metrics.ts
```typescript
// All "/customer/..." -> "/api/v1/customer/..."
```

### jobs.ts
```typescript
// All "/customer/jobs..." -> "/api/v1/customer/jobs..."
```

### notifications.ts, escalation.ts, oncall.ts, roles.ts, users.ts, delivery.ts, integrations.ts, sites.ts, alert-rules.ts
```typescript
// Same pattern: prefix all /customer/ with /api/v1/ and all /operator/ with /api/v1/
```

**Approach:** Use find-and-replace across all `frontend/src/services/api/*.ts` files:
- Replace `"/customer/` with `"/api/v1/customer/`
- Replace `"/operator/` with `"/api/v1/operator/`
- Replace `` `/customer/`` with `` `/api/v1/customer/``
- Replace `` `/operator/`` with `` `/api/v1/operator/``

Also check for any WebSocket URLs that reference `/api/v2/ws` in the frontend:
```bash
grep -r "api/v2/ws" frontend/src/
```
These should remain as-is (the ws_router still serves `/api/v2/ws`).

## Step 8: Update CSRF exempt paths if needed

In `app.py`, check if any of the CSRF exempt paths need updating:
```python
CSRF_EXEMPT_PATHS = (
    "/ingest/",
    "/health",
    "/metrics",
    "/webhook/",
    "/.well-known/",
)
```
These do NOT start with `/customer/` or `/operator/`, so they should be fine. But verify no other path checks exist.

## Verification

```bash
# 1. Redirect works (308 preserves method)
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/customer/devices
# Expected: 308

curl -v http://localhost:8080/customer/devices 2>&1 | grep -i location
# Expected: Location: /api/v1/customer/devices

# 2. New v1 paths return data
curl -s http://localhost:8080/api/v1/customer/devices \
  -H "Authorization: Bearer $TOKEN" | jq .total

curl -s http://localhost:8080/api/v1/operator/tenants \
  -H "Authorization: Bearer $TOKEN" | jq .total

# 3. /api/v2/ REST endpoints return 404
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/v2/devices \
  -H "Authorization: Bearer $TOKEN"
# Expected: 404 (or 405)

# 4. /api/v2/ws still works (WebSocket kept)
# Use wscat or browser DevTools

# 5. Frontend builds and works
cd frontend && npm run build
# No compilation errors

# 6. Health endpoint moved
curl -s http://localhost:8080/api/v1/health | jq .api_version
# Expected: "v1"

# 7. Operator routes redirect
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/operator/tenants
# Expected: 308
```

## Rollback
If something breaks, revert prefixes back to `/customer` and `/operator`. The redirect middleware is additive and can be removed independently.
