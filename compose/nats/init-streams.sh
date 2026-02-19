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
nats stream add ROUTES \
  --server "$NATS_URL" \
  --subjects "routes.>" \
  --retention work \
  --max-age 24h \
  --max-bytes 512MB \
  --storage file \
  --replicas 1 \
  --discard old \
  --defaults 2>/dev/null || true

echo "Stream ROUTES ready"

# ─── Create consumers ──────────────────────────────────
nats consumer add TELEMETRY ingest-workers \
  --server "$NATS_URL" \
  --ack explicit \
  --deliver all \
  --max-deliver 3 \
  --max-pending 1000 \
  --wait 5s \
  --pull \
  --defaults 2>/dev/null || true

echo "Consumer ingest-workers ready"

nats consumer add SHADOW ingest-shadow \
  --server "$NATS_URL" \
  --ack explicit \
  --deliver all \
  --max-deliver 3 \
  --max-pending 1000 \
  --wait 5s \
  --pull \
  --defaults 2>/dev/null || true

echo "Consumer ingest-shadow ready"

nats consumer add COMMANDS ingest-commands \
  --server "$NATS_URL" \
  --ack explicit \
  --deliver all \
  --max-deliver 3 \
  --max-pending 1000 \
  --wait 5s \
  --pull \
  --defaults 2>/dev/null || true

echo "Consumer ingest-commands ready"

nats consumer add ROUTES route-delivery \
  --server "$NATS_URL" \
  --ack explicit \
  --deliver all \
  --max-deliver 3 \
  --wait 30s \
  --max-pending 100 \
  --pull \
  --defaults 2>/dev/null || true

echo "Consumer route-delivery ready"

echo "All streams and consumers initialized"

