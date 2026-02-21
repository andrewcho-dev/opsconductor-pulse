# Task 5: Replace Hardcoded Credential Defaults in `ops_worker`

## Context

`services/ops_worker/main.py` (line ~35), `health_monitor.py` (line ~18), and `metrics_collector.py` (line ~20) all contain credential defaults. Apply the same `require_env` pattern.

## Actions

1. Read each of these files in full before editing:
   - `services/ops_worker/main.py`
   - `services/ops_worker/health_monitor.py`
   - `services/ops_worker/metrics_collector.py`
   - Any other `.py` files under `services/ops_worker/workers/`

2. In each file, add the import:
   ```python
   from shared.config import require_env, optional_env
   ```

3. Replace all credential-bearing `os.getenv(...)` calls with `require_env(...)`.

4. Move all `require_env()` calls to module-level constants at the top of each file.

5. Do not change any logic beyond env-reading calls.

## Verification

```bash
grep -rn 'getenv.*iot_dev\|getenv.*changeme\|getenv.*password' services/ops_worker/
# Must return zero results
```
