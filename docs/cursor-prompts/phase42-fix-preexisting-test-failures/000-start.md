# Phase 42: Fix Pre-Existing Unit Test Failures

## Why This Phase Comes Before ui_iot Extraction

Phase 41 is complete. `pytest -m unit -v` reports **58 pre-existing failures** in:
- `tests/unit/test_customer_route_handlers.py`
- `tests/unit/test_operator_route_handlers.py`
- `tests/unit/test_tenant_middleware.py`

All failures are auth/403-related. These are NOT from Phase 41 changes — they pre-date it. However, we cannot proceed to Phase 43 (ui_iot service extraction) with a broken test suite. When we refactor ui_iot, we need tests that actually catch regressions.

**The rule: `pytest -m unit -v` must be 0 failures before any architectural refactor.**

## What Likely Caused These Failures

These tests cover customer routes, operator routes, and tenant middleware — the core of `services/ui_iot/`. Auth/403 failures in unit tests typically mean one of:

1. **JWT/token mock is stale** — the auth middleware changed (e.g., Keycloak issuer, token claims, session cookie format) and the test fixtures were not updated to match
2. **Role extraction changed** — `RequireOperator` / `RequireCustomer` guards may have changed how they extract roles from the JWT, and the mock tokens don't match the new expectation
3. **Middleware order changed** — a middleware was added/reordered in `app.py` that intercepts requests before the route handler, returning 403 before the mock is applied
4. **FakePool/FakeConn schema mismatch** — the route handlers now expect new DB columns or query shapes that the fake DB doesn't return

## Execution Order

| Prompt | Description | Priority |
|--------|-------------|----------|
| 001 | Diagnose the 58 failures — categorize by root cause | CRITICAL |
| 002 | Fix auth/token mock fixtures | CRITICAL |
| 003 | Fix tenant middleware test failures | CRITICAL |
| 004 | Verify full suite passes: 0 failures | CRITICAL |

## Verification After All Prompts Complete

```bash
pytest -m unit -v 2>&1 | tail -20
```

Expected: all tests pass, 0 failures, 0 errors.

## Key Files

- `tests/unit/test_customer_route_handlers.py`
- `tests/unit/test_operator_route_handlers.py`
- `tests/unit/test_tenant_middleware.py`
- `tests/unit/conftest.py` — shared fixtures including mock tokens
- `services/ui_iot/app.py` — middleware stack
- `services/ui_iot/routes/customer.py` — customer route handlers
- `services/ui_iot/routes/operator.py` — operator route handlers
- `services/ui_iot/middleware/` or equivalent — auth/tenant middleware
