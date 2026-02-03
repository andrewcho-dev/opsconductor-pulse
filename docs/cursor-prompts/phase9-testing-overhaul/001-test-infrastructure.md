# Task 001: Test Infrastructure Overhaul

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> This task fixes the structural problems in the test suite so subsequent tasks can build on a solid foundation.
> RUN THE TESTS in the Test section. Do not proceed if tests fail.

---

## Context

The test suite has structural problems that undermine its reliability:

1. `test_rls_enforcement.py` has no pytest marker — it doesn't run in CI under `pytest -m integration`
2. `test_delivery_e2e.py` is confusingly named (it's not E2E) and has duplicate fixtures
3. `check_coverage.py` exits 0 even when coverage fails — it never blocks anything
4. `.coveragerc` has `fail_under = 0` — coverage is advisory only
5. No `requirements-test.txt` — test dependencies are scattered across workflow YAML and service requirements
6. No pytest-benchmark for performance baselines (added in later task)

**Read first**:
- `pytest.ini`
- `.coveragerc`
- `scripts/check_coverage.py`
- `tests/test_rls_enforcement.py` (look for missing marker)
- `tests/integration/test_delivery_e2e.py` (fixture duplication, naming)
- `tests/conftest.py` (main fixtures)
- `.github/workflows/test.yml`

---

## Task

### 1.1 Fix missing marker on RLS tests

In `tests/test_rls_enforcement.py`, add the integration marker at module level:

```python
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]
```

Remove individual `@pytest.mark.asyncio` decorators from each test function (the module-level marker covers them).

### 1.2 Rename and clean up delivery pipeline tests

Rename the file:
```bash
mv tests/integration/test_delivery_e2e.py tests/integration/test_delivery_pipeline.py
```

In the renamed file:
- Remove the duplicate `db_pool` and `test_tenant` fixture definitions (lines ~596-620). These duplicate fixtures from `conftest.py` and can cause conflicts.
- Ensure the file uses `db_pool` and `test_tenants` from the main `conftest.py` instead.
- If the file defines its own database connection logic, refactor to use the shared `db_pool` fixture.

### 1.3 Create `requirements-test.txt`

Create `requirements-test.txt` in the project root:

```
# Test dependencies — install with: pip install -r requirements-test.txt
# Assumes service dependencies are already installed

# Test framework
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0

# HTTP testing
httpx>=0.27.0
respx>=0.20.0

# Browser testing
playwright>=1.40.0
pytest-playwright>=0.4.0

# Performance benchmarking
pytest-benchmark>=4.0.0

# Mocking (stdlib unittest.mock is sufficient, but this adds convenience)
# No extra dependency needed — unittest.mock is in stdlib
```

### 1.4 Fix `check_coverage.py` to actually enforce thresholds

Modify `scripts/check_coverage.py`:
- Change `sys.exit(0)` on line 65 to `sys.exit(1)` — make coverage failures actually fail
- Update `OVERALL_MINIMUM` from 70 to 60 (realistic starting target given current 52.6%)
- Add the new critical modules that need coverage:

```python
CRITICAL_MODULES = {
    "services/ui_iot/middleware/auth.py": 85,
    "services/ui_iot/middleware/tenant.py": 85,
    "services/ui_iot/db/pool.py": 85,
    "services/ui_iot/utils/url_validator.py": 80,
    "services/ui_iot/utils/snmp_validator.py": 75,
    "services/ui_iot/utils/email_validator.py": 80,
}

OVERALL_MINIMUM = 60
```

### 1.5 Fix `.coveragerc` threshold

In `.coveragerc`, change:
```ini
fail_under = 60
```

### 1.6 Add `pytest-benchmark` to pytest.ini

Add the benchmark marker to pytest.ini:
```ini
markers =
    unit: Unit tests (fast, no external dependencies)
    integration: Integration tests (require database)
    e2e: End-to-end tests (require running services)
    slow: Slow tests (skip with -m "not slow")
    benchmark: Performance benchmark tests
```

### 1.7 Organize test directory structure

Ensure the test directory follows this structure:
```
tests/
├── conftest.py                    # Shared fixtures
├── unit/                          # Fast, no infrastructure
│   ├── __init__.py
│   ├── test_email_validator.py
│   ├── test_snmp_validator.py
│   ├── test_url_validator.py      # NEW (task 004)
│   ├── test_email_sender.py
│   ├── test_snmp_sender.py
│   ├── test_alert_dispatcher.py
│   ├── test_oauth_flow.py         # NEW (task 002)
│   ├── test_worker_logic.py       # NEW (task 003)
│   └── test_dispatcher_logic.py   # NEW (task 003)
├── integration/                   # Needs Postgres + Keycloak
│   ├── __init__.py
│   ├── test_delivery_pipeline.py  # RENAMED from test_delivery_e2e.py
│   ├── test_email_routes.py
│   └── test_rls_enforcement.py    # MOVED from tests/ root
├── api/                           # API endpoint tests (integration)
│   ├── __init__.py
│   ├── test_auth.py
│   ├── test_customer_routes.py
│   ├── test_operator_routes.py
│   └── test_deprecated_routes.py
├── e2e/                           # Full stack browser tests
│   ├── conftest.py
│   ├── test_login_flow.py
│   ├── test_customer_dashboard.py
│   ├── test_operator_dashboard.py
│   ├── test_integrations.py
│   ├── test_navigation.py         # NEW (task 005)
│   └── test_visual_regression.py  # NEW (task 006)
├── benchmarks/                    # Performance tests
│   ├── __init__.py
│   ├── test_api_performance.py    # NEW (task 007)
│   └── test_query_performance.py  # NEW (task 007)
├── fixtures/
│   └── __init__.py
└── helpers/
    ├── __init__.py
    └── auth.py
```

Move `test_rls_enforcement.py`:
```bash
mv tests/test_rls_enforcement.py tests/integration/test_rls_enforcement.py
```

Create placeholder `__init__.py` for new directories:
```bash
touch tests/benchmarks/__init__.py
```

### 1.8 Update CI workflow

In `.github/workflows/test.yml`, update the integration test job:

**Add coverage enforcement step** after the pytest run:
```yaml
    - name: Check coverage thresholds
      run: python scripts/check_coverage.py
```

**Update the unit test job** to also install from `requirements-test.txt`:
```yaml
    - name: Install dependencies
      run: |
        pip install -r services/ui_iot/requirements.txt
        pip install -r requirements-test.txt
```

Do the same for integration and e2e jobs.

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `requirements-test.txt` |
| CREATE | `tests/benchmarks/__init__.py` |
| MODIFY | `tests/test_rls_enforcement.py` → MOVE to `tests/integration/` |
| MODIFY | `tests/integration/test_delivery_e2e.py` → RENAME to `test_delivery_pipeline.py` |
| MODIFY | `scripts/check_coverage.py` |
| MODIFY | `.coveragerc` |
| MODIFY | `pytest.ini` |
| MODIFY | `.github/workflows/test.yml` |

---

## Test

```bash
# 1. Install test dependencies
pip install -r requirements-test.txt

# 2. Verify RLS tests now run under integration marker
pytest -m integration --collect-only -q tests/integration/test_rls_enforcement.py

# 3. Verify delivery pipeline tests still run
pytest -m integration --collect-only -q tests/integration/test_delivery_pipeline.py

# 4. Verify all markers are assigned (no unmarked tests)
pytest --collect-only -q tests/ --ignore=tests/e2e 2>&1 | tail -5

# 5. Run all unit tests
pytest -m unit -v --tb=short

# 6. Run all integration tests
source compose/.env
KEYCLOAK_URL=http://${HOST_IP}:8180 pytest -m integration -v --tb=short -x

# 7. Verify check_coverage.py reports correctly (may fail threshold — that's expected until unit tests are added)
python scripts/check_coverage.py || echo "Coverage below threshold (expected until tasks 002-004 complete)"
```

---

## Acceptance Criteria

- [ ] `test_rls_enforcement.py` has `pytest.mark.integration` and is in `tests/integration/`
- [ ] `test_delivery_e2e.py` renamed to `test_delivery_pipeline.py`, no duplicate fixtures
- [ ] `requirements-test.txt` exists with all test dependencies including pytest-benchmark
- [ ] `check_coverage.py` exits non-zero when coverage is below threshold
- [ ] `.coveragerc` has `fail_under = 60`
- [ ] `pytest.ini` has `benchmark` marker defined
- [ ] `tests/benchmarks/` directory exists
- [ ] CI workflow installs from `requirements-test.txt`
- [ ] CI workflow runs `check_coverage.py` after integration tests
- [ ] All existing tests still pass (unit + integration)
- [ ] No tests exist without a category marker (unit/integration/e2e/benchmark)

---

## Commit

```
Overhaul test infrastructure and enforce coverage

- Fix missing pytest.mark.integration on RLS tests
- Rename test_delivery_e2e.py to test_delivery_pipeline.py
- Remove duplicate fixtures from delivery pipeline tests
- Create requirements-test.txt with all test dependencies
- Make check_coverage.py actually fail (exit 1) below threshold
- Set .coveragerc fail_under=60 (realistic starting target)
- Add benchmark marker to pytest.ini
- Reorganize test directory structure
- Update CI to install from requirements-test.txt and enforce coverage

Part of Phase 9: Testing Overhaul
```
