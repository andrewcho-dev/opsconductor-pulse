# Task 001: InfluxDB Infrastructure

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> This task adds InfluxDB 3 Core to the Docker Compose stack and wires env vars to all services that will use it.
> RUN THE TESTS in the Test section. Do not proceed if tests fail.

---

## Context

We are migrating time-series telemetry data from PostgreSQL `raw_events` table to InfluxDB 3 Core. This task sets up the infrastructure: the InfluxDB container, environment variables, and health checks.

**Read first**:
- `compose/docker-compose.yml` (full file — understand all services and their depends_on)
- `compose/.env` (current env vars)
- `compose/.env.example` (documented env vars)

---

## Task

### 1.1 Add InfluxDB service to Docker Compose

In `compose/docker-compose.yml`, add a new `influxdb` service block **after** the `postgres` service (after line 31). Insert it before the `ingest` service:

```yaml
  influxdb:
    image: influxdb:3-core
    container_name: iot-influxdb
    environment:
      INFLUXDB3_HTTP_BIND_ADDR: "0.0.0.0:8181"
      INFLUXDB3_DB_DIR: /var/lib/influxdb3
      INFLUXDB3_AUTH_TOKEN: "${INFLUXDB_TOKEN:-influx-dev-token-change-me}"
    ports:
      - "8181:8181"
    volumes:
      - ../data/influxdb3:/var/lib/influxdb3
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8181/health"]
      interval: 5s
      timeout: 5s
      retries: 12
      start_period: 10s
    restart: unless-stopped
```

### 1.2 Add InfluxDB env vars to `ingest` service

In the `ingest` service environment block (currently lines 36-49), add these two env vars at the end:

```yaml
      INFLUXDB_URL: "http://iot-influxdb:8181"
      INFLUXDB_TOKEN: "${INFLUXDB_TOKEN:-influx-dev-token-change-me}"
```

In the `ingest` depends_on block (currently lines 50-54), add:

```yaml
      influxdb:
        condition: service_healthy
```

### 1.3 Add InfluxDB env vars to `evaluator` service

In the `evaluator` service environment block (currently lines 60-67), add the same two env vars:

```yaml
      INFLUXDB_URL: "http://iot-influxdb:8181"
      INFLUXDB_TOKEN: "${INFLUXDB_TOKEN:-influx-dev-token-change-me}"
```

In the `evaluator` depends_on block (currently lines 68-70), add:

```yaml
      influxdb:
        condition: service_healthy
```

### 1.4 Add InfluxDB env vars to `ui` service

In the `ui` service environment block (currently lines 140-153), add the same two env vars:

```yaml
      INFLUXDB_URL: "http://iot-influxdb:8181"
      INFLUXDB_TOKEN: "${INFLUXDB_TOKEN:-influx-dev-token-change-me}"
```

In the `ui` depends_on block (currently lines 156-160), add:

```yaml
      influxdb:
        condition: service_healthy
```

### 1.5 Add InfluxDB env vars to `api` service

In the `api` (provision_api) service environment block (currently lines 166-173), add the same two env vars:

```yaml
      INFLUXDB_URL: "http://iot-influxdb:8181"
      INFLUXDB_TOKEN: "${INFLUXDB_TOKEN:-influx-dev-token-change-me}"
```

In the `api` depends_on block (currently lines 176-178), add:

```yaml
      influxdb:
        condition: service_healthy
```

### 1.6 Update `.env` file

Append to `compose/.env`:

```
INFLUXDB_TOKEN=influx-dev-token-change-me
```

### 1.7 Update `.env.example` file

Append to `compose/.env.example` (after line 17):

```

# InfluxDB 3 Core auth token
INFLUXDB_TOKEN=influx-dev-token-change-me
```

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| MODIFY | `compose/docker-compose.yml` |
| MODIFY | `compose/.env` |
| MODIFY | `compose/.env.example` |

---

## Test

```bash
# 1. Validate docker-compose YAML syntax
cd compose && docker compose config --quiet

# 2. Start the stack
docker compose up -d

# 3. Wait for InfluxDB health check
sleep 15

# 4. Verify InfluxDB is healthy
curl -sf http://localhost:8181/health && echo "InfluxDB healthy"

# 5. Verify all services are running
docker compose ps

# 6. Run existing unit tests (no regressions)
cd /home/opsconductor/simcloud
python -m pytest tests/unit/ -v -x
```

---

## Acceptance Criteria

- [ ] `compose/docker-compose.yml` has an `influxdb` service with image `influxdb:3-core`
- [ ] InfluxDB listens on port 8181 with health check
- [ ] `ingest`, `evaluator`, `ui`, and `api` services have `INFLUXDB_URL` and `INFLUXDB_TOKEN` env vars
- [ ] `ingest`, `evaluator`, `ui`, and `api` services depend on `influxdb` with `service_healthy`
- [ ] `compose/.env` contains `INFLUXDB_TOKEN`
- [ ] `compose/.env.example` documents the `INFLUXDB_TOKEN` variable
- [ ] `curl http://localhost:8181/health` returns 200
- [ ] All existing unit tests still pass

---

## Commit

```
Add InfluxDB 3 Core to Docker Compose stack

- Add influxdb service with health check on port 8181
- Add INFLUXDB_URL and INFLUXDB_TOKEN env vars to ingest, evaluator, ui, api
- Add depends_on influxdb to all consuming services
- Update .env and .env.example with INFLUXDB_TOKEN

Part of Phase 11: InfluxDB Telemetry Migration
```
