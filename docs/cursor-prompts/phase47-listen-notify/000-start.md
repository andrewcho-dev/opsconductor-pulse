# Phase 47: PostgreSQL LISTEN/NOTIFY — Event-Driven Alert Pipeline

## Why This Phase

The entire alert pipeline is poll-based today:

| Service | Polls | Interval | Table |
|---------|-------|----------|-------|
| evaluator_iot | telemetry | 5s | telemetry |
| dispatcher | fleet_alert | 5s | fleet_alert |
| delivery_worker | delivery_jobs | 2s | delivery_jobs |
| ui_iot WebSocket | device_state + fleet_alert | 5s | multiple |

**End-to-end minimum latency:** ~13 seconds from device telemetry to alert delivery.

**With LISTEN/NOTIFY:** Each service wakes immediately when data arrives.
**End-to-end latency:** ~1–2 seconds. No architecture change — just replace sleep loops with listeners.

## Design Principles

**1. Notifications are hints, not data.**
The NOTIFY payload contains only `tenant_id:device_id` (or similar). Services still query the DB for the actual data. This avoids the 8KB PostgreSQL notify payload limit and keeps logic simple.

**2. Keep polling as a fallback.**
After switching to LISTEN, keep a slow polling loop (every 30s) as a safety net. If a notification is missed (connection blip, restart), the slow poll catches it within 30s. This is belt-and-suspenders.

**3. Debounce per tenant+device.**
If 50 telemetry rows arrive in 1 second for the same device, fire ONE evaluation — not 50. Use a short debounce window (0.5s): collect notifications, then process unique tenant+device combinations.

**4. One dedicated LISTEN connection per service.**
asyncpg `add_listener()` requires a dedicated connection (not from the pool — pool connections are transient). Each service keeps one long-lived listener connection alongside its normal pool.

## What Changes

| File | Change |
|------|--------|
| `db/migrations/056_listen_notify_triggers.sql` | Triggers on telemetry, fleet_alert, delivery_jobs |
| `services/evaluator_iot/evaluator.py` | Replace 5s sleep loop with LISTEN on `new_telemetry` + 30s fallback poll |
| `services/dispatcher/dispatcher.py` | Replace 5s sleep loop with LISTEN on `new_fleet_alert` + 30s fallback poll |
| `services/delivery_worker/worker.py` | Replace 2s sleep loop with LISTEN on `new_delivery_job` + 30s fallback poll |
| `services/ui_iot/app.py` | WebSocket: LISTEN on `device_state_changed` + `fleet_alert_changed` |

## Execution Order

| Prompt | Description | Priority |
|--------|-------------|----------|
| 001 | DB migration: triggers on telemetry, fleet_alert, delivery_jobs | CRITICAL |
| 002 | Evaluator: replace poll loop with LISTEN + fallback poll | CRITICAL |
| 003 | Dispatcher: replace poll loop with LISTEN + fallback poll | CRITICAL |
| 004 | Delivery worker: replace poll loop with LISTEN + fallback poll | HIGH |
| 005 | WebSocket in ui_iot: LISTEN for real-time push to browser | HIGH |
| 006 | Unit tests for listen/notify logic | HIGH |
| 007 | Verify: end-to-end latency smoke test | CRITICAL |

## Key Files

- `services/evaluator_iot/evaluator.py` — main eval loop (prompt 002)
- `services/dispatcher/dispatcher.py` — dispatcher loop (prompt 003)
- `services/delivery_worker/worker.py` — delivery loop (prompt 004)
- `services/ui_iot/app.py` — WebSocket handler (prompt 005)
- `db/migrations/` — triggers (prompt 001)
