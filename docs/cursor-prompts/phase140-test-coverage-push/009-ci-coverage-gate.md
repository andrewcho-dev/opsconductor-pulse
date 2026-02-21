# 140-009: CI Coverage Gate

## Task
Update CI pipeline to enforce 70% overall coverage and 90% for critical paths.

## Files to Modify

### 1. .github/workflows/test.yml

Update the unit tests job:
```yaml
- name: Run unit tests
  run: |
    mkdir -p test-results
    pytest -m unit -v --tb=short \
      --cov=services/ui_iot \
      --cov-fail-under=70 \
      --junitxml=test-results/unit.xml
```

**Changed**: `--cov-fail-under=30` → `--cov-fail-under=70`

Update the integration tests job:
```yaml
- name: Run integration tests with coverage
  run: |
    pytest -m integration -v --tb=short \
      --cov=services/ui_iot \
      --cov-report=xml --cov-report=term-missing \
      --cov-fail-under=70 \
      --junitxml=test-results/integration.xml
```

**Changed**: `--cov-fail-under=55` → `--cov-fail-under=70`

**Remove deprecated coverage targets**: Remove `--cov=services/dispatcher --cov=services/delivery_worker` (these services were removed in Phase 138).

### 2. Add Per-Module Coverage Checks

Add a new CI step after the main test runs:

```yaml
- name: Enforce critical path coverage
  run: |
    # Auth middleware: 90% minimum
    pytest tests/unit/test_auth_middleware.py -v --tb=short \
      --cov=services/ui_iot/middleware/auth \
      --cov-fail-under=90 \
      --no-header -q 2>/dev/null || \
      (echo "FAILED: auth middleware coverage below 90%" && exit 1)

    # Tenant middleware: 90% minimum
    pytest tests/unit/test_tenant_middleware.py -v --tb=short \
      --cov=services/ui_iot/middleware/tenant \
      --cov-fail-under=90 \
      --no-header -q 2>/dev/null || \
      (echo "FAILED: tenant middleware coverage below 90%" && exit 1)

    # DB pool: 90% minimum
    pytest tests/unit/test_db_pool.py -v --tb=short \
      --cov=services/ui_iot/db/pool \
      --cov-fail-under=90 \
      --no-header -q 2>/dev/null || \
      (echo "FAILED: db pool coverage below 90%" && exit 1)

    # URL validator: 90% minimum
    pytest tests/unit/test_url_validator.py -v --tb=short \
      --cov=services/ui_iot/utils/url_validator \
      --cov-fail-under=90 \
      --no-header -q 2>/dev/null || \
      (echo "FAILED: url_validator coverage below 90%" && exit 1)

    echo "All critical path coverage checks passed!"
```

### 3. Update pytest.ini (optional)

If the `[coverage:run]` section needs updates:

```ini
[coverage:run]
source = .
relative_files = false
include = services/ui_iot/*
omit = */tests/*, */__pycache__/*, */migrations/*
branch = True
```

No changes needed here unless the coverage source paths changed.

### 4. Update scripts/check_coverage.py (if it exists)

Read `scripts/check_coverage.py` and update the thresholds:

```python
OVERALL_THRESHOLD = 70  # was lower
CRITICAL_MODULES = {
    "services/ui_iot/middleware/auth.py": 90,
    "services/ui_iot/middleware/tenant.py": 90,
    "services/ui_iot/db/pool.py": 90,
    "services/ui_iot/utils/url_validator.py": 90,
}
```

### 5. Update scripts/coverage_ratchet.py (if it exists)

Read `scripts/coverage_ratchet.py` and update the minimum values to match the new thresholds. The ratchet should prevent coverage from dropping below the current level on any PR.

## Verification
```bash
# Run full test suite with coverage
pytest tests/ --cov=services/ui_iot --cov-report=term-missing --cov-fail-under=70
# Should pass with >= 70% overall

# Run critical module checks
pytest tests/unit/test_auth_middleware.py --cov=services/ui_iot/middleware/auth --cov-fail-under=90
pytest tests/unit/test_tenant_middleware.py --cov=services/ui_iot/middleware/tenant --cov-fail-under=90
pytest tests/unit/test_db_pool.py --cov=services/ui_iot/db/pool --cov-fail-under=90
pytest tests/unit/test_url_validator.py --cov=services/ui_iot/utils/url_validator --cov-fail-under=90
# All should pass

# Push a commit → CI runs → coverage gate passes
```
