# Phase 128: Simplification & Consolidation

## Depends On

- Phase 122 (Alert Engine v2 completed -- evaluator_iot supports threshold, anomaly, telemetry_gap, and WINDOW rule types)

## Objective

Eliminate duplicate services, notification pipelines, and API surfaces that accumulated during the platform's evolution from SimCloud to OpsConductor-Pulse. After this phase, the system has:

1. **One ingest service** (`ingest_iot`) -- legacy `services/ingest/` removed
2. **One evaluator service** (`evaluator_iot`) -- legacy `services/evaluator/` removed
3. **One notification pipeline** -- all delivery types (slack, pagerduty, teams, webhook, email, snmp, mqtt) consolidated into `notifications/senders.py`; legacy dispatcher/delivery_worker marked DEPRECATED
4. **One primary API surface** (`/customer/`) -- `/api/v2/` endpoints marked deprecated with Sunset headers; WebSocket endpoint moved to `/customer/ws`

## Execution Order

| Step | File | Commit message | Risk |
|------|------|----------------|------|
| 1 | `001-merge-duplicate-services.md` | `refactor: remove legacy ingest and evaluator services` | Low -- compose already uses `_iot` variants; legacy dirs are dead code |
| 2 | `002-consolidate-notification-pipelines.md` | `feat: consolidate all notification senders into unified pipeline` | Medium -- adds new sender functions, marks old pipeline deprecated |
| 3 | `003-deprecate-duplicate-api.md` | `feat: deprecate /api/v2/ endpoints in favor of /customer/` | Low -- additive headers and redirect only |

## Key Files (read these first for context)

### Services being removed
- `services/ingest/ingest.py` -- legacy MQTT ingest, writes to `_deprecated_raw_events` table
- `services/ingest/requirements.txt`
- `services/evaluator/evaluator.py` -- legacy evaluator, reads from `_deprecated_raw_events`, hardcoded site logic
- `services/evaluator/requirements.txt`

### Services being kept (canonical)
- `services/ingest_iot/ingest.py` -- current MQTT ingest with device auth, TimescaleDB batch writes, subscriptions, auto-provision
- `services/ingest_iot/Dockerfile`
- `services/evaluator_iot/evaluator.py` -- current evaluator with rule_type support, LISTEN/NOTIFY, anomaly detection, telemetry_gap, WINDOW duration
- `services/evaluator_iot/Dockerfile`

### Notification pipeline files
- `services/ui_iot/notifications/senders.py` -- current senders (slack, pagerduty, teams, webhook)
- `services/ui_iot/notifications/dispatcher.py` -- routing engine that queues notification_jobs
- `services/delivery_worker/worker.py` -- processes both legacy `delivery_jobs` and new `notification_jobs`
- `services/delivery_worker/email_sender.py` -- email delivery implementation
- `services/delivery_worker/snmp_sender.py` -- SNMP trap delivery implementation
- `services/delivery_worker/mqtt_sender.py` -- MQTT alert delivery implementation
- `services/dispatcher/dispatcher.py` -- legacy dispatcher creating delivery_jobs from fleet_alert + integration_routes

### API files
- `services/ui_iot/app.py` -- FastAPI app with all routers, middleware, startup/shutdown
- `services/ui_iot/routes/api_v2.py` -- `/api/v2/` routes (devices, fleet, alerts, telemetry, WebSocket)
- `services/ui_iot/routes/notifications.py` -- `/customer/notification-channels` and `/customer/notification-routing-rules`
- `services/ui_iot/routes/customer.py` -- `/customer/` routes (sites, subscriptions, etc.)

### Docker Compose
- `compose/docker-compose.yml` -- all service definitions

## Verification After All Steps

```bash
# 1. Validate compose config
cd compose && docker compose config --quiet && echo "OK"

# 2. Build and start
docker compose up -d --build

# 3. Check services are healthy
docker compose ps
docker compose logs ingest --tail 20
docker compose logs evaluator --tail 20

# 4. Verify deprecated services still start (backward compat)
docker compose logs dispatcher --tail 10 | grep -i deprecat
docker compose logs delivery_worker --tail 10 | grep -i deprecat

# 5. Verify /api/v2/ deprecation headers
curl -sI http://localhost:8080/api/v2/health | grep -i deprecation
curl -sI http://localhost:8080/api/v2/health | grep -i sunset

# 6. Verify legacy dirs are gone
test ! -d services/ingest && echo "ingest removed"
test ! -d services/evaluator && echo "evaluator removed"
```
