# Phase 206 — Performance Baseline CI Gate

## Goal

Make the benchmark CI job meaningful. Right now `pytest -m benchmark` runs and uploads `benchmark_results.json` to CI artifacts, but nothing fails if a key endpoint regresses by 2x. Add a baseline comparison that fails CI if performance degrades beyond a defined threshold.

## Current State (problem)

`.github/workflows/test.yml` runs benchmarks on push to main, uploads results, but there is no comparison step. A developer could merge a change that doubles API response time and CI would stay green.

## Target State

- A committed `benchmarks/baseline.json` stores the reference performance numbers.
- CI compares current results to baseline and fails if any benchmark degrades by more than 20%.
- A script `scripts/update_benchmark_baseline.py` lets developers intentionally update the baseline when performance characteristics legitimately change.

## Execution Order

| Step | File | What | Depends On |
|------|------|------|------------|
| 1 | `001-capture-baseline.md` | Run benchmarks and commit baseline | — |
| 2 | `002-comparison-script.md` | Write the comparison script | — |
| 3 | `003-ci-integration.md` | Add comparison step to test.yml | Step 2 |
| 4 | `004-update-documentation.md` | Update docs | Steps 1–3 |

## Verification

```bash
# Baseline file exists
ls benchmarks/baseline.json

# Comparison script exists
ls scripts/check_benchmark_regression.py

# CI runs the comparison
grep 'check_benchmark_regression' .github/workflows/test.yml
```

## Documentation Impact

- `docs/development/testing.md` — Document benchmark baseline process and how to update it
