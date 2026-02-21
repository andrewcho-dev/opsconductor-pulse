# Prompt 003 — Fix Middleware and FakeConn/FakePool Failures

## Context

This prompt fixes failures in categories C (middleware ordering) and D (FakeConn/FakePool data mismatch) identified in prompt 001. It runs after prompt 002.

## Your Task

### Part 1: Fix middleware ordering failures (Category C)

If failures are caused by a middleware added to `app.py` that intercepts requests before the route handler runs:

**Read:**
- `services/ui_iot/app.py` — find all middleware in the stack in order
- The failing test functions — find what request they send and what they expect

**Fix:**
- If a new middleware (e.g., rate limiting, tenant validation, subscription check) was added since the tests were written and now returns 403 before the route runs, update the test to either:
  - Mock the new middleware's dependency (e.g., mock the subscription check to return ACTIVE)
  - OR add the required header/cookie that the middleware needs to pass through

Do NOT disable or remove middleware. Fix the tests to work with the full middleware stack.

### Part 2: Fix FakeConn/FakePool data mismatches (Category D)

If failures are caused by route handlers querying columns/tables that FakeConn doesn't return:

**Read:**
- The failing test's FakeConn setup — find what rows/columns it returns
- The route handler being tested — find what it queries and what columns it expects

**Fix:**
- Update FakeConn mock data in the failing tests to include any new columns added to the queries since the tests were written
- If a route now joins a new table, add the join result to FakeConn

### Part 3: Fix any remaining categories (E, F)

- For import errors (Category E): fix the import — update module paths if a module was moved/renamed during Phase 41
- For other failures (Category F): read the specific error and fix the root cause

## Acceptance Criteria

- [ ] `pytest tests/unit/test_tenant_middleware.py -v` — all tests pass
- [ ] `pytest tests/unit/test_customer_route_handlers.py tests/unit/test_operator_route_handlers.py -v` — all remaining failures resolved
- [ ] No production code changed — only test fixtures and mocks
- [ ] Each fix has a brief inline comment explaining why the mock was updated
