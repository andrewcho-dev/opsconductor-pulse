# Phase 120: Backend Security Hardening

## Overview

This phase closes five categories of security gaps in the OpsConductor-Pulse backend:

1. **RBAC enforcement on write endpoints** -- most write routes only check `require_customer`, not the granular `require_permission()` from Phase 080.
2. **Database safety** -- missing `statement_timeout`, unwrapped multi-statement transactions, and a health check that opens raw connections outside the pool.
3. **Rate-limiting gaps** -- heavy or destructive endpoints lack per-endpoint rate limits, and one monitoring endpoint is entirely unauthenticated.
4. **MQTT internal TLS** -- the internal plaintext listener (1883) carries production telemetry over the Docker network without encryption.
5. **Catch-all exception handler** -- unhandled exceptions can leak stack traces to clients; no trace_id in 500 responses; metric keys are not length-validated.

## Execution Order

Run these prompts **in order**. Each builds on the previous:

| Step | File | Summary |
|------|------|---------|
| 1 | `001-rbac-write-endpoints.md` | Migration 081 + apply `require_permission()` to all write endpoints |
| 2 | `002-database-safety.md` | Add `statement_timeout`, wrap transactions, fix pool usage |
| 3 | `003-rate-limiting-gaps.md` | Add slowapi rate limits to heavy/destructive endpoints, auth on metrics |
| 4 | `004-mqtt-internal-tls.md` | Enable TLS on internal MQTT listener, update service connections |
| 5 | `005-catch-all-exception-handler.md` | Global exception handler with trace_id, metric key validation |

## Key Source Files

| File | Purpose |
|------|---------|
| `services/ui_iot/app.py` | FastAPI app, pool init, exception handlers, middleware |
| `services/ui_iot/middleware/auth.py` | JWT validation, JWTBearer class |
| `services/ui_iot/middleware/permissions.py` | `require_permission()`, `load_user_permissions()`, RBAC |
| `services/ui_iot/middleware/tenant.py` | `inject_tenant_context`, `require_customer`, `require_operator` |
| `services/ui_iot/middleware/trace.py` | TraceMiddleware, sets `request.state.trace_id` |
| `services/ui_iot/routes/devices.py` | Device CRUD, tags, groups, maintenance windows |
| `services/ui_iot/routes/alerts.py` | Alert management, alert rules CRUD |
| `services/ui_iot/routes/notifications.py` | Notification channels and routing rules |
| `services/ui_iot/routes/escalation.py` | Escalation policies |
| `services/ui_iot/routes/oncall.py` | On-call schedules, layers, overrides |
| `services/ui_iot/routes/ingest.py` | HTTP ingest endpoints, rate-limit stats |
| `services/ui_iot/routes/system.py` | System health (operator), has its own pool |
| `services/ui_iot/routes/customer.py` | Shared imports, `limiter`, `CUSTOMER_RATE_LIMIT`, models |
| `services/shared/ingest_core.py` | Ingest validation, `validate_and_prepare()` |
| `services/shared/rate_limiter.py` | RateLimiter class |
| `services/shared/logging.py` | JsonFormatter, `trace_id_var` |
| `services/ops_worker/main.py` | ops_worker pool init |
| `services/ingest_iot/ingest.py` | MQTT ingest service, paho-mqtt connection |
| `services/ui_iot/services/mqtt_sender.py` | `publish_alert()` MQTT helper |
| `compose/mosquitto/mosquitto.conf` | Mosquitto config |
| `compose/docker-compose.yml` | Service definitions, env vars |
| `db/migrations/080_iam_permissions.sql` | Current permission schema and seed data |
| `scripts/seed_demo_data.py` | Demo data seeder |

## Verification (full phase)

After completing all 5 prompts:

```bash
# 1. Run migration
psql "$DATABASE_URL" -f db/migrations/081_rbac_permissions.sql

# 2. Start stack
docker compose -f compose/docker-compose.yml up -d

# 3. Verify RBAC
# Authenticate as Viewer role user, attempt POST /customer/devices -> expect 403
# Authenticate as Full Admin, attempt POST /customer/devices -> expect 201

# 4. Verify statement_timeout
# psql: SELECT pg_sleep(35); -- should fail after 30s

# 5. Verify rate limits
# Rapid-fire GET /customer/devices/{id}/telemetry/export -> expect 429 after 5 calls

# 6. Verify MQTT TLS
# docker compose exec mqtt mosquitto_sub -h localhost -p 1883 --cafile /mosquitto/certs/ca.crt ...

# 7. Verify exception handler
# Trigger unhandled error -> response should be {"detail": "Internal server error", "trace_id": "..."} with no stack trace
```
