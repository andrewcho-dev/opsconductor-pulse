# Task 2: Replace Hardcoded Credential Defaults in `ui_iot`

## Context

`services/ui_iot/app.py` and its sub-modules use `os.getenv("PG_PASS", "iot_dev")` and similar patterns. These must be replaced with `require_env()` so the service fails at startup if credentials are missing.

## Actions

1. Read `services/ui_iot/app.py` in full before making any changes.

2. At the top of the file, add the import:
   ```python
   from shared.config import require_env, optional_env
   ```

3. Find every `os.getenv(...)` call in the file. Apply this rule:
   - **Security-sensitive variables** (passwords, secrets, signing keys, API keys, tokens): replace with `require_env("VAR_NAME")`.
   - **Non-sensitive variables** (ports, hostnames, log levels, feature flags, URLs with no embedded credentials): replace with `optional_env("VAR_NAME", "default_value")` or keep `os.getenv` if the existing default is safe.

   Variables that MUST use `require_env`:
   - `PG_PASS` / `POSTGRES_PASSWORD` / any database password
   - `SECRET_KEY` / `JWT_SECRET` / `SIGNING_SECRET`
   - `ADMIN_KEY`
   - `SMTP_PASSWORD`
   - `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET`
   - Any variable whose name contains `PASSWORD`, `SECRET`, `KEY`, `TOKEN` (unless it's a timeout/feature flag)

4. Move all `require_env()` calls to module-level constants (top of file, after imports), not inside functions. This ensures the failure happens at import time, not at first request.

   Example pattern:
   ```python
   # Before
   PG_PASS = os.getenv("PG_PASS", "iot_dev")

   # After
   PG_PASS = require_env("PG_PASS")
   ```

5. Repeat the same scan for any other Python files under `services/ui_iot/` (routes, workers, middleware, etc.) that independently call `os.getenv` for credentials.

6. Do not change any logic beyond the env-reading calls. Do not refactor anything else.

## Verification

```bash
grep -rn 'getenv.*iot_dev\|getenv.*changeme\|getenv.*password' services/ui_iot/
# Must return zero results

grep -rn 'require_env' services/ui_iot/
# Must show require_env usage for all credential variables
```
