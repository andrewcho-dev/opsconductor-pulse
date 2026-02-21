# 001: Merge Duplicate Services

## Goal

Remove the legacy `services/ingest/` and `services/evaluator/` directories entirely. These are dead code -- the docker-compose.yml already uses `ingest_iot/Dockerfile` and `evaluator_iot/Dockerfile` for the `ingest` and `evaluator` service definitions respectively. No running infrastructure depends on the legacy files.

## Context

### Legacy ingest (`services/ingest/ingest.py`)
- Subscribes to `tenant/+/site/+/+` (site-based topic format)
- Writes to `_deprecated_raw_events` table (note the table name is constructed as `"_deprecated_" + "raw" + "_events"` to avoid grep detection)
- No device auth, no rate limiting, no quarantine, no batch writes
- No health endpoint, no metrics

### Current ingest (`services/ingest_iot/ingest.py`)
- Subscribes to `tenant/+/device/+/+` (device-based topic format) plus shadow and command-ack topics
- Device auth via provision token hashing
- Subscription status checking (SUSPENDED/EXPIRED)
- Rate limiting with token buckets
- Quarantine events for rejected messages
- TimescaleDB batch writer
- Health endpoint on port 8080 with /health, /metrics
- Device shadow, command, job execution HTTP endpoints
- Audit logging, structured logging, Prometheus metrics

### Legacy evaluator (`services/evaluator/evaluator.py`)
- Reads from `_deprecated_raw_events` table
- Hardcoded site logic for "MET-GLD" and "MET-ANA" sites
- Manual staleness detection, propagation logic
- Writes to `entity_state` and `site_incident` tables (legacy schema)
- No rule_type support, no anomaly detection, no telemetry_gap

### Current evaluator (`services/evaluator_iot/evaluator.py`)
- Reads from `telemetry` TimescaleDB hypertable via `device_registry` join
- Rule types: threshold, anomaly, telemetry_gap, WINDOW (duration_seconds/duration_minutes)
- Multi-condition rules with match_mode (all/any)
- LISTEN/NOTIFY for reactive evaluation
- Maintenance windows, alert silencing, escalation
- Metric mappings with normalization
- Health endpoint on port 8080 with /health, /metrics
- Audit logging, structured logging, Prometheus metrics

### Docker Compose (current)
The `compose/docker-compose.yml` already points both services to the `_iot` variants:
- `ingest` service: `dockerfile: ingest_iot/Dockerfile`, container name `iot-ingest`
- `evaluator` service: `dockerfile: evaluator_iot/Dockerfile`, container name `iot-evaluator`

There are NO compose service definitions for the legacy `services/ingest/` or `services/evaluator/` directories. They are purely dead code on disk.

## Step-by-Step Changes

### Step 1: Delete `services/ingest/` directory

Delete the entire directory:
```
services/ingest/ingest.py
services/ingest/requirements.txt
```

Verification: confirm no other file in the repo imports from or references `services/ingest/ingest.py`.

Run these searches to confirm no references exist:
```bash
grep -r "services/ingest/" --include="*.py" --include="*.yml" --include="*.yaml" --include="*.sh" --include="*.md" --include="*.toml" .
grep -r "from ingest import" --include="*.py" .
grep -r "ingest/ingest" --include="*.py" --include="*.yml" .
```

All should return no results. The only `ingest` references should be to `ingest_iot`.

### Step 2: Delete `services/evaluator/` directory

Delete the entire directory:
```
services/evaluator/evaluator.py
services/evaluator/requirements.txt
```

Verification: confirm no other file references these files:
```bash
grep -r "services/evaluator/" --include="*.py" --include="*.yml" --include="*.yaml" --include="*.sh" --include="*.md" --include="*.toml" .
grep -r "from evaluator import" --include="*.py" .
grep -r "evaluator/evaluator" --include="*.py" --include="*.yml" .
```

All should return no results. The only `evaluator` references should be to `evaluator_iot`.

### Step 3: Verify docker-compose.yml is correct (no changes needed)

Open `compose/docker-compose.yml` and confirm:

1. **Ingest service** (lines ~75-121):
   - `build.dockerfile: ingest_iot/Dockerfile` (already correct)
   - `container_name: iot-ingest` (already correct)
   - No reference to legacy `services/ingest/`

2. **Evaluator service** (lines ~123-154):
   - `build.dockerfile: evaluator_iot/Dockerfile` (already correct)
   - `container_name: iot-evaluator` (already correct)
   - No reference to legacy `services/evaluator/`

3. **ops_worker service** (lines ~230-270):
   - Has `INGEST_HEALTH_URL: "http://iot-ingest:8080"` -- correct, points to iot-ingest container
   - Has `EVALUATOR_HEALTH_URL: "http://iot-evaluator:8080"` -- correct, points to iot-evaluator container

4. **ui service** (lines ~340-401):
   - Has `INGEST_HEALTH_URL: "http://iot-ingest:8080"` -- correct
   - Has `EVALUATOR_HEALTH_URL: "http://iot-evaluator:8080"` -- correct

No changes to docker-compose.yml are required.

### Step 4: Verify Dockerfiles are correct (no changes needed)

Open `services/ingest_iot/Dockerfile` and confirm it only copies from `ingest_iot/`:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY ingest_iot/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY ingest_iot/ingest.py /app/ingest.py
COPY shared /app/shared
ENV PYTHONUNBUFFERED=1
CMD ["python", "/app/ingest.py"]
```
No reference to legacy `services/ingest/`. No changes needed.

Open `services/evaluator_iot/Dockerfile` and confirm it only copies from `evaluator_iot/`:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY evaluator_iot/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY evaluator_iot/evaluator.py .
COPY shared/ ./shared/
ENV PYTHONUNBUFFERED=1
CMD ["python", "/app/evaluator.py"]
```
No reference to legacy `services/evaluator/`. No changes needed.

### Step 5: Check for any test files referencing legacy services

```bash
grep -r "ingest/ingest\|evaluator/evaluator\|from ingest import\|from evaluator import" tests/ --include="*.py" 2>/dev/null || echo "No test references found"
```

If any test files reference the legacy services, update them to reference the `_iot` variants instead or delete them if they only test the legacy code.

## Verification

```bash
# Confirm directories are deleted
test ! -d services/ingest && echo "PASS: services/ingest removed"
test ! -d services/evaluator && echo "PASS: services/evaluator removed"

# Confirm iot variants still exist
test -f services/ingest_iot/ingest.py && echo "PASS: ingest_iot exists"
test -f services/evaluator_iot/evaluator.py && echo "PASS: evaluator_iot exists"

# Validate compose
cd compose && docker compose config --quiet && echo "PASS: compose valid"

# Build and verify services start
docker compose up -d --build ingest evaluator
docker compose ps | grep -E "ingest|evaluator"
sleep 5
docker compose logs ingest --tail 5
docker compose logs evaluator --tail 5

# Health check
curl -sf http://localhost:8080/health 2>/dev/null || \
  docker compose exec ingest python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8080/health').read().decode())"
```

## Commit

```
refactor: remove legacy ingest and evaluator services

The legacy services/ingest/ and services/evaluator/ directories are dead
code. Docker Compose already uses ingest_iot/Dockerfile and
evaluator_iot/Dockerfile for the ingest and evaluator service definitions.

- Delete services/ingest/ (legacy MQTT ingest writing to _deprecated_raw_events)
- Delete services/evaluator/ (legacy evaluator with hardcoded site logic)
- No compose or Dockerfile changes needed (already using _iot variants)

The ingest_iot service provides: device auth, rate limiting, quarantine,
TimescaleDB batch writes, shadow/command endpoints, audit logging.

The evaluator_iot service provides: threshold/anomaly/telemetry_gap/WINDOW
rule types, multi-condition evaluation, LISTEN/NOTIFY, maintenance windows,
escalation, metric normalization.
```
