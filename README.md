# OpsConductor-Pulse

OpsConductor-Pulse is an edge telemetry, health, and signaling platform for managed IoT devices. Provides secure multi-tenant device ingestion, real-time state evaluation, alert generation, and operational dashboards.

## Features

- **React SPA frontend** — TypeScript + Vite + TailwindCSS + shadcn/ui with role-based views
- **Multi-tenant isolation** — JWT claims + database RLS + tenant_id column filtering
- **Real-time device monitoring** — Heartbeat tracking, stale detection, WebSocket live updates
- **Flexible telemetry** — Arbitrary numeric/boolean metrics accepted without schema changes
- **TimescaleDB time-series** — PostgreSQL with TimescaleDB extension, hypertables, compression, batched writes
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

## Subscription & Entitlement System

OpsConductor Pulse includes a comprehensive subscription management system:

### Subscription Types
- **MAIN** — Primary annual subscription with device limit
- **ADDON** — Additional capacity, coterminous with parent MAIN
- **TRIAL** — Short-term evaluation (default 14 days)
- **TEMPORARY** — Project or event-based subscriptions

### Subscription Lifecycle
```
TRIAL → ACTIVE → (renewal) → ACTIVE
                     ↓ (no payment)
                   GRACE (14 days)
                     ↓ (still no payment)
                   SUSPENDED (access blocked)
                     ↓ (90 days)
                   EXPIRED (data retained 1 year)
```

### Device Entitlements
- Each device assigned to exactly one subscription
- Device limits enforced at creation time
- Auto-provisioning respects subscription capacity
- Operators can reassign devices between subscriptions

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
  migrations/           # PostgreSQL + TimescaleDB migrations (001-040)
services/
  ingest_iot/           # MQTT device ingestion, auth cache, batched TimescaleDB writes
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
| **ingest_iot** | MQTT device ingress with auth caching, multi-worker pipeline, batched TimescaleDB writes |
| **evaluator_iot** | Device state tracking, NO_HEARTBEAT alerts, threshold rule evaluation from TimescaleDB |
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
Cross-tenant Overview, All Devices (with tenant filter), System Dashboard (health, metrics, capacity), Audit Log (admin only), System Settings (admin only).

## API Endpoints

## HTTP Telemetry Ingestion

Alternative to MQTT for devices that prefer HTTP.

### Single Message

```bash
curl -X POST "https://<host>/ingest/v1/tenant/{tenant_id}/device/{device_id}/telemetry" \
  -H "Content-Type: application/json" \
  -H "X-Provision-Token: tok-xxxxx" \
  -d '{"site_id": "lab-1", "seq": 1, "metrics": {"temp_c": 25.5, "humidity_pct": 60}}'
```

Response: `202 Accepted`

### Batch (up to 100 messages)

```bash
curl -X POST "https://<host>/ingest/v1/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"tenant_id": "t1", "device_id": "d1", "msg_type": "telemetry", "provision_token": "tok-xxx", "site_id": "lab-1", "seq": 1, "metrics": {"temp_c": 25}},
      {"tenant_id": "t1", "device_id": "d2", "msg_type": "heartbeat", "provision_token": "tok-yyy", "site_id": "lab-1", "seq": 1, "metrics": {}}
    ]
  }'
```

Response: `202 Accepted` with `{"accepted": 2, "rejected": 0, "results": [...]}`

### Error Codes

| Code | Meaning |
|------|---------|
| 400 | Invalid msg_type, payload too large, site mismatch |
| 401 | Invalid or missing provision token |
| 403 | Device revoked or unregistered |
| 429 | Rate limited |

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

### Subscription System (Customer)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/customer/subscriptions` | List all subscriptions with summary |
| GET | `/customer/subscriptions/{id}` | Subscription detail with devices |
| GET | `/customer/subscription/audit` | Subscription audit history |
| POST | `/customer/subscription/renew` | Request renewal |

### Device Management (Customer)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/customer/devices` | List devices with pagination |
| POST | `/customer/devices` | Register new device |
| GET | `/customer/devices/{id}` | Device details |
| PATCH | `/customer/devices/{id}` | Update device attributes |
| DELETE | `/customer/devices/{id}` | Deactivate device |
| GET | `/customer/devices/{id}/tags` | Get device tags |
| PUT | `/customer/devices/{id}/tags` | Replace device tags |
| POST | `/customer/devices/{id}/tags` | Add tags |
| DELETE | `/customer/devices/{id}/tags` | Remove tags |
| GET | `/customer/tags` | List all tenant tags |
| GET | `/customer/geocode` | Geocode address |

### Operator Endpoints (Operator role required)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/operator/devices` | All devices (with optional tenant filter) |
| GET | `/operator/alerts` | All alerts (with optional tenant filter) |
| GET | `/operator/quarantine` | Quarantine events |
| GET | `/operator/integrations` | All integrations |
| GET | `/operator/audit-log` | Operator audit log (admin only) |
| POST | `/operator/settings` | Update system settings (admin only) |
| GET | `/operator/system/health` | Service health status (Postgres, MQTT, Keycloak, services) |
| GET | `/operator/system/metrics` | Throughput, queue depth, last activity |
| GET | `/operator/system/metrics/history` | Historical time-series (supports rate calculation) |
| GET | `/operator/system/capacity` | Disk, DB connections, table sizes |
| GET | `/operator/system/aggregates` | Platform totals (tenants, devices, alerts) |
| GET | `/operator/system/errors` | Recent errors and failures |

### Subscription System (Operator)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/operator/subscriptions` | Create subscription |
| GET | `/operator/subscriptions` | List all subscriptions |
| GET | `/operator/subscriptions/{id}` | Subscription detail |
| PATCH | `/operator/subscriptions/{id}` | Update subscription |
| POST | `/operator/devices/{id}/subscription` | Assign device |
| GET | `/operator/subscriptions/expiring` | Expiring subscriptions |
| GET | `/operator/subscriptions/summary` | Platform summary |

### Tenant Management (Operator)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/operator/tenants` | Create tenant |
| GET | `/operator/tenants` | List all tenants |
| GET | `/operator/tenants/{id}` | Tenant details |
| PATCH | `/operator/tenants/{id}` | Update tenant |
| DELETE | `/operator/tenants/{id}` | Delete tenant |
| GET | `/operator/tenants/stats/summary` | Platform statistics |
| GET | `/operator/tenants/{id}/stats` | Tenant statistics |
| GET | `/operator/tenants/{id}/devices` | Tenant devices |

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
- **TimescaleDB isolation** — Tenant filtering via tenant_id column with application-level enforcement
- **SSRF prevention** — Webhook URLs and SNMP/SMTP hosts validated (blocks private IPs, loopback, cloud metadata)
- **HTTPS** — Caddy TLS termination with self-signed certificates (production should use real certs)
- **Audit logging** — All operator cross-tenant access logged with IP and user agent
- **Admin key protection** — Provisioning API requires X-Admin-Key header
- **Rate limiting** — Per-tenant API rate limiting on `/api/v2/` endpoints

## Environment Variables

### Database
| Variable | Default | Description |
|----------|---------|-------------|
| DATABASE_URL | postgresql://iot:iot_dev@postgres:5432/iotcloud | PostgreSQL connection |
| TIMESCALE_BATCH_SIZE | 1000 | Telemetry batch insert size |
| TIMESCALE_FLUSH_INTERVAL_MS | 1000 | Batch flush interval |

### Authentication
| Variable | Default | Description |
|----------|---------|-------------|
| KEYCLOAK_URL | https://localhost | Keycloak server URL |
| KEYCLOAK_REALM | iotcloud | Keycloak realm |
| AUTH_CACHE_TTL_SECONDS | 300 | JWKS cache TTL |

### Ingestion
| Variable | Default | Description |
|----------|---------|-------------|
| INGEST_WORKER_COUNT | 4 | Parallel ingest workers |
| INGEST_QUEUE_SIZE | 10000 | Message queue size |
| API_RATE_LIMIT | 100 | Requests per window |
| API_RATE_WINDOW_SECONDS | 60 | Rate limit window |

### WebSocket
| Variable | Default | Description |
|----------|---------|-------------|
| WS_POLL_SECONDS | 5 | WebSocket poll interval |

### CORS
| Variable | Default | Description |
|----------|---------|-------------|
| CORS_ORIGINS | (empty) | Allowed origins (comma-separated); empty uses dev defaults |

### Notifications
| Variable | Default | Description |
|----------|---------|-------------|
| NOTIFICATION_WEBHOOK_URL | (none) | External notification webhook |
| WORKER_INTERVAL_SECONDS | 3600 | Subscription worker interval |

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
