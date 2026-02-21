# Prompt 006 — Unit Tests

## Note

This phase is frontend-only — no new backend endpoints. Unit tests focus on verifying the API client functions are correctly typed and that key components render without errors.

## File: `tests/unit/test_operator_frontend.py`

These are lightweight smoke tests for the operator API client shapes:

Since the frontend is TypeScript and unit tests are Python (pytest), this file verifies that the operator backend endpoints that the frontend calls actually exist and return expected shapes.

Tests using `@pytest.mark.unit` and `@pytest.mark.asyncio` with FakeConn/FakePool:

1. `test_operator_tenants_endpoint_exists` — GET /operator/tenants returns list with `tenants` key
2. `test_operator_tenant_stats_endpoint_exists` — GET /operator/tenants/{id}/stats returns stats
3. `test_operator_subscriptions_endpoint_exists` — GET /operator/subscriptions returns list
4. `test_operator_audit_log_endpoint_exists` — GET /operator/audit-log returns events
5. `test_create_tenant_endpoint_exists` — POST /operator/tenants with name → created
6. `test_create_subscription_endpoint_exists` — POST /operator/subscriptions → created

All `@pytest.mark.unit` and `@pytest.mark.asyncio`.

## Acceptance Criteria

- [ ] 6 tests pass under `pytest -m unit -v`
- [ ] No existing tests broken
