---
last-verified: 2026-02-19
sources:
  - services/ui_iot/app.py
  - services/ui_iot/routes/ingest.py
  - services/ui_iot/routes/internal.py
  - services/ui_iot/routes/templates.py
  - services/evaluator_iot/evaluator.py
  - services/ingest_iot/ingest.py
  - services/ops_worker/main.py
  - services/mqtt_nats_bridge/bridge.py
  - services/route_delivery/delivery.py
  - compose/docker-compose.yml
  - compose/emqx/emqx.conf
  - compose/nats/nats.conf
  - compose/nats/init-streams.sh
  - db/migrations/109_device_templates.sql
  - db/migrations/110_seed_device_templates.sql
  - db/migrations/111_device_modules.sql
  - db/migrations/112_device_sensors_transports.sql
  - db/migrations/113_device_registry_template_fk.sql
phases: [1, 23, 43, 88, 98, 99, 122, 128, 138, 142, 160, 161, 162, 163, 164, 165, 166, 167, 168]
---

# System Architecture

> One authoritative reference for the OpsConductor-Pulse platform architecture.

## Overview

OpsConductor-Pulse is a multi-tenant IoT fleet management and operations platform:

- Devices send telemetry via MQTT (EMQX broker, mTLS) or HTTP (`ui_iot` ingest endpoints).
- Both paths publish envelopes into NATS JetStream using PubAck (`js.publish()`).
- `ingest_iot` consumes from JetStream as a horizontally-scalable worker group and batch-writes telemetry to TimescaleDB.
- `evaluator_iot` evaluates telemetry for device state + alerts.
- Message route delivery is decoupled: `ingest_iot` publishes delivery jobs to JetStream and `route_delivery` executes webhook/MQTT republish asynchronously.
- Export artifacts are stored in S3-compatible object storage (MinIO in compose; AWS S3 in production).
- Prometheus + Grafana provide operational metrics and dashboards (including NATS/JetStream metrics via `nats-exporter`).

## Architecture Diagram

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                                External Actors                                │
│                                                                               │
│  IoT Devices (MQTT/TLS)            Browser SPA (customers/operators)           │
│                                                                               │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
          MQTT/TLS (:8883)                 HTTPS (:443)
          MQTT/WS  (:9001)                       │
                │                               ▼
                │                    ┌──────────────────────┐
                │                    │ Caddy (TLS proxy)    │
                │                    │ /realms/* → Keycloak │
                │                    │ /app/*    → ui_iot   │
                │                    │ /api/v2/* → ui_iot   │
                │                    │ /customer/* → ui_iot │
                │                    │ /operator/* → ui_iot │
                │                    │ /ingest/* → ui_iot   │
                │                    └──────────┬───────────┘
                │                               │
                ▼                               ▼
      ┌──────────────────┐             ┌────────────────────────┐
      │ EMQX (MQTT 5.0)  │             │ ui_iot (FastAPI)        │
      │ broker + ACL     │             │ - REST + WS/SSE         │
      └──────────┬───────┘             │ - HTTP ingest → NATS    │
                 │                     └──────────┬─────────────┘
                 │                                │ js.publish() PubAck
                 ▼                                ▼
        ┌──────────────────────┐          ┌──────────────────────┐
        │ mqtt_nats_bridge      │          │ NATS JetStream        │
        │ (custom OSS bridge)   │─────────►│ Streams: TELEMETRY,   │
        └──────────────────────┘          │ SHADOW, COMMANDS,      │
                                         │ ROUTES                │
                                         └──────────┬───────────┘
                                                    │ pull consumers (max_deliver=3)
                                                    ▼
                                      ┌───────────────────────┐
                                      │ ingest_iot             │
                                      │ - validate + rate limit│
                                      │ - batch write telemetry│
                                      └──────────┬────────────┘
                                                 │ asyncpg via PgBouncer
                                                 ▼
                                      ┌───────────────────────┐
                                      │ PostgreSQL + Timescale │
                                      │ - telemetry hypertable │
                                      │ - dead_letter_messages │
                                      └──────────┬────────────┘
                                                 │
                                                 ▼
                                      ┌───────────────────────┐
                                      │ evaluator_iot          │
                                      └──────────┬────────────┘
                                                 ▼
                                      ┌───────────────────────┐
                                      │ ops_worker             │
                                      │ - exports → MinIO/S3   │
                                      └───────────────────────┘

      ┌───────────────────────┐        ┌───────────────────────┐
      │ Prometheus (:9090)     │◄───────│ /metrics + /health     │
      └──────────┬────────────┘        └───────────────────────┘
                 ▼
      ┌───────────────────────┐
      │ Grafana (:3001)        │
      └───────────────────────┘
```

## Services

### ui_iot (API Gateway + UI Backend)

Primary platform API service. Responsibilities:

- Serves the React SPA bundle (behind Caddy `/app/*` routing).
- Customer APIs (`/api/v1/customer/*`) and operator APIs (`/api/v1/operator/*`).
- Legacy v2 endpoints (`/api/v2/*`) and real-time protocols (WebSocket/SSE).
- HTTP ingestion endpoints (`/ingest/*`) that publish envelopes to JetStream (`telemetry.{tenant_id}`).
- Notification routing + delivery engine (Phase 91+) for Slack/PagerDuty/Teams/HTTP.
- Request-context audit logging (async buffered flush).

### ingest_iot (Telemetry Ingestion)

Telemetry ingestion service consuming from NATS JetStream (aiohttp health server):

- Pull consumer: durable `ingest-workers` on stream `TELEMETRY` (subject filter `telemetry.>`).
- Validates device authorization via an in-memory auth cache to avoid per-message DB hits.
- Enforces per-device and per-tenant rate limiting (token bucket).
- Writes to TimescaleDB in batches and quarantines invalid messages for later inspection.

### mqtt_nats_bridge (MQTT to NATS Bridge)

Custom bridge service required for EMQX OSS (no native NATS bridge):

- Subscribes to EMQX MQTT topics (`tenant/{tenant_id}/device/{device_id}/{msg_type}`).
- Republishes messages into JetStream with PubAck (`js.publish()`), using subjects:
  - `telemetry.{tenant_id}`
  - `shadow.{tenant_id}`
  - `commands.{tenant_id}`

### evaluator_iot (Alert Rule Engine)

Rules engine that evaluates telemetry to:

- Maintain device status (ONLINE/STALE/OFFLINE) based on heartbeat freshness.
- Emit NO_HEARTBEAT alerts automatically.
- Evaluate customer-defined threshold rules (GT/GTE/LT/LTE) with optional time-window semantics.

### ops_worker (Background Operations)

Background worker process that runs periodic tasks that are independent of HTTP request handling:

- Health monitoring and service status alerts.
- Metrics collection to `system_metrics` hypertable.
- Operational jobs (OTA, certificate maintenance, exports, report generation, job expiry).

### route_delivery (Asynchronous Route Delivery)

Dedicated service consuming delivery jobs from JetStream `ROUTES` stream (subjects `routes.>`):

- Retries are handled by JetStream redelivery (`max_deliver=3` configured by `compose/nats/init-streams.sh`).
- On final failure, the service writes a DLQ record to PostgreSQL (`dead_letter_messages`).
- Exposes Prometheus metrics on `:8080/metrics`.

### subscription_worker (Subscription Lifecycle)

Lifecycle process for subscriptions (renewal notifications and state transitions).

### provision_api (Device Provisioning)

Standalone provisioning API (separate FastAPI service) for device registration and activation flows.

## Device Template Model (Phase 166)

Templates define device *capability*; instances define device *reality*.

- System templates: `tenant_id IS NULL`, `is_locked = true`, `source = 'system'`
  - Visible to all tenants
  - Not editable by tenant-scoped application roles (enforced by RLS)
- Tenant templates: `tenant_id = <tenant>`, `source = 'tenant'`
  - Private to the owning tenant

API access control (Phase 168):

- Tenants can create/update/delete their own templates via `/api/v1/customer/templates`, but cannot modify system templates.
- Operators can manage templates cross-tenant via `/api/v1/operator/templates` (RLS bypass via `operator_connection()`), including locked system templates.
- Tenants can clone templates into an editable tenant-owned copy via `POST /api/v1/customer/templates/{template_id}/clone`.

Template hierarchy:

- `device_templates` — device type definition
- `template_metrics` — what this device type can measure
- `template_commands` — what commands this device type accepts
- `template_slots` — expansion ports / bus interfaces for module assignment
  - `compatible_templates` constrains which expansion module templates can be assigned to a slot

Instance hierarchy (Phase 167):

- `device_registry.template_id` — which device template this device instance uses
- `device_registry.parent_device_id` — gateway hierarchy pointer for child/peripheral devices
- `device_modules` — modules installed into slots (per device)
- `device_sensors` — active measurement points (per device), optionally linked to template metrics and modules
- `device_transports` — ingestion protocol and physical connectivity configuration (per device)

Both MQTT and HTTP ingestion flows use the same backend pipeline regardless of whether a device's template is system-defined or tenant-defined.

## Infrastructure

### PostgreSQL + TimescaleDB

PostgreSQL with TimescaleDB extension stores:

- Time-series telemetry (hypertable).
- Transactional fleet tables (devices, alerts, rules, subscriptions, on-call, notification routing).

### PgBouncer

Connection pooler used by services to reduce connection churn and enforce pooling limits.

### Keycloak

OIDC identity provider (realm `pulse`) used by the SPA and API services for authentication and roles.

### EMQX (MQTT Broker)

MQTT broker for device telemetry and command topics:

- External mTLS listener on port 8883.
- Uses internal HTTP auth/ACL endpoints in `ui_iot` (`/api/v1/internal/mqtt-auth`, `/api/v1/internal/mqtt-acl`).

### NATS JetStream

Durable message backbone for ingestion and delivery:

- Streams: `TELEMETRY`, `SHADOW`, `COMMANDS`, `ROUTES`.
- Publications use PubAck via `js.publish()` (not core `nc.publish()`).

### MinIO (S3-compatible Object Storage)

Stores exports and reports in local dev (replace with AWS S3 in production):

- `ops_worker` uploads export artifacts and stores an S3 key in the export job record.
- `ui_iot` generates pre-signed URLs for direct client downloads (default expiry: 1 hour).

### Caddy (Reverse Proxy)

TLS termination and routing by path prefix (Keycloak vs ui_iot).

### Prometheus + Grafana

Prometheus scrapes service health/metrics; Grafana provides pre-provisioned dashboards.

## Data Flow

### Telemetry Ingestion Pipeline

1. Device publishes MQTT messages to EMQX.
2. `mqtt_nats_bridge` republishes MQTT messages into JetStream (`telemetry.{tenant_id}` / `shadow.{tenant_id}` / `commands.{tenant_id}`).
3. `ui_iot` HTTP ingest also publishes to JetStream (`telemetry.{tenant_id}`), unifying the pipeline.
4. `ingest_iot` consumes from JetStream, validates/rate-limits, and batch-writes to TimescaleDB.
5. Invalid messages are quarantined in database tables for troubleshooting.

### Alert Evaluation Loop

1. `evaluator_iot` polls for rule/device state changes on a configured interval.
2. For each device/rule, evaluates thresholds (and optional duration window) and updates alert tables.
3. Device heartbeat freshness drives NO_HEARTBEAT alerts and device status.

### Notification Routing

When an alert is opened/escalated:

1. `ui_iot` routing engine matches routing rules (severity/type/throttle).
2. `ui_iot` delivers notifications using the configured channel senders (Slack/PagerDuty/Teams/HTTP webhook).

Message route delivery (webhook/MQTT republish) is handled separately by `route_delivery` via JetStream `ROUTES`.

### Escalation Flow

1. Alerts can be linked to escalation policies with multi-level delays.
2. A periodic escalation tick evaluates pending escalation deadlines and triggers additional notifications.
3. On-call schedules can be used to resolve the current responder at notification time.

## Background Workers

Background work is split between:

- `ui_iot` request-coupled background tasks:
  - Request-context audit logger (buffered flush loop).
- `ops_worker` periodic operational tasks:
  - Service health monitor.
  - Metrics collector.
  - OTA, exports, reports, cert maintenance, command expiry, etc.

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend framework | React 18 + TypeScript |
| Build tool | Vite |
| Styling | TailwindCSS + shadcn/ui |
| Charts | ECharts (gauges, heatmaps, area charts), uPlot (time-series) |
| Server state | TanStack Query |
| Client state | Zustand (WebSocket live data) |
| Authentication | keycloak-js (OIDC/PKCE) |
| Routing | React Router v6 |
| Backend | FastAPI (Python) + asyncpg |
| Database | PostgreSQL 15 + TimescaleDB |
| Connection pooling | PgBouncer |
| MQTT broker | EMQX |
| Message backbone | NATS JetStream |
| Object storage | MinIO (dev) / S3-compatible |
| Identity provider | Keycloak |
| Reverse proxy | Caddy |
| Container runtime | Docker Compose (dev) / Kubernetes + Helm (prod) |

## Configuration

Operational knobs are controlled by environment variables read by the services at startup. Examples:

- Database connectivity: `PG_*` and/or `DATABASE_URL`
- NATS: `NATS_URL`
- Ingest throughput: `BATCH_SIZE`, `FLUSH_INTERVAL_MS`, worker count
- Evaluator cadence: `POLL_SECONDS`, `HEARTBEAT_STALE_SECONDS`
- Auth behavior: Keycloak URLs, JWKS cache TTL, token requirements
- DB pools: `PG_POOL_MIN`, `PG_POOL_MAX`
- S3/MinIO: `S3_ENDPOINT`, `S3_PUBLIC_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_REGION`

For complete per-service configuration, see the service docs.

## See Also

- [Service Map](service-map.md)
- [Tenant Isolation](tenant-isolation.md)
- [API Overview](../api/overview.md)
- [ui-iot service](../services/ui-iot.md)

