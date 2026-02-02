# Task 004: Customer Routes

## Context

We have JWT middleware and tenant enforcement helpers. Now we implement the customer-facing routes that are strictly tenant-scoped.

**Read first**:
- `docs/CUSTOMER_PLANE_ARCHITECTURE.md` (Section 3.1: Customer-Plane Routes)
- `services/ui_iot/app.py` (existing route patterns)
- `services/ui_iot/middleware/auth.py` (JWTBearer)
- `services/ui_iot/middleware/tenant.py` (context helpers)
- `services/ui_iot/db/queries.py` (query builders)

**Depends on**: Tasks 002, 003

## Task

### 4.1 Create `services/ui_iot/routes/__init__.py`

Empty `__init__.py` to make it a package.

### 4.2 Create `services/ui_iot/routes/customer.py`

Implement customer routes with mandatory tenant scoping.

**Imports**:
- `fastapi` (APIRouter, Depends, Request, HTTPException, Query)
- `fastapi.responses` (HTMLResponse)
- `fastapi.templating` (Jinja2Templates)
- From `middleware.auth`: `JWTBearer`
- From `middleware.tenant`: `inject_tenant_context`, `get_tenant_id`, `require_customer`
- From `db.queries`: all fetch functions

**Router setup**:
```python
router = APIRouter(
    prefix="/customer",
    tags=["customer"],
    dependencies=[
        Depends(JWTBearer()),
        Depends(inject_tenant_context),
        Depends(require_customer)
    ]
)
```

This means ALL routes under `/customer` require:
1. Valid JWT
2. Tenant context injected
3. Customer role

**Templates**:
- Reference templates from parent app or create local reference
- Templates path: `/app/templates`

**Routes to implement**:

1. `GET /customer/dashboard` (HTMLResponse):
   - Get tenant_id via `get_tenant_id()`
   - Fetch device counts for tenant
   - Fetch devices (limit 50)
   - Fetch open alerts (limit 20)
   - Fetch delivery attempts (limit 10)
   - Render `customer_dashboard.html` template with:
     - `tenant_id`
     - `device_counts` (total, online, stale)
     - `devices`
     - `alerts`
     - `delivery_attempts`
     - `user` (from context, for display)

2. `GET /customer/devices` (JSON):
   - Query params: `limit` (default 100, max 500), `offset` (default 0)
   - Get tenant_id
   - Fetch devices with pagination
   - Return: `{"tenant_id": ..., "devices": [...], "limit": ..., "offset": ...}`

3. `GET /customer/devices/{device_id}` (HTMLResponse or JSON):
   - Path param: `device_id`
   - Query param: `format` (default "html", or "json")
   - Get tenant_id
   - Fetch device using COMPOSITE KEY: `fetch_device(conn, tenant_id, device_id)`
   - If device is None: raise HTTPException(404, "Device not found")
   - Fetch device events (limit 50)
   - Fetch device telemetry (limit 120)
   - Generate sparkline data (reuse existing `sparkline_points` function)
   - If format=json: return JSON
   - Else: render `customer_device.html` template (or reuse existing device.html with modifications)

4. `GET /customer/alerts` (JSON):
   - Query params: `status` (default "OPEN"), `limit` (default 100, max 500)
   - Get tenant_id
   - Fetch alerts for tenant
   - Return: `{"tenant_id": ..., "alerts": [...], "status": ..., "limit": ...}`

5. `GET /customer/alerts/{alert_id}` (JSON):
   - Path param: `alert_id`
   - Get tenant_id
   - Fetch alert by id AND tenant_id (add query if needed)
   - If not found: raise HTTPException(404)
   - Return alert details

6. `GET /customer/integrations` (JSON):
   - Get tenant_id
   - Fetch integrations for tenant
   - Redact URLs (show only scheme://host:port)
   - Return: `{"tenant_id": ..., "integrations": [...]}`

7. `GET /customer/delivery-status` (JSON):
   - Query param: `limit` (default 20, max 100)
   - Get tenant_id
   - Fetch delivery attempts
   - Return: `{"tenant_id": ..., "attempts": [...]}`

**Helper functions** (copy from existing app.py):
- `sparkline_points(values, width, height, pad)` — for chart rendering
- `redact_url(value)` — for URL redaction
- `to_float(v)`, `to_int(v)` — for safe type conversion

**Error handling**:
- All routes should catch database errors and return 500 with generic message
- Log actual errors server-side
- Never expose tenant_id mismatch details (just 404)

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `services/ui_iot/routes/__init__.py` |
| CREATE | `services/ui_iot/routes/customer.py` |

## Acceptance Criteria

- [ ] `/customer/dashboard` returns 401 without token
- [ ] `/customer/dashboard` returns 403 with operator token
- [ ] `/customer/dashboard` returns 200 with customer token, shows only tenant's data
- [ ] `/customer/devices` returns paginated device list for tenant only
- [ ] `/customer/devices/{device_id}` returns 404 if device belongs to different tenant
- [ ] `/customer/devices/{device_id}` returns device detail if device belongs to tenant
- [ ] All JSON responses include `tenant_id` field
- [ ] URLs in integrations response are redacted

**Test scenario**:
1. Login as customer1 (tenant-a)
2. Create test device in tenant-a and tenant-b
3. Access `/customer/devices` — should see only tenant-a device
4. Access `/customer/devices/{tenant-b-device}` — should get 404

## Commit

```
Add customer routes with tenant enforcement

- /customer/dashboard: tenant-scoped overview
- /customer/devices: paginated device list
- /customer/devices/{id}: composite key lookup (tenant_id, device_id)
- /customer/alerts: tenant alerts
- /customer/integrations: redacted webhook list
- All routes require JWT with customer role

Part of Phase 1: Customer Read-Only Dashboard
```
