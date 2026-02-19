---
last-verified: 2026-02-19
sources:
  - services/ui_iot/app.py
  - services/ui_iot/Dockerfile
  - services/ui_iot/services/carrier_service.py
  - services/ui_iot/services/carrier_sync.py
  - services/ui_iot/routes/operator.py
  - services/ui_iot/routes/internal.py
  - compose/docker-compose.yml
phases: [1, 23, 43, 88, 91, 122, 128, 138, 142, 157, 158, 160, 161]
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

## Architecture

Primary packages:

- `routes/` — API routers (customer/operator/devices/alerts/etc.)
- `middleware/` — auth, tenant context, permissions
- `db/` — pool wrappers, queries, audit helpers
- `notifications/` — routing engine and senders
- `oncall/` — schedule resolver
- `reports/` + `workers/` — scheduled report/export/escalation related logic

Background tasks (documented in `app.py`):

- Batch writer (telemetry buffering/flush for HTTP ingest)
- Audit logger (async buffered audit flush)

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

Ingestion and batching:

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTH_CACHE_TTL_SECONDS` | `60` | Auth cache TTL (shared ingest/auth caching behaviors). |
| `BATCH_SIZE` | `500` | Batch size threshold for HTTP ingest buffering. |
| `FLUSH_INTERVAL_MS` | `1000` | Max time before flushing telemetry batch. |
| `REQUIRE_TOKEN` | `1` | When enabled, ingestion paths require device tokens. |

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

