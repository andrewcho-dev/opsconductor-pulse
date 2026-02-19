---
last-verified: 2026-02-19
sources:
  - compose/docker-compose.yml
  - compose/caddy/Caddyfile
phases: [88, 98, 138, 139, 142, 161]
---

# Service Map

> Quick-reference topology, ports, dependencies, and data flows.

## Network Topology

High-level routing:

- Browser traffic terminates at Caddy on HTTPS (:443).
- Caddy routes Keycloak paths (`/realms/*`, `/admin/*`, etc.) to the Keycloak service.
- All application paths (`/app/*`, `/customer/*`, `/operator/*`, `/api/v2/*`, `/ingest/*`) route to `ui_iot`.
- Devices publish telemetry to EMQX MQTT (external TLS port 8883) which feeds `ingest_iot`.
- EMQX uses internal `ui_iot` endpoints for CONNECT auth and per-topic ACL enforcement (`/api/v1/internal/*`).

## Port Reference

| Service | Internal Port | External Port | Protocol |
|---------|--------------|---------------|----------|
| ui_iot | 8000 | 443 (via Caddy) | HTTPS |
| ingest_iot | 8080 | — | HTTP (internal) |
| evaluator_iot | 8080 | — | HTTP (internal) |
| ops_worker | — | — | Background only |
| subscription_worker | — | — | Background only |
| provision_api | 8081 | 8081 | HTTP |
| Keycloak | 8080 | 443 (via Caddy) | HTTPS |
| PostgreSQL | 5432 | 5432 | TCP |
| PgBouncer | 6432 | — | TCP |
| EMQX | 1883/9001/18083 | 8883 (TLS), 18083 | MQTT/WS/HTTP |
| Prometheus | 9090 | 9090 | HTTP |
| Grafana | 3000 | 3001 | HTTP |

## Service Dependencies

| Service | Depends On | Why |
|---------|------------|-----|
| ui_iot | PgBouncer, Keycloak | API + auth + DB |
| ingest_iot | EMQX, PgBouncer/PostgreSQL | MQTT intake + telemetry writes |
| evaluator_iot | PgBouncer/PostgreSQL | Reads telemetry and writes alerts/state |
| ops_worker | ui_iot, ingest_iot, evaluator_iot, PgBouncer/PostgreSQL | Health polling + metrics |
| subscription_worker | PostgreSQL | Subscription lifecycle updates |
| provision_api | PostgreSQL | Provisioning registry and activation |
| Prometheus | ui_iot, ingest_iot, evaluator_iot, ops_worker | Scrapes health/metrics |
| Grafana | Prometheus | Dashboards |

## Core Data Flow

Telemetry ingestion:

1. Device → EMQX (MQTT/TLS) → `ingest_iot`
2. `ingest_iot` → TimescaleDB telemetry hypertable (via asyncpg)
3. `evaluator_iot` polls telemetry → updates device state + creates/updates/closes alerts
4. `ui_iot` serves the UI and exposes APIs to view devices/telemetry/alerts

Alert operations:

1. Alert created/updated (evaluator or user action)
2. Escalation tick evaluates pending escalations
3. Notification routing engine in `ui_iot` delivers to configured channels

## Database Tables (by domain)

The schema evolves via migrations in `db/migrations/` (84 migrations). Table groupings commonly referenced:

- Device & fleet: `device_state`, `device_api_tokens`, `device_groups`, `sites`, `maintenance_windows`
- Telemetry: `telemetry` (hypertable), telemetry helper tables, `quarantine_events`
- Alerts & rules: `fleet_alert`, `alert_rules`, `alert_rule_conditions`, escalation-related tables
- Notifications & on-call: `notification_channels`, `notification_routing_rules`, `notification_log`, on-call tables
- Subscriptions & billing: `subscriptions`, tier allocation tables, audit tables
- Operator/system: `operator_audit_log`, `system_metrics` (hypertable), settings tables

For the full schema and migration index, see the database operations doc.

## API Route Mapping

Major API surface area by prefix:

- Customer: `/api/v1/customer/*` (tenant-scoped)
- Operator: `/api/v1/operator/*` (cross-tenant, audited)
- Ingestion: `/ingest/*` (provision token / device auth)
- Legacy v2: `/api/v2/*` (deprecated)
- Provisioning: `provision_api` on `:8081` (X-Admin-Key)

## See Also

- [System Overview](overview.md)
- [Tenant Isolation](tenant-isolation.md)
- [API Overview](../api/overview.md)
- [Deployment](../operations/deployment.md)

