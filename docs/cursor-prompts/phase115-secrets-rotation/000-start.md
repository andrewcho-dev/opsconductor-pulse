# Phase 115 — Production Secrets Rotation

## Context

The platform is internet-facing at `pulse.enabledconsultants.com` but every
secret in `compose/.env` is still a dev default. Keycloak has 4 test users
with password `test123`. This phase rotates all credentials to
production-strength values.

## Severity: CRITICAL

The port lockdown from phase 114 buys time, but these dev credentials are
trivially guessable. Anyone who gains any foothold (SSRF, log leak, config
exposure) can escalate to full control.

## Pre-Flight Checklist (BEFORE starting step 001)

### 1. Schedule a Maintenance Window
This is NOT zero-downtime. The site will be down for 15-20 minutes.
Notify anyone who needs to know.

### 2. Save Rollback Artifacts

```bash
cd ~/simcloud/compose

# Backup .env
cp .env .env.pre-rotation.$(date +%Y%m%d-%H%M%S)

# Backup docker-compose.yml (will be modified for Keycloak env var)
cp docker-compose.yml docker-compose.yml.pre-rotation.$(date +%Y%m%d-%H%M%S)

# Snapshot current DB roles and passwords (hashes, not plaintext)
docker exec iot-postgres psql -U iot -d postgres -c \
  "SELECT rolname, rolpassword FROM pg_authid WHERE rolname IN ('iot','keycloak');" \
  > /tmp/db-roles-snapshot-$(date +%Y%m%d-%H%M%S).txt

# Backup the MQTT password volume
docker cp iot-mqtt:/mosquitto/passwd/passwd /tmp/mqtt-passwd-backup-$(date +%Y%m%d-%H%M%S)
```

### 3. Verify Break-Glass Admin Access Works NOW

Before rotating anything, confirm you can currently:
```bash
# Keycloak admin console login (use current dev password):
curl -s -X POST \
  "https://pulse.enabledconsultants.com/realms/master/protocol/openid-connect/token" \
  -d "username=admin&password=admin_dev&grant_type=password&client_id=admin-cli" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK' if 'access_token' in d else 'FAIL')"

# Postgres direct access (use current dev password):
docker exec iot-postgres psql -U iot -d iotcloud -c "SELECT 1;"
```

If either fails, fix access BEFORE proceeding.

### 4. Proceed with Steps 001–006

## What Gets Rotated

| Secret | Current (dev) | New | Storage |
|--------|--------------|-----|---------|
| POSTGRES_PASSWORD | `iot_dev` | 32-byte hex | .env + ALTER USER in DB |
| PG_PASS | `iot_dev` | (same as above) | .env only (alias) |
| ADMIN_KEY | `dev-admin-key-not-for-production` | 32-byte hex | .env only |
| PROVISION_ADMIN_KEY | `dev-provision-key-not-for-production` | 32-byte hex | .env only |
| KEYCLOAK_ADMIN_PASSWORD | `admin_dev` | 32-byte hex | .env (read on boot) |
| KC_DB_USER_PASSWORD | `keycloak_dev_local` | 32-byte hex | .env + ALTER USER in DB |
| MQTT_ADMIN_PASSWORD | `mqtt_dev_local` | 32-byte hex | .env + mosquitto passwd volume |
| Keycloak client secret | `pulse-api-secret-dev` | 32-byte hex | realm JSON + Keycloak DB |
| 4 Keycloak test users | `test123` | disabled/reset | Keycloak DB |

### Rotation Gotchas

- **POSTGRES_PASSWORD env var:** Only used on first `initdb`. With existing
  data, it does NOTHING. The ALTER USER command is the real rotation.
  `POSTGRES_PASSWORD` and `PG_PASS` in `.env` must match what ALTER USER set.
- **MQTT_ADMIN_PASSWORD:** Persisted in the Mosquitto password volume, not
  just .env. Updating .env alone will desync services from the broker.
  The passwd file inside the volume MUST be regenerated.
- **KC_DB_USER_PASSWORD:** Same as Postgres — must ALTER USER in DB first,
  then update .env to match.

## Execution Order

| Step | File | Description |
|------|------|-------------|
| 1 | `001-generate-secrets.md` | Generate all new secrets, save to password manager |
| 2 | `002-rotate-env.md` | Postgres ALTER USER + MQTT passwd + .env update |
| 3 | `003-rotate-keycloak.md` | Client secret + test user passwords via Admin API |
| 4 | `004-fix-script-defaults.md` | Remove dangerous fallback defaults in scripts |
| 5 | `005-harden-env-file.md` | File permissions + cleanup |
| 6 | `006-restart-verify.md` | Full restart + dead-credential verification |

## Rollback

If anything goes wrong mid-rotation:

```bash
cd ~/simcloud/compose

# Restore .env
cp .env.pre-rotation.* .env

# Restore docker-compose.yml
cp docker-compose.yml.pre-rotation.* docker-compose.yml

# If Postgres passwords were already ALTER'd, revert them:
docker compose up -d postgres
docker exec iot-postgres psql -U iot -d iotcloud -c \
  "ALTER USER iot WITH PASSWORD 'iot_dev';"
docker exec iot-postgres psql -U iot -d postgres -c \
  "ALTER USER keycloak WITH PASSWORD 'keycloak_dev_local';"

# If MQTT passwd was changed, restore backup:
docker cp /tmp/mqtt-passwd-backup-* iot-mqtt:/mosquitto/passwd/passwd

# Restart everything
docker compose down && docker compose up -d
```

## Files Modified

- `compose/.env` — all 7 secret values
- `compose/docker-compose.yml` — add KEYCLOAK_CLIENT_SECRET env var to keycloak service
- `compose/keycloak/realm-pulse.json` — client secret + test users
- `scripts/provision_simulator_devices.py` — remove fallback default
- `scripts/seed_demo_data.py` — remove fallback default
