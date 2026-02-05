# Task 001: Backend SPA Cutover

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

The React SPA is feature-complete at `/app/*` but users are still redirected to old Jinja template pages. This task modifies the backend to:
1. Redirect `/` to the SPA
2. Remove all template-rendering routes
3. Convert dual HTML/JSON routes to JSON-only
4. Remove dead template helper code

**Read first**:
- `services/ui_iot/app.py` — root redirect (line 334), template init (line 43), static mount (line 44), deprecated routes
- `services/ui_iot/routes/customer.py` — template routes (lines 306-373), dual routes (lines 376-500, 1985-2007)
- `services/ui_iot/routes/operator.py` — template routes (lines 256-289, 355-425, 570-600)

---

## Task

### 1.1 Modify `services/ui_iot/app.py`

#### Change root redirect

Replace the `root()` function (lines 334-349) with a simple redirect to `/app/`:

```python
@app.get("/")
async def root():
    return RedirectResponse(url="/app/", status_code=302)
```

The SPA handles its own auth via keycloak-js — no need to check `pulse_session` cookies here.

#### Change OAuth callback redirect

In the `oauth_callback()` function (around line 426-431), change the role-based redirects to all go to `/app/`:

```python
    # After successful token validation, redirect to SPA
    redirect_url = "/app/"
```

Remove the role-based if/elif block that sets `redirect_url` based on operator/customer role. Just set `redirect_url = "/app/"`. The SPA will handle routing based on user role.

#### Remove deprecated route

Delete the `device_detail_deprecated()` function (lines 652-671) — the `GET /device/{device_id}` route that returns a 410 Gone HTML page.

#### Remove legacy admin form routes

Delete these functions:
- `admin_create_device()` (lines 218-248) — `POST /admin/create-device`
- `admin_activate_device()` (lines 250-276) — `POST /admin/activate-device`
- `settings_redirect()` (lines 210-212) — `POST /settings`

These were form-based routes for the old template UI.

#### Remove template init and static mount

Remove these two lines (lines 43-44):

```python
templates = Jinja2Templates(directory="/app/templates")
app.mount("/static", StaticFiles(directory="static"), name="static")
```

Also remove unused imports that are no longer needed:
- Remove `Jinja2Templates` from the `from fastapi.templating import` line
- Remove `StaticFiles` from the `from fastapi.staticfiles import` line
- Remove `HTMLResponse` from the `from fastapi.responses import` line (keep `RedirectResponse`, `JSONResponse`, `FileResponse`)
- Remove `Form` from the `from fastapi import` line (check if it's still used elsewhere in this file — it's not after removing admin routes)

#### Remove dead helper functions

Delete these functions from app.py (they were only used for template rendering):
- `sparkline_points()` (lines 118-138)
- `redact_url()` (lines 140-151)
- `to_float()` (lines 102-108)
- `to_int()` (lines 110-116)

Also remove `from urllib.parse import urlparse, urlencode` — check that `urlparse` is still used elsewhere (it is, in `startup()` and `debug_auth()`). Keep `urlparse` but remove `urlencode` only if it's unused. Actually, `urlencode` is used in the `logout()` function, so keep both.

### 1.2 Modify `services/ui_iot/routes/customer.py`

#### Remove template initialization

Remove or comment out this line (line 82):

```python
templates = Jinja2Templates(directory="/app/templates")
```

Remove the template-related imports:
- Remove `HTMLResponse` from `from fastapi.responses import HTMLResponse, JSONResponse`
- Remove `Jinja2Templates` from `from fastapi.templating import Jinja2Templates`

Keep all other imports as they are.

#### Remove pure template routes

Delete these functions entirely:

1. `customer_dashboard()` (lines 306-333) — `GET /dashboard`
2. `snmp_integrations_page()` (lines 336-343) — `GET /snmp-integrations`
3. `email_integrations_page()` (lines 346-353) — `GET /email-integrations`
4. `mqtt_integrations_page()` (lines 356-363) — `GET /mqtt-integrations`
5. `webhooks_page()` (lines 366-373) — `GET /webhooks`

#### Convert dual HTML/JSON routes to JSON-only

These routes currently serve HTML by default and JSON when `format=json`. Convert them to always return JSON.

**`GET /devices` (list_devices, line 376)**:

Change from:
```python
@router.get("/devices", response_class=HTMLResponse)
async def list_devices(
    request: Request,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    format: str = Query("html"),
):
```

To:
```python
@router.get("/devices")
async def list_devices(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
```

Remove `request: Request` and `format` parameters. Remove the `format == "json"` check. Remove the `templates.TemplateResponse(...)` branch. Always return the JSON payload directly:

```python
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
```

**`GET /devices/{device_id}` (get_device_detail, line 412)**:

Same pattern — remove `request`, `format`, `response_class=HTMLResponse`. Remove template response branch. Remove sparkline logic. Always return JSON:

```python
@router.get("/devices/{device_id}")
async def get_device_detail(device_id: str):
    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            device = await fetch_device(conn, tenant_id, device_id)
            if not device:
                raise HTTPException(status_code=404, detail="Device not found")

            ic = _get_influx_client()
            events = await fetch_device_events_influx(ic, tenant_id, device_id, limit=50)
            telemetry = await fetch_device_telemetry_influx(ic, tenant_id, device_id, limit=120)
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
```

**`GET /alerts` (list_alerts, line 471)**:

Same pattern — remove `request`, `format`, `response_class=HTMLResponse`. Always return JSON:

```python
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
```

**`GET /alert-rules` (list_alert_rules, line 1985)**:

Remove `request`, `format` param, template response. Always return JSON:

```python
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
```

#### Remove dead helper functions

Delete these functions from customer.py (only used for template sparklines):
- `to_float()` (lines 109-115)
- `to_int()` (lines 118-124)
- `sparkline_points()` (lines 127-147)
- `redact_url()` (lines 150-159)

Also remove `from urllib.parse import urlparse` if it's no longer used after removing `redact_url`. Check: `urlparse` is imported but only used in `redact_url`. Remove it.

Remove `from starlette.requests import Request` if `Request` is no longer used in any remaining route. Check: `Request` may still be used in some remaining routes — look for any remaining function that takes `request: Request`. If not used, remove the import. If still used, keep it.

**Important**: After removing all template branches, check if `jsonable_encoder` is still imported and used. It was used in the `JSONResponse(jsonable_encoder(payload))` calls. Since we now return dicts directly (FastAPI auto-serializes), remove `from fastapi.encoders import jsonable_encoder` if no longer used elsewhere in the file.

### 1.3 Modify `services/ui_iot/routes/operator.py`

#### Remove template initialization

Remove this line (line 47):

```python
templates = Jinja2Templates(directory="/app/templates")
```

Remove template-related imports:
- Remove `HTMLResponse, RedirectResponse` from `from fastapi.responses import`
- Remove `Jinja2Templates` from `from fastapi.templating import`
- Remove `Form` from `from fastapi import` — check if it's still used. It IS used in `update_settings()` (POST /settings). **Keep Form**.

#### Remove pure template routes

Delete these functions entirely:

1. `operator_dashboard()` (lines 256-289) — `GET /dashboard`
2. `settings()` (lines 570-600) — `GET /settings` (the HTML-rendering GET, NOT the POST)

**Keep** `update_settings()` (POST /settings, line 603) — this is the JSON/form API endpoint the SPA calls.

#### Convert dual route to JSON-only

**`GET /tenants/{tenant_id}/devices/{device_id}` (view_device, line 355)**:

Remove `request`, `format`, `response_class=HTMLResponse`. Remove template branch and sparkline logic. Always return JSON:

```python
@router.get("/tenants/{tenant_id}/devices/{device_id}")
async def view_device(
    request: Request,
    tenant_id: str,
    device_id: str,
):
    user = get_user()
    ip, user_agent = get_request_metadata(request)
    try:
        p = await get_pool()
        async with p.acquire() as conn:
            await log_operator_access(
                conn,
                user_id=user["sub"],
                action="view_device",
                tenant_filter=tenant_id,
                resource_type="device",
                resource_id=device_id,
                ip_address=ip,
                user_agent=user_agent,
                rls_bypassed=True,
            )
        async with operator_connection(p) as conn:
            device = await fetch_device(conn, tenant_id, device_id)
            if not device:
                raise HTTPException(status_code=404, detail="Device not found")

            ic = _get_influx_client()
            events = await fetch_device_events_influx(ic, tenant_id, device_id, limit=50)
            telemetry = await fetch_device_telemetry_influx(ic, tenant_id, device_id, limit=120)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch operator device detail")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {
        "tenant_id": tenant_id,
        "device": device,
        "events": events,
        "telemetry": telemetry,
    }
```

Note: This route still needs `request: Request` for `get_request_metadata()`. Remove `format` param only.

#### Remove dead helper functions

Delete from operator.py:
- `to_float()` (lines 80-86)
- `to_int()` (lines 89-95)
- `sparkline_points()` (lines 98-117)

Also delete `_load_dashboard_context()` if it exists and is only used by the removed dashboard and settings GET routes. Check if any remaining route uses it. If not, delete it.

#### Check Request import

`Request` is still needed for `get_request_metadata(request)` in remaining routes. Keep the `from starlette.requests import Request` import.

---

## Files to Modify

| Action | Path | What changes |
|--------|------|--------------|
| MODIFY | `services/ui_iot/app.py` | Root redirect → /app/, remove template init, remove deprecated/admin routes, remove dead helpers |
| MODIFY | `services/ui_iot/routes/customer.py` | Remove template routes, convert dual routes to JSON-only, remove dead helpers |
| MODIFY | `services/ui_iot/routes/operator.py` | Remove template routes, convert dual route to JSON-only, remove dead helpers |

---

## Test

### Step 1: Verify Python syntax

```bash
cd /home/opsconductor/simcloud/services/ui_iot && python3 -c "import app; print('app.py OK')"
```

This may fail due to missing template files (which Task 2 removes). If it fails because Jinja2Templates can't find templates or StaticFiles can't find the static directory, that's expected — the templates/static lines should already be removed in this task. If it fails for other reasons, fix them.

### Step 2: Verify no template references remain

```bash
grep -n "TemplateResponse\|Jinja2Templates\|response_class=HTMLResponse" /home/opsconductor/simcloud/services/ui_iot/app.py /home/opsconductor/simcloud/services/ui_iot/routes/customer.py /home/opsconductor/simcloud/services/ui_iot/routes/operator.py || echo "No template references found - clean"
```

Should show "No template references found".

### Step 3: Verify no sparkline/redact references remain

```bash
grep -n "sparkline_points\|redact_url" /home/opsconductor/simcloud/services/ui_iot/app.py /home/opsconductor/simcloud/services/ui_iot/routes/customer.py /home/opsconductor/simcloud/services/ui_iot/routes/operator.py || echo "No dead helpers found - clean"
```

Should show "No dead helpers found".

---

## Acceptance Criteria

- [ ] `GET /` redirects to `/app/` (not `/customer/dashboard` or `/operator/dashboard`)
- [ ] OAuth callback redirects to `/app/` after login
- [ ] No `templates.TemplateResponse()` calls remain in app.py, customer.py, or operator.py
- [ ] No `Jinja2Templates` initialization in any of the three files
- [ ] No `StaticFiles` mount for `/static` in app.py
- [ ] `/customer/devices`, `/customer/devices/{id}`, `/customer/alerts`, `/customer/alert-rules` return JSON directly (no `format` param)
- [ ] `/operator/tenants/{tenant_id}/devices/{device_id}` returns JSON directly
- [ ] Dead helper functions removed (sparkline_points, redact_url, to_float, to_int)
- [ ] Deprecated `/device/{device_id}` route removed
- [ ] Admin form routes removed (`/admin/create-device`, `/admin/activate-device`, `POST /settings` redirect)
- [ ] `_load_dashboard_context` removed from operator.py (if unused)
- [ ] No unused imports

---

## Commit

```
Remove Jinja template routes and redirect root to React SPA

Root / now redirects to /app/ (React SPA). All template-rendering
routes removed from customer.py and operator.py. Dual HTML/JSON
routes converted to JSON-only. Dead template helper functions
(sparklines, redact_url) removed.

Phase 22 Task 1: Backend SPA Cutover
```
