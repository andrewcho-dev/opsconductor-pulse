# Task 4: Write Per-Service Documentation

## Context

7 backend services exist with zero individual documentation. Each needs a doc covering what it does, how it's configured, how it connects to other services, and how to troubleshoot it.

## Consistent Structure

Every service doc follows this template:

```markdown
---
last-verified: 2026-02-17
sources:
  - <main source file(s)>
phases: [relevant phase numbers]
---

# Service Name

> One-line description.

## Overview
What this service does and its role in the platform.

## Architecture
How it fits into the system. Key internal components.

## Configuration
Table of ALL environment variables the service reads, with defaults and descriptions.
Read the actual source code to build this table — do not guess.

## Health & Metrics
Health check endpoint (if any), Prometheus metrics exposed.

## Dependencies
What it connects to (PostgreSQL, other services, Keycloak, MQTT).

## Troubleshooting
Common failure modes and how to diagnose them.

## See Also
Links to related docs.
```

## Actions

### File 1: `docs/services/ui-iot.md`

**Source files to read:**
- `services/ui_iot/app.py` — main app, all env vars, router mounting
- `services/ui_iot/Dockerfile`
- `compose/docker-compose.yml` (ui service definition)

**Key content:**
- Main API gateway serving React SPA + all REST/WS endpoints
- Background workers: escalation_worker (60s tick), report_worker (daily), batch_writer (1s flush), audit_logger
- Packages: routes/, middleware/, workers/, notifications/, oncall/, reports/, db/, shared/
- All env vars from app.py module level (PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASS, DATABASE_URL, AUTH_CACHE_TTL, BATCH_SIZE, FLUSH_INTERVAL_MS, REQUIRE_TOKEN, UI_REFRESH_SECONDS, CORS_ORIGINS, etc.)
- Mounts: Caddy routes /app/*, /api/v2/*, /customer/*, /operator/*, /ingest/* to this service

### File 2: `docs/services/evaluator.md`

**Source files to read:**
- `services/evaluator_iot/evaluator.py` — main module, all env vars, evaluation loop

**Key content:**
- Polls device_state and alert_rules tables on POLL_SECONDS interval
- Evaluates threshold rules (GT/GTE/LT/LTE) with optional time-window (duration_seconds)
- Creates/updates/closes alerts in fleet_alert table
- Generates NO_HEARTBEAT alerts based on HEARTBEAT_STALE_SECONDS
- Env vars: PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASS, DATABASE_URL, POLL_SECONDS, HEARTBEAT_STALE_SECONDS
- Health endpoint on port 8080
- Prometheus metrics: evaluator_rules_evaluated_total, evaluator_alerts_created_total, evaluator_evaluation_errors_total

### File 3: `docs/services/ingest.md`

**Source files to read:**
- `services/ingest_iot/ingest.py` — main module, MQTT + HTTP, all env vars

**Key content:**
- Dual ingestion: MQTT subscriber + aiohttp HTTP server
- MQTT topics: `tenant/+/device/+/+` (configurable), shadow reported, command ack
- Auth: device provision tokens via DeviceAuthCache (TTL-based)
- Rate limiting: per-device TokenBucket
- Batch writing: TimescaleBatchWriter with configurable batch size and flush interval
- Quarantine: invalid messages written to quarantine_events
- Env vars: MQTT_HOST, MQTT_PORT, MQTT_TOPIC, MQTT_USERNAME, MQTT_PASSWORD, MQTT_CA_CERT, PG_*, AUTO_PROVISION, REQUIRE_TOKEN, CERT_AUTH_ENABLED, AUTH_CACHE_TTL, BATCH_SIZE, FLUSH_INTERVAL_MS, INGEST_WORKER_COUNT, INGEST_QUEUE_SIZE, etc.

### File 4: `docs/services/ops-worker.md`

**Source files to read:**
- `services/ops_worker/main.py` — entry point, worker orchestration
- `services/ops_worker/health_monitor.py` — health polling loop
- `services/ops_worker/metrics_collector.py` — metrics collection loop
- `services/ops_worker/workers/` directory — all background workers

**Key content:**
- Background process running multiple tick-based workers
- Workers: health_monitor, metrics_collector, commands_expiry, certificate_worker, escalation_worker, export_worker, export_cleanup, jobs_expiry, ota_campaign, ota_status_listener, report_worker
- Each worker has its own interval and function
- Env vars from main.py, health_monitor.py, metrics_collector.py

### File 5: `docs/services/subscription-worker.md`

**Source files to read:**
- `services/subscription_worker/worker.py` — all logic

**Key content:**
- Scheduled job for subscription lifecycle management
- Sends renewal notifications at 90/60/30/14/7/1 days before expiry
- State transitions: ACTIVE → GRACE (when term_end passes), GRACE → SUSPENDED (when grace_end passes)
- Nightly device count reconciliation
- Env vars: DATABASE_URL, NOTIFICATION_WEBHOOK_URL

### File 6: `docs/services/provision-api.md`

**Source files to read:**
- `services/provision_api/app.py` — FastAPI app, all endpoints, env vars

**Key content:**
- Standalone FastAPI service for device provisioning (port 8081)
- Auth: X-Admin-Key header
- Endpoints: device registration, token generation, activation
- Env vars: PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASS, DATABASE_URL, ADMIN_KEY, ACTIVATION_TTL_MINUTES, MQTT_PASSWD_FILE

### File 7: `docs/services/keycloak.md`

**Source files to read:**
- `compose/keycloak/realm-pulse.json` — realm configuration
- `compose/docker-compose.yml` (keycloak service definition)
- `services/ui_iot/services/keycloak_admin.py` — admin API client

**Key content:**
- Keycloak 24+ with Organizations feature
- Realm: `pulse`
- Client: `pulse-spa` (OIDC/PKCE, public client)
- Roles: customer, tenant-admin, operator, operator-admin
- Organizations map to tenants
- JWT claims: sub, preferred_username, email, realm_access.roles, organization
- Admin API client in ui_iot for user management
- Env vars: KEYCLOAK_INTERNAL_URL, KEYCLOAK_REALM, KEYCLOAK_ADMIN_USERNAME, KEYCLOAK_ADMIN_PASSWORD
- Custom login theme in compose/keycloak/themes/

## Accuracy Rules

- Read the actual source files before writing. Every env var must come from the code, not from memory.
- Do not reference dispatcher or delivery_worker — they are deleted.
- Cross-link to architecture docs and API docs where relevant.
