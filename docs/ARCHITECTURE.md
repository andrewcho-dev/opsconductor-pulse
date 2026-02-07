# OpsConductor-Pulse Architecture

OpsConductor-Pulse is an edge telemetry, health, and signaling platform for managed devices. It provides secure multi-tenant device ingestion, real-time state evaluation, alert generation, and operational dashboards for IoT fleet management.

## Architecture Overview

```
Browser ──► https://HOST (Caddy, ports 80/443)
              │
              ├── /realms/*     ──► Keycloak (OIDC identity provider)
              ├── /resources/*  ──► Keycloak (static assets)
              ├── /admin/*      ──► Keycloak (admin console)
              ├── /app/*        ──► ui_iot (React SPA static files)
              ├── /api/v2/*     ──► ui_iot (REST API + WebSocket)
              ├── /customer/*   ──► ui_iot (customer JSON APIs)
              ├── /operator/*   ──► ui_iot (operator JSON APIs)
              └── /*            ──► ui_iot (catch-all)

IoT Devices ──► MQTT (1883) ──► ingest_iot ──► TimescaleDB (telemetry)
                                                    │
                                              evaluator_iot
                                                    │
                                          device_state + fleet_alert
                                                    │
                                               dispatcher
                                                    │
                                            delivery_worker
                                            │    │    │    │
                                            ▼    ▼    ▼    ▼
                                      Webhook SNMP Email MQTT
```

## Network Architecture

All browser traffic goes through a **Caddy** reverse proxy that terminates TLS with a self-signed certificate. This puts the React SPA and Keycloak behind a single HTTPS origin, which is required for the Web Crypto API (PKCE code challenge) used by keycloak-js.

| Port | Service | Access |
|------|---------|--------|
| 443 | Caddy | HTTPS — all browser traffic |
| 80 | Caddy | Redirects to HTTPS |
| 8081 | provision_api | Admin API (direct, no proxy) |
| 1883 | Mosquitto | MQTT device ingestion |
| 5432 | PostgreSQL | Database (internal) |

## Services and Responsibilities

### Caddy (caddy:2-alpine)
HTTPS reverse proxy. Terminates TLS with internally generated self-signed certificate. Routes `/realms/*`, `/resources/*`, `/admin/*`, `/js/*` to Keycloak and everything else to `ui_iot`. Port 80 redirects to HTTPS.

### services/ingest_iot
Device ingress, authentication, validation, and quarantine. Handles MQTT device connections, validates provision tokens via a TTL-based auth cache (eliminates per-message PG lookups), enforces rate limits, and writes accepted telemetry to TimescaleDB using batched writes. Multi-worker async pipeline processes ~20,000 msg/sec per instance. Supports arbitrary numeric/boolean metrics without schema changes.

### services/evaluator_iot
Heartbeat tracking, state management, alert generation, and threshold rule evaluation. Reads telemetry from TimescaleDB to maintain `device_state`, detects stale devices (NO_HEARTBEAT alerts), and evaluates customer-defined threshold rules against latest device metrics (THRESHOLD alerts). Rules support GT, LT, GTE, LTE operators on any metric. Creates and manages `alert_rules` table DDL on startup.

### services/ui_iot
FastAPI backend serving the React SPA and providing JSON APIs. Three API layers:

- **`/api/v2/*`** — REST API with JWT Bearer auth, per-tenant rate limiting, TimescaleDB telemetry queries, and WebSocket live data streaming. Customer-scoped (RLS-enforced).
- **`/customer/*`** — Customer JSON APIs for integrations, alert rules, devices, and alerts. Customer-scoped (RLS-enforced).
- **`/operator/*`** — Operator JSON APIs for cross-tenant views (BYPASSRLS), quarantine, audit log, and system settings. All access audited.

The SPA is served from `/app/` via a volume mount of `frontend/dist` at `/app/spa`.

### services/provision_api
Admin and device provisioning APIs. Handles device registration, activation code generation, token management, and administrative operations protected by X-Admin-Key.

### services/dispatcher
Alert-to-delivery job dispatcher. Polls `fleet_alert` for open alerts, matches them against `integration_routes`, and creates `delivery_jobs` for the worker.

### services/delivery_worker
Alert delivery via webhook, SNMP, email, and MQTT. Processes delivery_jobs with retry logic and exponential backoff (up to 5 attempts, 30s-7200s backoff range). Supports:
- **Webhooks**: HTTP POST with JSON payload
- **SNMP**: v2c and v3 trap delivery
- **Email**: SMTP with HTML/text templates, multiple recipients
- **MQTT**: Publish to customer-configured topics with QoS and retain

### simulator/device_sim_iot
Simulation only. Generates realistic device telemetry (battery_pct, temp_c, pressure_psi, humidity_pct, vibration_g, rssi_dbm, snr_db) and heartbeat messages for 25 simulated devices. Includes battery drain/recharge cycles and periodic uplink drops.

## Frontend Architecture

The frontend is a React SPA built with Vite and TypeScript, served at `/app/` by the `ui_iot` FastAPI backend.

### Technology Stack
| Layer | Technology |
|-------|-----------|
| Framework | React 18 + TypeScript |
| Build | Vite |
| Styling | TailwindCSS + shadcn/ui |
| Server state | TanStack Query (REST API data) |
| Client state | Zustand (WebSocket live data, UI state) |
| Auth | keycloak-js (browser-native OIDC/PKCE) |
| Charts | ECharts (gauges), uPlot (time-series) |
| Routing | React Router v6 |

### Page Structure
- **Customer pages**: Dashboard, Device List, Device Detail (telemetry charts + gauges), Alerts, Alert Rules CRUD, Webhook/SNMP/Email/MQTT integration management
- **Operator pages**: Cross-tenant Overview, All Devices (with tenant filter), Audit Log (admin only), System Settings (admin only)
- **Role-based routing**: Operators see only operator nav; customers see only customer nav. Index redirects to role-appropriate dashboard.

### Data Flow
1. **Initial load**: TanStack Query fetches data from REST API (`/api/v2/*`)
2. **Live updates**: WebSocket at `/api/v2/ws` pushes telemetry and alerts to Zustand stores
3. **Fusion**: Device detail charts merge REST historical data with WebSocket live data into a rolling buffer (500 points max, deduplicated by timestamp)
4. **Mutations**: CRUD operations use TanStack Query mutations that invalidate list caches on success

## Data Stores

### PostgreSQL
Transactional data store for all non-telemetry data:
- `device_state` — Current device status, last seen, state JSONB
- `fleet_alert` — Open/closed alerts with severity, fingerprint dedup
- `alert_rules` — Customer-defined threshold rules
- `integrations` — Webhook, SNMP, email, MQTT configurations
- `integration_routes` — Alert-to-integration routing rules
- `delivery_jobs` — Queued delivery work items
- `delivery_attempts` — Delivery attempt history
- `delivery_log` — Delivery event log
- `quarantine_events` — Rejected device events
- `operator_audit_log` — Operator cross-tenant access audit
- `app_settings` — System configuration
- `rate_limits` — Per-device rate limiting

### TimescaleDB (PostgreSQL Extension)
Time-series telemetry stored in a single `telemetry` hypertable:
- Automatic time-based partitioning (chunks)
- Compression policies for older data
- All metrics stored as JSONB in `metrics` column
- Tenant isolation via `tenant_id` column with application-level filtering
- Supports 20,000+ msg/sec with batched COPY inserts

## Authentication Model

### Browser Authentication (SPA)
The React SPA uses **keycloak-js** for direct browser-to-Keycloak OIDC authentication with PKCE. Keycloak is accessed at `window.location.origin` (same origin via Caddy reverse proxy). No server-side OAuth flow is needed — the browser handles the full OIDC code exchange.

### API Authentication
All `/api/v2/*`, `/customer/*`, and `/operator/*` endpoints require a JWT Bearer token in the `Authorization` header. The backend validates tokens against Keycloak's JWKS endpoint.

### User Roles

| Role | Description | Access |
|------|-------------|--------|
| `customer_viewer` | Read-only customer access | View devices, alerts, delivery status |
| `customer_admin` | Full customer access | Above + manage integrations, alert rules, routes |
| `operator` | Cross-tenant operator access | All tenant data, audited |
| `operator_admin` | Operator with admin functions | Above + system settings, audit log |

### JWT Claims

```json
{
  "iss": "https://192.168.10.53/realms/pulse",
  "sub": "user-uuid",
  "tenant_id": "tenant-a",
  "role": "customer_admin"
}
```

Operators have `tenant_id: ""` (empty) and use `operator_connection` (BYPASSRLS) for cross-tenant access.

## Core Flows

### Telemetry Ingestion Paths

```
Device → MQTT → ingest_iot → TimescaleDB
Device → HTTP POST → ui_iot/ingest → TimescaleDB
```

Both paths use shared validation (`services/shared/ingest_core.py`):
- DeviceAuthCache for credential caching
- TimescaleBatchWriter for batched writes (COPY for large batches, executemany for small)
- TokenBucket for per-device rate limiting

### Device Telemetry/Heartbeat Flow
```
Device → MQTT → ingest_iot → auth cache → validation → TimescaleDB (batched writes)
                                                              ↓
                                                      evaluator_iot → device_state + fleet_alert
                                                              ↓
ui_iot (REST API reads from TimescaleDB)
                                                              ↓
                                       React SPA (charts, gauges, WebSocket live updates)
```

### Alert Pipeline
```
evaluator_iot → fleet_alert (NO_HEARTBEAT + THRESHOLD)
                      ↓
                 dispatcher → route match → delivery_job
                                                 ↓
                                         delivery_worker
                                       ↓    ↓     ↓     ↓
                             webhook  SNMP  email  MQTT
                                       ↓    ↓     ↓     ↓
                                 delivery_attempts (logged)
```

### Rejection/Quarantine Flow
```
Device → MQTT → ingest_iot → validation failure → quarantine_events
                                                         ↓
                                              operator dashboard (SPA)
```

### Provisioning Flow
```
Admin → provision_api (X-Admin-Key) → create device → activation_code
Device → provision_api → activation_code → provision_token
Device → ingest_iot → provision_token validation → accepted telemetry
```

## Security Architecture

### Tenant Isolation

1. **JWT-based identity**: tenant_id extracted from validated JWT claims only
2. **Application enforcement**: All queries include tenant_id in WHERE clause
3. **RLS defense-in-depth**: PostgreSQL row-level security as backup layer
4. **TimescaleDB isolation**: Tenant filtering via tenant_id column with application-level enforcement
5. **Audit logging**: All operator cross-tenant access is logged with IP and user agent

### RLS Configuration

Two database roles used by `ui_iot`:
- `pulse_app` — Subject to RLS. Customer connections use `SET LOCAL ROLE pulse_app` with `app.tenant_id` context.
- `pulse_operator` — BYPASSRLS. Operator connections use `SET LOCAL ROLE pulse_operator` for cross-tenant access.

```sql
-- Customer connection (RLS enforced)
SET LOCAL ROLE pulse_app;
SELECT set_config('app.tenant_id', 'tenant-a', true);

-- Operator connection (BYPASSRLS)
SET LOCAL ROLE pulse_operator;
```

### SSRF Prevention

Customer-provided URLs (webhooks, SNMP destinations, SMTP hosts) are validated:
- Private IP ranges blocked (10.x, 172.16.x, 192.168.x)
- Loopback addresses blocked
- Cloud metadata endpoints blocked
- DNS resolution validated

## Operational Knobs

### MODE DEV/PROD
- PROD: Debug storage disabled, rejects not stored/mirrored, HTTPS required for webhooks
- DEV: Full debugging enabled, rejects can be stored for analysis

### Ingestion Performance
- `INGEST_WORKER_COUNT`: Async worker count (default: 4)
- `INGEST_QUEUE_SIZE`: Processing queue depth (default: 50000)
- `TIMESCALE_BATCH_SIZE`: TimescaleDB write batch size (default: 500)
- `TIMESCALE_FLUSH_INTERVAL_MS`: Max batch wait time (default: 1000)
- `AUTH_CACHE_TTL_SECONDS`: Device auth cache TTL (default: 60)

### Delivery Configuration
- `WORKER_MAX_ATTEMPTS`: Maximum retry attempts (default: 5)
- `WORKER_BACKOFF_BASE_SECONDS`: Initial retry delay (default: 30)
- `WORKER_TIMEOUT_SECONDS`: HTTP/SNMP/SMTP timeout (default: 30)

### API Rate Limiting
- `API_RATE_LIMIT`: Requests per window per tenant (default: 100)
- `API_RATE_WINDOW_SECONDS`: Rate limit window (default: 60)
- `WS_POLL_SECONDS`: WebSocket push interval (default: 5)
