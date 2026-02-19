---
last-verified: 2026-02-19
sources:
  - services/ui_iot/middleware/auth.py
  - services/ui_iot/middleware/tenant.py
  - services/ui_iot/db/pool.py
  - services/ui_iot/routes/internal.py
  - services/ingest_iot/ingest.py
  - compose/emqx/emqx.conf
  - compose/nats/nats.conf
  - compose/nats/init-streams.sh
phases: [4, 36, 43, 96, 97, 142, 161, 162, 165]
---

# Tenant Isolation

> Authentication model, tenant context propagation, and database enforcement.

## Overview

Tenant isolation is enforced as defense-in-depth:

1. Authentication (JWT validation) establishes user identity and roles.
2. Tenant context is derived from the authenticated token (never from request parameters).
3. Database access uses connection wrappers that set tenant context for Row-Level Security (RLS).
4. Operator access uses a separate DB role that bypasses RLS and is audited.
5. Device plane isolation is enforced at the MQTT broker via per-device topic ACL checks (EMQX HTTP ACL backend).

## Authentication Model

### Keycloak Integration

- Identity provider: Keycloak (realm `pulse`)
- SPA auth: OIDC/PKCE (via `keycloak-js`)
- API auth: JWT Bearer tokens validated by `ui_iot` using Keycloak JWKS

### JWT Claims

`ui_iot` validates:

- Signature (Keycloak JWKS, RS256)
- Issuer: `KEYCLOAK_PUBLIC_URL/realms/<realm>`
- Audience: `JWT_AUDIENCE` (default `pulse-ui`)
- Expiry (standard `exp`)

Tenant identity is extracted from the authenticated payload:

- Preferred/standard: `organization` claim (dict or list form)
- Transitional fallback: `tenant_id` claim (legacy tokens)

### User Roles

Roles are read from `realm_access.roles`. The core roles used by authorization checks include:

- `customer`
- `tenant-admin`
- `operator`
- `operator-admin`

## Tenant Context Propagation

### HTTP → App (middleware)

The request flow is:

1. `JWTBearer` validates the token and stores the decoded payload on `request.state.user`.
2. `inject_tenant_context` extracts tenant id from `request.state.user` and sets context variables:
   - `tenant_context`
   - `user_context`

Customer route guards require:

- Non-operator users must have an organization membership (tenant id present).
- User must have at least one of `customer` or `tenant-admin`.

### App → DB (SET LOCAL)

Tenant-scoped DB access uses `tenant_connection(pool, tenant_id)`:

- `SET LOCAL ROLE pulse_app` (subject to RLS)
- `SELECT set_config('app.tenant_id', tenant_id, true)` to set tenant context
- Runs inside a transaction so `SET LOCAL` scope is bounded automatically

## Database Enforcement (RLS)

RLS policies (configured via migrations) rely on `app.tenant_id` being set. The expected model:

- Tenant-scoped tables include `tenant_id` and RLS policies enforce matching `current_setting('app.tenant_id')`.
- If tenant context is missing, the app fails closed (HTTP 401/403 at middleware; DB wrapper raises for missing tenant).

## Operator Access Model

Operator routes use `operator_connection(pool)`:

- `SET LOCAL ROLE pulse_operator` (BYPASSRLS)
- No tenant context is set by default
- Operator access should always be audited at the route/service layer

## Tenant Context Invariants

These invariants are the contract for tenant identity across the system:

1. Actors and planes: customer plane (tenant-scoped), operator plane (cross-tenant), device plane.
2. Tenant identity source: tenant identity comes only from authenticated session context.
3. Customer auth: JWT binds a user to exactly one tenant (organization membership).
4. Propagation: HTTP → app extracts tenant id into immutable request scope/context vars.
5. DB enforcement: app sets tenant context via `SET LOCAL` and relies on RLS.
6. Operator bypass: separate DB role/connection wrapper; all bypass access is audited.
7. UI binding: customer routes are tenant-scoped; operator routes are isolated under `/operator/*`.
8. Device identity: `(tenant_id, device_id)` is the canonical key; avoid `device_id`-only access.
9. Rate limiting: rate limits must be tenant-scoped so one tenant cannot starve others.
10. Failure modes: fail closed on missing/invalid auth, missing tenant context, or access violations.

## UI Route Binding

- Customer UI pages call customer APIs which derive tenant context from the session token.
- Operator UI pages call operator APIs guarded by operator roles; cross-tenant operations are audited.

## Device Identity

Device identity is always tenant-scoped:

- In telemetry topics and DB records, devices belong to a tenant.
- Authorization checks must prevent cross-tenant device access.

## Broker-Level MQTT ACLs (EMQX)

EMQX enforces per-device publish/subscribe ACLs at the broker level via internal HTTP endpoints:

- `POST /api/v1/internal/mqtt-auth` (CONNECT auth)
- `POST /api/v1/internal/mqtt-acl` (PUBLISH/SUBSCRIBE authorization)

These checks close the previous "read-side ACL gap" where a device could subscribe to another tenant's topics if application-layer validation was bypassed.

## NATS Subject Scoping (Internal Bus)

NATS JetStream is an internal message backbone; devices never connect to NATS directly.

Subject conventions:

- Telemetry envelopes are published to `telemetry.{tenant_id}` (stream `TELEMETRY`, subject filter `telemetry.>`).
- Shadow updates are published to `shadow.{tenant_id}` (stream `SHADOW`).
- Command messages are published to `commands.{tenant_id}` (stream `COMMANDS`).
- Route delivery jobs are published to `routes.{tenant_id}` (stream `ROUTES`).

These subjects provide an additional isolation boundary between tenants at the messaging layer (and allow future per-tenant consumer filtering if required). Device identity (`device_id`) is carried in the envelope payload and re-validated by consumers (e.g., `ingest_iot` auth cache + DB lookup fallback).

## Rate Limiting

Rate limiting occurs at multiple layers:

- Auth rate limiting for token validation attempts (disabled under pytest).
- Ingestion rate limiting (token bucket) to bound per-device/per-tenant ingestion.

## Failure Modes

Expected failure behavior:

- Missing token: HTTP 401
- Invalid token/signature/claims: HTTP 401
- Missing organization membership for customer routes: HTTP 403
- Operator access required but missing operator role: HTTP 403
- Missing tenant id when acquiring a tenant DB connection: raise error (fail closed)

## See Also

- [System Overview](overview.md)
- [Service Map](service-map.md)
- [API Overview](../api/overview.md)
- [Security](../operations/security.md)

