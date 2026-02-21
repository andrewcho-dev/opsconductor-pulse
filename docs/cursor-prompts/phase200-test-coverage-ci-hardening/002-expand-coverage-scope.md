# Task 2: Expand Coverage Scope to Critical Microservices

## Context

`pytest.ini` has `--cov=services/ui_iot` — only `ui_iot` is measured. The evaluator, ingest service, shared utilities, and ops_worker have no coverage enforcement. These are the most critical paths in the system (data ingestion, alert evaluation, shared auth logic).

## Actions

1. Read `pytest.ini` and `.github/workflows/test.yml` in full.

2. In `pytest.ini`, expand the `--cov` flag to include additional services:
   ```ini
   addopts =
     --cov=services/ui_iot
     --cov=services/evaluator_iot
     --cov=services/ingest_iot
     --cov=services/shared
     --cov-report=term-missing
     --cov-report=html:htmlcov
     --cov-report=xml:coverage.xml
   ```

3. In `test.yml`, add coverage thresholds for the newly-covered services. Set realistic initial thresholds based on how much code is actually tested today (start conservative — the goal is to prevent regression, not to instantly hit 80%):

   - `services/evaluator_iot`: start at 30% (it is largely untested currently)
   - `services/ingest_iot`: start at 30%
   - `services/shared`: start at 60% (shared utilities are often better tested)

   Add these to the `coverage_thresholds` section of `test.yml` where the other 4 critical-path thresholds are defined.

4. Add a comment in `test.yml` next to each new threshold explaining the current state and the target:
   ```yaml
   # evaluator_iot: initially 30%, target 60% — increase as tests are added
   ```

5. Do not write any new test files in this task — only expand what is measured. It is expected that the build may now show lower coverage numbers; that's the honest state.

## Verification

```bash
# Coverage config shows multiple services
grep 'cov=' pytest.ini | grep 'evaluator_iot\|ingest_iot\|shared'

# CI thresholds exist for new services
grep 'evaluator_iot\|ingest_iot' .github/workflows/test.yml
```
