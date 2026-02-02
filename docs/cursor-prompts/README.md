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

| # | File | Description | Status | Dependencies |
|---|------|-------------|--------|--------------|
| 1 | `001-keycloak-setup.md` | Add Keycloak to Docker Compose, create realm config | `[ ]` | None |
| 2 | `002-jwt-middleware.md` | JWT validation, JWKS fetching, token verification | `[ ]` | #1 |
| 3 | `003-tenant-enforcement.md` | Context vars, tenant helpers, query builders | `[ ]` | #2 |
| 4 | `004-customer-routes.md` | /customer/* routes with tenant scoping | `[ ]` | #2, #3 |
| 5 | `005-operator-routes.md` | /operator/* routes with audit logging | `[ ]` | #2, #3 |
| 6 | `006-app-refactor.md` | Mount routers, deprecate unsafe routes | `[ ]` | #4, #5 |
| 7 | `007-templates.md` | Customer dashboard template, operator UI updates | `[ ]` | #4, #5 |
| 8 | `008-audit-migration.md` | operator_audit_log table | `[ ]` | None (can run early) |

**Exit Criteria**:
- [ ] Customer can login via Keycloak and see only their tenant's data
- [ ] Operator can login and see cross-tenant view with audit trail
- [ ] No queries use device_id without tenant_id
- [ ] All customer routes return 401/403 for invalid/missing tokens
- [ ] Old /device/{device_id} returns 410 Gone

---

## Phase 2: Customer Integration Management

**Goal**: Customers can create/manage their own webhook integrations.

**Directory**: `phase2-integration-management/` (not yet created)

**Status**: Pending Phase 1 completion

---

## Phase 3: RLS Enforcement

**Goal**: Add database-level tenant isolation as defense-in-depth.

**Directory**: `phase3-rls-enforcement/` (not yet created)

**Status**: Pending Phase 2 completion

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
5. **UI is read-only** for customers (Phase 1-2)
6. **Admin APIs** require X-Admin-Key header
7. **Rate limiting** must fail closed
8. **Tenant from JWT only** — never from URL params or request body for customer routes
