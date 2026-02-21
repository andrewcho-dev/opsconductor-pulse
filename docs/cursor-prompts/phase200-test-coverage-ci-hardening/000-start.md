# Phase 200 — Test Coverage and CI Hardening

## Goal

Expand test coverage enforcement to all microservices (not just `ui_iot`), fix the permanently-skipped tests in `test_alert_rules.py` and `test_api_v2.py`, make integration tests assert actual outcomes rather than accepting multiple status codes, and make MyPy non-optional in CI.

## Current State (problem)

1. **Coverage scope**: `pytest.ini` only measures coverage for `services/ui_iot`. The other 10 microservices have no enforced coverage at all.
2. **Skipped tests**: `test_alert_rules.py` and `test_api_v2.py` skip entire test classes due to import failures — alert rule validation and WebSocket rate limiting are untested.
3. **Weak integration assertions**: Tests like `assert status_code in (200, 403, 404)` verify reachability, not correctness.
4. **MyPy non-blocking**: `test.yml:344` runs `mypy || true` — type errors never fail CI.

## Target State

- Coverage measured and thresholds enforced for `evaluator_iot`, `ingest_iot`, `ops_worker`, and `shared`.
- The 6+ permanently-skipped tests are fixed or explicitly documented as xfail with a tracking issue.
- Integration tests assert the expected status code and validate response payload shape, not "any of these codes."
- MyPy errors fail CI builds.

## Execution Order

| Step | File | What | Depends On |
|------|------|------|------------|
| 1 | `001-fix-skipped-tests.md` | Fix import failures in test_alert_rules and test_api_v2 | — |
| 2 | `002-expand-coverage-scope.md` | Add coverage thresholds for other microservices | — |
| 3 | `003-strengthen-integration-assertions.md` | Replace multi-status-code assertions | — |
| 4 | `004-mypy-ci-blocking.md` | Make MyPy block CI builds | — |
| 5 | `005-update-documentation.md` | Update affected docs | Steps 1–4 |

## Verification

```bash
# All tests in test_alert_rules and test_api_v2 run without skips
pytest tests/unit/test_alert_rules.py tests/unit/test_api_v2.py -v 2>&1 | grep -E 'SKIP|PASS|FAIL'

# Coverage scope includes evaluator and ingest
grep 'evaluator_iot\|ingest_iot' pytest.ini

# MyPy is blocking
grep 'mypy' .github/workflows/test.yml | grep -v '|| true'
```

## Documentation Impact

- `docs/development/testing.md` — Update coverage targets and what services are in scope
