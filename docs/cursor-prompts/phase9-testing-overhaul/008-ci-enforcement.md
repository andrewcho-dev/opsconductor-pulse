# Task 008: CI Enforcement and Hardening

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> This task makes the CI pipeline enforce the quality standards established in previous tasks.
> Tests must pass before and after CI changes.

---

## Context

Currently the CI pipeline has gaps:
- Coverage failures don't block merges (check_coverage.py exits 0)
- No performance regression detection in CI
- Visual regression screenshots aren't compared in CI
- No summary report of test results
- The pipeline doesn't enforce that every test has a marker

Task 001 fixed `check_coverage.py` and `.coveragerc`, but the CI workflow itself needs updating to use these properly and to add the new test categories.

**Read first**:
- `.github/workflows/test.yml` (current CI workflow)
- `scripts/check_coverage.py` (updated in task 001)
- `pytest.ini` (markers)
- `.github/BRANCH_PROTECTION.md` (current branch rules)

---

## Task

### 8.1 Update CI workflow for new test categories

Rewrite `.github/workflows/test.yml` to handle all test categories properly:

```yaml
name: Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  unit-tests:
    name: Unit Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install -r services/ui_iot/requirements.txt
          pip install -r requirements-test.txt

      - name: Run unit tests
        run: pytest -m unit -v --tb=short --junitxml=test-results/unit.xml

      - name: Upload unit test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: unit-test-results
          path: test-results/unit.xml

  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: iotcloud_test
          POSTGRES_USER: iot
          POSTGRES_PASSWORD: iot_dev
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U iot -d iotcloud_test"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10

      keycloak:
        image: quay.io/keycloak/keycloak:24.0
        env:
          KEYCLOAK_ADMIN: admin
          KEYCLOAK_ADMIN_PASSWORD: admin_dev
          KC_DB: postgres
          KC_DB_URL: jdbc:postgresql://postgres:5432/iotcloud_test
          KC_DB_USERNAME: iot
          KC_DB_PASSWORD: iot_dev
          KC_HOSTNAME_URL: http://localhost:8180
          KC_HTTP_ENABLED: "true"
        ports:
          - 8180:8080
        options: >-
          --health-cmd "curl -sf http://localhost:8080/health/ready || exit 1"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 30
          --health-start-period 60s

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install -r services/ui_iot/requirements.txt
          pip install -r requirements-test.txt

      - name: Wait for Keycloak
        run: |
          for i in $(seq 1 30); do
            curl -sf http://localhost:8180/realms/master && break
            echo "Waiting for Keycloak... ($i)"
            sleep 5
          done

      - name: Run database migrations
        run: |
          for f in db/migrations/*.sql; do
            PGPASSWORD=iot_dev psql -h localhost -U iot -d iotcloud_test -f "$f" || true
          done

      - name: Run integration tests with coverage
        env:
          KEYCLOAK_URL: http://localhost:8180
          TEST_DATABASE_URL: postgresql://iot:iot_dev@localhost:5432/iotcloud_test
        run: >
          pytest -m integration -v --tb=short
          --cov=services/ui_iot --cov=services/dispatcher --cov=services/delivery_worker
          --cov-report=xml --cov-report=term-missing
          --junitxml=test-results/integration.xml

      - name: Enforce coverage thresholds
        run: python scripts/check_coverage.py

      - name: Upload coverage
        if: always()
        uses: codecov/codecov-action@v4
        with:
          file: coverage.xml
          fail_ci_if_error: false

      - name: Upload integration test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: integration-test-results
          path: test-results/integration.xml

  e2e-tests:
    name: E2E Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install -r services/ui_iot/requirements.txt
          pip install -r requirements-test.txt
          playwright install chromium

      - name: Start services
        run: |
          cd compose
          docker compose up -d
          cd ..

      - name: Wait for services
        run: |
          echo "Waiting for UI..."
          for i in $(seq 1 30); do
            curl -sf http://localhost:8080/login && break
            sleep 5
          done
          echo "Waiting for Keycloak..."
          for i in $(seq 1 30); do
            curl -sf http://localhost:8180/realms/pulse && break
            sleep 5
          done

      - name: Run E2E tests
        env:
          KEYCLOAK_URL: http://localhost:8180
          UI_BASE_URL: http://localhost:8080
          RUN_E2E: "1"
        run: >
          pytest -m e2e -v --tb=short
          --junitxml=test-results/e2e.xml

      - name: Upload E2E test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: e2e-test-results
          path: test-results/e2e.xml

      - name: Upload Playwright traces on failure
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-traces
          path: test-results/

      - name: Collect container logs on failure
        if: failure()
        run: |
          cd compose
          docker compose logs ui > ../test-results/ui.log 2>&1
          docker compose logs keycloak > ../test-results/keycloak.log 2>&1
          cd ..

      - name: Upload container logs on failure
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: container-logs
          path: test-results/*.log

      - name: Cleanup
        if: always()
        run: |
          cd compose
          docker compose down -v
          cd ..

  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install linters
        run: pip install ruff mypy

      - name: Ruff check
        run: ruff check services/

      - name: Ruff format check
        run: ruff format --check services/

      - name: Type check (non-blocking)
        run: mypy services/ui_iot --ignore-missing-imports || true
```

### 8.2 Add benchmark job (non-blocking, tracking only)

Add a benchmark job to the workflow that runs on `main` pushes (not PRs — benchmarks are noisy on shared CI):

```yaml
  benchmarks:
    name: Performance Benchmarks
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    needs: [unit-tests, integration-tests]
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: iotcloud_test
          POSTGRES_USER: iot
          POSTGRES_PASSWORD: iot_dev
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U iot -d iotcloud_test"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10

      keycloak:
        image: quay.io/keycloak/keycloak:24.0
        env:
          KEYCLOAK_ADMIN: admin
          KEYCLOAK_ADMIN_PASSWORD: admin_dev
          KC_DB: postgres
          KC_DB_URL: jdbc:postgresql://postgres:5432/iotcloud_test
          KC_DB_USERNAME: iot
          KC_DB_PASSWORD: iot_dev
          KC_HOSTNAME_URL: http://localhost:8180
          KC_HTTP_ENABLED: "true"
        ports:
          - 8180:8080
        options: >-
          --health-cmd "curl -sf http://localhost:8080/health/ready || exit 1"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 30
          --health-start-period 60s

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install -r services/ui_iot/requirements.txt
          pip install -r requirements-test.txt

      - name: Run database migrations
        run: |
          for f in db/migrations/*.sql; do
            PGPASSWORD=iot_dev psql -h localhost -U iot -d iotcloud_test -f "$f" || true
          done

      - name: Run benchmarks
        env:
          KEYCLOAK_URL: http://localhost:8180
          TEST_DATABASE_URL: postgresql://iot:iot_dev@localhost:5432/iotcloud_test
        run: >
          pytest -m benchmark -v
          --benchmark-json=benchmark_results.json
          --benchmark-enable

      - name: Upload benchmark results
        uses: actions/upload-artifact@v4
        with:
          name: benchmark-results
          path: benchmark_results.json
```

### 8.3 Add marker enforcement

In `pytest.ini`, ensure strict markers are enforced:
```ini
addopts = --strict-markers
```

This makes pytest fail if any test uses an undefined marker.

### 8.4 Update branch protection documentation

Update `.github/BRANCH_PROTECTION.md` to reflect the new CI requirements:

```markdown
## Required Status Checks

The following checks must pass before merging to main:

- **Unit Tests** — all unit tests pass (no infrastructure required)
- **Integration Tests** — all integration tests pass with coverage enforcement
- **E2E Tests** — all end-to-end browser tests pass
- **Lint** — ruff check and format check pass

## Coverage Requirements

- Overall: 60% minimum (enforced by check_coverage.py)
- Critical modules: 85-90% (auth.py, tenant.py, pool.py, url_validator.py)

## Performance Benchmarks

- Run on main pushes (not PRs)
- Results uploaded as artifacts for tracking
- Not blocking — used for trend analysis
```

---

## Files to Modify

| Action | Path |
|--------|------|
| MODIFY | `.github/workflows/test.yml` |
| MODIFY | `pytest.ini` |
| MODIFY | `.github/BRANCH_PROTECTION.md` |

---

## Test

```bash
# 1. Verify strict markers are enforced
pytest --collect-only -q 2>&1 | grep -i "error\|warning" || echo "No marker errors"

# 2. Verify all tests have markers (this should find 0 unmarked tests)
pytest --collect-only tests/ --ignore=tests/e2e -q 2>&1 | tail -5

# 3. Run unit tests
pytest -m unit -v

# 4. Run integration tests with coverage
source compose/.env
KEYCLOAK_URL=http://${HOST_IP}:8180 pytest -m integration -v --cov=services/ui_iot --cov-report=term-missing

# 5. Verify coverage enforcement
python scripts/check_coverage.py

# 6. Validate workflow YAML syntax
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/test.yml'))" && echo "YAML valid"
```

---

## Acceptance Criteria

- [ ] CI workflow has 5 jobs: unit-tests, integration-tests, e2e-tests, lint, benchmarks
- [ ] Coverage enforcement step runs `check_coverage.py` and blocks on failure
- [ ] Benchmark job runs only on main pushes, not PRs
- [ ] All test results uploaded as artifacts (JUnit XML)
- [ ] Container logs collected on E2E failure
- [ ] Playwright traces uploaded on E2E failure
- [ ] `--strict-markers` in pytest.ini
- [ ] Workflow YAML is valid
- [ ] BRANCH_PROTECTION.md documents all requirements
- [ ] All existing tests still pass

---

## Commit

```
Harden CI pipeline with coverage enforcement and benchmarks

- Rewrite test workflow with 5 jobs (unit, integration, e2e, lint, benchmarks)
- Coverage thresholds enforced — CI fails below 60%
- Benchmark job tracks performance on main pushes
- Test results uploaded as JUnit XML artifacts
- Container logs and Playwright traces captured on failure
- Strict markers enforced — no test without a category

Part of Phase 9: Testing Overhaul
```
