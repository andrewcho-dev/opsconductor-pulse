# Phase 113 — Verify Keycloak Production Mode

## Step 1: Keycloak starts in production mode

```bash
docker logs pulse-keycloak 2>&1 | grep -i "start\|mode\|running"
```

Expected: no `Running in development mode` warning.

```bash
docker logs pulse-keycloak 2>&1 | grep -i "error\|WARN" | grep -v "^$" | head -20
```

Expected: no critical errors. Minor warnings about optional config are acceptable.

## Step 2: Health check passes

```bash
docker inspect pulse-keycloak --format='{{.State.Health.Status}}'
```

Expected: `healthy`

```bash
curl -s http://localhost:8080/health/ready | python3 -m json.tool
```

Expected: `{"status": "UP", ...}`

## Step 3: Realm imported correctly

```bash
curl -s http://localhost:8080/realms/pulse/.well-known/openid-configuration \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('issuer:', d['issuer'])"
```

Expected: `issuer: http://<KC_HOSTNAME>/realms/pulse`

## Step 4: Login still works end-to-end

```bash
# Get a token using an existing user
TOKEN=$(curl -s -X POST \
  "http://localhost:8080/realms/pulse/protocol/openid-connect/token" \
  -d "grant_type=password&client_id=pulse-ui&username=admin&password=admin" \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token','FAILED'))")

echo "Token length: ${#TOKEN}"
```

Expected: token of 400+ characters (not `FAILED`).

```bash
# Use token against API
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/customer/devices | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print('devices:', len(d) if isinstance(d, list) else 'ok')"
```

Expected: device count or `ok`.

## Step 5: Keycloak DB is separate

```bash
docker exec iot-postgres psql -U iot iotcloud -c \
  "SELECT datname FROM pg_database WHERE datname LIKE '%keycloak%';"
```

Expected: `keycloak_db` exists.

```bash
# Confirm no keycloak tables in application DB
docker exec iot-postgres psql -U iot iotcloud -c \
  "SELECT count(*) FROM information_schema.tables WHERE table_name LIKE 'kc_%';"
```

Expected: `count = 0` (keycloak tables are in keycloak_db, not iotcloud).

## Step 6: SMTP config present in realm

```bash
# Check SMTP config via Keycloak admin API
ADMIN_TOKEN=$(curl -s -X POST \
  "http://localhost:8080/realms/master/protocol/openid-connect/token" \
  -d "grant_type=password&client_id=admin-cli&username=${KEYCLOAK_ADMIN_USERNAME}&password=${KEYCLOAK_ADMIN_PASSWORD}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -H "Authorization: Bearer $ADMIN_TOKEN" \
  "http://localhost:8080/admin/realms/pulse" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('smtp host:', d.get('smtpServer',{}).get('host','NOT SET'))"
```

Expected: `smtp host: <value from .env>` (or empty string for local dev with no SMTP).

## Step 7: Commit

```bash
git add \
  compose/docker-compose.yml \
  compose/keycloak/realm-pulse.json \
  compose/.env.example \
  compose/postgres/init-keycloak-db.sh \
  db/keycloak_db_init.sql

git commit -m "feat: Keycloak production mode — dedicated DB, start mode, SMTP, health check

- Keycloak: start-dev → start (production mode, caches enabled)
- KC_HOSTNAME: removes hardcoded 192.168.x.x; fully parameterised via \${KC_HOSTNAME}
- Dedicated keycloak_db database (separate from iotcloud application DB)
- realm-pulse.json: SMTP config via \${env.SMTP_*} substitution
- SMTP env vars in .env.example with Mailpit dev option
- Health check: /health/ready with 60s start_period
- keycloak service_healthy added to ui depends_on"

git push origin main
git log --oneline -3
```

## Definition of Done

- [ ] `docker logs pulse-keycloak` shows NO `development mode` warning
- [ ] `docker inspect pulse-keycloak` health status = `healthy`
- [ ] `/health/ready` returns `{"status": "UP"}`
- [ ] Login and token issuance works end-to-end
- [ ] `keycloak_db` database exists, separate from `iotcloud`
- [ ] No `kc_*` tables in `iotcloud` database
- [ ] SMTP config present in realm (even if host is empty for local dev)
- [ ] No hardcoded IPs in docker-compose.yml (`git grep 192.168` = 0 results)
