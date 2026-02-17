---
last-verified: 2026-02-17
sources:
  - tests/conftest.py
  - tests/coverage_requirements.md
  - pytest.ini
phases: [9, 40, 100, 140, 141, 142]
---

# Testing

> Test strategy, running tests, and coverage requirements.

## Test Structure

- `tests/unit/` — Unit tests (fast; DB/external services are mocked)
- `tests/integration/` — Integration tests (require running Postgres/Keycloak stack)
- `tests/e2e/` — End-to-end browser tests

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

## Writing New Tests

Common patterns in this repo:

- Use `FakeConn` / `FakePool` patterns for DB isolation.
- Use dependency overrides for FastAPI `Depends(...)` injection.
- Mark new unit tests with `@pytest.mark.unit`.

## CI Enforcement

- CI fails if overall coverage drops below the gate.
- Critical modules must maintain higher coverage thresholds.
- New features and behavior changes should add/update tests and the relevant docs.

## See Also

- [Conventions](conventions.md)
- [Operations: Deployment](../operations/deployment.md)

