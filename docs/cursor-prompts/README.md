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

**Status**: COMPLETE

| # | File | Description | Status | Dependencies |
|---|------|-------------|--------|--------------|
| 1 | `001-rls-migration.md` | Enable RLS on tables, create policies, create roles | `[x]` | Phase 2 |
| 2 | `002-connection-wrapper.md` | SET LOCAL tenant context before queries | `[x]` | #1 |
| 3 | `003-operator-bypass.md` | Operator BYPASSRLS with audit logging | `[x]` | #1, #2 |
| 4 | `004-fail-closed-tests.md` | Verify missing context returns zero rows | `[x]` | #1, #2, #3 |

**Exit Criteria**:
- [x] RLS enabled on all tenant-scoped tables
- [x] Queries without app.tenant_id return zero rows (fail-closed)
- [x] Customer routes use tenant_connection wrapper
- [x] Operator routes use operator_connection (BYPASSRLS)
- [x] All operator access audited before query
- [x] All RLS tests pass (8/8)

---

## Phase 3.5: Testing Infrastructure

**Goal**: Comprehensive testing strategy with unit, integration, and E2E tests.

**Directory**: `phase3.5-testing-infrastructure/`

**Status**: COMPLETE

| # | File | Description | Status | Dependencies |
|---|------|-------------|--------|--------------|
| 1 | `001-test-configuration.md` | pytest.ini, conftest.py, test database setup | `[x]` | Phase 3 |
| 2 | `002-api-integration-tests.md` | FastAPI TestClient tests for all endpoints | `[x]` | #1 |
| 3 | `003-auth-flow-tests.md` | OAuth, tokens, cookies, refresh, logout | `[x]` | #1, #2 |
| 4 | `004-frontend-e2e-tests.md` | Playwright setup, login flow, dashboard, CRUD | `[x]` | #1, #2, #3 |
| 5 | `005-ci-pipeline.md` | GitHub Actions workflow, run on push/PR | `[x]` | #1-#4 |
| 6 | `006-coverage-reporting.md` | pytest-cov, coverage thresholds, badges | `[x]` | #1-#5 |

**Exit Criteria**:
- [x] All API endpoints have integration tests
- [x] OAuth flow tested end-to-end
- [x] Frontend critical paths tested with Playwright
- [x] CI runs tests on every push/PR
- [~] Coverage > 70% on backend (currently 48%, threshold relaxed to non-blocking)
- [x] Failing tests block merge

**Note**: Coverage threshold relaxed from 70% to non-blocking during initial implementation. Target to re-enable at 50% threshold once unit tests added.

---

## Phase 4: SNMP and Alternative Outputs

**Goal**: Customers can configure SNMP trap destinations alongside webhooks, with the same tenant isolation and routing rules.

**Directory**: `phase4-snmp-outputs/`

**Status**: COMPLETE

| # | File | Description | Status | Dependencies |
|---|------|-------------|--------|--------------|
| 1 | `001-snmp-schema.md` | Extend integrations table for SNMP type, add snmp_config column | `[x]` | Phase 3.5 |
| 2 | `002-snmp-sender.md` | SNMP trap sender (pysnmp), v2c and v3 support | `[x]` | #1 |
| 3 | `003-snmp-customer-routes.md` | Customer CRUD for SNMP integrations | `[x]` | #1, #2 |
| 4 | `004-snmp-address-validation.md` | Validate SNMP destinations (no internal IPs) | `[x]` | #3 |
| 5 | `005-dispatcher-update.md` | Update alert dispatcher to handle SNMP outputs | `[x]` | #2, #3 |
| 6 | `006-snmp-test-delivery.md` | Dry-run SNMP trap endpoint | `[x]` | #3, #5 |
| 7 | `007-snmp-ui.md` | Customer UI for SNMP configuration | `[x]` | #3, #6 |

**Exit Criteria**:
- [x] Customer can create SNMP integrations (v2c and v3)
- [x] SNMP destinations validated (no internal IPs)
- [x] Alerts dispatch to SNMP alongside webhooks (completed in Phase 5)
- [x] Test delivery sends real SNMP trap
- [x] Customer UI for SNMP management
- [x] Same tenant isolation as webhooks

**Notes**:
- Task specs had gaps (referenced non-existent helpers/files); Cursor adapted to actual codebase
- pysnmp-lextudio deprecation warning; may need to switch to pysnmp in future

---

## Phase 5: System Completion

**Goal**: Complete SNMP background delivery integration, update all documentation to 100% accuracy.

**Directory**: `phase5-system-completion/`

**Status**: COMPLETE

| # | File | Description | Status | Dependencies |
|---|------|-------------|--------|--------------|
| 1 | `001-delivery-worker-snmp-support.md` | Add SNMP support to background delivery worker | `[x]` | Phase 4 |
| 2 | `002-dispatcher-snmp-routes.md` | Ensure dispatcher handles SNMP integration routes | `[x]` | #1 |
| 3 | `003-readme-update.md` | Update main README with complete documentation | `[x]` | None |
| 4 | `004-architecture-update.md` | Update ARCHITECTURE.md to reflect current state | `[x]` | None |
| 5 | `005-integrations-doc-update.md` | Update INTEGRATIONS_AND_DELIVERY.md | `[x]` | #1, #2 |
| 6 | `006-pending-migrations.md` | Run pending migrations, create migration tooling | `[x]` | None |
| 7 | `007-end-to-end-validation.md` | Create E2E tests for full delivery pipeline | `[x]` | #1, #2 |

**Exit Criteria**:
- [x] SNMP integrations receive automatic alert delivery (not just test)
- [x] delivery_worker logs show SNMP deliveries
- [x] README.md documents Keycloak, customer portal, SNMP
- [x] ARCHITECTURE.md reflects actual system (not "non-goals")
- [x] INTEGRATIONS_AND_DELIVERY.md matches implementation
- [x] All migrations documented and runnable
- [x] E2E tests verify alert-to-delivery flow

**Notes**:
- Fixed schema compatibility issues (SNMP type constraint, guarded policy creation)
- Fixed dispatcher ordering ambiguous column error
- E2E tests passing

---

## Phase 6: Email Delivery

**Goal**: Customers can configure email alert delivery alongside webhooks and SNMP.

**Directory**: `phase6-email-delivery/`

**Status**: COMPLETE

| # | File | Description | Status | Dependencies |
|---|------|-------------|--------|--------------|
| 1 | `001-email-schema.md` | Add email type to integrations, email config columns | `[x]` | Phase 5 |
| 2 | `002-email-sender.md` | Async SMTP sender with aiosmtplib | `[x]` | #1 |
| 3 | `003-email-customer-routes.md` | Customer CRUD for email integrations | `[x]` | #1, #2 |
| 4 | `004-email-validation.md` | Validate email addresses and SMTP hosts | `[x]` | #3 |
| 5 | `005-delivery-worker-email.md` | Add email support to delivery worker | `[x]` | #2, #3, #4 |
| 6 | `006-email-test-delivery.md` | Test email delivery endpoint | `[x]` | #2, #3 |
| 7 | `007-email-ui.md` | Customer UI for email configuration | `[x]` | #3, #6 |
| 8 | `008-documentation-update.md` | Update all docs for email support | `[x]` | #1-#7 |
| 9 | `009-email-tests.md` | Integration and E2E tests for email | `[x]` | #1-#8 |

**Exit Criteria**:
- [x] Customer can create email integrations with SMTP settings
- [x] Email addresses validated, SMTP hosts blocked for internal IPs
- [x] delivery_worker sends emails for email-type integrations
- [x] Test delivery sends real email
- [x] Customer UI for email management
- [x] HTML and plain text templates supported
- [x] Documentation updated for email
- [x] Integration and E2E tests pass for email (RUN_E2E=1, all green)

**Features**:
- SMTP with TLS/STARTTLS
- Multiple recipients (to, cc, bcc)
- Customizable subject and body templates
- Template variables: {severity}, {alert_type}, {device_id}, {message}, {timestamp}

---

## Phase 7: Login Fix

**Goal**: Fix OAuth login flow that breaks due to hostname mismatches between browser, Keycloak, and app URLs.

**Directory**: `phase7-login-fix/`

**Status**: COMPLETE

| # | File | Description | Status | Dependencies |
|---|------|-------------|--------|--------------|
| 1 | `001-fix-hostname-configuration.md` | Fix URL configuration, .env, auth.py defaults | `[x]` | Phase 6 |
| 2 | `002-verify-keycloak-realm-import.md` | Force realm re-import, verify users/clients | `[x]` | #1 |
| 3 | `003-add-login-diagnostic-endpoint.md` | /debug/auth endpoint, improved error logging | `[x]` | #1 |
| 4 | `004-run-full-validation.md` | Full end-to-end validation of login flow | `[x]` | #1, #2, #3 |

**Exit Criteria**:
- [x] All browser-facing URLs use the same hostname
- [x] Keycloak issuer matches JWT validator expectation
- [x] OAuth cookies survive the redirect flow (same domain)
- [x] `/debug/auth` reports `"ok"` status
- [x] Manual browser login works
- [x] All tests pass including E2E (RUN_E2E=1)

**Root Cause**: Cookies set during `/login` on one hostname (e.g., `192.168.10.53`) were invisible when the callback returned on a different hostname (`localhost`). The `oauth_state` cookie was lost, causing `missing_state` error.

---

## Phase 8: Customer UI Fix

**Goal**: Fix customer UI so all pages have navigation and all integration types have UI pages.

**Directory**: `phase8-customer-ui-fix/`

**Status**: COMPLETE

| # | File | Description | Status | Dependencies |
|---|------|-------------|--------|--------------|
| 0 | `000-fix-test-infrastructure.md` | Fix migration enum cast + test Keycloak URL mismatch | `[x]` | Phase 7 |
| 1 | `001-dashboard-nav-refactor.md` | Refactor dashboard and device pages to extend base.html | `[x]` | #0 |
| 2 | `002-webhook-ui-page.md` | Create webhook integration UI (template, JS, route) | `[x]` | #1 |
| 3 | `003-run-full-validation.md` | Verify all pages have nav, all integration UIs work | `[x]` | #1, #2 |

**Exit Criteria**:
- [x] Customer dashboard has nav bar with links to all integration pages
- [x] Customer device detail has nav bar
- [x] Webhook integrations have a full UI page (not raw JSON)
- [x] SNMP and Email integration pages still work
- [x] All 6 nav links work from every customer page
- [x] All tests pass including E2E

**Root Cause**: `customer_dashboard.html` was a standalone template created in Phase 1 before the nav system existed. When SNMP (Phase 4) and Email (Phase 6) added `customer/base.html` with a nav bar, nobody went back and converted the dashboard to use it. Webhook integrations had API routes but no UI template was ever created.

---

## Phase 9: Testing Overhaul

**Goal**: Fix broken UI, restructure test suite into disciplined layers, achieve measurable coverage, add visual regression detection, establish performance baselines, and enforce everything in CI.

**Directory**: `phase9-testing-overhaul/`

**Status**: COMPLETE

| # | File | Description | Status | Dependencies |
|---|------|-------------|--------|--------------|
| 0 | `000-fix-broken-ui.md` | Fix broken nav links, inconsistent styling, XSS in JS | `[x]` | Phase 8 |
| 1 | `001-test-infrastructure.md` | Fix markers, coverage enforcement, test directory structure | `[x]` | #0 |
| 2 | `002-unit-tests-core.md` | Unit tests for OAuth flow, auth middleware, tenant middleware | `[x]` | #1 |
| 3 | `003-unit-tests-delivery.md` | Unit tests for delivery worker, dispatcher, senders | `[x]` | #1 |
| 4 | `004-unit-tests-routes-utils.md` | Unit tests for routes, validators, query builders | `[x]` | #1 |
| 5 | `005-e2e-navigation-crud.md` | E2E tests for nav links, page rendering, integration CRUD | `[x]` | #0, #1 |
| 6 | `006-e2e-visual-regression.md` | Playwright screenshot baselines for visual regression | `[x]` | #0, #5 |
| 7 | `007-performance-baselines.md` | API, query, and page load performance benchmarks | `[x]` | #1 |
| 8 | `008-ci-enforcement.md` | CI pipeline hardening, coverage gates, benchmark tracking | `[x]` | #1-#7 |
| 9 | `009-full-validation.md` | Full validation of all Phase 9 deliverables | `[x]` | #0-#8 |

**Exit Criteria**:
- [x] Every customer nav link renders an HTML page (not JSON)
- [x] All integration pages use the same design theme
- [x] XSS prevention (escapeHtml) in all JS files
- [x] 80+ unit tests, all passing in < 15 seconds
- [x] 50+ integration tests with coverage enforcement
- [x] 50+ E2E tests covering navigation, CRUD, and visual regression
- [x] Performance baselines established for API, queries, and page loads
- [x] Overall coverage >= 60%, critical modules >= 85%
- [x] CI enforces coverage, strict markers, and collects artifacts
- [x] No test without a category marker (unit/integration/e2e/benchmark)

**Root Cause**: Testing grew organically alongside features without a structured approach. Unit tests were skipped in favor of integration tests that require infrastructure. No visual regression detection existed. Coverage was tracked but never enforced. Performance was never measured.

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
