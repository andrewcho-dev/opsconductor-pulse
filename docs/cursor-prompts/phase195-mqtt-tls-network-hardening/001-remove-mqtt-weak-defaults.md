# Task 1: Remove Weak MQTT/EMQX Defaults from docker-compose

## Context

`compose/docker-compose.yml` contains hardcoded fallback values for EMQX credentials. These must be removed so that missing environment variables cause a startup failure rather than silently using weak passwords.

## Actions

1. Read `compose/docker-compose.yml` in full.

2. Find and fix every occurrence of these patterns:

   | Current | Replace With |
   |---------|-------------|
   | `${EMQX_DASHBOARD_PASSWORD:-admin123}` | `${EMQX_DASHBOARD_PASSWORD:?EMQX_DASHBOARD_PASSWORD is required}` |
   | `${EMQX_NODE_COOKIE:-emqx_pulse_secret}` | `${EMQX_NODE_COOKIE:?EMQX_NODE_COOKIE is required}` |
   | `${MQTT_INTERNAL_AUTH_SECRET:-changeme_auth_secret}` | `${MQTT_INTERNAL_AUTH_SECRET:?MQTT_INTERNAL_AUTH_SECRET is required}` |
   | Any other `:-<weak_value>` pattern for credentials | Same `:?VAR is required` pattern |

   The `:?message` Docker Compose syntax causes `docker compose up` to exit with a clear error if the variable is not set. This is the correct behavior.

3. Open `compose/.env.example` (create it if it doesn't exist from phase 193 task 7). Add entries for all MQTT/EMQX variables with placeholder values:
   ```
   EMQX_DASHBOARD_PASSWORD=<required: generate with openssl rand -hex 16>
   EMQX_NODE_COOKIE=<required: generate with openssl rand -hex 32>
   MQTT_INTERNAL_AUTH_SECRET=<required: generate with openssl rand -hex 32>
   MQTT_ADMIN_PASSWORD=<required: generate with openssl rand -hex 32>
   ```

4. Do not change any other settings in docker-compose.yml.

## Verification

```bash
grep -E 'admin123|changeme|emqx_pulse_secret' compose/docker-compose.yml
# Must return zero results
```
