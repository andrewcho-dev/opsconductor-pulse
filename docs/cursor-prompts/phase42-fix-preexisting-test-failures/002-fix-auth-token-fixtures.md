# Prompt 002 — Fix Auth/Token Mock Fixtures

## Context

Based on the diagnosis from prompt 001, this prompt fixes failures in categories A (JWT token mismatch) and B (role/guard mismatch).

The root issue: the test fixtures that generate mock JWT tokens no longer match what the auth middleware expects. This happens when auth logic evolves (Keycloak issuer changes, role claim path changes, session cookie format changes) but test fixtures are not updated.

## Your Task

**Read the following files first:**
- `tests/unit/conftest.py` — find all mock token / auth fixture functions
- `services/ui_iot/auth.py` (or wherever JWT validation + role extraction lives) — find the CURRENT logic for:
  - How the bearer token is validated
  - How `tenant_id` is extracted from the token
  - How roles (`customer`, `operator`) are extracted from the token
  - What claims are required (issuer, audience, expiry)
- `services/ui_iot/app.py` — find how auth middleware is mounted

**Then fix the mock fixtures:**

1. Update `conftest.py` mock token generation to produce tokens that match the CURRENT auth middleware expectations:
   - Correct claim structure for roles
   - Correct claim for `tenant_id`
   - Correct issuer / audience (or mock the JWKS validation to skip signature checking — the tests should already do this)

2. If `RequireCustomer` / `RequireOperator` guards changed how they extract roles, update the mock tokens to match. Do NOT change the guards themselves — just align the mocks.

3. If the session cookie name or format changed, update the test fixtures to use the correct cookie.

4. Do NOT add new test cases in this prompt — only fix existing fixture mocks.

## Acceptance Criteria

- [ ] `pytest tests/unit/test_customer_route_handlers.py -v` — failures from category A/B are resolved
- [ ] `pytest tests/unit/test_operator_route_handlers.py -v` — failures from category A/B are resolved
- [ ] Mocks in `conftest.py` match the CURRENT auth.py / middleware expectations exactly
- [ ] No changes to production auth code — only test fixtures
