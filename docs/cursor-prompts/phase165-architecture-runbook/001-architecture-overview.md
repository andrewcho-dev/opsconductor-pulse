# Task 1: Rewrite Architecture Overview

## File to Modify

- `docs/architecture/overview.md`

## What to Do

Rewrite the architecture overview to reflect the post-rearchitecture state. The current doc describes Mosquitto as the MQTT broker, a monolithic ingest pipeline, and Docker Compose as the only deployment target. After Phases 160–164, the platform uses EMQX, NATS JetStream, a dedicated route delivery service, MinIO for exports, and supports Kubernetes deployment.

### Changes Required

#### 1. Update the Overview section

Replace:
> Devices send telemetry via MQTT (primary) or HTTP (alternate).

With a description that reflects the unified pipeline:
- Devices send telemetry via MQTT (EMQX broker) or HTTP (ui_iot ingestion endpoints)
- Both paths publish to NATS JetStream streams for durable, ordered processing
- NATS consumer groups provide horizontal scaling of ingest workers
- Route delivery is a dedicated service consuming from the ROUTES stream

#### 2. Replace the Architecture Diagram

The current ASCII diagram shows Mosquitto → ingest_iot → PostgreSQL as a direct pipeline. Replace with a diagram that shows:

```
IoT Devices ──MQTT/TLS──► EMQX (clusterable)
                              │
                        NATS Bridge
                              │
                              ▼
Browser SPA ──HTTPS──► Caddy ──► ui_iot (FastAPI)
                                    │
                              HTTP ingest also
                              publishes to NATS
                                    │
                                    ▼
                             NATS JetStream
                          ┌────────┴────────┐
                          │                 │
                    TELEMETRY stream    ROUTES stream
                          │                 │
                          ▼                 ▼
                    ingest_workers    route_delivery
                    (consumer group)  (consumer group)
                          │                 │
                          ▼                 ▼
                    PostgreSQL +      Webhooks/Slack/
                    TimescaleDB       PagerDuty/Teams
                          │
                          ▼
                    evaluator_iot
                          │
                          ▼
                    ops_worker
```

Also show:
- MinIO (S3-compatible) for export storage
- Prometheus scraping EMQX, NATS, ingest, route-delivery, ui_iot, evaluator, ops_worker
- Grafana for dashboards

#### 3. Update the Services section

- **ingest_iot**: Now subscribes to NATS JetStream `TELEMETRY.*.*` subjects (not directly to Mosquitto). Runs as a consumer group (`ingest-workers`) for horizontal scaling. Still validates, rate-limits, and batch-writes to TimescaleDB.
- **ui_iot**: HTTP ingestion endpoints now publish to NATS instead of direct DB writes. Notification routing publishes to NATS `ROUTES.*` instead of inline delivery.
- **evaluator_iot**: Unchanged in core function but benefits from configurable DB pool sizing (Phase 160).
- **ops_worker**: Export worker uses S3/MinIO via boto3. Health monitor and metrics collector have configurable pools.
- **NEW — route_delivery**: Dedicated NATS consumer service for webhook/notification delivery. Consumes from `ROUTES` stream with retry and DLQ semantics.

#### 4. Update the Infrastructure section

- Replace **Mosquitto (MQTT)** with **EMQX (MQTT Broker)**:
  - Clusterable MQTT 5.0 broker
  - HTTP authentication backend for per-device topic ACLs
  - Built-in NATS bridge for telemetry forwarding
  - Native Prometheus metrics at `/api/v5/prometheus/stats`
  - Supports mTLS, WebSocket, and rate limiting at broker level

- Add **NATS JetStream**:
  - Durable message backbone for all inter-service communication
  - Streams: TELEMETRY, SHADOW, COMMANDS, ROUTES
  - Consumer groups enable horizontal scaling without code changes
  - Built-in retry semantics via `max_deliver` and `ack_wait`

- Add **MinIO (S3-compatible storage)**:
  - Export files, reports stored in S3 buckets
  - Pre-signed URLs for direct client downloads
  - Production: swap for AWS S3, GCS, or Azure Blob

- Update **Technology Stack** table:
  - MQTT broker: EMQX (replaces Eclipse Mosquitto)
  - Message backbone: NATS JetStream (new)
  - Object storage: MinIO / S3-compatible (new)
  - Container runtime: Docker Compose (dev) / Kubernetes + Helm (production)

#### 5. Update the Data Flow section

- **Telemetry Ingestion Pipeline**: Now goes Device → EMQX → NATS bridge → TELEMETRY stream → ingest_workers consumer group → TimescaleDB
- **HTTP Ingestion**: ui_iot `/ingest/*` → publish to NATS TELEMETRY → same consumer group
- **Notification Routing**: Alert triggers → publish to NATS ROUTES → route_delivery consumers → webhook/Slack/PagerDuty/Teams

#### 6. Update Configuration section

Add new environment variables:
- NATS: `NATS_URL`, `NATS_CREDS_FILE`
- EMQX: `EMQX_NODE_NAME`, `EMQX_DASHBOARD_*`
- S3: `S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`
- DB pools: `PG_POOL_MIN`, `PG_POOL_MAX` (now configurable, no longer hard-coded)

#### 7. Update YAML frontmatter

```yaml
---
last-verified: 2026-02-19
sources:
  - services/ui_iot/app.py
  - services/evaluator_iot/evaluator.py
  - services/ingest_iot/ingest.py
  - services/ops_worker/main.py
  - services/route_delivery/delivery.py
  - compose/docker-compose.yml
  - compose/emqx/emqx.conf
  - compose/nats/nats-server.conf
phases: [1, 23, 43, 88, 98, 99, 122, 128, 138, 142, 160, 161, 162, 163, 164, 165]
---
```
