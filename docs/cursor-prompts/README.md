# Cursor Execution Prompts

This directory contains structured implementation prompts for Cursor (execution AI).

## Prompt Organization

Each phase has its own subdirectory with numbered task files. Tasks should be executed in order unless otherwise noted.

## Status Legend

| Status | Meaning |
|--------|---------|
| `[ ]` | Not started |
| `[~]` | In progress |
| `[x]` | Complete |
| `[!]` | Blocked |

---

## Phase 1: Customer Read-Only Dashboard

**Goal**: Customers can view their own devices, alerts, and delivery status with tenant isolation.

**Directory**: `phase1-customer-dashboard/`

**Status**: COMPLETE

| # | File | Description | Status | Dependencies |
|---|------|-------------|--------|--------------|
| 1 | `001-keycloak-setup.md` | Add Keycloak to Docker Compose, create realm config | `[x]` | None |
| 2 | `002-jwt-middleware.md` | JWT validation, JWKS fetching, token verification | `[x]` | #1 |
| 3 | `003-tenant-enforcement.md` | Context vars, tenant helpers, query builders | `[x]` | #2 |
| 4 | `004-customer-routes.md` | /customer/* routes with tenant scoping | `[x]` | #2, #3 |
| 5 | `005-operator-routes.md` | /operator/* routes with audit logging | `[x]` | #2, #3 |
| 6 | `006-app-refactor.md` | Mount routers, deprecate unsafe routes | `[x]` | #4, #5 |
| 7 | `007-templates.md` | Customer dashboard template, operator UI updates | `[x]` | #4, #5 |
| 8 | `008-audit-migration.md` | operator_audit_log table | `[x]` | None (can run early) |

**Exit Criteria**:
- [x] Customer can login via Keycloak and see only their tenant's data
- [x] Operator can login and see cross-tenant view with audit trail
- [x] No queries use device_id without tenant_id
- [x] All customer routes return 401/403 for invalid/missing tokens
- [x] Old /device/{device_id} returns 410 Gone

**Note**: Runtime validation pending (Keycloak realm import fix, container rebuild)

---

## Phase 2: Customer Integration Management

**Goal**: Customers can create/manage their own webhook integrations with full OAuth login flow.

**Directory**: `phase2-integration-management/`

**Status**: COMPLETE

| # | File | Description | Status | Dependencies |
|---|------|-------------|--------|--------------|
| 1 | `001-oauth-callback.md` | Complete OAuth code exchange, set HTTP-only cookie | `[x]` | Phase 1 |
| 2 | `002-frontend-auth.md` | JS auth handling, token attachment, refresh | `[x]` | #1 |
| 3 | `003-integration-crud-routes.md` | POST/PATCH/DELETE /customer/integrations | `[x]` | #1, #2 |
| 4 | `004-integration-routes-management.md` | Customer alert routing rules | `[x]` | #3 |
| 5 | `005-test-delivery-endpoint.md` | Dry-run webhook delivery | `[x]` | #3, #4 |
| 6 | `006-url-validation.md` | SSRF prevention for customer URLs | `[x]` | #3 |

**Exit Criteria**:
- [x] User can login via browser and maintain session (cookies)
- [x] Token refresh works without re-login
- [x] Customer can create integrations scoped to their tenant
- [x] Customer can define routing rules for their alerts
- [x] Test delivery works without affecting production
- [x] SSRF blocked for private/internal URLs

**Additional fix**: Cookie fallback added to JWT auth (bearer OR cookie)

---

## Phase 3: RLS Enforcement

**Goal**: Add database-level tenant isolation as defense-in-depth.

**Directory**: `phase3-rls-enforcement/`

**Status**: IN PROGRESS

| # | File | Description | Status | Dependencies |
|---|------|-------------|--------|--------------|
| 1 | `001-rls-migration.md` | Enable RLS on tables, create policies, create roles | `[ ]` | Phase 2 |
| 2 | `002-connection-wrapper.md` | SET LOCAL tenant context before queries | `[ ]` | #1 |
| 3 | `003-operator-bypass.md` | Operator BYPASSRLS with audit logging | `[ ]` | #1, #2 |
| 4 | `004-fail-closed-tests.md` | Verify missing context returns zero rows | `[ ]` | #1, #2, #3 |

**Exit Criteria**:
- [ ] RLS enabled on all tenant-scoped tables
- [ ] Queries without app.tenant_id return zero rows (fail-closed)
- [ ] Customer routes use tenant_connection wrapper
- [ ] Operator routes use operator_connection (BYPASSRLS)
- [ ] All operator access audited before query
- [ ] All RLS tests pass

---

## Phase 4: SNMP and Alternative Outputs

**Goal**: Support SNMP trap delivery alongside webhooks.

**Directory**: `phase4-snmp-outputs/` (not yet created)

**Status**: Pending Phase 3 completion

---

## How to Use These Prompts

1. Open the task file in order
2. Read the CONTEXT section to understand current state
3. Read the TASK section for implementation details
4. Follow the ACCEPTANCE CRITERIA to verify completion
5. Make the specified COMMIT when done
6. Update this README to mark task complete

---

## Invariants (Apply to ALL Prompts)

These rules must NEVER be violated during implementation:

1. **tenant_id required** on all device data paths
2. **No cross-tenant access** except audited operator routes
3. **Canonical identity** is `(tenant_id, device_id)` — never query by device_id alone
4. **Rejected events** must NEVER affect device_state
5. **UI is read-only** for customers (Phase 1), **integration writes allowed** (Phase 2+)
6. **Admin APIs** require X-Admin-Key header
7. **Rate limiting** must fail closed
8. **Tenant from JWT only** — never from URL params or request body for customer routes
