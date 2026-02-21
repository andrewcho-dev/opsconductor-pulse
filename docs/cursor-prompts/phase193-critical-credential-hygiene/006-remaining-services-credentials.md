# Task 6: Replace Hardcoded Credential Defaults in Remaining Services

## Context

Apply the same `require_env` pattern to the five remaining microservices: `provision_api`, `subscription_worker`, `route_delivery`, `mqtt_nats_bridge`, and `webhook_receiver`.

## Actions

For each service directory listed below, perform these steps:

**Services to update:**
- `services/provision_api/`
- `services/subscription_worker/`
- `services/route_delivery/`
- `services/mqtt_nats_bridge/`
- `services/webhook_receiver/`

**For each service:**

1. List all `.py` files in the service directory.
2. Read each file and identify all `os.getenv(...)` calls.
3. Add the import where needed:
   ```python
   from shared.config import require_env, optional_env
   ```
4. Replace credential-bearing `os.getenv(...)` with `require_env(...)`. Variables matching these patterns are security-sensitive:
   - Contains `PASSWORD`, `SECRET`, `KEY`, `TOKEN`, `PASS`, `CRED`, `AUTH`
5. Move `require_env()` calls to module-level constants at the top of each file.
6. Do not change any logic beyond env-reading calls.

## Verification

```bash
# Run across ALL services at once
grep -rn 'getenv.*iot_dev\|getenv.*changeme\|getenv.*password123\|getenv.*admin123' services/
# Must return zero results

# Confirm helper is used broadly
grep -rn 'require_env' services/ | wc -l
# Should show many usages across services
```
