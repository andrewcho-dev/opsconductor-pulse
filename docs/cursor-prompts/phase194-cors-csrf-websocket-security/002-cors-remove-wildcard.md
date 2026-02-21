# Task 2: Remove CORS Wildcard Default

## Context

`compose/docker-compose.yml` line ~472 sets `CORS_ALLOWED_ORIGINS: "${CORS_ALLOWED_ORIGINS:-*}"`. If the env var is absent in any environment, every origin is permitted. This must have no fallback — misconfiguration should result in denial, not permissiveness.

`services/ui_iot/app.py` lines ~140-150 reads `CORS_ORIGINS` and falls back to localhost in non-prod. This is acceptable for local dev but the docker-compose default must not propagate `*` into any environment.

## Actions

1. Open `compose/docker-compose.yml`.

2. Find the `CORS_ALLOWED_ORIGINS` env var entry. Remove the `:-*` default so it becomes:
   ```yaml
   CORS_ALLOWED_ORIGINS: "${CORS_ALLOWED_ORIGINS}"
   ```
   If the variable is unset, the service receives an empty string, and `app.py`'s logic will correctly apply the non-prod localhost default or empty list.

3. Open `services/ui_iot/app.py`. Find the CORS configuration (around lines 140-150 and the `CORSMiddleware` setup around line 222).

4. In the `CORSMiddleware` setup, change `allow_headers=["*"]` to an explicit allowlist:
   ```python
   allow_headers=[
       "Authorization",
       "Content-Type",
       "X-CSRF-Token",
       "X-Request-ID",
       "X-Tenant-ID",
   ],
   ```
   Add or remove headers only if you can confirm they are actually used by the frontend. Do not add speculative headers.

5. Do not change any other CORS logic.

## Verification

```bash
grep 'CORS_ALLOWED_ORIGINS.*\*' compose/docker-compose.yml
# Must return zero results

grep 'allow_headers.*\[.*\*' services/ui_iot/app.py
# Must return zero results
```
