# Phase 24.2: Add Seed Command to Compose

## Task

Make it easy to run the seed script inside the Docker network.

## Option A: One-off docker compose run

Add a `seed` service to `compose/docker-compose.yml`:

```yaml
  seed:
    image: python:3.11-slim
    working_dir: /app
    volumes:
      - ../scripts:/app/scripts:ro
    environment:
      PG_HOST: iot-postgres
      PG_PORT: "5432"
      PG_DB: iotcloud
      PG_USER: iot
      PG_PASS: iot_dev
      INFLUXDB_URL: "http://iot-influxdb:8181"
      INFLUXDB_TOKEN: "${INFLUXDB_TOKEN:-influx-dev-token-change-me}"
    depends_on:
      - iot-postgres
      - iot-influxdb
    command: >
      sh -c "pip install asyncpg httpx && python scripts/seed_demo_data.py"
    profiles:
      - seed
```

**Usage:**
```bash
cd /home/opsconductor/simcloud/compose
docker compose --profile seed run --rm seed
```

The `profiles: [seed]` means it won't start with normal `docker compose up`.

## Option B: Script with docker compose exec

Create `scripts/run_seed.sh`:

```bash
#!/bin/bash
set -e
cd "$(dirname "$0")/.."

echo "Installing dependencies in ui container..."
docker compose exec -T ui pip install asyncpg httpx

echo "Running seed script..."
docker compose exec -T ui python /app/scripts/seed_demo_data.py
```

This requires mounting scripts into ui container.

## Recommended: Option A

Use the dedicated seed service with `profiles`. Cleaner separation.

## Verification

```bash
# Run seed
cd /home/opsconductor/simcloud/compose
docker compose --profile seed run --rm seed

# Verify data
docker compose exec iot-postgres psql -U iot -d iotcloud -c "SELECT tenant_id, COUNT(*) FROM device_registry GROUP BY tenant_id"
docker compose exec iot-postgres psql -U iot -d iotcloud -c "SELECT tenant_id, COUNT(*) FROM alert_rules GROUP BY tenant_id"
docker compose exec iot-postgres psql -U iot -d iotcloud -c "SELECT tenant_id, status, COUNT(*) FROM fleet_alert GROUP BY tenant_id, status"

# Check InfluxDB
curl -s "http://localhost:8181/api/v3/query_sql?db=telemetry_tenant-a&format=json" \
  -H "Authorization: Bearer influx-dev-token-change-me" \
  -d "SELECT COUNT(*) FROM telemetry"
```

## Expected Output After Seed

| Table | Count |
|-------|-------|
| device_registry | 30 (15 per tenant) |
| device_state | 30 |
| alert_rules | 10 (5 per tenant) |
| fleet_alert | ~6-10 (STALE + threshold violations) |
| InfluxDB telemetry | ~60,000 points (30 devices × 2016 points) |

## Files

| Action | File |
|--------|------|
| MODIFY | `compose/docker-compose.yml` |
