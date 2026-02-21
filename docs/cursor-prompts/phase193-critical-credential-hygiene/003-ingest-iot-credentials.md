# Task 3: Replace Hardcoded Credential Defaults in `ingest_iot`

## Context

`services/ingest_iot/ingest.py` contains `os.getenv` calls with credential defaults. Apply the same `require_env` pattern established in Task 1.

## Actions

1. Read `services/ingest_iot/ingest.py` in full.

2. Add the import at the top:
   ```python
   from shared.config import require_env, optional_env
   ```

3. Replace all credential-bearing `os.getenv(...)` calls with `require_env(...)`. See Task 2 for the list of variable name patterns that are security-sensitive.

4. Move all `require_env()` calls to module-level constants at the top of the file.

5. Scan all other Python files under `services/ingest_iot/` for the same pattern and apply the same replacement.

6. Do not change any logic beyond env-reading calls.

## Verification

```bash
grep -rn 'getenv.*iot_dev\|getenv.*changeme\|getenv.*password' services/ingest_iot/
# Must return zero results
```
