# Task 4: Update Per-Service Documentation

## Files to Modify

- `docs/services/ingest.md` — NATS consumer model, configurable pools, graceful shutdown
- `docs/services/ui-iot.md` — HTTP ingest now publishes to NATS, route delivery decoupled
- `docs/services/evaluator.md` — Configurable pool sizing
- `docs/services/ops-worker.md` — S3 export workflow, configurable pools
- Create `docs/services/route-delivery.md` — New dedicated delivery service

## What to Do

### 1. Update `docs/services/ingest.md`

Read the current content, then update:

**Connection model:**
- Replaces direct Mosquitto subscription with NATS JetStream consumer
- Consumer group: `ingest-workers` on `TELEMETRY` stream
- Subscribes to `telemetry.>` (all tenants) — tenant isolation via subject parsing
- Horizontal scaling: add more replicas, NATS distributes messages automatically

**Processing pipeline:**
- Message arrives from NATS with subject `telemetry.{tenant_id}.{device_id}`
- Same 6-layer validation pipeline (auth cache, rate limit, payload validation, quarantine)
- Batch writer flushes to TimescaleDB on interval or batch size threshold
- On validation failure: message is NAK'd or sent to quarantine, not retried

**Graceful shutdown (Phase 160):**
- SIGTERM handler drains NATS subscription (no new messages)
- Flushes batch writer (`stop()` now called)
- Closes DB pool connections
- Exit after drain timeout

**Configurable DB pools (Phase 160):**
- `PG_POOL_MIN` and `PG_POOL_MAX` environment variables (no longer hard-coded at 2/10)

**Prometheus metrics:**
- `pulse_ingest_messages_total` (labels: `tenant_id`, `result`)
- `pulse_ingest_batch_write_seconds` (labels: `tenant_id`)
- `pulse_ingest_nats_pending` (gauge)

### 2. Update `docs/services/ui-iot.md`

Read the current content, then update:

**HTTP ingestion:**
- `/ingest/*` endpoints now publish to NATS `TELEMETRY.{tenant_id}.{device_id}` instead of direct DB writes
- This unifies the ingestion pipeline — same consumers process MQTT and HTTP telemetry
- Removes the separate `TimescaleBatchWriter` instance that previously ran inside ui_iot

**Route delivery decoupled (Phase 160 + 162):**
- Alert routing no longer delivers inline in ui_iot request handlers
- Instead, route match publishes a delivery job to NATS `ROUTES.{tenant_id}.{route_id}`
- Dedicated `route_delivery` service handles actual webhook/notification delivery
- Removes the 10-second webhook timeout that previously blocked ingest workers

**EMQX auth backend (Phase 161):**
- New internal endpoint: `POST /api/v1/internal/mqtt-auth`
- Called by EMQX HTTP auth plugin for device authentication + topic ACL
- Returns allowed publish/subscribe topics per device

### 3. Update `docs/services/evaluator.md`

Read the current content, then update:

**Configurable DB pools:**
- `PG_POOL_MIN` / `PG_POOL_MAX` environment variables (Phase 160)

**No other changes** — evaluator still polls TimescaleDB directly. Future phases may move to NATS-triggered evaluation.

### 4. Update `docs/services/ops-worker.md`

Read the current content, then update:

**Export worker (Phase 164):**
- Uses boto3 to upload exports to S3/MinIO instead of local filesystem
- Stores S3 key in export job record
- Download endpoint generates pre-signed URLs (1-hour expiry)
- Environment variables: `S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`
- `export-data` Docker volume removed

**Configurable DB pools:**
- `PG_POOL_MIN` / `PG_POOL_MAX` environment variables (Phase 160)

### 5. Create `docs/services/route-delivery.md`

New file for the dedicated route delivery service (Phase 162 Task 5):

```markdown
---
last-verified: 2026-02-19
sources:
  - services/route_delivery/delivery.py
phases: [162, 165]
---

# Route Delivery Service

> Dedicated webhook and notification delivery service.

## Overview

Consumes route delivery jobs from NATS JetStream and delivers notifications to configured destinations.

## Architecture

- NATS consumer group: `route-delivery` on `ROUTES` stream
- Subscribes to: `routes.>`
- Horizontal scaling: add replicas, NATS distributes jobs

## Delivery Targets

- HTTP webhook (HMAC signed)
- Slack incoming webhook
- PagerDuty Events API v2
- Microsoft Teams webhook (MessageCard)

## Retry Semantics

- NATS `max_deliver`: 5 attempts
- `ack_wait`: 30s (message redelivered if not ack'd)
- After max retries: message goes to DLQ stream
- DLQ can be replayed manually via NATS CLI

## Prometheus Metrics

- `pulse_delivery_total` (labels: `tenant_id`, `destination_type`, `result`)
- `pulse_delivery_seconds` (labels: `destination_type`)
- `pulse_delivery_dlq_total` (labels: `tenant_id`)

Metrics server on port 8080.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| NATS_URL | nats://iot-nats:4222 | NATS server URL |
| PG_POOL_MIN | 2 | Min DB pool connections |
| PG_POOL_MAX | 10 | Max DB pool connections |
| DELIVERY_TIMEOUT | 10 | HTTP delivery timeout (seconds) |
| DELIVERY_MAX_RETRIES | 5 | Max NATS redelivery attempts |

## Health

- `GET :8080/health` — readiness check
- `GET :8080/metrics` — Prometheus metrics
```

### 6. Update YAML frontmatter on all modified files

- Set `last-verified: 2026-02-19`
- Add `165` (and relevant earlier phases: `160`, `161`, `162`, `164`) to the `phases` array
- Add new source paths as applicable
