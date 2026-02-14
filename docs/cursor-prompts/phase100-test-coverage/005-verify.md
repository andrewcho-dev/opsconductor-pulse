# Phase 100 — Verify Test Coverage

## Step 1: Run unit tests only

```bash
pytest tests/unit/ -v --tb=short 2>&1 | tail -30
```

Expected: all new tests pass. Note total pass/fail count.

## Step 2: Run with coverage report

```bash
pytest tests/unit/ \
  --cov=services/ui_iot \
  --cov=services/evaluator \
  --cov=services/ingest_iot \
  --cov=services/shared \
  --cov-report=term-missing \
  --cov-fail-under=65 \
  -v 2>&1 | tail -40
```

Expected:
- Coverage >= 65% — no FAIL line
- Three new test files all green
- `test_evaluator_logic.py` — all threshold + heartbeat tests pass
- `test_ingest_core.py` — all validation + normalization tests pass
- `test_tenant_isolation.py` — all non-skipped isolation tests pass

## Step 3: Implement the skipped test

Go back to `tests/unit/test_tenant_isolation.py` and implement
`test_device_auth_rejects_wrong_tenant` by reading the actual `DeviceAuthCache` class
in `services/ingest_iot/ingest.py`. Remove the `pytest.skip()` and write a real assertion.

## Step 4: Commit

```bash
git add \
  tests/unit/test_evaluator_logic.py \
  tests/unit/test_ingest_core.py \
  tests/unit/test_tenant_isolation.py \
  .coveragerc \
  .github/workflows/test.yml

git commit -m "test: add evaluator, ingest, and tenant isolation unit tests; raise coverage to 65%

- tests/unit/test_evaluator_logic.py: threshold rules (all 6 operators), heartbeat,
  metric normalization
- tests/unit/test_ingest_core.py: envelope validation, topic parsing, metric normalization
- tests/unit/test_tenant_isolation.py: tenant_connection sets correct context,
  operator_connection uses BYPASSRLS role, ingest tenant validation
- .coveragerc: fail_under raised from 45 → 65
- CI: coverage threshold updated to match"

git push origin main
git log --oneline -3
```

## Definition of Done

- [ ] `test_evaluator_logic.py` exists and all tests pass
- [ ] `test_ingest_core.py` exists and all tests pass
- [ ] `test_tenant_isolation.py` exists, no tests skipped
- [ ] Coverage threshold is 65% in `.coveragerc`
- [ ] CI pipeline passes with new threshold
- [ ] `pytest tests/unit/ --cov-fail-under=65` exits with code 0
