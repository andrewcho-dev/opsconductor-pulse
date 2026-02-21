# Phase 140 — Test Coverage Push

## Goal
Push overall test coverage from 45% to 70%+ and critical path coverage from ~20% to 90%+.

## Current State
- 104 test files, 45.85% overall coverage
- Critical modules (auth.py, tenant.py, pool.py, url_validator.py) at ~20%
- CI thresholds: unit=30%, integration=55%
- Coverage config in `pytest.ini`: `--cov=services/ui_iot`

## Testing Patterns (from codebase analysis)

### Unit Tests (mocked DB)
- Use `FakeConn` / `FakePool` for mocking asyncpg
- Use `monkeypatch` + `importlib.import_module` for middleware
- Use `httpx.AsyncClient` with `ASGITransport(app=app)` for route tests
- Use `_mock_customer_deps(monkeypatch, conn)` to set up auth/tenant context
- Markers: `@pytest.mark.unit`, `@pytest.mark.asyncio`

### Integration Tests (real DB + Keycloak)
- Use fixtures: `db_pool`, `clean_db`, `test_tenants`, `client`
- Use session-scoped auth tokens: `customer_a_token`, `operator_token`
- Class-based organization: `class TestCustomerDevices`

### Key Fixtures
- `db_pool` (session) — asyncpg pool to test DB
- `client` (function) — httpx AsyncClient with ASGI transport
- `auth_headers` (function) — `{"Authorization": "Bearer <token>"}`
- `clean_db` (function) — cleans test data before/after

## Execution Order
1. `001-auth-middleware.md` — auth.py to 90%+
2. `002-tenant-middleware.md` — tenant.py to 90%+
3. `003-db-pool-url-validator.md` — pool.py and url_validator.py to 90%+
4. `004-devices-routes.md` — devices route coverage to 70%+
5. `005-alerts-routes.md` — alerts/alert-rules routes to 70%+
6. `006-users-billing-notifications.md` — users, billing, notifications to 70%+
7. `007-ota-certs-escalation.md` — OTA, certificates, escalation to 60%+
8. `008-integration-tests.md` — key workflow integration tests
9. `009-ci-coverage-gate.md` — CI pipeline coverage enforcement

## Verification (after all tasks)
```bash
pytest tests/ --cov=services/ui_iot --cov-report=term-missing
# Overall: >= 70%
pytest tests/ --cov=services/ui_iot/middleware/auth.py
# auth.py: >= 90%
```
