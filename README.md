# OpsConductor-Pulse

**OpsConductor-Pulse** is a multi-tenant IoT fleet management and operations platform. It provides secure device ingestion, real-time state evaluation, alert generation, escalation, on-call scheduling, outbound notifications, and professional operator dashboards for managing large IoT deployments.

---

## Quick Start

```bash
cd compose/
docker compose up -d --build

# Access
# Application:       https://192.168.10.53  (or https://localhost)
# Keycloak Admin:    https://192.168.10.53/admin  (admin / admin_dev)
# Provisioning API:  http://localhost:8081
# MQTT Broker:       localhost:1883
# PostgreSQL:        localhost:5432
```

All traffic goes through a **Caddy** reverse proxy on ports 80/443. Port 80 redirects to HTTPS. Caddy generates a self-signed certificate (browser will show a security warning on first visit — click through).

---

## Default Development Users

| Username | Password | Role | Tenant |
|----------|----------|------|--------|
| customer1 | test123 | customer_admin | tenant-a |
| operator1 | test123 | operator | (all tenants) |

---

## Feature Summary

### Device & Fleet Management
- Multi-tenant device registry with status tracking (ONLINE / STALE / OFFLINE)
- MQTT and HTTP telemetry ingestion with high-throughput batched writes
- Arbitrary metric schema — any numeric/boolean metric accepted without changes
- Guided device provisioning wizard (4-step: identity → tags → rules → credentials)
- Bulk CSV device import with client-side preview and error reporting
- Device API token management with rotation and one-time credential display
- Multi-site support with per-site device grouping
- Device decommissioning with audit trail

### Alerting & Escalation
- Automatic NO_HEARTBEAT alerts when devices miss heartbeat windows
- Customer-defined THRESHOLD rules (GT / LT / GTE / LTE on any metric)
- Alert acknowledgment, closure, and silence
- Escalation policies: multi-level (up to 5) with per-level delay and notification targets
- On-call schedules: rotation layers, daily/weekly cadence, temporary overrides, 14-day timeline

### Outbound Notifications
- **Legacy delivery pipeline**: Webhook, SNMP (v2c/v3), Email (SMTP), MQTT
- **Phase 91+ routing engine**: Slack, PagerDuty (Events API v2), Microsoft Teams, generic HTTP
- Per-channel routing rules with severity filter, alert type filter, and throttle
- HMAC signing for generic webhooks

### Reporting & Exports
- SLA summary report: online %, MTTR, top alerting devices
- CSV and JSON export for devices and alerts
- Report run history with status tracking
- Daily scheduled SLA report generation per tenant

### Subscription Management
- Multi-subscription model: MAIN, ADDON, TRIAL, TEMPORARY
- Lifecycle: TRIAL → ACTIVE → GRACE → SUSPENDED → EXPIRED
- Device limit enforcement at provisioning time
- Subscription audit history

### Operator Tools
- NOC command center with ECharts gauges, time-series charts, and service topology
- Tenant health matrix with per-tenant alert counts and activity sparklines
- Alert heatmap (day × hour) and live event feed
- TV mode (F key fullscreen) with dark NOC theme
- Cross-tenant device and alert inventory
- Operator audit log (admin only)

---

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

---

## Repository Structure

```
compose/               # Docker Compose configuration
  caddy/              # Caddy TLS configuration
  keycloak/           # Keycloak realm export
  .env                # Environment variables
frontend/              # React SPA (Vite + TypeScript + TailwindCSS)
  src/
    app/              # Router, providers
    components/       # Layout shell, shared components, shadcn/ui
    features/         # Feature modules (see below)
    hooks/            # React Query + WebSocket hooks
    services/         # API client, auth, per-domain API modules
    stores/           # Zustand stores (live telemetry, alerts)
    lib/              # Chart wrappers (ECharts, uPlot), NOC theme tokens
  dist/               # Built SPA (volume-mounted into ui container)
db/
  migrations/         # 069 PostgreSQL + TimescaleDB migrations
docs/
  ARCHITECTURE.md     # Full system architecture reference
  PROJECT_MAP.md      # Quick-reference network + data flow map
  API_REFERENCE.md    # Complete API endpoint reference
  RUNBOOK.md          # Operations, migrations, troubleshooting
  TENANT_CONTEXT_CONTRACT.md  # Tenant isolation invariants
  CUSTOMER_PLANE_ARCHITECTURE.md  # Auth and customer API design
  INTEGRATIONS_AND_DELIVERY.md    # Alert delivery pipeline
  cursor-prompts/     # Phase-by-phase implementation history (phases 1–92)
services/
  ingest_iot/         # MQTT + HTTP telemetry ingestion
  evaluator_iot/      # State evaluation, alert generation
  ui_iot/             # FastAPI backend (APIs, SPA serving, workers)
    routes/           # customer.py, operator.py, api_v2.py, escalation.py,
                      #   notifications.py, oncall.py
    workers/          # escalation_worker.py, report_worker.py
    reports/          # sla_report.py
    notifications/    # dispatcher.py, senders.py
    oncall/           # resolver.py
  provision_api/      # Device provisioning admin API
  dispatcher/         # Alert → delivery job routing (legacy pipeline)
  delivery_worker/    # Webhook/SNMP/email/MQTT delivery (legacy pipeline)
  ops_worker/         # Platform health monitoring
  subscription_worker/# Subscription lifecycle management
  maintenance/        # DB housekeeping
  shared/             # Shared utilities (ingest_core, auth cache, batch writer)
simulator/
  device_sim_iot/     # 25-device IoT simulator
tests/
  unit/               # Unit tests (pytest, FakeConn/FakePool pattern)
  integration/        # Integration tests
  e2e/                # End-to-end browser tests
scripts/              # Utility scripts
```

### Frontend Feature Modules

| Module | Pages |
|--------|-------|
| `dashboard/` | Fleet Overview (KPI strip, active alerts, recent devices) |
| `devices/` | Device list (split-pane), device detail (5 tabs), wizard, bulk import |
| `alerts/` | Alert inbox (tabs by severity, bulk actions, expand detail) |
| `alert-rules/` | Threshold rule CRUD |
| `escalation/` | Escalation policy CRUD with level builder |
| `notifications/` | Notification channels (Slack/PD/Teams/webhook) + routing rules |
| `oncall/` | On-call schedules, rotation layers, override management, timeline |
| `reports/` | CSV exports, SLA summary, report history |
| `sites/` | Multi-site management |
| `integrations/` | Legacy webhook/SNMP/email/MQTT integrations |
| `subscription/` | Subscription status and renewal |
| `users/` | Tenant user management (tenant-admin only) |
| `audit/` | Subscription audit log |
| `operator/` | Operator landing, NOC command center, tenant health matrix |
| `metrics/` | Metric catalog and normalization |

---

## Authentication

OpsConductor-Pulse uses **Keycloak** for OIDC authentication. The React SPA uses **keycloak-js** with PKCE for direct browser-to-Keycloak authentication.

### User Roles

| Role | Description |
|------|-------------|
| `customer` | Standard tenant user — view and manage own tenant's resources |
| `tenant-admin` | Elevated tenant access — manage users, subscriptions |
| `operator` | Cross-tenant read access — audited |
| `operator-admin` | Cross-tenant full access — system settings, audit log |

---

## Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Full system design, data flows, security model |
| [API_REFERENCE.md](docs/API_REFERENCE.md) | All API endpoints with parameters and examples |
| [RUNBOOK.md](docs/RUNBOOK.md) | Operations guide — migrations, deployment, troubleshooting |
| [PROJECT_MAP.md](docs/PROJECT_MAP.md) | Quick-reference topology and flow map |
| [TENANT_CONTEXT_CONTRACT.md](docs/TENANT_CONTEXT_CONTRACT.md) | Tenant isolation invariants |
| [CUSTOMER_PLANE_ARCHITECTURE.md](docs/CUSTOMER_PLANE_ARCHITECTURE.md) | Auth and customer API design |
| [INTEGRATIONS_AND_DELIVERY.md](docs/INTEGRATIONS_AND_DELIVERY.md) | Legacy alert delivery pipeline |

---

## Running Tests

```bash
# Unit tests
python3 -m pytest tests/unit/ -v

# With coverage
pytest --cov=services tests/unit/

# Frontend type check
cd frontend && npx tsc --noEmit

# Frontend build
cd frontend && npm run build
```

## Applying Migrations

```bash
# Apply a specific migration
psql "$DATABASE_URL" -f db/migrations/066_escalation_policies.sql

# Apply all pending (in order)
for f in db/migrations/*.sql; do psql "$DATABASE_URL" -f "$f"; done
```

## Rebuilding After Backend Changes

```bash
docker compose build ui && docker compose up -d ui
```

> **Note**: If you add a new top-level Python package under `services/ui_iot/`
> (e.g., `oncall/`, `notifications/`), add a `COPY <package> /app/<package>`
> line in `services/ui_iot/Dockerfile` before rebuilding.
