# Task 006: Main App Refactor

## Context

Customer and operator routers are implemented. Now we need to mount them in the main app, add auth dependencies, and deprecate unsafe routes.

**Read first**:
- `services/ui_iot/app.py` (current implementation — this is what we're refactoring)
- `services/ui_iot/routes/customer.py` (new customer routes)
- `services/ui_iot/routes/operator.py` (new operator routes)

**Depends on**: Tasks 004, 005

## Task

### 6.1 Modify `services/ui_iot/app.py`

**Imports to add**:
```python
from routes.customer import router as customer_router
from routes.operator import router as operator_router
from middleware.auth import JWTBearer, validate_token
from middleware.tenant import get_user, is_operator
```

**Mount routers** (after app creation):
```python
app.include_router(customer_router)
app.include_router(operator_router)
```

**Modify root route `/`**:

Current behavior: Shows cross-tenant dashboard with no auth.

New behavior:
- Check for Authorization header
- If no auth: redirect to Keycloak login page
- If auth present: validate token
- If valid and operator role: redirect to `/operator/dashboard`
- If valid and customer role: redirect to `/customer/dashboard`
- If invalid: redirect to Keycloak login

```python
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        # No token - redirect to login
        return RedirectResponse(url=get_login_url(), status_code=302)

    try:
        token = auth_header[7:]
        payload = await validate_token(token)
        role = payload.get("role", "")

        if role in ("operator", "operator_admin"):
            return RedirectResponse(url="/operator/dashboard", status_code=302)
        elif role in ("customer_admin", "customer_viewer"):
            return RedirectResponse(url="/customer/dashboard", status_code=302)
        else:
            return RedirectResponse(url=get_login_url(), status_code=302)
    except:
        return RedirectResponse(url=get_login_url(), status_code=302)

def get_login_url():
    # Keycloak login URL for pulse-ui client
    keycloak_url = os.getenv("KEYCLOAK_URL", "http://localhost:8180")
    realm = os.getenv("KEYCLOAK_REALM", "pulse")
    client_id = "pulse-ui"
    redirect_uri = "http://localhost:8080/callback"
    return (
        f"{keycloak_url}/realms/{realm}/protocol/openid-connect/auth"
        f"?client_id={client_id}"
        f"&response_type=code"
        f"&redirect_uri={redirect_uri}"
        f"&scope=openid"
    )
```

**Add callback route** (for OAuth code exchange):
```python
@app.get("/callback")
async def oauth_callback(code: str = Query(...)):
    # Exchange code for token
    # In a real app, this would:
    # 1. POST to Keycloak token endpoint with code
    # 2. Get access_token and refresh_token
    # 3. Set cookie or return to frontend
    # For now, redirect to a page that handles this client-side
    return RedirectResponse(url=f"/?code={code}", status_code=302)
```

**Add logout route**:
```python
@app.get("/logout")
async def logout():
    keycloak_url = os.getenv("KEYCLOAK_URL", "http://localhost:8180")
    realm = os.getenv("KEYCLOAK_REALM", "pulse")
    redirect_uri = "http://localhost:8080/"
    return RedirectResponse(
        url=f"{keycloak_url}/realms/{realm}/protocol/openid-connect/logout?redirect_uri={redirect_uri}",
        status_code=302
    )
```

**Deprecate `/device/{device_id}` route**:

Replace the existing route with:
```python
@app.get("/device/{device_id}", response_class=HTMLResponse)
async def device_detail_deprecated(request: Request, device_id: str):
    return HTMLResponse(
        content="""
        <html>
        <head><title>410 Gone</title></head>
        <body>
        <h1>410 Gone</h1>
        <p>This endpoint is deprecated.</p>
        <p>Use one of:</p>
        <ul>
            <li><code>/customer/devices/{device_id}</code> — for customers (requires login)</li>
            <li><code>/operator/tenants/{tenant_id}/devices/{device_id}</code> — for operators</li>
        </ul>
        <p><a href="/">Go to login</a></p>
        </body>
        </html>
        """,
        status_code=410
    )
```

**Modify `/settings` POST route**:

This should now require operator_admin role. Either:
- Move the logic to operator router (preferred, already done in Task 005)
- Or add auth check here and redirect to operator router

Simplest: redirect to operator endpoint:
```python
@app.post("/settings")
async def settings_redirect():
    # Deprecated - use /operator/settings
    return RedirectResponse(url="/operator/settings", status_code=307)
```

**Remove or comment out**:
- The existing `dashboard()` function that renders cross-tenant data without auth
- Any direct database queries that don't go through the query builders
- Keep utility functions like `sparkline_points`, `redact_url`, `to_float`, `to_int` — these are still used

**Keep**:
- `get_pool()` function — still needed
- `startup` event handler
- Admin device creation routes (`/admin/create-device`, `/admin/activate-device`) — these use X-Admin-Key, not JWT

**Environment variables to add**:
- `KEYCLOAK_URL` (default: `http://pulse-keycloak:8080`)
- `KEYCLOAK_REALM` (default: `pulse`)

## Files to Create/Modify

| Action | Path |
|--------|------|
| MODIFY | `services/ui_iot/app.py` |

## Summary of Changes

| Route | Before | After |
|-------|--------|-------|
| `GET /` | Cross-tenant dashboard, no auth | Redirect to login or role-based dashboard |
| `GET /device/{id}` | Query by device_id only | 410 Gone with redirect hint |
| `POST /settings` | No auth | Redirect to /operator/settings |
| `GET /customer/*` | N/A | New routes (Task 004) |
| `GET /operator/*` | N/A | New routes (Task 005) |
| `POST /admin/*` | X-Admin-Key | Unchanged |

## Acceptance Criteria

- [ ] `GET /` without auth redirects to Keycloak login
- [ ] `GET /` with customer token redirects to `/customer/dashboard`
- [ ] `GET /` with operator token redirects to `/operator/dashboard`
- [ ] `GET /device/{id}` returns 410 Gone
- [ ] `POST /settings` redirects to `/operator/settings`
- [ ] `/admin/create-device` still works with X-Admin-Key
- [ ] App starts without errors
- [ ] No cross-tenant queries exist outside operator routes

## Commit

```
Refactor main app to use auth routers

- Mount customer and operator routers
- Root route redirects based on auth/role
- Deprecate /device/{id} with 410 Gone
- Redirect /settings to operator route
- Add OAuth callback and logout endpoints
- Keep admin routes with X-Admin-Key auth

Part of Phase 1: Customer Read-Only Dashboard
```
