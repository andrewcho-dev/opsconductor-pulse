# OpsConductor-Pulse — Customer Plane Architecture (v1.0)

## Status: IMPLEMENTED

**Date**: 2026-02-02
**Decisions By**: Principal Engineer
**Prepared By**: Architecture Review

---

## Executive Summary

This document defines the architecture for introducing customer-facing dashboards with strict tenant isolation, unified authentication via Keycloak, and a phased approach to database enforcement.

### Key Decisions Locked

| Decision | Choice | Rationale |
|----------|--------|-----------|
| JWT Issuance | Keycloak (external IdP) | Battle-tested, SSO support, OIDC standard |
| Operator Access Model | Unified auth with role claim | Single system, operators get elevated `role: operator` |
| RLS Enforcement | Application-level first, RLS later | Preserve dev velocity; RLS as defense-in-depth |

---

## 1. Unified Authentication Model

### 1.1 Keycloak Integration

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐
│   Browser   │────▶│  Keycloak   │────▶│  OpsConductor   │
│  (Customer) │     │  (IdP)      │     │  UI / API       │
└─────────────┘     └─────────────┘     └─────────────────┘
       │                   │                    │
       │  1. Login         │                    │
       │──────────────────▶│                    │
       │                   │                    │
       │  2. OIDC Flow     │                    │
       │◀─────────────────▶│                    │
       │                   │                    │
       │  3. JWT (id_token + access_token)      │
       │◀──────────────────│                    │
       │                   │                    │
       │  4. API Request + Bearer Token         │
       │───────────────────────────────────────▶│
       │                   │                    │
       │                   │  5. Validate JWT   │
       │                   │  6. Extract tenant │
       │                   │  7. Enforce scope  │
```

### 1.2 JWT Claims Structure

```json
{
  "iss": "https://auth.opsconductor.io/realms/pulse",
  "sub": "user-uuid-here",
  "aud": "opsconductor-pulse",
  "exp": 1735689600,
  "iat": 1735686000,
  "tenant_id": "customer-abc",
  "role": "customer_admin",
  "email": "admin@customer-abc.com"
}
```

**Role Values**:
| Role | Description | Access |
|------|-------------|--------|
| `customer_viewer` | Read-only customer access | View devices, alerts, delivery status |
| `customer_admin` | Full customer access | Above + manage integrations, routes |
| `operator` | Cross-tenant operator access | All customer data, audited |
| `operator_admin` | Operator with admin functions | Above + system settings, provisioning |

### 1.3 Keycloak Realm Configuration

**Realm**: `pulse`
**Clients**:
- `pulse-ui` — Browser-based SPA (public client, PKCE)
- `pulse-api` — Backend service (confidential client for token introspection)

**Custom Mapper** (tenant_id from user attribute):
```
Name: tenant_id_mapper
Mapper Type: User Attribute
User Attribute: tenant_id
Token Claim Name: tenant_id
Claim JSON Type: String
Add to ID token: true
Add to access token: true
```

**Operator Users**: Have `role: operator` attribute and `tenant_id: *` (or null).

---

## 2. Application-Level Tenant Enforcement

### 2.1 Core Principle

**Every database query in customer-plane code MUST include `tenant_id` in the WHERE clause.**

This is not optional. This is not "we'll add it later." This is the law.

### 2.2 Enforcement Patterns

#### Pattern A: Tenant Context Middleware

```python
# middleware/tenant_context.py

from contextvars import ContextVar
from fastapi import Request, HTTPException
from jose import jwt, JWTError

tenant_context: ContextVar[str | None] = ContextVar("tenant_context", default=None)
user_context: ContextVar[dict | None] = ContextVar("user_context", default=None)

KEYCLOAK_JWKS_URL = "https://auth.opsconductor.io/realms/pulse/protocol/openid-connect/certs"

async def require_tenant(request: Request):
    """Extract and validate tenant from JWT. Sets context vars."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid Authorization header")

    token = auth_header[7:]
    try:
        # In production: validate against JWKS, check exp, aud, iss
        payload = jwt.decode(token, options={"verify_signature": False})  # PLACEHOLDER

        tid = payload.get("tenant_id")
        role = payload.get("role", "")

        if not tid and role not in ("operator", "operator_admin"):
            raise HTTPException(403, "No tenant_id in token and not operator")

        tenant_context.set(tid)
        user_context.set(payload)

    except JWTError as e:
        raise HTTPException(401, f"Invalid token: {e}")

def get_tenant_id() -> str:
    """Get current tenant_id or raise. NEVER returns None for customer routes."""
    tid = tenant_context.get()
    if not tid:
        raise RuntimeError("tenant_id not set — middleware misconfiguration")
    return tid

def is_operator() -> bool:
    """Check if current user is operator (cross-tenant access)."""
    user = user_context.get()
    return user and user.get("role") in ("operator", "operator_admin")
```

#### Pattern B: Query Builders with Mandatory Tenant

```python
# db/queries.py

async def fetch_devices_for_tenant(conn, tenant_id: str):
    """Fetch devices for a specific tenant. tenant_id is REQUIRED."""
    if not tenant_id:
        raise ValueError("tenant_id is required")

    return await conn.fetch(
        """
        SELECT device_id, site_id, status, last_seen_at, state
        FROM device_state
        WHERE tenant_id = $1
        ORDER BY site_id, device_id
        """,
        tenant_id
    )

async def fetch_device_detail(conn, tenant_id: str, device_id: str):
    """Fetch single device. BOTH tenant_id and device_id required."""
    if not tenant_id or not device_id:
        raise ValueError("tenant_id and device_id are both required")

    return await conn.fetchrow(
        """
        SELECT tenant_id, device_id, site_id, status, last_seen_at, state
        FROM device_state
        WHERE tenant_id = $1 AND device_id = $2
        """,
        tenant_id, device_id
    )
```

#### Pattern C: Route-Level Enforcement

```python
# routes/customer.py

from fastapi import APIRouter, Depends
from middleware.tenant_context import require_tenant, get_tenant_id
from db.queries import fetch_devices_for_tenant, fetch_device_detail

router = APIRouter(prefix="/customer", dependencies=[Depends(require_tenant)])

@router.get("/devices")
async def list_devices():
    tenant_id = get_tenant_id()  # Will raise if not set
    async with pool.acquire() as conn:
        devices = await fetch_devices_for_tenant(conn, tenant_id)
    return {"devices": devices}

@router.get("/devices/{device_id}")
async def get_device(device_id: str):
    tenant_id = get_tenant_id()
    async with pool.acquire() as conn:
        device = await fetch_device_detail(conn, tenant_id, device_id)
        if not device:
            raise HTTPException(404, "Device not found")
    return {"device": device}
```

### 2.3 Operator Routes with Audit

```python
# routes/operator.py

from fastapi import APIRouter, Depends
from middleware.tenant_context import require_tenant, is_operator, user_context
from db.audit import log_operator_access

router = APIRouter(prefix="/operator", dependencies=[Depends(require_tenant)])

@router.get("/devices")
async def list_all_devices(tenant_filter: str | None = None):
    if not is_operator():
        raise HTTPException(403, "Operator access required")

    user = user_context.get()
    await log_operator_access(
        user_id=user["sub"],
        action="list_all_devices",
        tenant_filter=tenant_filter
    )

    async with pool.acquire() as conn:
        if tenant_filter:
            devices = await fetch_devices_for_tenant(conn, tenant_filter)
        else:
            # Cross-tenant query — only for operators, always audited
            devices = await conn.fetch(
                "SELECT * FROM device_state ORDER BY tenant_id, site_id, device_id LIMIT 1000"
            )
    return {"devices": devices}
```

### 2.4 Prohibited Patterns (Code Review Blockers)

```python
# BAD: Query by device_id alone
await conn.fetch("SELECT * FROM device_state WHERE device_id = $1", device_id)

# BAD: Tenant from URL parameter
@router.get("/tenant/{tenant_id}/devices")  # NO! Tenant from JWT only

# BAD: Tenant from request body
async def create_device(payload: dict):
    tenant_id = payload.get("tenant_id")  # NO! From auth context only

# BAD: Optional tenant_id with default
def fetch_device(conn, tenant_id: str = None):  # NO! tenant_id always required
```

---

## 3. Route Structure

### 3.1 Customer-Plane Routes (Tenant-Scoped)

| Method | Route | Auth | Description |
|--------|-------|------|-------------|
| GET | `/customer/dashboard` | JWT (customer_*) | Tenant dashboard overview |
| GET | `/customer/devices` | JWT (customer_*) | List devices for tenant |
| GET | `/customer/devices/{device_id}` | JWT (customer_*) | Device detail (composite key) |
| GET | `/customer/alerts` | JWT (customer_*) | Open alerts for tenant |
| GET | `/customer/alerts/{alert_id}` | JWT (customer_*) | Alert detail |
| GET | `/customer/integrations` | JWT (customer_admin) | List integrations |
| POST | `/customer/integrations` | JWT (customer_admin) | Create integration |
| PATCH | `/customer/integrations/{id}` | JWT (customer_admin) | Update integration |
| DELETE | `/customer/integrations/{id}` | JWT (customer_admin) | Delete integration |
| GET | `/customer/delivery-status` | JWT (customer_*) | Recent delivery attempts |

### 3.2 Operator-Plane Routes (Cross-Tenant, Audited)

| Method | Route | Auth | Description |
|--------|-------|------|-------------|
| GET | `/operator/dashboard` | JWT (operator*) | Cross-tenant overview |
| GET | `/operator/devices` | JWT (operator*) | All devices (paginated) |
| GET | `/operator/tenants/{tid}/devices` | JWT (operator*) | Devices for specific tenant |
| GET | `/operator/alerts` | JWT (operator*) | All open alerts |
| GET | `/operator/quarantine` | JWT (operator*) | Quarantine events |
| GET | `/operator/settings` | JWT (operator_admin) | System settings |
| POST | `/operator/settings` | JWT (operator_admin) | Update settings |

### 3.3 Admin API Routes (Existing, Keep)

| Method | Route | Auth | Description |
|--------|-------|------|-------------|
| POST | `/api/admin/devices` | X-Admin-Key | Provision device |
| POST | `/api/admin/devices/{id}/activate-code` | X-Admin-Key | Generate activation code |
| POST | `/api/admin/integrations` | X-Admin-Key | Create integration |
| POST | `/api/admin/integration-routes` | X-Admin-Key | Create route |

**Note**: Admin API routes remain protected by `X-Admin-Key` header. These are for automation/CI pipelines. Keycloak auth applies to UI routes only.

---

## 4. Database Connection Strategy

### 4.1 Connection Pools (Phase 1: Application-Level)

```python
# Two logical pools, same database, different query patterns

customer_pool = asyncpg.create_pool(...)  # Used by /customer/* routes
operator_pool = asyncpg.create_pool(...)  # Used by /operator/* routes

# Both pools connect as same user initially
# Queries are tenant-scoped by application code, not RLS
```

### 4.2 Connection Pools (Phase 2: With RLS)

```python
# After RLS is enabled:

async def get_customer_connection(tenant_id: str):
    conn = await customer_pool.acquire()
    await conn.execute("SET LOCAL app.tenant_id = $1", tenant_id)
    return conn

async def get_operator_connection(user_id: str, bypass_rls: bool = False):
    conn = await operator_pool.acquire()
    if bypass_rls:
        await conn.execute("SET LOCAL row_security = off")
        await log_rls_bypass(user_id)
    return conn
```

---

## 5. Phased Implementation Plan

### Phase 1: Foundation (Customer Read-Only Dashboard)

**Goal**: Customers can view their own devices, alerts, and delivery status.

**Scope**:
1. Deploy Keycloak (Docker Compose addition)
2. Create `pulse` realm with tenant_id mapper
3. Implement JWT validation middleware
4. Add `/customer/*` routes with tenant enforcement
5. Fix existing `/device/{device_id}` to require composite key
6. Create customer dashboard template
7. Add operator role support to existing dashboard

**Work Items**:
| Item | File(s) | Priority |
|------|---------|----------|
| Keycloak compose service | `compose/docker-compose.yml` | P0 |
| Keycloak realm export | `compose/keycloak/realm-pulse.json` | P0 |
| JWT middleware | `services/ui_iot/middleware/auth.py` | P0 |
| Tenant context helpers | `services/ui_iot/middleware/tenant.py` | P0 |
| Customer routes | `services/ui_iot/routes/customer.py` | P0 |
| Fix device detail query | `services/ui_iot/app.py:381-449` | P0 |
| Customer dashboard template | `services/ui_iot/templates/customer_dashboard.html` | P1 |
| Operator route refactor | `services/ui_iot/routes/operator.py` | P1 |
| Audit logging | `services/ui_iot/db/audit.py` | P1 |

**Exit Criteria**:
- [ ] Customer can login via Keycloak and see only their tenant's data
- [ ] Operator can login and see cross-tenant view with audit trail
- [ ] No queries use device_id without tenant_id
- [ ] All customer routes return 401/403 for invalid/missing tokens

### Phase 2: Customer Integration Management

**Goal**: Customers can create/manage their own webhook integrations.

**Scope**:
1. Add `/customer/integrations` CRUD routes
2. Add `/customer/integration-routes` management
3. Implement integration test mode (dry-run)
4. Add URL validation for customer-created webhooks

**Work Items**:
| Item | File(s) | Priority |
|------|---------|----------|
| Integration CRUD routes | `services/ui_iot/routes/customer.py` | P0 |
| Route management UI | `services/ui_iot/templates/customer_integrations.html` | P1 |
| Test delivery endpoint | `services/provision_api/app.py` | P1 |
| URL allowlist (enterprise) | `db/migrations/002_customer_integration_limits.sql` | P2 |

**Exit Criteria**:
- [ ] Customer can create integrations scoped to their tenant
- [ ] Customer can define routes for their alerts
- [ ] Test delivery works without affecting production alerts
- [ ] URL validation prevents SSRF from customer-supplied URLs

### Phase 3: RLS Enforcement

**Goal**: Add database-level tenant isolation as defense-in-depth.

**Scope**:
1. Enable RLS on all tenant-scoped tables
2. Create policies using `current_setting('app.tenant_id')`
3. Update connection helpers to SET LOCAL before queries
4. Test fail-closed behavior when context missing
5. Implement operator RLS bypass with audit

**Work Items**:
| Item | File(s) | Priority |
|------|---------|----------|
| RLS migration | `db/migrations/003_enable_rls.sql` | P0 |
| Connection wrapper update | `services/ui_iot/db/pool.py` | P0 |
| Fail-closed tests | `tests/test_rls_enforcement.py` | P0 |
| Operator bypass audit | `services/ui_iot/db/audit.py` | P1 |

**Exit Criteria**:
- [ ] Queries without app.tenant_id return zero rows
- [ ] Application tests pass with RLS enabled
- [ ] Operator bypass is logged and auditable

### Phase 4: SNMP and Alternative Outputs

**Goal**: Support SNMP trap delivery alongside webhooks.

**Scope**:
1. Extend `integrations.type` CHECK constraint
2. Create SNMP delivery worker (or extend existing)
3. Define OID mapping configuration
4. Customer-configurable trap destinations

**Deferred to separate design document.**

---

## 6. Invariants (Unchanged)

These invariants from TENANT_CONTEXT_CONTRACT.md remain in force:

1. **tenant_id required on all device data paths**
2. **No cross-tenant data access** (except audited operator)
3. **Canonical device identity is (tenant_id, device_id)**
4. **Rejected/quarantined events MUST NEVER affect device_state**
5. **UI is read-only** (customer writes only for integrations in Phase 2)
6. **Admin APIs require X-Admin-Key**
7. **Rate limiting must fail closed**

---

## 7. Security Considerations

### 7.1 JWT Validation Checklist

- [ ] Verify signature against Keycloak JWKS endpoint
- [ ] Check `exp` claim (reject expired tokens)
- [ ] Check `aud` claim matches `opsconductor-pulse`
- [ ] Check `iss` claim matches expected Keycloak URL
- [ ] Extract `tenant_id` from validated claims only
- [ ] Cache JWKS with reasonable TTL (5 minutes)

### 7.2 Token Refresh Strategy

- Access token TTL: 15 minutes (900s, configured in Keycloak `accessTokenLifespan`)
- Refresh token TTL: 30 minutes
- `pulse_session` cookie `max_age` set to `expires_in + 60` seconds (60s buffer so the cookie outlives the token, giving refresh logic time to act)
- API returns 401 on expired token (not auto-refresh)

**Client-side refresh mechanisms** (`auth.js`):

| Mechanism | How it works |
|-----------|-------------|
| `setInterval` polling | `maybeRefresh()` runs every 30 seconds; refreshes when within 90 seconds of expiry |
| `visibilitychange` listener | Calls `maybeRefresh()` immediately when a background tab becomes visible |
| Fetch 401 interceptor | Wraps `window.fetch`; on any non-auth 401, attempts a token refresh then retries the original request |
| Retry-once logic | `maybeRefresh()` retries once (after 5s delay) before redirecting to login |

**401 exception handler** (`app.py`): Browser page-navigation requests (`Accept: text/html`) that receive a 401 are redirected to the login page (302 to `/`) instead of returning raw JSON.

### 7.3 Audit Log Schema

```sql
CREATE TABLE operator_audit_log (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    action TEXT NOT NULL,
    tenant_filter TEXT,
    resource_type TEXT,
    resource_id TEXT,
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX operator_audit_log_user_idx ON operator_audit_log(user_id);
CREATE INDEX operator_audit_log_timestamp_idx ON operator_audit_log(timestamp DESC);
```

---

## Appendix A: Keycloak Docker Compose Addition

```yaml
# To be added to compose/docker-compose.yml

keycloak:
  image: quay.io/keycloak/keycloak:24.0
  container_name: pulse-keycloak
  environment:
    KEYCLOAK_ADMIN: admin
    KEYCLOAK_ADMIN_PASSWORD: admin_dev  # Change in production
    KC_DB: postgres
    KC_DB_URL: jdbc:postgresql://iot-postgres:5432/iotcloud
    KC_DB_USERNAME: iot
    KC_DB_PASSWORD: iot_dev
    KC_HOSTNAME_STRICT: "false"
    KC_HTTP_ENABLED: "true"
  command: start-dev --import-realm
  volumes:
    - ./keycloak/realm-pulse.json:/opt/keycloak/data/import/realm-pulse.json
  ports:
    - "8180:8080"
  depends_on:
    postgres:
      condition: service_healthy
  restart: unless-stopped
```

---

## Appendix B: Migration Path for Existing UI

The existing `ui_iot` service will be refactored:

**Before** (current):
```
/                     → Cross-tenant dashboard (no auth)
/device/{device_id}   → Device detail (device_id only, BROKEN)
/settings             → Mode toggle (no auth)
```

**After** (Phase 1 complete):
```
/                     → Redirect to /customer/dashboard or /operator/dashboard based on role
/customer/*           → Tenant-scoped routes (JWT required)
/operator/*           → Cross-tenant routes (JWT with operator role required)
/settings             → Moved to /operator/settings (operator_admin required)
/device/{device_id}   → DEPRECATED, returns 410 Gone with redirect hint
```

---

*Document version 1.1 — All phases implemented. This document serves as a reference for the authentication and tenant isolation design.*
