# Task 005: CI Pipeline

> **CURSOR: EXECUTE THIS TASK**
>
> This is an implementation task. Read the instructions below and implement them.
> Modify the files listed in "Files to Create/Modify" section.
> Follow the acceptance criteria to verify your work.
> Commit with the message in the "Commit" section when done.

---

## Context

We need a CI pipeline to run tests automatically on every push and pull request. GitHub Actions is the recommended solution for GitHub-hosted repositories.

**Read first**:
- `pytest.ini` (test configuration)
- `scripts/run_tests.sh` (test runner)
- GitHub Actions documentation

**Depends on**: Tasks 001-004

## Task

### 5.1 Create GitHub Actions workflow

Create `.github/workflows/test.yml`:

```yaml
name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

env:
  PYTHON_VERSION: "3.11"
  POSTGRES_USER: iot
  POSTGRES_PASSWORD: iot_dev
  POSTGRES_DB: iotcloud_test

jobs:
  # ============================================
  # Unit Tests (fast, no services needed)
  # ============================================
  unit-tests:
    name: Unit Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: "pip"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r services/ui_iot/requirements.txt
          pip install pytest pytest-asyncio pytest-cov

      - name: Run unit tests
        run: |
          pytest -m unit -v --tb=short

  # ============================================
  # Integration Tests (require database)
  # ============================================
  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: ${{ env.POSTGRES_USER }}
          POSTGRES_PASSWORD: ${{ env.POSTGRES_PASSWORD }}
          POSTGRES_DB: ${{ env.POSTGRES_DB }}
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      keycloak:
        image: quay.io/keycloak/keycloak:24.0
        env:
          KEYCLOAK_ADMIN: admin
          KEYCLOAK_ADMIN_PASSWORD: admin_dev
          KC_DB: postgres
          KC_DB_URL: jdbc:postgresql://postgres:5432/${{ env.POSTGRES_DB }}
          KC_DB_USERNAME: ${{ env.POSTGRES_USER }}
          KC_DB_PASSWORD: ${{ env.POSTGRES_PASSWORD }}
          KC_HOSTNAME_STRICT: "false"
          KC_HTTP_ENABLED: "true"
        ports:
          - 8180:8080
        options: >-
          --health-cmd "curl -f http://localhost:8080/health/ready || exit 1"
          --health-interval 30s
          --health-timeout 10s
          --health-retries 10
          --health-start-period 60s

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: "pip"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r services/ui_iot/requirements.txt
          pip install pytest pytest-asyncio pytest-cov httpx

      - name: Wait for Keycloak
        run: |
          echo "Waiting for Keycloak to be ready..."
          for i in {1..30}; do
            if curl -s http://localhost:8180/health/ready > /dev/null; then
              echo "Keycloak is ready"
              break
            fi
            echo "Waiting... ($i/30)"
            sleep 10
          done

      - name: Import Keycloak realm
        run: |
          # Import realm configuration
          docker exec $(docker ps -q -f ancestor=quay.io/keycloak/keycloak:24.0) \
            /opt/keycloak/bin/kcadm.sh config credentials \
            --server http://localhost:8080 \
            --realm master \
            --user admin \
            --password admin_dev
          # TODO: Import realm-pulse.json

      - name: Run database migrations
        env:
          DATABASE_URL: postgresql://${{ env.POSTGRES_USER }}:${{ env.POSTGRES_PASSWORD }}@localhost:5432/${{ env.POSTGRES_DB }}
        run: |
          for f in db/migrations/*.sql; do
            echo "Running migration: $f"
            PGPASSWORD=${{ env.POSTGRES_PASSWORD }} psql -h localhost -U ${{ env.POSTGRES_USER }} -d ${{ env.POSTGRES_DB }} -f "$f"
          done

      - name: Run integration tests
        env:
          TEST_DATABASE_URL: postgresql://${{ env.POSTGRES_USER }}:${{ env.POSTGRES_PASSWORD }}@localhost:5432/${{ env.POSTGRES_DB }}
          KEYCLOAK_URL: http://localhost:8180
        run: |
          pytest -m integration -v --tb=short --cov=services/ui_iot --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          fail_ci_if_error: false

  # ============================================
  # E2E Tests (require full stack)
  # ============================================
  e2e-tests:
    name: E2E Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: "pip"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r services/ui_iot/requirements.txt
          pip install pytest pytest-asyncio playwright pytest-playwright

      - name: Install Playwright browsers
        run: playwright install chromium

      - name: Start services with Docker Compose
        run: |
          cd compose
          docker compose up -d --build
          echo "Waiting for services to be ready..."
          sleep 60

      - name: Wait for services
        run: |
          # Wait for UI
          for i in {1..30}; do
            if curl -s http://localhost:8080/ > /dev/null; then
              echo "UI is ready"
              break
            fi
            echo "Waiting for UI... ($i/30)"
            sleep 5
          done

          # Wait for Keycloak
          for i in {1..30}; do
            if curl -s http://localhost:8180/health/ready > /dev/null; then
              echo "Keycloak is ready"
              break
            fi
            echo "Waiting for Keycloak... ($i/30)"
            sleep 5
          done

      - name: Run E2E tests
        env:
          E2E_BASE_URL: http://localhost:8080
          KEYCLOAK_URL: http://localhost:8180
        run: |
          pytest -m e2e -v --tb=short

      - name: Upload Playwright traces on failure
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-traces
          path: test-results/

      - name: Stop services
        if: always()
        run: |
          cd compose
          docker compose down -v

  # ============================================
  # Lint and Type Check
  # ============================================
  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: "pip"

      - name: Install linters
        run: |
          pip install ruff mypy

      - name: Run ruff
        run: ruff check services/

      - name: Run mypy
        run: mypy services/ui_iot --ignore-missing-imports
        continue-on-error: true  # Don't fail on type errors initially
```

### 5.2 Create PR template

Create `.github/pull_request_template.md`:

```markdown
## Summary

<!-- Brief description of changes -->

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Refactoring
- [ ] Documentation
- [ ] Tests

## Testing

- [ ] Unit tests pass locally
- [ ] Integration tests pass locally
- [ ] E2E tests pass locally (if UI changes)

## Checklist

- [ ] Code follows project style
- [ ] Self-reviewed code
- [ ] Added tests for new functionality
- [ ] Updated documentation if needed
- [ ] No console.log or debug statements
```

### 5.3 Create branch protection reminder

Create `.github/BRANCH_PROTECTION.md`:

```markdown
# Branch Protection Settings

Configure these settings in GitHub repository settings:

## Main Branch Protection

1. Go to Settings > Branches > Add rule
2. Branch name pattern: `main`
3. Enable:
   - [x] Require a pull request before merging
   - [x] Require status checks to pass before merging
     - Required checks:
       - `Unit Tests`
       - `Integration Tests`
       - `Lint`
   - [x] Require branches to be up to date before merging
   - [x] Do not allow bypassing the above settings

## Develop Branch Protection (if used)

1. Branch name pattern: `develop`
2. Enable:
   - [x] Require status checks to pass before merging
     - Required checks:
       - `Unit Tests`
       - `Integration Tests`
```

### 5.4 Create workflow for dependency updates

Create `.github/workflows/dependencies.yml`:

```yaml
name: Dependency Check

on:
  schedule:
    - cron: "0 0 * * 0"  # Weekly on Sunday
  workflow_dispatch:

jobs:
  check-updates:
    name: Check for updates
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Check for outdated packages
        run: |
          pip install pip-tools
          pip list --outdated

      - name: Security audit
        run: |
          pip install safety
          safety check -r services/ui_iot/requirements.txt || true
```

### 5.5 Add CI badges to README

If a `README.md` exists, add badges at the top:

```markdown
# OpsConductor Pulse

![Tests](https://github.com/OWNER/REPO/workflows/Tests/badge.svg)
![Coverage](https://codecov.io/gh/OWNER/REPO/branch/main/graph/badge.svg)
```

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `.github/workflows/test.yml` |
| CREATE | `.github/workflows/dependencies.yml` |
| CREATE | `.github/pull_request_template.md` |
| CREATE | `.github/BRANCH_PROTECTION.md` |
| MODIFY | `README.md` (add badges, if exists) |

## Acceptance Criteria

- [ ] Workflow file valid (check with `act` or push to branch)
- [ ] Unit tests job runs
- [ ] Integration tests job runs with Postgres
- [ ] E2E tests job runs with full stack
- [ ] Lint job runs
- [ ] PR template created
- [ ] Branch protection documented

**Test locally** (optional, requires `act`):
```bash
# Install act: https://github.com/nektos/act
act -j unit-tests
```

**Verify on GitHub**:
1. Push to a feature branch
2. Open PR
3. Check Actions tab for running workflows
4. Verify all jobs pass

## Commit

```
Add GitHub Actions CI pipeline

- test.yml: unit, integration, E2E test jobs
- Postgres and Keycloak services for integration tests
- Docker Compose for E2E tests
- Lint job with ruff and mypy
- Coverage upload to Codecov
- PR template and branch protection docs
- Weekly dependency check workflow

Part of Phase 3.5: Testing Infrastructure
```
