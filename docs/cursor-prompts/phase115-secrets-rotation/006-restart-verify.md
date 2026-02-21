# 006 — Full Restart and Verification

## Goal

Bring up all services with the new credentials and verify everything
connects properly.

## Step 1 — Start Everything

```bash
cd ~/simcloud/compose
docker compose up -d
```

## Step 2 — Watch for Connection Failures

```bash
# Watch logs for the first 60 seconds
docker compose logs -f --tail=50 2>&1 | head -200
```

**Red flags to watch for:**
- `FATAL: password authentication failed` — Postgres password mismatch
- `Connection refused` — service not ready (may just need time)
- `401 Unauthorized` — Keycloak credential mismatch
- `Connection error` from ingest — MQTT password mismatch

## Step 3 — Check Individual Service Health

```bash
# Postgres
docker exec iot-postgres pg_isready -U iot -d iotcloud

# PgBouncer → Postgres
docker exec iot-pgbouncer pg_isready -h 127.0.0.1 -p 5432

# Keycloak
curl -s http://127.0.0.1:8180/health/ready 2>/dev/null || \
  docker compose exec keycloak bash -c 'exec 3<>/dev/tcp/localhost/9000; echo -e "GET /health/ready HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n" >&3; cat <&3'

# UI backend
curl -s http://127.0.0.1:8080/healthz 2>/dev/null || \
  docker compose logs ui --tail=10

# Ingest (MQTT connection)
docker compose logs ingest --tail=20

# All services
docker compose ps
```

## Step 4 — Test Public Access

```bash
# Site loads
curl -sI https://pulse.enabledconsultants.com | head -3

# Keycloak OIDC
curl -s https://pulse.enabledconsultants.com/realms/pulse/.well-known/openid-configuration | head -1
```

## Step 5 — Test Login

Open `https://pulse.enabledconsultants.com` in a browser:
- [ ] Login page loads
- [ ] Login completes with valid credentials
- [ ] Old password `test123` does NOT work (if users were disabled/reset)
- [ ] Dashboard renders

## Step 6 — Verify Old Credentials Are Dead

```bash
# This should FAIL (old Postgres password):
docker run --rm --network=host postgres:16 \
  psql "postgresql://iot:iot_dev@127.0.0.1:5432/iotcloud" -c "SELECT 1" 2>&1
# Expected: FATAL: password authentication failed

# This should FAIL (old admin key):
curl -s -H "X-Admin-Key: dev-admin-key-not-for-production" \
  http://127.0.0.1:8081/api/admin/devices
# Expected: 401 or 403
```

## Troubleshooting

### Postgres won't start / password mismatch
The password in `.env` must match what was set via ALTER USER in step 002.
If mismatched:
```bash
# Temporarily revert .env to old password
# Start postgres, run ALTER USER again, stop, update .env, restart
```

### Keycloak boot loop
Check logs: `docker compose logs keycloak --tail=50`
Common cause: KC_DB_USER_PASSWORD mismatch with what's in Postgres.

### Ingest can't connect to MQTT
The MQTT password file must match MQTT_ADMIN_PASSWORD in .env.
Re-run step 5 from 002-rotate-env.md to regenerate the passwd file.

### PgBouncer auth failures
PgBouncer uses scram-sha-256. After changing the Postgres password,
PgBouncer's cached auth may be stale. Restart it:
```bash
docker compose restart pgbouncer
```
