# OpsConductor-Pulse — Tenant Context & Authentication Contract (Design-Only)

## Purpose
Define exactly how tenant identity is established, propagated, enforced, and audited across the system.

## 1) Actors & Planes
Actors: Customer User, Customer Admin, Operator, Device
Planes: Customer Plane (tenant-scoped), Operator Plane (cross-tenant, audited), Control Plane (enforces invariants)

## 2) Single Source of Truth for Tenant Identity
Tenant identity MUST come from authenticated session context only.
Never from URL params, request body, query strings, or client-supplied headers (except auth tokens).

Allowed sources:
- Customer user: signed session/JWT claim
- Operator: operator session (no tenant by default)
- Device: MQTT topic + registry validation

## 3) Customer Authentication Model
JWT contains: sub, tenant_id, role, exp.
JWT binds user to exactly one tenant and tenant cannot be overridden or switched.

## 4) Tenant Context Propagation
HTTP → app: auth middleware verifies token and extracts tenant_id into immutable request scope.
App → DB: before every tenant query:
  SET LOCAL app.tenant_id = '<tenant_id_from_session>';

## 5) Database Enforcement (RLS)
All tenant-scoped tables enforce:
  tenant_id = current_setting('app.tenant_id')
If app.tenant_id is unset, queries must fail closed.

## 6) Operator Access Model
Operator has no tenant by default; RLS applies.
Operator bypass requires:
- separate DB pool
- explicit context function
- SET LOCAL row_security = off
- full audit log entry

## 7) UI Route Binding Rules
Customer routes are tenant-scoped via session tenant:
- /dashboard
- /devices/{device_id} (resolved by tenant + device_id)
- /alerts
Operator routes are separate:
- /operator/*

Never accept tenant_id from URL/query for customer routes.

## 8) Canonical Device Identity
(tenant_id, device_id) is the only valid key. No query may use device_id alone.

## 9) Rate Limiting Scope
Rate limits must be tenant-scoped. A noisy tenant cannot impact others.

## 10) Failure Modes
Fail closed:
- missing tenant context → reject
- invalid JWT → 401
- tenant mismatch → 403
- RLS violation → request fails
- operator bypass → audited

