---
last-verified: 2026-02-20
sources:
  - tests/conftest.py
  - tests/coverage_requirements.md
  - pytest.ini
phases: [9, 40, 100, 140, 141, 142, 200, 203, 206]
---

# Testing

> Test strategy, running tests, and coverage requirements.

## Test Structure

- `tests/unit/` — Unit tests (fast; DB/external services are mocked)
- `tests/integration/` — Integration tests (require running Postgres/Keycloak stack)
- `tests/e2e/` — End-to-end browser tests

Unit test rule:

- Unit tests must never require a live PostgreSQL connection.
- If a test needs real DB state, it must be marked as integration.
- Route/service unit tests should mock DB acquisition paths at the dependency boundary.

## Running Tests

### Unit Tests

```bash
pytest tests/unit/ -m unit -q
```

### With Coverage

```bash
pytest -o addopts='' tests/unit/ -m unit --cov=services --cov-report=term-missing -q
```

### Frontend Type Check

```bash
cd frontend && npx tsc --noEmit
```

### Frontend Build

```bash
cd frontend && npm run build
```

## Coverage Requirements

Minimums (enforced in CI):

- Overall: 70%
- Critical paths: 90%

### Critical Path Modules (90%+)

- `services/ui_iot/middleware/auth.py`
- `services/ui_iot/middleware/tenant.py`
- `services/ui_iot/db/pool.py`
- `services/ui_iot/utils/url_validator.py`

Coverage collection scope also includes:

- `services/evaluator_iot` (initial threshold target: 30%, long-term 60%+)
- `services/ingest_iot` (initial threshold target: 30%, long-term 60%+)
- `services/shared` (initial threshold target: 60%, long-term 75%+)

### Exemptions

- `*/migrations/*`
- `*/tests/*`
- `*/__pycache__/*`

## Test Configuration

### conftest.py

`tests/conftest.py` sets up the unit test environment by:

- Setting default env vars required at import time (`PG_PASS`, `KEYCLOAK_ADMIN_PASSWORD`, `DATABASE_URL`, `ADMIN_KEY`)
- Managing `sys.path` so both `routes/*` and `services/*` imports resolve consistently
- Providing shared fixtures (FastAPI client, auth helpers, DB mocks)

### pytest markers

- `@pytest.mark.unit` — fast tests, no external dependencies
- `@pytest.mark.integration` — integration tests requiring infrastructure
- `@pytest.mark.e2e` — browser/system tests

### FakeConn / FakePool (unit DB isolation)

- `tests/conftest.py` provides `FakeConn`, `FakePool`, and the `mock_conn` fixture.
- Use `mock_conn.set_response("fetchrow", fake_tenant())` (etc.) to pre-wire DB calls.
- Factories live in `tests/factories.py` (`fake_tenant`, `fake_device`, `fake_device_plan`, `fake_site`, `fake_alert`).
- For multiple sequential responses, set a list: `mock_conn.fetchrow_results = [fake_tenant(), fake_device_plan()]`.
- For async side effects, replace the method: `mock_conn.fetchrow = AsyncMock(side_effect=[...])`.
- Route tests should override the DB dependency to return `FakePool(mock_conn)` and avoid live connections.

## Writing New Tests

Common patterns in this repo:

- Use `FakeConn` / `FakePool` patterns for DB isolation.
- Use dependency overrides for FastAPI `Depends(...)` injection.
- Mark new unit tests with `@pytest.mark.unit`.
- Reclassify DB-dependent tests to `@pytest.mark.integration` instead of reaching real DB from unit scope.

## Performance Benchmarks

- Baseline: `benchmarks/baseline.json` (committed)
- Current run: `benchmarks/current.json` (CI artifact, gitignored)
- Regression threshold: 20% slowdown → CI fails
- Comparison script: `scripts/check_benchmark_regression.py`
- To update baseline after intentional perf changes:

```bash
python scripts/update_benchmark_baseline.py
# then commit benchmarks/baseline.json
```

## CI Enforcement

- CI fails if overall coverage drops below the gate.
- Critical modules must maintain higher coverage thresholds.
- New features and behavior changes should add/update tests and the relevant docs.
- MyPy type checks are a blocking CI gate.
- Integration tests should assert specific expected status codes and validate response payload shape.

## See Also

- [Conventions](conventions.md)
- [Operations: Deployment](../operations/deployment.md)

