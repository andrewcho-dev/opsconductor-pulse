# OpsConductor-Pulse

OpsConductor-Pulse is an edge telemetry, health, and signaling platform for managed IoT devices. Provides secure multi-tenant device ingestion, real-time state evaluation, alert generation, and operational dashboards.

## Features

- **React SPA frontend** — TypeScript + Vite + TailwindCSS + shadcn/ui with role-based views
- **Multi-tenant isolation** — JWT claims + database RLS + per-tenant InfluxDB databases
- **Real-time device monitoring** — Heartbeat tracking, stale detection, WebSocket live updates
- **Flexible telemetry** — Arbitrary numeric/boolean metrics accepted without schema changes
- **InfluxDB time-series** — InfluxDB 3 Core with per-tenant databases, batched writes
- **Custom alert rules** — Customer-defined threshold rules (GT/LT/GTE/LTE) on any metric
- **Alert generation** — Automatic NO_HEARTBEAT and THRESHOLD alerts with deduplication
- **REST API (v2)** — JSON API at `/api/v2/` with JWT auth, rate limiting, dynamic telemetry
- **WebSocket streaming** — Live telemetry and alert push at `/api/v2/ws`
- **Webhook delivery** — HTTP POST with JSON payload, retry with exponential backoff, SSRF protection
- **SNMP trap delivery** — SNMPv2c and SNMPv3, custom OID prefix, address validation
- **Email delivery** — SMTP with TLS, HTML/text templates, multiple recipients
- **MQTT delivery** — Publish to customer topics with QoS, retain, and template variables
- **Customer self-service** — Manage integrations, alert rules, and routing via SPA
- **Operator dashboards** — Cross-tenant visibility, device inventory, audit log
- **HTTPS reverse proxy** — Caddy with self-signed TLS, single-origin for SPA + Keycloak
- **ECharts + uPlot** — Interactive gauges and time-series charts with live WebSocket data fusion

## Quick Start

```bash
# Start all services
cd compose/
docker compose up -d --build

# View logs
docker compose logs -f

# Access services
# Application:        https://192.168.10.53 (or https://localhost)
# Keycloak Admin:     https://192.168.10.53/admin (admin/admin_dev)
# Provisioning API:   http://localhost:8081
# MQTT Broker:        localhost:1883
# PostgreSQL:         localhost:5432
# InfluxDB:           localhost:8181
```

All traffic goes through a Caddy reverse proxy on ports 80/443. Port 80 redirects to HTTPS. Caddy generates a self-signed certificate (browser will show a warning on first visit).

## Authentication

OpsConductor-Pulse uses **Keycloak** for authentication. The React SPA uses **keycloak-js** for direct browser-to-Keycloak OIDC (PKCE) authentication.

### Default Users (Development)

| Username | Password | Role | Tenant |
|----------|----------|------|--------|
| customer1 | test123 | customer_admin | tenant-a |
| operator1 | test123 | operator | (all tenants) |

### User Roles

| Role | Access |
|------|--------|
| `customer_viewer` | Read-only access to own tenant's devices, alerts, and delivery status |
| `customer_admin` | Above + manage integrations, alert rules, and alert routes |
| `operator` | Cross-tenant device and alert views with audit logging |
| `operator_admin` | Above + system settings and audit log access |

## Documentation

- [Architecture Overview](docs/ARCHITECTURE.md) — System design, services, data flows, and frontend architecture
- [Customer Plane Architecture](docs/CUSTOMER_PLANE_ARCHITECTURE.md) — Multi-tenant authentication design
- [Integrations & Delivery](docs/INTEGRATIONS_AND_DELIVERY.md) — Alert delivery pipeline design
- [Tenant Context Contract](docs/TENANT_CONTEXT_CONTRACT.md) — Tenant isolation invariants
- [Project Map](docs/PROJECT_MAP.md) — Quick reference overview

## Repository Structure

```
compose/                 # Docker Compose configuration
  caddy/                # Caddy reverse proxy (TLS termination)
  keycloak/             # Keycloak realm configuration
  .env                  # Environment variables
frontend/                # React SPA (Vite + TypeScript + TailwindCSS)
  src/
    app/               # Router, providers
    components/        # Layout shell, shared components, shadcn/ui
    features/          # Page components (dashboard, devices, alerts, integrations, operator)
    hooks/             # React Query + WebSocket hooks
    services/          # API client, WebSocket manager, Keycloak auth
    stores/            # Zustand state stores
    lib/               # Chart wrappers (ECharts, uPlot), utilities
  dist/                # Built SPA output (volume-mounted into ui container)
docs/                    # Architecture and design documentation
  cursor-prompts/      # Phase-by-phase implementation prompts
db/
  migrations/           # PostgreSQL migrations (001-017)
services/
  ingest_iot/           # MQTT device ingestion, auth cache, batched InfluxDB writes
  evaluator_iot/        # State evaluation, alert generation, threshold rule engine
  ui_iot/               # FastAPI backend — JSON APIs, SPA serving, WebSocket
  provision_api/        # Device provisioning and admin APIs
  dispatcher/           # Alert-to-delivery-job dispatcher
  delivery_worker/      # Webhook, SNMP, email, and MQTT delivery with retry
  webhook_receiver/     # Test webhook receiver (development only)
simulator/
  device_sim_iot/       # Device simulation (25 devices with varied telemetry)
tests/                   # Unit, integration, E2E, and benchmark tests
scripts/                 # Utility scripts (coverage, test DB setup)
```

## Services Overview

| Service | Purpose |
|---------|---------|
| **caddy** | HTTPS reverse proxy — TLS termination, path-based routing to UI and Keycloak |
| **ingest_iot** | MQTT device ingress with auth caching, multi-worker pipeline, batched InfluxDB writes |
| **evaluator_iot** | Device state tracking, NO_HEARTBEAT alerts, threshold rule evaluation from InfluxDB |
| **ui_iot** | FastAPI backend — serves React SPA, JSON APIs (`/api/v2/`, `/customer/`, `/operator/`), WebSocket |
| **provision_api** | Device registration, activation codes, admin operations (X-Admin-Key) |
| **dispatcher** | Matches open alerts to integration routes, creates delivery jobs |
| **delivery_worker** | Delivers alerts via webhook, SNMP, email, or MQTT with retry and backoff |
| **keycloak** | Identity provider — OIDC/OAuth2, realm management, user federation |
| **device_sim_iot** | Simulates 25 IoT devices with heartbeats, telemetry, and battery drain |

## Frontend Architecture

The frontend is a React SPA served at `/app/` by the `ui_iot` FastAPI backend.

| Technology | Purpose |
|------------|---------|
| **React 18 + TypeScript** | Component framework |
| **Vite** | Build tool and dev server |
| **TailwindCSS + shadcn/ui** | Styling and component library |
| **TanStack Query** | Server state management (REST API) |
| **Zustand** | Client state management (WebSocket live data) |
| **keycloak-js** | Browser-native OIDC authentication (PKCE) |
| **ECharts** | Interactive metric gauges with color zones |
| **uPlot** | High-performance time-series charts |

### Customer Pages
Dashboard, Device List, Device Detail (with telemetry charts), Alerts, Alert Rules, Webhook/SNMP/Email/MQTT Integration Management.

### Operator Pages
Cross-tenant Overview, All Devices (with tenant filter), Audit Log (admin only), System Settings (admin only).

## API Endpoints

### REST API v2 (JWT Bearer required)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v2/devices` | List devices with full state JSONB |
| GET | `/api/v2/devices/{device_id}` | Device detail |
| GET | `/api/v2/devices/{device_id}/telemetry` | Time-range telemetry (all metrics) |
| GET | `/api/v2/devices/{device_id}/telemetry/latest` | Most recent readings |
| GET | `/api/v2/alerts` | List alerts with status/type filters |
| GET | `/api/v2/alerts/{alert_id}` | Alert detail with JSONB details |
| GET | `/api/v2/alert-rules` | List alert rules |
| GET | `/api/v2/alert-rules/{rule_id}` | Alert rule detail |
| WS | `/api/v2/ws?token=JWT` | Live telemetry + alert streaming |

### Customer Endpoints (JWT required)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/customer/devices` | List tenant devices (JSON) |
| GET | `/customer/devices/{device_id}` | Device detail (JSON) |
| GET | `/customer/alerts` | List tenant alerts (JSON) |
| GET | `/customer/alert-rules` | List alert rules (JSON) |
| POST | `/customer/alert-rules` | Create alert rule |
| PATCH | `/customer/alert-rules/{rule_id}` | Update alert rule |
| DELETE | `/customer/alert-rules/{rule_id}` | Delete alert rule |
| GET | `/customer/integrations` | List webhook integrations |
| POST | `/customer/integrations` | Create webhook integration |
| GET | `/customer/integrations/snmp` | List SNMP integrations |
| POST | `/customer/integrations/snmp` | Create SNMP integration |
| GET | `/customer/integrations/email` | List email integrations |
| POST | `/customer/integrations/email` | Create email integration |
| GET | `/customer/integrations/mqtt` | List MQTT integrations |
| POST | `/customer/integrations/mqtt` | Create MQTT integration |
| POST | `/customer/integrations/{type}/{id}/test` | Test delivery |
| GET | `/customer/integration-routes` | List alert routing rules |
| POST | `/customer/integration-routes` | Create alert routing rule |
| GET | `/customer/delivery-status` | Recent delivery attempts |

### Operator Endpoints (Operator role required)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/operator/devices` | All devices (with optional tenant filter) |
| GET | `/operator/alerts` | All alerts (with optional tenant filter) |
| GET | `/operator/quarantine` | Quarantine events |
| GET | `/operator/integrations` | All integrations |
| GET | `/operator/audit-log` | Operator audit log (admin only) |
| POST | `/operator/settings` | Update system settings (admin only) |

### Admin Endpoints (X-Admin-Key required)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/admin/devices` | Provision device |
| POST | `/api/admin/devices/{id}/activate-code` | Generate activation code |

## Alert Delivery

Customers configure integrations to receive alerts through four channels:

### Webhooks
HTTP POST with JSON payload, automatic retry with exponential backoff, SSRF protection.

### SNMP Traps
SNMPv2c (community string) and SNMPv3 (auth/priv), custom OID prefix, address validation.

### Email
SMTP with TLS support, HTML and plain text templates, multiple recipients (to, cc, bcc), customizable subject and body with template variables.

### MQTT
Publish to customer topics with configurable QoS and retain settings, topic template variables ({tenant_id}, {device_id}, {severity}, etc.).

## Security

- **Keycloak OIDC** — Browser-native PKCE authentication via keycloak-js
- **JWT + RLS** — Application-level tenant filtering backed by database row-level security
- **InfluxDB isolation** — Per-tenant databases for telemetry data
- **SSRF prevention** — Webhook URLs and SNMP/SMTP hosts validated (blocks private IPs, loopback, cloud metadata)
- **HTTPS** — Caddy TLS termination with self-signed certificates (production should use real certs)
- **Audit logging** — All operator cross-tenant access logged with IP and user agent
- **Admin key protection** — Provisioning API requires X-Admin-Key header
- **Rate limiting** — Per-tenant API rate limiting on `/api/v2/` endpoints

## Development

### Running Tests

```bash
# Run unit tests
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v

# Run with coverage
pytest --cov=services

# Run specific test file
pytest tests/unit/test_api_v2.py -v
```

### Database Migrations

Migrations are in `db/migrations/`. Apply them:

```bash
docker compose exec postgres psql -U iot -d iotcloud -f /dev/stdin < db/migrations/017_alert_rules_rls.sql
```

### Frontend Development

```bash
cd frontend/
npm install
npm run dev     # Vite dev server with API proxy
npm run build   # Production build to dist/
npx tsc --noEmit  # Type checking
```

The built SPA in `frontend/dist/` is volume-mounted into the `ui_iot` container at `/app/spa`.
