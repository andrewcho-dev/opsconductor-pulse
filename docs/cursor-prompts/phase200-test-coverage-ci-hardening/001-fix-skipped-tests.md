# Task 1: Fix Permanently-Skipped Tests

## Context

`tests/unit/test_alert_rules.py` and `tests/unit/test_api_v2.py` skip 6+ test functions because their module imports fail (likely `AlertRuleCreate` model or `api_v2` module cannot be imported in the test environment due to missing dependencies or circular imports).

These tests cover alert rule validation and WebSocket connection management — both critical paths.

## Actions

1. Read `tests/unit/test_alert_rules.py` and `tests/unit/test_api_v2.py` in full.

2. Read the import block at the top of each file. Identify exactly which imports fail and why. Common causes:
   - The module depends on a database pool or external service that isn't initialized in the test environment.
   - The import path is wrong (sys.path issue).
   - Circular import caused by importing a module that imports app state at module level.

3. For `test_alert_rules.py`:
   - Find the `AlertRuleCreate` model (likely in `services/ui_iot/models/` or similar).
   - If the import fails because the model depends on app state, refactor the test to either mock that dependency or import only the pure model/schema class without triggering the full app initialization.
   - The test should be able to import and instantiate `AlertRuleCreate` without a running database.

4. For `test_api_v2.py`:
   - Find the `api_v2` module. Determine why it cannot be imported.
   - If it depends on the NATS client or database at import time, mock those dependencies in the test's `conftest.py` or module-level setup.

5. After fixing imports, verify all previously-skipped tests now run. If any test is genuinely untestable without a full stack (e.g., requires live Keycloak), mark it with `@pytest.mark.integration` and a clear comment explaining why, rather than silently skipping it.

6. Do not add new tests in this task — only fix the import failures that cause existing tests to skip.

## Verification

```bash
pytest tests/unit/test_alert_rules.py tests/unit/test_api_v2.py -v
# Must show PASSED or FAILED, not SKIPPED, for the previously-skipped tests
```
