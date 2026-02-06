# Phase 26.2: Add Simulator to Docker Compose

## Task

Add the device simulator as a service in docker-compose.

## Add Service

Add to `compose/docker-compose.yml`:

```yaml
  simulator:
    image: python:3.11-slim
    working_dir: /app
    volumes:
      - ../scripts:/app/scripts:ro
    environment:
      INGEST_URL: "http://ui:8080"
      PG_HOST: iot-postgres
      PG_PORT: "5432"
      PG_DB: iotcloud
      PG_USER: iot
      PG_PASS: iot_dev
      NUM_DEVICES_PER_TENANT: "3"
      TELEMETRY_INTERVAL: "10"
      HEARTBEAT_INTERVAL: "30"
    depends_on:
      - ui
      - iot-postgres
    command: >
      sh -c "pip install asyncpg httpx && python scripts/device_simulator.py"
    restart: unless-stopped
    profiles:
      - simulator
```

## Usage

```bash
# Start simulator (runs in background)
cd /home/opsconductor/simcloud/compose
docker compose --profile simulator up -d simulator

# View logs
docker compose logs -f simulator

# Stop simulator
docker compose --profile simulator stop simulator
```

Using `profiles: [simulator]` means it won't start with normal `docker compose up`, only when explicitly requested.

## Verification

```bash
# Start simulator
docker compose --profile simulator up -d simulator

# Watch logs for telemetry being sent
docker compose logs -f simulator

# Check dashboard - should see live data updating
# Check device detail page - charts should show recent data
```

Expected log output:
```
[telemetry] warehouse-east-sim-01 seq=1 battery=95.3%
[heartbeat] warehouse-east-sim-01 seq=1
[telemetry] warehouse-east-sim-02 seq=1 battery=88.7%
...
```

## Files

| Action | File |
|--------|------|
| MODIFY | `compose/docker-compose.yml` |
