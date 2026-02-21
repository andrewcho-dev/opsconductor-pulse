# Phase 110 — Replace Hardcoded Secrets in docker-compose.yml

## File to modify
`compose/docker-compose.yml`

Read the full file before making changes. For every hardcoded credential,
replace with a `${VAR}` reference that reads from the `.env` file.

## Rule

**No secret may have a hardcoded fallback value.**

BAD:  `POSTGRES_PASSWORD: iot_dev`
BAD:  `KEYCLOAK_ADMIN_PASSWORD: ${KEYCLOAK_ADMIN_PASSWORD:-admin_dev}`
GOOD: `POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}`

The `:-default` fallback syntax is acceptable ONLY for non-secret tuning
parameters (timeouts, batch sizes, log levels). Never for passwords or keys.

---

## Changes required

### postgres service
```yaml
# BEFORE
POSTGRES_PASSWORD: iot_dev

# AFTER
POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
```

### pgbouncer service
```yaml
# BEFORE
DB_PASSWORD: iot_dev

# AFTER
DB_PASSWORD: ${PG_PASS}
```

### All application services (ingest, evaluator, dispatcher,
### delivery_worker, ops_worker, ui, api, subscription-worker)

Replace every occurrence of:
```yaml
PG_PASS: iot_dev
```
with:
```yaml
PG_PASS: ${PG_PASS}
```

Replace every occurrence of hardcoded DATABASE_URL containing `iot_dev`:
```yaml
# BEFORE
DATABASE_URL: "postgresql://iot:iot_dev@iot-pgbouncer:5432/iotcloud"

# AFTER
DATABASE_URL: "postgresql://iot:${PG_PASS}@iot-pgbouncer:5432/iotcloud"
```

Same for NOTIFY_DATABASE_URL:
```yaml
# BEFORE
NOTIFY_DATABASE_URL: "postgresql://iot:iot_dev@iot-postgres:5432/iotcloud"

# AFTER
NOTIFY_DATABASE_URL: "postgresql://iot:${PG_PASS}@iot-postgres:5432/iotcloud"
```

### provision_api service
```yaml
# BEFORE
ADMIN_KEY: "change-me-now"

# AFTER
ADMIN_KEY: ${ADMIN_KEY}
```

### ui_iot service
```yaml
# BEFORE
PROVISION_ADMIN_KEY: "change-me-now"

# AFTER
PROVISION_ADMIN_KEY: ${PROVISION_ADMIN_KEY}
```

### keycloak service
```yaml
# BEFORE
KEYCLOAK_ADMIN: admin
KEYCLOAK_ADMIN_PASSWORD: admin_dev
KC_DB_PASSWORD: iot_dev
KC_HOSTNAME: "192.168.10.53"

# AFTER
KEYCLOAK_ADMIN: ${KEYCLOAK_ADMIN_USERNAME}
KEYCLOAK_ADMIN_PASSWORD: ${KEYCLOAK_ADMIN_PASSWORD}
KC_DB_PASSWORD: ${KC_DB_PASSWORD}
KC_HOSTNAME: ${KC_HOSTNAME}
```

### Keycloak public URL fallback
```yaml
# BEFORE
KEYCLOAK_PUBLIC_URL: "${KEYCLOAK_URL:-https://192.168.10.53}"

# AFTER
KEYCLOAK_PUBLIC_URL: "${KEYCLOAK_URL}"
```

### All services that reference KEYCLOAK_JWKS_URI or similar
Find any remaining `192.168.10.53` references:
```bash
grep -n "192.168" compose/docker-compose.yml
```
Replace each with the appropriate `${VAR}` reference.

---

## After changes: validate the compose file

```bash
cd compose
docker compose config 2>&1 | head -30
```

Expected: no errors, no warnings about missing variables (all variables
are now defined in `.env`).

If any `variable is not set` warnings appear, add the missing variable
to `.env` and `.env.example`.
