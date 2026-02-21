# Phase 193 — Critical Credential Hygiene

## Goal

Remove every hardcoded credential default from the Python service layer and add fail-fast startup validation. Services must refuse to start rather than silently fall back to weak development passwords.

## Current State (problem)

Every microservice calls `os.getenv("PG_PASS", "iot_dev")` (and similar) for database credentials. If an environment variable is missing in production, the service silently connects using the development password. This is a critical security regression vector — a misconfigured deployment looks healthy while being trivially compromised.

## Target State

- All `os.getenv("VAR", "<default>")` calls for security-sensitive variables replaced with a helper that raises `RuntimeError` if the variable is absent.
- Services fail loudly at import/startup if any required credential is missing.
- Non-sensitive config (ports, log levels, feature flags) may retain safe defaults.

## Execution Order

| Step | File | What | Depends On |
|------|------|------|------------|
| 1 | `001-shared-env-helper.md` | Add `require_env()` helper to `services/shared/` | — |
| 2 | `002-ui-iot-credentials.md` | Replace defaults in `ui_iot` | Step 1 |
| 3 | `003-ingest-iot-credentials.md` | Replace defaults in `ingest_iot` | Step 1 |
| 4 | `004-evaluator-credentials.md` | Replace defaults in `evaluator_iot` | Step 1 |
| 5 | `005-ops-worker-credentials.md` | Replace defaults in `ops_worker` | Step 1 |
| 6 | `006-remaining-services-credentials.md` | Replace defaults in `provision_api`, `subscription_worker`, `route_delivery`, `mqtt_nats_bridge`, `webhook_receiver` | Step 1 |
| 7 | `007-update-documentation.md` | Update affected docs | Steps 1–6 |

## Verification

```bash
# Confirm no remaining weak defaults in Python source
grep -rn 'getenv.*iot_dev\|getenv.*changeme\|getenv.*password123\|getenv.*secret123' services/
# Should return zero results

# Confirm require_env helper exists
grep -rn 'require_env' services/shared/

# Start a service without PG_PASS set — it must exit non-zero immediately
# (Manual test in dev environment)
```

## Documentation Impact

- `docs/operations/deployment.md` — Document that all credential env vars are now required (no defaults)
- `docs/development/getting-started.md` — Ensure local dev setup instructions include all required vars
