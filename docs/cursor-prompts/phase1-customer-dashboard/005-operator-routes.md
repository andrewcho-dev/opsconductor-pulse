# Task 005: Operator Routes

## Context

Operators need cross-tenant access to all data, but this access must be audited. We're creating separate operator routes that require operator role and log all access.

**Read first**:
- `docs/CUSTOMER_PLANE_ARCHITECTURE.md` (Section 3.2: Operator-Plane Routes)
- `services/ui_iot/app.py` (existing dashboard implementation to migrate)
- `services/ui_iot/db/audit.py` (audit logging)

**Depends on**: Tasks 002, 003

## Task

### 5.1 Create `services/ui_iot/routes/operator.py`

Implement operator routes with audit logging.

**Imports**:
- `fastapi` (APIRouter, Depends, Request, HTTPException, Query)
- `fastapi.responses` (HTMLResponse, RedirectResponse)
- `fastapi.templating` (Jinja2Templates)
- From `middleware.auth`: `JWTBearer`
- From `middleware.tenant`: `inject_tenant_context`, `get_tenant_id_or_none`, `get_user`, `require_operator`, `require_operator_admin`, `is_operator`
- From `db.queries`: query functions
- From `db.audit`: `log_operator_access`

**Router setup**:
```python
router = APIRouter(
    prefix="/operator",
    tags=["operator"],
    dependencies=[
        Depends(JWTBearer()),
        Depends(inject_tenant_context),
        Depends(require_operator)
    ]
)
```

**Helper to extract request metadata**:
```python
def get_request_metadata(request: Request) -> tuple[str, str]:
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return ip, user_agent
```

**Routes to implement**:

1. `GET /operator/dashboard` (HTMLResponse):
   - Get user from context
   - Get request metadata
   - Log operator access: action="view_dashboard"
   - Fetch cross-tenant stats:
     - Total devices, online, stale (no tenant filter)
     - Open alerts count
     - Quarantine events (last 10 minutes)
     - Rate limited count
   - Fetch devices (all tenants, limit 100)
   - Fetch open alerts (all tenants, limit 50)
   - Fetch integrations (all tenants, limit 50)
   - Fetch delivery attempts (all tenants, limit 20)
   - Fetch quarantine events (limit 50)
   - Render existing `dashboard.html` with operator context flag

2. `GET /operator/devices` (JSON):
   - Query params: `tenant_filter` (optional), `limit` (default 100), `offset` (default 0)
   - Log operator access: action="list_devices", tenant_filter=...
   - If tenant_filter: use tenant-scoped query
   - Else: cross-tenant query
   - Return: `{"devices": [...], "tenant_filter": ..., "limit": ..., "offset": ...}`

3. `GET /operator/tenants/{tenant_id}/devices` (JSON):
   - Path param: `tenant_id`
   - Log operator access: action="list_tenant_devices", tenant_filter=tenant_id
   - Fetch devices for specific tenant
   - Return device list

4. `GET /operator/tenants/{tenant_id}/devices/{device_id}` (JSON or HTML):
   - Path params: `tenant_id`, `device_id`
   - Query param: `format` (default "json")
   - Log operator access: action="view_device", resource_type="device", resource_id=device_id
   - Fetch device using composite key
   - If not found: raise HTTPException(404)
   - Fetch events and telemetry
   - Return JSON or render template

5. `GET /operator/alerts` (JSON):
   - Query params: `tenant_filter` (optional), `status` (default "OPEN"), `limit` (default 100)
   - Log operator access: action="list_alerts"
   - Cross-tenant or filtered query
   - Return alert list

6. `GET /operator/quarantine` (JSON):
   - Query params: `minutes` (default 60), `limit` (default 100)
   - Log operator access: action="view_quarantine"
   - Fetch quarantine events
   - Return events list

7. `GET /operator/integrations` (JSON):
   - Query param: `tenant_filter` (optional)
   - Log operator access: action="list_integrations"
   - Cross-tenant or filtered
   - Include full URLs (operators can see them)
   - Return integrations list

8. `GET /operator/settings` (HTMLResponse):
   - Additional dependency: `require_operator_admin`
   - Log operator access: action="view_settings"
   - Fetch current settings
   - Render settings template (or section of dashboard)

9. `POST /operator/settings` (Redirect):
   - Additional dependency: `require_operator_admin`
   - Form params: `mode`, `store_rejects`, `mirror_rejects`
   - Log operator access: action="update_settings"
   - Update settings in database
   - Redirect to `/operator/dashboard`

**Cross-tenant query examples** (add to db/queries.py if needed):

```python
async def fetch_all_devices(conn, limit: int = 100, offset: int = 0):
    # NO tenant filter - operator only
    return await conn.fetch("""
        SELECT tenant_id, device_id, site_id, status, last_seen_at, ...
        FROM device_state
        ORDER BY tenant_id, site_id, device_id
        LIMIT $1 OFFSET $2
    """, limit, offset)

async def fetch_all_alerts(conn, status: str = "OPEN", limit: int = 100):
    return await conn.fetch("""
        SELECT * FROM fleet_alert
        WHERE status = $1
        ORDER BY created_at DESC
        LIMIT $2
    """, status, limit)
```

**Audit logging pattern**:
Every route handler should start with:
```python
user = get_user()
ip, user_agent = get_request_metadata(request)
async with pool.acquire() as conn:
    await log_operator_access(
        conn,
        user_id=user["sub"],
        action="...",
        tenant_filter=...,
        resource_type=...,
        resource_id=...,
        ip_address=ip,
        user_agent=user_agent
    )
    # ... rest of handler
```

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `services/ui_iot/routes/operator.py` |
| MODIFY | `services/ui_iot/db/queries.py` (add cross-tenant queries) |

## Acceptance Criteria

- [ ] `/operator/dashboard` returns 401 without token
- [ ] `/operator/dashboard` returns 403 with customer token
- [ ] `/operator/dashboard` returns 200 with operator token
- [ ] `/operator/dashboard` shows data from ALL tenants
- [ ] `/operator/settings` returns 403 for regular operator (not admin)
- [ ] `/operator/settings` returns 200 for operator_admin
- [ ] Every operator route creates an entry in `operator_audit_log`
- [ ] Audit log includes user_id, action, timestamp

**Test scenario**:
1. Login as operator1
2. Access `/operator/dashboard`
3. Check `operator_audit_log` table — should have entry
4. Try `/operator/settings` — should get 403
5. Login as operator_admin
6. Access `/operator/settings` — should work

## Commit

```
Add operator routes with audit logging

- /operator/dashboard: cross-tenant overview
- /operator/devices: all devices with optional tenant filter
- /operator/tenants/{tid}/devices/{did}: explicit tenant access
- /operator/alerts: cross-tenant alerts
- /operator/quarantine: quarantine events
- /operator/settings: admin-only settings management
- All access logged to operator_audit_log

Part of Phase 1: Customer Read-Only Dashboard
```
