# 002 — Rotate All Secrets in compose/.env

## Goal

Replace every dev credential with production values. This step handles
three distinct credential stores that must stay in sync:

1. **Postgres** — password lives in the DB (pg_authid), .env is just config
2. **MQTT** — password lives in the mosquitto passwd volume AND .env
3. **Everything else** — .env only (read on service startup)

## IMPORTANT: Maintenance Window Required

The site will be down during this step. Expect 15-20 minutes.

---

## Step 1 — Stop Everything

```bash
cd ~/simcloud/compose
docker compose down
```

---

## Step 2 — Rotate Postgres Passwords in the Database

`POSTGRES_PASSWORD` only takes effect on first `initdb`. With existing data
it does NOTHING. The ALTER USER command is the real rotation.

Start ONLY Postgres with the old .env (passwords still match):

```bash
docker compose up -d postgres
# Wait for healthy:
until docker exec iot-postgres pg_isready -U iot; do sleep 2; done
```

Change both database user passwords:

```bash
# Rotate the main application user (iot)
docker exec iot-postgres psql -U iot -d postgres -c \
  "ALTER USER iot WITH PASSWORD '<NEW_POSTGRES_PASSWORD>';"

# Rotate the Keycloak database user
docker exec iot-postgres psql -U iot -d postgres -c \
  "ALTER USER keycloak WITH PASSWORD '<NEW_KC_DB_USER_PASSWORD>';"
```

Replace `<NEW_POSTGRES_PASSWORD>` and `<NEW_KC_DB_USER_PASSWORD>` with
values from step 001.

**Verify the new passwords work before proceeding:**

```bash
# Test iot user with new password (via psql inside container using md5):
docker exec iot-postgres psql "postgresql://iot:<NEW_POSTGRES_PASSWORD>@localhost:5432/iotcloud" \
  -c "SELECT 1;"
# Expected: returns 1

# Test keycloak user with new password:
docker exec iot-postgres psql "postgresql://keycloak:<NEW_KC_DB_USER_PASSWORD>@localhost:5432/keycloak_db" \
  -c "SELECT 1;"
# Expected: returns 1
```

**STOP HERE IF EITHER TEST FAILS.** Rollback per 000-start.md.

Stop Postgres:

```bash
docker compose down
```

---

## Step 3 — Update compose/.env

Replace these values with the secrets from step 001:

```
POSTGRES_PASSWORD=<NEW_POSTGRES_PASSWORD>
PG_PASS=<NEW_POSTGRES_PASSWORD>

ADMIN_KEY=<NEW_ADMIN_KEY>
PROVISION_ADMIN_KEY=<NEW_PROVISION_ADMIN_KEY>

KEYCLOAK_ADMIN_PASSWORD=<NEW_KEYCLOAK_ADMIN_PASSWORD>
KC_DB_USER_PASSWORD=<NEW_KC_DB_USER_PASSWORD>

MQTT_ADMIN_PASSWORD=<NEW_MQTT_ADMIN_PASSWORD>
```

**CRITICAL:** `POSTGRES_PASSWORD` and `PG_PASS` MUST be identical and MUST
match what ALTER USER set in step 2. If they don't match, every service
will fail to connect to the database.

Leave these unchanged (not secrets):
```
HOST_IP=localhost
KEYCLOAK_URL=https://pulse.enabledconsultants.com
UI_BASE_URL=https://pulse.enabledconsultants.com
KC_HOSTNAME=pulse.enabledconsultants.com
KEYCLOAK_ADMIN_USERNAME=admin
LOG_LEVEL=INFO
```

---

## Step 4 — Rotate MQTT Service Account Password

**Why this is a separate step:** The MQTT broker stores passwords in a
hashed file inside a Docker volume (`mosquitto-passwd`). Updating
`MQTT_ADMIN_PASSWORD` in .env only changes what the *ingest service* sends
to the broker. If the broker's passwd file still has the old hash, auth
will fail and ingestion breaks silently.

Start only MQTT:

```bash
docker compose up -d mqtt
# Wait for it:
sleep 5
```

Regenerate the service_pulse password in the broker's passwd file:

```bash
docker exec iot-mqtt mosquitto_passwd -b /mosquitto/passwd/passwd \
  service_pulse "<NEW_MQTT_ADMIN_PASSWORD>"
```

Replace `<NEW_MQTT_ADMIN_PASSWORD>` with the value from step 001 (same
value now in .env).

Restart MQTT to reload the passwd file:

```bash
docker compose restart mqtt
```

**Verify the new password works:**

```bash
# Quick auth test — subscribe for 3 seconds then exit:
docker compose exec mqtt mosquitto_sub \
  -h localhost -p 1883 \
  -u service_pulse -P "<NEW_MQTT_ADMIN_PASSWORD>" \
  -t "test/verify" -W 3 || true
# Expected: exits after timeout, NOT "Connection Refused: not authorised"
```

**STOP HERE IF AUTH FAILS.** Restore the mqtt passwd backup per 000-start.md.

Stop MQTT:

```bash
docker compose down
```

---

## Step 5 — Pre-Flight Check

Before bringing everything up, confirm the three credential stores are
consistent:

- [ ] Postgres `iot` user password matches `PG_PASS` / `POSTGRES_PASSWORD` in .env
- [ ] Postgres `keycloak` user password matches `KC_DB_USER_PASSWORD` in .env
- [ ] MQTT `service_pulse` passwd file hash matches `MQTT_ADMIN_PASSWORD` in .env
- [ ] `POSTGRES_PASSWORD` and `PG_PASS` are identical in .env

If all four checks pass, proceed to step 003 (Keycloak rotation).

---

## Notes

- The `KC_DB_PASSWORD` key in .env (if present) is unused. The actual
  variable consumed by docker-compose.yml is `KC_DB_USER_PASSWORD`.
- PgBouncer uses scram-sha-256 auth. After Postgres password rotation,
  PgBouncer may cache old auth. It will reconnect automatically on
  restart, but if you see auth errors, `docker compose restart pgbouncer`.
- The Keycloak admin password (`KEYCLOAK_ADMIN_PASSWORD`) is read from
  the environment on Keycloak boot. No database ALTER needed — just
  updating .env is sufficient.
