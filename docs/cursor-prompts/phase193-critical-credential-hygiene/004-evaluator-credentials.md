# Task 4: Replace Hardcoded Credential Defaults in `evaluator_iot`

## Context

`services/evaluator_iot/evaluator.py` contains credential defaults at approximately line 47. Apply the same `require_env` pattern.

## Actions

1. Read `services/evaluator_iot/evaluator.py` in full.

2. Add the import at the top:
   ```python
   from shared.config import require_env, optional_env
   ```

3. Replace all credential-bearing `os.getenv(...)` calls with `require_env(...)`.

4. Move all `require_env()` calls to module-level constants at the top of the file.

5. Scan all other Python files under `services/evaluator_iot/` and apply the same replacement.

6. Do not change any logic beyond env-reading calls.

## Verification

```bash
grep -rn 'getenv.*iot_dev\|getenv.*changeme\|getenv.*password' services/evaluator_iot/
# Must return zero results
```
