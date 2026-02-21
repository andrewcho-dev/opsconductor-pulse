# Phase 111 — Add Migrator Service to docker-compose.yml

## File to modify
`compose/docker-compose.yml`

## Step 1: Add the migrator service

Add this service definition. Place it after `pgbouncer` and before `ingest`:

```yaml
  migrator:
    build:
      context: ../db
      dockerfile: Dockerfile.migrator
    container_name: iot-migrator
    environment:
      NOTIFY_DATABASE_URL: "postgresql://iot:${PG_PASS}@iot-postgres:5432/iotcloud"
      DATABASE_URL: "postgresql://iot:${PG_PASS}@iot-postgres:5432/iotcloud"
    depends_on:
      postgres:
        condition: service_healthy
    restart: "no"
    networks:
      - iot-network
```

Key points:
- `restart: "no"` — runs once and exits. Does not restart.
- Uses `iot-postgres` directly (not pgbouncer) — DDL requires a real session connection.
- `depends_on` with `service_healthy` ensures Postgres is accepting connections before migrations run.

## Step 2: Add migrator as dependency for all application services

Every application service that uses the database must wait for the migrator
to complete successfully before starting. Update `depends_on` for these
services: `ingest`, `evaluator`, `dispatcher`, `delivery_worker`, `ops_worker`,
`ui`, `api`, `subscription-worker`.

For each, add or update `depends_on`:

```yaml
  ingest:
    depends_on:
      postgres:
        condition: service_healthy
      pgbouncer:
        condition: service_healthy
      migrator:
        condition: service_completed_successfully  # ← add this
```

Apply the same `migrator: condition: service_completed_successfully` to all
other application services.

**Important:** `service_completed_successfully` requires Docker Compose v2.
Verify:
```bash
docker compose version
```
Expected: `Docker Compose version v2.x.x`

## Step 3: Add health checks to services that are missing them

While editing docker-compose.yml, add missing health checks:

### ui service
```yaml
  ui:
    healthcheck:
      test: ["CMD", "python3", "-c",
        "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 20s
```

### api (provision_api) service
```yaml
  api:
    healthcheck:
      test: ["CMD", "python3", "-c",
        "import urllib.request; urllib.request.urlopen('http://localhost:8081/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 20s
```

### ops_worker service
```yaml
  ops_worker:
    healthcheck:
      test: ["CMD", "python3", "-c", "import sys; sys.exit(0)"]
      interval: 60s
      timeout: 5s
      retries: 3
```

(ops_worker has no HTTP port — a process-alive check is sufficient.)

### subscription-worker service
Same pattern as ops_worker.

## Step 4: Pin image tags

Replace floating `latest` tags with pinned versions:

```yaml
# BEFORE
image: timescale/timescaledb:latest-pg16
image: edoburu/pgbouncer:latest
image: eclipse-mosquitto:2.0
image: caddy:2-alpine
image: quay.io/keycloak/keycloak:26.0

# AFTER — pin to specific versions
image: timescale/timescaledb:2.16.1-pg16
image: edoburu/pgbouncer:1.23.1
image: eclipse-mosquitto:2.0.18
image: caddy:2.8.4-alpine
image: quay.io/keycloak/keycloak:26.0.0
```

Verify current versions in use:
```bash
docker images | grep -E "timescale|pgbouncer|mosquitto|caddy|keycloak"
```

Use whatever versions are currently running (as shown by `docker images`) —
pinning to what's running ensures no unintended upgrade during this phase.
