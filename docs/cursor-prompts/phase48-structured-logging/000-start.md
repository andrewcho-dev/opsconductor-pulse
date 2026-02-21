# Phase 48: Structured Logging / Observability

## Current State

- `services/shared/logging.py` exists with `get_logger()` but uses plain-text format: `"%(asctime)s - %(name)s - %(levelname)s - %(message)s"` — not JSON, not machine-parseable
- `services/shared/sampled_logger.py` exists with `SampledLogger` — good, keep it
- Worker services (evaluator, dispatcher, delivery_worker, ingest, ops_worker) still use ad-hoc `print()` calls — 26 total across those services
- `services/ui_iot/` already uses Python `logging` module — needs JSON format upgrade only
- No `request_id` propagation across the pipeline
- No structured context on log lines (tenant_id, device_id, alert_id, etc.)

## What This Phase Does

1. **Upgrade `services/shared/logging.py`** — JSON formatter with standard fields
2. **Replace all `print()` calls** in worker services with structured logger
3. **Add `request_id` middleware** to `ui_iot` — every HTTP request gets a unique ID logged with all log lines in that request
4. **Log key business events** with context fields (tenant_id, device_id, alert_id, etc.)
5. **Consistent log levels** across all services

## Target Log Format (JSON, one line per event)

```json
{
  "ts": "2026-02-13T20:00:00.123Z",
  "level": "INFO",
  "service": "evaluator",
  "msg": "alert created",
  "tenant_id": "acme-industrial",
  "device_id": "SENSOR-001",
  "alert_id": "42",
  "alert_type": "THRESHOLD",
  "duration_ms": 12
}
```

Every line has: `ts`, `level`, `service`, `msg`. Additional context fields as needed.

## Log Levels (standard)

| Level | Use |
|-------|-----|
| DEBUG | Verbose per-device/per-message trace (disabled in prod) |
| INFO | Normal operations: alert created, delivery sent, device online |
| WARNING | Degraded but functional: LISTEN setup failed, fallback poll running, rate limited |
| ERROR | Failed operation: delivery failed, DB error, auth error |
| CRITICAL | Service cannot continue: pool exhausted, unrecoverable error |

## Execution Order

| Prompt | Description | Priority |
|--------|-------------|----------|
| 001 | Upgrade `shared/logging.py` to JSON formatter | CRITICAL |
| 002 | Replace `print()` calls in evaluator, dispatcher, delivery_worker | HIGH |
| 003 | Replace `print()` calls in ingest_iot, ops_worker, provision_api | HIGH |
| 004 | Add `request_id` middleware to ui_iot | HIGH |
| 005 | Unit tests for JSON log format | MEDIUM |
| 006 | Verify: log output is valid JSON, key events logged with context | CRITICAL |

## Key Files

- `services/shared/logging.py` — upgrade this (prompt 001)
- `services/evaluator_iot/evaluator.py` — 10+ print() calls (prompt 002)
- `services/dispatcher/dispatcher.py` — print() calls (prompt 002)
- `services/delivery_worker/worker.py` — print() calls (prompt 002)
- `services/ingest_iot/ingest.py` — print() calls (prompt 003)
- `services/ops_worker/health_monitor.py`, `metrics_collector.py` — print() calls (prompt 003)
- `services/ui_iot/app.py` — add request_id middleware (prompt 004)
