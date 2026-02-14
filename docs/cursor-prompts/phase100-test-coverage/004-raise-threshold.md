# Phase 100 — Raise Coverage Threshold to 65%

## Files to modify

### 1. `.coveragerc`

Find the line:
```ini
fail_under = 45
```

Change it to:
```ini
fail_under = 65
```

### 2. `.github/workflows/test.yml`

Find any `--cov-fail-under` flag in the pytest commands. If present, update from 45 to 65.
If not present, add `--cov-fail-under=65` to the integration test command.

## Why 65% and not higher

- 45% was the current threshold (already enforced)
- 65% is achievable with the three new test files added in steps 001-003
- 80%+ requires mocking the entire DB layer for route-level tests — worthwhile but a separate phase
- Do NOT set it to 100% or any unreachable number — the CI must stay green

## Verify threshold works

```bash
pytest tests/unit/ --cov=services/ui_iot --cov=services/evaluator \
  --cov=services/ingest_iot --cov=services/shared \
  --cov-report=term-missing --cov-fail-under=65 -v 2>&1 | tail -20
```

If coverage is below 65%, the test suite will fail with:
```
FAIL Required test coverage of 65% not reached.
```

In that case, add more test cases to the three files from steps 001-003 until coverage passes.
Focus on the highest-value uncovered lines shown in `--cov-report=term-missing` output.
