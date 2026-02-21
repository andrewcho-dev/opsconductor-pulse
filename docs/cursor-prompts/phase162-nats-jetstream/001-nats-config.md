# Task 1: Add NATS JetStream to Docker Compose

## Files to Create/Modify

- **Create:** `compose/nats/nats.conf`
- **Create:** `compose/nats/init-streams.sh` — one-time stream creation script
- **Modify:** `compose/docker-compose.yml`

## What to Do

### Step 1: Create NATS configuration

Create `compose/nats/nats.conf`:

```
# NATS Server Configuration for OpsConductor-Pulse

# Server
server_name: pulse-nats
listen: 0.0.0.0:4222

# HTTP monitoring
http_port: 8222

# JetStream (durable streams)
jetstream {
  store_dir: /data/jetstream
  max_mem: 256MB
  max_file: 2GB
}

# Cluster-ready configuration (single node for now)
# To add nodes later, uncomment and configure:
# cluster {
#   name: pulse-nats-cluster
#   listen: 0.0.0.0:6222
#   routes: [
#     nats-route://nats-1:6222
#     nats-route://nats-2:6222
#   ]
# }

# Logging
debug: false
trace: false
logtime: true

# Limits
max_payload: 1MB
max_connections: 1024
```

### Step 2: Create stream initialization script

Create `compose/nats/init-streams.sh`:

```bash
#!/bin/bash
# Initialize NATS JetStream streams for OpsConductor-Pulse
# Run once after NATS starts (idempotent — safe to re-run)

set -e

NATS_URL="${NATS_URL:-nats://iot-nats:4222}"

echo "Waiting for NATS..."
until nats server check connection --server "$NATS_URL" 2>/dev/null; do
  sleep 1
done
echo "NATS is ready"

# ─── TELEMETRY stream ──────────────────────────────────
# Device telemetry messages from EMQX and HTTP ingest
nats stream add TELEMETRY \
  --server "$NATS_URL" \
  --subjects "telemetry.>" \
  --retention limits \
  --max-msgs-per-subject 100000 \
  --max-age 1h \
  --max-bytes 1GB \
  --storage file \
  --replicas 1 \
  --discard old \
  --dupe-window 2m \
  --no-deny-delete \
  --no-deny-purge \
  --defaults 2>/dev/null || \
nats stream update TELEMETRY \
  --server "$NATS_URL" \
  --max-age 1h \
  --max-bytes 1GB \
  --force 2>/dev/null || true

echo "Stream TELEMETRY ready"

# ─── SHADOW stream ─────────────────────────────────────
# Device shadow/twin reported state updates
nats stream add SHADOW \
  --server "$NATS_URL" \
  --subjects "shadow.>" \
  --retention limits \
  --max-msgs-per-subject 10000 \
  --max-age 1h \
  --max-bytes 256MB \
  --storage file \
  --replicas 1 \
  --discard old \
  --defaults 2>/dev/null || true

echo "Stream SHADOW ready"

# ─── COMMANDS stream ───────────────────────────────────
# Device command acknowledgments
nats stream add COMMANDS \
  --server "$NATS_URL" \
  --subjects "commands.>" \
  --retention limits \
  --max-msgs-per-subject 10000 \
  --max-age 1h \
  --max-bytes 256MB \
  --storage file \
  --replicas 1 \
  --discard old \
  --defaults 2>/dev/null || true

echo "Stream COMMANDS ready"

# ─── ROUTES stream ─────────────────────────────────────
# Message route delivery jobs (webhooks, MQTT republish)
nats stream add ROUTES \
  --server "$NATS_URL" \
  --subjects "routes.>" \
  --retention work \
  --max-age 24h \
  --max-bytes 512MB \
  --storage file \
  --replicas 1 \
  --discard old \
  --max-deliver 3 \
  --defaults 2>/dev/null || true

echo "Stream ROUTES ready"

# ─── Create consumers ──────────────────────────────────

# Ingest workers consumer group
nats consumer add TELEMETRY ingest-workers \
  --server "$NATS_URL" \
  --filter "" \
  --ack explicit \
  --deliver all \
  --max-deliver 3 \
  --max-pending 1000 \
  --wait 5s \
  --pull \
  --defaults 2>/dev/null || true

echo "Consumer ingest-workers ready"

# Route delivery consumer group
nats consumer add ROUTES route-delivery \
  --server "$NATS_URL" \
  --filter "" \
  --ack explicit \
  --deliver all \
  --max-deliver 3 \
  --ack-wait 30s \
  --max-pending 100 \
  --pull \
  --defaults 2>/dev/null || true

echo "Consumer route-delivery ready"

echo "All streams and consumers initialized"
```

Make it executable: `chmod +x compose/nats/init-streams.sh`

### Step 3: Add NATS service to docker-compose.yml

Add after the `pgbouncer` service:

```yaml
  nats:
    image: nats:2.10-alpine
    container_name: iot-nats
    command: ["-c", "/etc/nats/nats.conf"]
    ports:
      - "127.0.0.1:4222:4222"   # NATS client
      - "127.0.0.1:8222:8222"   # HTTP monitoring
    volumes:
      - ./nats/nats.conf:/etc/nats/nats.conf:ro
      - nats-data:/data
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:8222/healthz"]
      interval: 5s
      timeout: 3s
      retries: 12
      start_period: 5s
    restart: unless-stopped

  nats-init:
    image: natsio/nats-box:latest
    container_name: iot-nats-init
    entrypoint: ["/bin/sh", "/scripts/init-streams.sh"]
    environment:
      NATS_URL: "nats://iot-nats:4222"
    volumes:
      - ./nats/init-streams.sh:/scripts/init-streams.sh:ro
    depends_on:
      nats:
        condition: service_healthy
    restart: "no"
```

Add the `nats-data` volume:

```yaml
volumes:
  nats-data:
  # ... existing volumes ...
```

### Step 4: Add NATS dependency to ingest and ui services

```yaml
  ingest:
    depends_on:
      nats:
        condition: service_healthy
      # ... existing depends_on ...
    environment:
      # ... existing ...
      NATS_URL: "nats://iot-nats:4222"

  ui:
    environment:
      # ... existing ...
      NATS_URL: "nats://iot-nats:4222"
```

## Important Notes

- **Retention `limits` vs `work`:** TELEMETRY/SHADOW/COMMANDS use `limits` (keep messages for 1h max). ROUTES uses `work` (message is removed after acknowledgment — like a work queue).
- **`max-deliver 3`:** Messages are retried up to 3 times if a consumer NAKs. After 3 attempts, the message is dropped (for TELEMETRY) or needs manual intervention (for ROUTES).
- **`max-age 1h`:** Telemetry messages older than 1 hour are automatically purged. The batch writer should process them well within this window. This prevents unbounded storage growth.
- **Subject naming:** `telemetry.{tenant_id}` allows per-tenant filtering and future partitioning. Consumers can subscribe to `telemetry.>` for all tenants or `telemetry.specific-tenant` for one.
- **Single node for now:** The `replicas 1` setting means no replication. To add HA later, increase replicas and add cluster config.
- **nats-box:** The init container uses `natsio/nats-box` which includes the `nats` CLI tool. It runs once and exits.

## Verification

```bash
# NATS health
curl -s http://localhost:8222/healthz

# List streams
docker exec iot-nats-init nats stream ls --server nats://iot-nats:4222

# Stream info
docker exec iot-nats-init nats stream info TELEMETRY --server nats://iot-nats:4222

# Publish a test message
docker exec iot-nats-init nats pub telemetry.test-tenant '{"test":1}' --server nats://iot-nats:4222

# Verify it's in the stream
docker exec iot-nats-init nats stream info TELEMETRY --server nats://iot-nats:4222 | grep "Messages:"
```
