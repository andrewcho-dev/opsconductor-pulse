---
last-verified: 2026-02-20
sources:
  - services/ui_iot/app.py
  - services/ui_iot/Dockerfile
  - services/ui_iot/services/carrier_service.py
  - services/ui_iot/services/carrier_sync.py
  - services/ui_iot/routes/devices.py
  - services/ui_iot/routes/sensors.py
  - services/ui_iot/routes/ingest.py
  - services/ui_iot/routes/exports.py
  - services/ui_iot/routes/operator.py
  - services/ui_iot/routes/templates.py
  - services/ui_iot/routes/internal.py
  - compose/docker-compose.yml
  - frontend/src/features/fleet/GettingStartedPage.tsx
phases: [1, 23, 43, 88, 91, 122, 128, 138, 142, 157, 158, 160, 161, 162, 164, 165, 168, 169, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186]
---

# ui-iot

> Main API gateway and UI backend (FastAPI + SPA serving + routing engine).

## Overview

`ui_iot` is the central service for the platform:

- Serves the React SPA under `/app/*` (when the frontend bundle is present in the container).
- Exposes customer APIs (`/api/v1/customer/*`) and operator APIs (`/api/v1/operator/*`).
- Hosts legacy v2 endpoints (`/api/v2/*`) for compatibility.
- Hosts HTTP ingestion endpoints (`/ingest/v1/*`).
- Runs the Phase 91+ notification routing engine for outbound alert delivery.
- Emits request-context audit events to the audit log.

## HTTP Ingest (JetStream)

`ui_iot` provides HTTP ingest endpoints under `/ingest/v1/*`. These endpoints do fast validation, then publish an ingestion envelope to NATS JetStream using PubAck:

- Subject: `telemetry.{tenant_id}`
- Publish API: `js.publish(..., timeout=1.0)` (durable PubAck)

This unifies HTTP and MQTT ingestion: both ultimately flow through the same `ingest_iot` JetStream consumers.

## Message Route Delivery (JetStream)

Message routes (webhook / MQTT republish / postgresql destinations) are delivered asynchronously by `route_delivery` consuming from JetStream `ROUTES` (`routes.>`). This is separate from the alert notification routing engine in `ui_iot` (Slack/PagerDuty/Teams).

## Exports (S3/MinIO)

Export artifacts are stored in S3-compatible storage (MinIO in compose). Download endpoints return a pre-signed URL redirect so the client downloads directly from S3/MinIO.

## Architecture

Primary packages:

- `routes/` — API routers (customer/operator/devices/alerts/etc.)
- `middleware/` — auth, tenant context, permissions
- `db/` — pool wrappers, queries, audit helpers
- `notifications/` — routing engine and senders
- `oncall/` — schedule resolver
- `reports/` + `workers/` — scheduled report/export/escalation related logic

Background tasks (documented in `app.py`):

- Audit logger (async buffered audit flush)
- NATS client lifecycle (lazy connection + drain on shutdown)

## Configuration

Environment variables read from the main entrypoint (`services/ui_iot/app.py`):

Database:

| Variable | Default | Description |
|----------|---------|-------------|
| `PG_HOST` | `iot-postgres` | PostgreSQL host (used when `DATABASE_URL` is not set). |
| `PG_PORT` | `5432` | PostgreSQL port. |
| `PG_DB` | `iotcloud` | Database name. |
| `PG_USER` | `iot` | Database user. |
| `PG_PASS` | `iot_dev` | Database password. |
| `DATABASE_URL` | empty | Optional DSN; when set, preferred over `PG_*`. |
| `PG_POOL_MIN` | `2` | DB pool minimum connections. |
| `PG_POOL_MAX` | `10` | DB pool maximum connections. |

Ingestion and messaging:

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTH_CACHE_TTL_SECONDS` | `60` | Auth cache TTL (shared ingest/auth caching behaviors). |
| `REQUIRE_TOKEN` | `1` | When enabled, ingestion paths require device tokens. |
| `NATS_URL` | `nats://iot-nats:4222` | NATS JetStream endpoint used by HTTP ingest and internal publishers. |

Exports (S3/MinIO):

| Variable | Default | Description |
|----------|---------|-------------|
| `S3_ENDPOINT` | `http://iot-minio:9000` | Internal S3 endpoint (MinIO in compose). |
| `S3_PUBLIC_ENDPOINT` | empty | Optional base URL rewrite for browser-facing pre-signed URLs. |
| `S3_BUCKET` | `exports` | Bucket used for export artifacts. |
| `S3_ACCESS_KEY` | `minioadmin` | S3/MinIO access key. |
| `S3_SECRET_KEY` | `minioadmin` | S3/MinIO secret key. |
| `S3_REGION` | `us-east-1` | S3 region. |

UI / request handling:

| Variable | Default | Description |
|----------|---------|-------------|
| `UI_REFRESH_SECONDS` | `5` | Frontend refresh cadence default. |
| `CORS_ORIGINS` | empty | Comma-separated allowed origins. In non-PROD dev defaults are applied when unset. |
| `ENV` | empty | If `PROD`, CORS defaults change to fail closed. |
| `MODE` | `DEV` | Controls dev-only behaviors (e.g. docs visibility). |
| `SECURE_COOKIES` | `false` | If true, sets secure cookie behaviors. |
| `UI_BASE_URL` | `http://localhost:8080` | Base URL used for building absolute links. |

Keycloak/JWT wiring (used for OpenAPI docs gating and auth bootstrapping):

| Variable | Default | Description |
|----------|---------|-------------|
| `KEYCLOAK_PUBLIC_URL` | `KEYCLOAK_URL` or `http://localhost:8180` | Public Keycloak URL. |
| `KEYCLOAK_INTERNAL_URL` | `KEYCLOAK_URL` or public URL | Internal Keycloak URL used by backend. |
| `KEYCLOAK_REALM` | `pulse` | Realm name. |
| `KEYCLOAK_JWKS_URI` | derived | Optional override for JWKS URL. |
| `JWKS_TTL_SECONDS` | `300` | JWKS cache TTL. |

Note: additional auth settings are defined in `middleware/auth.py` and apply to token validation.

## Health & Metrics

Common endpoints:

- `GET /health` (service health)
- `GET /openapi.json` (OpenAPI schema)
- `GET /docs` and `GET /redoc` (dev mode; restricted in prod)

Prometheus metrics may be exposed depending on the component (see `shared/metrics.py` and compose Prometheus config).

## Dependencies

- PostgreSQL + TimescaleDB (via PgBouncer in compose)
- Keycloak (OIDC/JWT auth)
- Caddy reverse proxy (TLS termination + routing)
- Optional: external notification endpoints (Slack/PagerDuty/Teams/webhooks)

## Internal MQTT Auth (EMQX)

EMQX calls internal-only endpoints in `ui_iot` for MQTT CONNECT authentication and per-topic ACL checks:

- `POST /api/v1/internal/mqtt-auth`
- `POST /api/v1/internal/mqtt-acl`

These endpoints require the `X-Internal-Auth` header to match `MQTT_INTERNAL_AUTH_SECRET` and should never be exposed externally.

## Carrier Integration

Carrier integrations are implemented in:

- Provider implementations: `services/ui_iot/services/carrier_service.py`
- Customer routes: `services/ui_iot/routes/carrier.py`
- Background sync worker: `services/ui_iot/services/carrier_sync.py`

Operator carrier management:

- Operators can manage carrier integrations across all tenants via `/api/v1/operator/carrier-integrations`.
- These endpoints bypass RLS using `operator_connection()` and audit access via `log_operator_access()`.
- Write operations (create/update/delete) require `require_operator_admin`.
- Operator UI route: `/operator/carriers`.

Provider notes:

- Hologram auth uses query parameters (`?apikey=...`), not header-based auth.
- Hologram operations use the live API endpoints:
  - State changes via `POST /devices/{id}/state` with JSON body `{"state":"live"|"pause"|"deactivate"}`
  - Usage via `GET /usage/data` (per-device `deviceid=...`, and org-level `orgid=...` for bulk sync)
  - SMS via `POST /sms/incoming` (`fromnumber` is lowercase per API)
- Provider capabilities include `claim_sim()` (SIM provisioning) and `list_plans()` (plan discovery). Providers that do not support these operations may raise `NotImplementedError`.

Sync worker notes:

- The carrier sync worker updates `device_connections.data_used_mb` and also syncs `sim_status` and `network_status` when device info is available.
- Bulk usage optimization is supported via `CarrierProvider.get_bulk_usage()`. For Hologram this uses a single org-level call and aggregates usage per device.

## Template Management

Device template CRUD and sub-resource management is implemented in:

- Customer routes: `services/ui_iot/routes/templates.py`
- Router registration: `services/ui_iot/app.py` (`app.include_router(templates_router)`)

## Device Instance Model

Phase 169 updates device management APIs to use the instance-level template model:

- Device provisioning supports `template_id` and `parent_device_id` (stored on `device_registry`).
- Module assignment endpoints live in `services/ui_iot/routes/devices.py` (`/devices/{device_id}/modules`).
- Sensor endpoints in `services/ui_iot/routes/sensors.py` are backed by `device_sensors` and keep the fleet-wide `/sensors` endpoint for backward compatibility.
- Transport endpoints in `services/ui_iot/routes/sensors.py` are backed by `device_transports`. Legacy `/devices/{device_id}/connection` remains temporarily but is marked deprecated.

## Fleet Navigation (Phase 174)

The frontend Fleet sidebar is restructured into Setup / Monitor / Maintain sub-groups. A Getting Started page is served at `/app/fleet/getting-started` with 5-step onboarding and live completion detection. The fleet-wide Sensors page (`/app/sensors`) is removed from sidebar navigation but the route is preserved for backward compatibility.

## Navigation & Hub Pages (Phase 176)

Phase 176 introduces a Home landing page at `/app/home` and consolidates multiple standalone pages into hub pages (tabbed navigation with `?tab=` deep links). Key hub routes:

- `/app/alerts` — Alert inbox (simplified in Phase 180)
- `/app/analytics` — Analytics hub (Explorer, Reports tabs)
- `/app/devices` — Devices hub with 4 tabs (Devices, Templates, Map, Updates)
- `/app/settings` — Settings hub with 9 flat tabs (Phase 182)

Legacy routes redirect to the appropriate hub route with the correct `?tab=` parameter.

## Settings Hub (Phase 182)

Phase 182 keeps settings as a flat hub page with single-level tabs:

- `/app/settings` — Settings hub with tabs: General, Billing, Channels, Delivery Log, Dead Letter, Integrations, Members, Roles, Profile
- `/app/settings?tab=general` — Organization settings (default tab)
- `/app/settings?tab=members` — Members tab (requires `users.read`)
- `/app/settings?tab=roles` — Roles tab (requires `users.roles`)

Old nested paths (`/app/settings/general`, `/app/settings/billing`, etc.) redirect to the corresponding `?tab=` parameter.

## Connection Tools (Phase 178)

Phase 178 adds connection tooling pages:

- **Connection Guide** (`/app/fleet/tools`) — Language-specific code snippets (Python, Node.js, curl, Arduino) showing how to connect devices and send telemetry
- **MQTT Test Client** (`/app/fleet/mqtt-client`) — Browser-based MQTT client using mqtt.js over WebSocket for publishing/subscribing to topics

The Home page (`/app/home`) also gains a "Resource Usage" section displaying quota KPI cards from the entitlements API (`GET /api/v1/customer/billing/entitlements`). The Billing page (`/app/settings/billing`) is refactored to use `KpiCard` components instead of custom progress bars for usage display.

## Navigation Simplification (Phase 180)

Phase 180 simplifies the sidebar to 7 items and introduces a Rules hub:

- `/app/rules` — Rules hub with tabs: Alert Rules, Escalation, On-Call, Maintenance
- `/app/alerts` — Simplified to alert inbox only (rules/escalation/oncall/maintenance moved to Rules hub)
- `/app/devices` — Became the fleet entry point; flattened to tab-based sub-navigation in Phase 182

Old tab-based URLs (`/alerts?tab=rules`, `/alerts?tab=escalation`, etc.) redirect to the corresponding Rules hub tab.

## Tab Standardization (Phases 181-182)

All sub-page navigation uses flat single-level tabs. No nested hubs, no left-nav, no button-link rows.

- `/app/devices` — Devices hub with 4 tabs: Devices, Templates, Map, Updates
- `/app/settings` — Settings hub with 9 tabs: General, Billing, Channels, Delivery Log, Dead Letter, Integrations, Members, Roles, Profile

Old standalone routes redirect to the appropriate hub tab:
- `/app/sites` — Sites overview (standalone page)
- `/app/templates` -> `/app/devices?tab=templates`
- `/app/updates` -> `/app/devices?tab=updates`
- `/app/ota/campaigns` -> `/app/devices?tab=updates`
- `/app/ota/firmware` -> `/app/devices?tab=updates`
- `/app/fleet/tools` — Connection guide (standalone page)
- `/app/fleet/mqtt-client` — MQTT test client (standalone page)
- `/app/device-groups` — Device groups management (standalone page)
- `/app/settings/notifications` -> `/app/settings?tab=channels`
- `/app/settings/access` -> `/app/settings?tab=members`

Members and Roles tabs are permission-gated (`users.read` and `users.roles` respectively).

## Troubleshooting

- 401/403 across customer APIs: verify Keycloak realm roles and organization membership claim.
- RLS/tenant issues: verify tenant context propagation and DB role configuration (see tenant isolation doc).
- CORS issues: set `CORS_ORIGINS` explicitly in production-like environments.

## See Also

- [System Overview](../architecture/overview.md)
- [Customer Endpoints](../api/customer-endpoints.md)
- [Operator Endpoints](../api/operator-endpoints.md)
- [Alerting](../features/alerting.md)
- [Security](../operations/security.md)

