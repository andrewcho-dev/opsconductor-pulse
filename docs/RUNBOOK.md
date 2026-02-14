# OpsConductor-Pulse — Operations Runbook

Procedures for deployment, migrations, maintenance, and troubleshooting.

---

## Deployment

### Start the platform
```bash
cd compose/
docker compose up -d --build
```

### Start with simulator
```bash
docker compose --profile simulator up -d --build
```

### Check status
```bash
docker compose ps
docker compose logs -f ui
docker compose logs -f ingest
```

### Stop
```bash
docker compose down
# Preserve data volumes:
docker compose down --remove-orphans
```

---

## Rebuilding Services

### After any backend Python change
```bash
docker compose build ui && docker compose up -d ui
```

### After frontend change (React)
```bash
cd frontend && npm run build
docker compose restart ui    # or just hard-refresh browser if dist/ is volume-mounted
```

> **Critical**: If you add a new top-level Python package directory under
> `services/ui_iot/` (e.g., `oncall/`, `notifications/`, `reports/`), you
> **must** add a `COPY <package> /app/<package>` line in
> `services/ui_iot/Dockerfile` before rebuilding. Missing this causes
> `ModuleNotFoundError` on startup.

### Rebuild all services
```bash
docker compose build && docker compose up -d
```

---

## Database Migrations

Migrations are in `db/migrations/` numbered `000` through `069` (and growing).
They are **idempotent** — all use `CREATE TABLE IF NOT EXISTS`, `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`, etc.

### Apply a single migration
```bash
psql "$DATABASE_URL" -f db/migrations/066_escalation_policies.sql
```

### Apply all migrations in order
```bash
for f in $(ls db/migrations/*.sql | sort); do
  echo "Applying $f..."
  psql "$DATABASE_URL" -f "$f"
done
```

### Connect to the database directly
```bash
docker compose exec postgres psql -U iot -d iotcloud
```

### DATABASE_URL format
```
postgresql://iot:iot_dev@localhost:5432/iotcloud
# or via pgbouncer:
postgresql://iot:iot_dev@localhost:6432/iotcloud
```

---

## Migration History

When adding a new migration:
1. Number it sequentially (next after `069` is `070`)
2. Use `IF NOT EXISTS` / `IF EXISTS` guards throughout
3. Add an entry to the Migration Index in [PROJECT_MAP.md](PROJECT_MAP.md)
4. Apply to running DB: `psql "$DATABASE_URL" -f db/migrations/070_....sql`
5. Commit both the migration file and the Runbook/ProjectMap update

---

## Frontend Build

```bash
cd frontend
npm install          # first time or after package.json changes
npm run build        # production build → frontend/dist/
npx tsc --noEmit     # type check only
npm run dev          # Vite dev server (proxies API to configured backend)
```

The built `frontend/dist/` is volume-mounted into the `ui` container at `/app/spa`.
After `npm run build`, restart the ui container (or just hard-refresh the browser
if the container already mounts the dist directory).

---

## Common Troubleshooting

### App not loading (`502 Bad Gateway` or blank page)

1. Check ui container logs:
   ```bash
   docker compose logs --tail=50 ui
   ```
2. Look for `ModuleNotFoundError` — means a new Python package was added to
   `services/ui_iot/` but not copied in the Dockerfile.
   Fix: Add `COPY <package> /app/<package>` to `services/ui_iot/Dockerfile`, then:
   ```bash
   docker compose build ui && docker compose up -d ui
   ```
3. Check if the container is running:
   ```bash
   docker compose ps ui
   ```

### 422 on `/customer/alerts`

The `/customer/alerts` endpoint only accepts `status` values:
`OPEN | ACKNOWLEDGED | CLOSED | ALL`

Do **not** pass severity values (CRITICAL, HIGH, etc.) as `status`.
Severity filtering is always done client-side after fetching.

Also check: `limit` parameter max is **200**. Passing `limit=500` causes 422.

### 500 on `/customer/subscriptions` or similar

Usually a `pool NameError` — a route handler is missing `pool=Depends(get_db_pool)`
in its function signature. Check that all routes that use `pool` declare it as
a FastAPI dependency parameter.

### `/api/v2/devices` 500 after new migration

Missing migration applied to running database. Apply the migration:
```bash
psql "$DATABASE_URL" -f db/migrations/058_device_decommission.sql
```
Then restart: `docker compose restart ui`

### pgbouncer fails to start (image not found)

Use `edoburu/pgbouncer:latest` — the `1.22.1` tag was removed from Docker Hub.
Check `compose/docker-compose.yml`.

### Stale browser bundle (old JS still loading)

1. Rebuild frontend: `cd frontend && npm run build`
2. Restart ui container: `docker compose restart ui`
3. Hard-refresh browser: `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (Mac)

Verify the new bundle is loading by checking the JS filename hash in the network tab.

### On-call schedule not resolving correct responder

The resolver uses `NOW()` in the server timezone (UTC by default). If the schedule
timezone differs from UTC, verify the `timezone` field on the schedule is set correctly
and that the `handoff_hour` is expressed in the schedule's local timezone.

### Escalation worker not firing

Check logs: `docker compose logs --tail=100 ui | grep escalation`

Common issues:
- `next_escalation_at` column missing → apply migration 066
- `escalation_policy_id` not linked on `alert_rules` row → set via PUT /customer/escalation-policies

---

## Accessing Running Services

### Application (browser)
```
https://192.168.10.53   (or https://localhost)
```
Accept the self-signed certificate warning.

### Keycloak Admin Console
```
https://192.168.10.53/admin
Username: admin
Password: admin_dev
```

### Provisioning API
```
http://localhost:8081
Header: X-Admin-Key: <value from compose/.env>
```

### Database (direct)
```bash
docker compose exec postgres psql -U iot -d iotcloud
# or
psql "postgresql://iot:iot_dev@localhost:5432/iotcloud"
```

### MQTT (mosquitto_pub / mosquitto_sub)
```bash
mosquitto_pub -h localhost -p 1883 -t "devices/tenant-a/sensor-001/telemetry" \
  -m '{"metrics":{"temp_c":25.5}}'
```

---

## Running Tests

### Unit tests
```bash
python3 -m pytest tests/unit/ -v
```

### Unit tests with coverage
```bash
pytest --cov=services tests/unit/ --cov-report=html
open htmlcov/index.html
```

### Specific test file
```bash
pytest tests/unit/test_escalation.py -v
```

### Frontend tests
```bash
cd frontend && npm test
```

---

## Environment Variables

### Core database
| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://iot:iot_dev@postgres:5432/iotcloud` | PostgreSQL connection string |
| `TIMESCALE_BATCH_SIZE` | `1000` | Telemetry batch insert size |
| `TIMESCALE_FLUSH_INTERVAL_MS` | `1000` | Max batch wait time (ms) |

### Authentication
| Variable | Default | Description |
|----------|---------|-------------|
| `KEYCLOAK_URL` | `https://localhost` | Keycloak server URL |
| `KEYCLOAK_REALM` | `pulse` | Keycloak realm name |
| `AUTH_CACHE_TTL_SECONDS` | `300` | JWKS cache TTL |

### Ingestion
| Variable | Default | Description |
|----------|---------|-------------|
| `INGEST_WORKER_COUNT` | `4` | Parallel MQTT ingest workers |
| `INGEST_QUEUE_SIZE` | `10000` | Message queue depth |
| `API_RATE_LIMIT` | `100` | Requests per window per tenant |
| `API_RATE_WINDOW_SECONDS` | `60` | Rate limit window |
| `WS_POLL_SECONDS` | `5` | WebSocket push interval |

### Delivery (legacy)
| Variable | Default | Description |
|----------|---------|-------------|
| `WORKER_MAX_ATTEMPTS` | `5` | Max retry attempts |
| `WORKER_BACKOFF_BASE_SECONDS` | `30` | Initial retry delay |
| `WORKER_TIMEOUT_SECONDS` | `30` | HTTP/SNMP/SMTP timeout |

---

## Data Retention

| Data | Retention | Policy |
|------|-----------|--------|
| Telemetry (hypertable) | 90 days | TimescaleDB retention policy |
| System metrics (hypertable) | 90 days | TimescaleDB retention policy |
| Telemetry compression | After 7 days | TimescaleDB compression policy |
| Closed alerts | Indefinite | No automatic purge |
| Operator audit log | Indefinite | No automatic purge |
| Notification log | Indefinite | Consider periodic cleanup |
| Report runs | Indefinite | Consider periodic cleanup |

---

## Security Notes

- **HTTPS**: Caddy uses a self-signed certificate. For production, replace with a
  CA-signed certificate or use Caddy's ACME/Let's Encrypt integration.
- **Admin key**: The provisioning API `X-Admin-Key` value is in `compose/.env`.
  Rotate it before any production deployment.
- **Keycloak default password**: Change `admin_dev` before production.
- **SSRF protection**: Webhook URLs and SNMP/SMTP hosts are validated to block
  private IP ranges, loopback, and cloud metadata endpoints.
- **Secrets in notification channels**: Webhook secrets and integration keys are
  stored in the `config` JSONB column. Mask them in API responses (return `"***"`
  for secret fields).
