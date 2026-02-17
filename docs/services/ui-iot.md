---
last-verified: 2026-02-17
sources:
  - services/ui_iot/app.py
  - services/ui_iot/Dockerfile
  - compose/docker-compose.yml
phases: [1, 23, 43, 88, 91, 122, 128, 138, 142]
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

