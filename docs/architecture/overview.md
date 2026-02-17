---
last-verified: 2026-02-17
sources:
  - services/ui_iot/app.py
  - services/evaluator_iot/evaluator.py
  - services/ingest_iot/ingest.py
  - services/ops_worker/main.py
  - compose/docker-compose.yml
phases: [1, 23, 43, 88, 98, 99, 122, 128, 138, 142]
---

# System Architecture

> One authoritative reference for the OpsConductor-Pulse platform architecture.

## Overview

OpsConductor-Pulse is a multi-tenant IoT fleet management and operations platform:

- Devices send telemetry via MQTT (primary) or HTTP (alternate).
- Telemetry is written to TimescaleDB (PostgreSQL + TimescaleDB hypertables).
- A rules engine evaluates telemetry to maintain device state and open/close alerts.
- The UI/API service exposes customer and operator APIs plus real-time streams.
- Notifications are delivered by the Phase 91+ routing engine inside `ui_iot` (no legacy separate routing/delivery services).
- Prometheus scrapes health/metrics and Grafana provides dashboards.

## Architecture Diagram

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                                External Actors                                │
│                                                                               │
│  IoT Devices (MQTT/HTTP)           Browser SPA (customers/operators)           │
│                                                                               │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
          MQTT/TLS (:8883)                 HTTPS (:443)
          MQTT/WS  (:9001)                       │
          HTTP (internal)                         │
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
      ┌──────────────────┐             ┌───────────────────────┐
      │ Mosquitto (MQTT) │             │ ui_iot (FastAPI)       │
      │                  │             │ - REST + WS/SSE        │
      └──────────┬───────┘             │ - SPA static serving   │
                 │                     │ - notification engine  │
                 │                     └──────────┬────────────┘
                 │                                │
                 │                         asyncpg via PgBouncer
                 │                                │
                 ▼                                ▼
      ┌──────────────────┐             ┌───────────────────────┐
      │ ingest_iot        │             │ PgBouncer             │
      │ (MQTT + HTTP)     │             └──────────┬────────────┘
      └──────────┬───────┘                        │
                 │                                ▼
                 │                     ┌───────────────────────┐
                 └────────────────────►│ PostgreSQL + Timescale │
                                       │ - telemetry hypertable │
                                       │ - transactional tables │
                                       └──────────┬────────────┘
                                                  │
                                                  ▼
                                       ┌───────────────────────┐
                                       │ evaluator_iot          │
                                       │ - device state         │
                                       │ - alert generation     │
                                       └──────────┬────────────┘
                                                  │
                                                  ▼
                                       ┌───────────────────────┐
                                       │ ops_worker             │
                                       │ - health monitor       │
                                       │ - metrics collector    │
                                       │ - background jobs      │
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
- HTTP ingestion endpoints (`/ingest/*`) that share telemetry writing logic with a batch writer.
- Notification routing + delivery engine (Phase 91+) for Slack/PagerDuty/Teams/HTTP.
- Request-context audit logging (async buffered flush).

### ingest_iot (Telemetry Ingestion)

Device telemetry ingestion service (MQTT subscriber + aiohttp HTTP server):

- Validates device authorization via an in-memory auth cache to avoid per-message DB hits.
- Enforces per-device and per-tenant rate limiting (token bucket).
- Writes to TimescaleDB in batches and quarantines invalid messages for later inspection.

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

### subscription_worker (Subscription Lifecycle)

Lifecycle process for subscriptions (renewal notifications and state transitions).

### provision_api (Device Provisioning)

Standalone provisioning API (separate FastAPI service) for device registration and activation flows.

## Infrastructure

### PostgreSQL + TimescaleDB

PostgreSQL with TimescaleDB extension stores:

- Time-series telemetry (hypertable).
- Transactional fleet tables (devices, alerts, rules, subscriptions, on-call, notification routing).

### PgBouncer

Connection pooler used by services to reduce connection churn and enforce pooling limits.

### Keycloak

OIDC identity provider (realm `pulse`) used by the SPA and API services for authentication and roles.

### Mosquitto (MQTT)

MQTT broker for device telemetry and command topics. Production/dev uses TLS on external port 8883.

### Caddy (Reverse Proxy)

TLS termination and routing by path prefix (Keycloak vs ui_iot).

### Prometheus + Grafana

Prometheus scrapes service health/metrics; Grafana provides pre-provisioned dashboards.

## Data Flow

### Telemetry Ingestion Pipeline

1. Device publishes MQTT messages (or sends HTTP POST for ingestion).
2. `ingest_iot` validates the device, rate-limits, and writes telemetry (batched).
3. Telemetry is stored in the TimescaleDB hypertable.
4. Invalid messages are written to quarantine tables for troubleshooting.

### Alert Evaluation Loop

1. `evaluator_iot` polls for rule/device state changes on a configured interval.
2. For each device/rule, evaluates thresholds (and optional duration window) and updates alert tables.
3. Device heartbeat freshness drives NO_HEARTBEAT alerts and device status.

### Notification Routing

When an alert is opened/escalated:

1. `ui_iot` routing engine matches routing rules (severity/type/throttle).
2. Delivery occurs via one of the supported senders:
   - Slack incoming webhook
   - PagerDuty Events API v2
   - Microsoft Teams webhook (MessageCard)
   - Generic HTTP webhook (HMAC signed)

### Escalation Flow

1. Alerts can be linked to escalation policies with multi-level delays.
2. A periodic escalation tick evaluates pending escalation deadlines and triggers additional notifications.
3. On-call schedules can be used to resolve the current responder at notification time.

## Background Workers

Background work is split between:

- `ui_iot` request-coupled background tasks:
  - Telemetry batch writer (flush interval + batch size thresholds).
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
| MQTT broker | Eclipse Mosquitto |
| Identity provider | Keycloak |
| Reverse proxy | Caddy |
| Container runtime | Docker Compose |

## Configuration

Operational knobs are controlled by environment variables read by the services at startup. Examples:

- Database connectivity: `PG_*` and/or `DATABASE_URL`
- Ingest throughput: `BATCH_SIZE`, `FLUSH_INTERVAL_MS`, worker count/queue sizing
- Evaluator cadence: `POLL_SECONDS`, `HEARTBEAT_STALE_SECONDS`
- Auth behavior: Keycloak URLs, JWKS cache TTL, token requirements

For complete per-service configuration, see the service docs.

## See Also

- [Service Map](service-map.md)
- [Tenant Isolation](tenant-isolation.md)
- [API Overview](../api/overview.md)
- [ui-iot service](../services/ui-iot.md)

