# 007: Unit Tests for routes/users.py and routes/ingest.py

## Why
- `services/ui_iot/routes/users.py` (948 LOC, 23 endpoints) has ZERO tests. It handles user CRUD, role assignment, and tenant membership — all security-critical.
- `services/ui_iot/routes/ingest.py` (336 LOC, 4 endpoints) has ZERO tests. It's the HTTP ingest gateway — every HTTP-submitted telemetry message goes through here.

## Source Files
Read: `services/ui_iot/routes/users.py`
Read: `services/ui_iot/routes/ingest.py`

## Pattern to Follow
Read: `tests/unit/test_customer_route_handlers.py` (first 80 lines) for FakeConn/FakePool pattern.
Read: `tests/unit/test_operator_route_handlers.py` for operator-auth mocking pattern.

## Test Files to Create

### `tests/unit/test_user_routes.py` (~18 tests)

#### Operator User Management (8 tests)
```
test_list_users_returns_keycloak_users
  - Mock keycloak_admin.get_users() → return user list
  - GET /api/operator/users → 200 with user array

test_create_user_calls_keycloak
  - POST /api/operator/users with {email, role, tenant_id}
  - Verify keycloak_admin.create_user() called with correct args
  - Returns 201

test_create_user_validates_email
  - POST with invalid email → 400/422

test_create_user_validates_role
  - POST with invalid role (e.g., "superadmin") → 400
  - Only valid roles: customer_viewer, customer_admin, operator, operator_admin

test_assign_role_updates_keycloak
  - PUT /api/operator/users/{id}/role with {role: "operator"}
  - Verify keycloak_admin.assign_realm_role() called

test_delete_user_calls_keycloak
  - DELETE /api/operator/users/{id}
  - Verify keycloak_admin.delete_user() called

test_user_management_requires_operator_admin
  - Call with operator (not admin) role → 403
  - Call with operator_admin → 200

test_list_users_audit_logged
  - After GET /api/operator/users
  - Verify audit log entry created
```

#### Customer User Management (5 tests)
```
test_tenant_admin_can_list_tenant_users
  - Auth as customer_admin for tenant-a
  - GET returns only tenant-a users

test_tenant_admin_can_invite_user
  - POST to invite user to own tenant
  - Verify keycloak call with tenant_id attribute

test_tenant_viewer_cannot_manage_users
  - Auth as customer_viewer → 403 on POST/PUT/DELETE

test_change_tenant_user_role
  - PUT to change user from viewer to admin
  - Only customer_admin or operator can do this

test_cannot_manage_other_tenant_users
  - Auth as tenant-a admin
  - Try to manage tenant-b user → 403
```

#### User Profile (5 tests)
```
test_get_current_user_profile
  - GET /api/users/me → returns user details from JWT

test_get_user_permissions
  - GET /api/users/me/permissions → returns role and permissions list

test_change_password_calls_keycloak
  - PUT /api/users/me/password with {current, new}
  - Verify Keycloak token endpoint called

test_change_password_validates_current
  - Wrong current password → 401

test_logout_clears_session
  - POST /api/users/logout
  - Verify session cookie cleared
```

### `tests/unit/test_ingest_routes.py` (~12 tests)

#### Single Message Ingest (6 tests)
```
test_valid_telemetry_accepted
  - POST /ingest/v1/tenant/t1/device/d1/telemetry
  - Header: X-Provision-Token
  - Body: {site_id, metrics: {temp_c: 25}}
  - Returns 202 Accepted

test_invalid_msg_type_rejected
  - POST with msg_type="invalid" → 400

test_missing_provision_token_rejected
  - POST without X-Provision-Token header
  - Returns 401

test_payload_too_large_rejected
  - POST with >8192 byte payload → 400

test_rate_limited_returns_429
  - Exhaust device rate limit
  - Next request → 429

test_global_limit_returns_503
  - Exhaust global rate limit
  - Returns 503
```

#### Batch Ingest (4 tests)
```
test_batch_accepts_multiple_messages
  - POST /ingest/v1/batch with 3 messages
  - Returns 202 with accepted=3

test_batch_partial_success
  - 2 valid + 1 invalid message
  - Returns 202 with accepted=2, rejected=1
  - Results array shows per-message status

test_batch_max_100_messages
  - POST with 101 messages → 400

test_batch_all_rejected
  - All messages invalid
  - Returns 400 with accepted=0
```

#### Rate Limit Metrics (2 tests)
```
test_rate_limit_metrics_endpoint
  - GET /ingest/v1/metrics/rate-limits
  - Returns current rate limiter stats

test_rate_limit_metrics_requires_no_auth
  - Verify this endpoint is accessible without token (or with operator token)
```

## Implementation Notes

### User Routes (`services/ui_iot/routes/users.py`)

**Exact operator endpoints:**
```
GET    /operator/users                        → list_all_users(search?, tenant_filter?, limit, offset)
GET    /operator/users/{user_id}              → get_user_detail
POST   /operator/users                        → create_new_user(CreateUserRequest)
PUT    /operator/users/{user_id}              → update_existing_user(UpdateUserRequest)
DELETE /operator/users/{user_id}              → delete_existing_user
POST   /operator/users/{user_id}/enable       → enable_user_account
POST   /operator/users/{user_id}/disable      → disable_user_account
POST   /operator/users/{user_id}/roles        → assign_user_role(AssignRoleRequest)
DELETE /operator/users/{user_id}/roles/{name}  → remove_user_role
POST   /operator/users/{user_id}/tenant       → assign_user_to_tenant(AssignTenantRequest)
POST   /operator/users/{user_id}/reset-password → send_password_reset
POST   /operator/users/{user_id}/password     → set_user_password(SetPasswordRequest)
GET    /operator/organizations                → list_organizations
```

**Exact customer endpoints:**
```
GET    /customer/users                        → list_tenant_users
GET    /customer/users/{user_id}              → get_tenant_user_detail
POST   /customer/users/invite                 → invite_user_to_tenant(InviteUserRequest)
PUT    /customer/users/{user_id}              → update_tenant_user
POST   /customer/users/{user_id}/role         → change_tenant_user_role(AssignRoleRequest)
DELETE /customer/users/{user_id}              → remove_user_from_tenant
POST   /customer/users/{user_id}/reset-password → send_tenant_user_password_reset
```

**Pydantic models:** `CreateUserRequest`, `UpdateUserRequest`, `AssignRoleRequest`, `AssignTenantRequest`, `SetPasswordRequest`, `InviteUserRequest`

**Auth guards:** `require_operator`, `require_operator_admin` decorators. Valid roles: `customer`, `tenant-admin`, `operator`, `operator-admin`

**Mock requirements:** All `keycloak_admin` functions (list_users, create_user, get_user, delete_user, assign_realm_role, etc.) with AsyncMock. Audit logger `_audit()` helper.

### Ingest Routes (`services/ui_iot/routes/ingest.py`)

**Exact endpoints:**
```
GET  /ingest/v1/metrics/rate-limits
POST /ingest/v1/tenant/{tenant_id}/device/{device_id}/{msg_type}   (Header: X-Provision-Token)
POST /ingest/v1/batch
```

**Pydantic models:** `IngestPayload(ts?, site_id, seq, metrics)`, `BatchMessage(tenant_id, device_id, msg_type, provision_token, ...)`, `BatchRequest(messages)`, `BatchResponse(accepted, rejected, results)`

**Helper:** `get_client_ip(request)` — parses X-Forwarded-For, X-Real-IP, scope.client

**Mock requirements:**
- `request.app.state.batch_writer` — TimescaleBatchWriter
- `request.app.state.auth_cache` — DeviceAuthCache
- `request.app.state.rate_buckets` — rate limiter state
- `validate_and_prepare` from `services/shared/ingest_core` — returns `IngestResult(success, reason)`
- Use `httpx.AsyncClient` with `ASGITransport` to call the FastAPI app
- Use `pytestmark = [pytest.mark.unit, pytest.mark.asyncio]`

### Existing test for reference
- `tests/unit/test_http_ingest.py` — may already have some ingest tests. Read it first and expand rather than duplicate.
- `tests/unit/test_customer_route_handlers.py` — FakeConn/FakePool pattern for route testing

## Verify
```bash
pytest tests/unit/test_user_routes.py tests/unit/test_ingest_routes.py -v
```
