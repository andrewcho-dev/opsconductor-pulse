# Phase 121 -- Audit & Observability

## Depends On

Phase 120 (Security Hardening) must be completed first.

## Goal

Add comprehensive audit logging for authentication events, HTTP request metrics via Prometheus, cross-service trace propagation, and per-service health/performance metrics. After this phase, every auth attempt is logged to `audit_log`, every HTTP request emits Prometheus histograms, trace IDs flow end-to-end across services, and each worker exposes queue depth and processing duration gauges.

## Execution Order

| # | File | Commit message | Key files |
|---|------|----------------|-----------|
| 1 | `001-auth-event-audit.md` | `feat(audit): add auth event logging to audit_log` | `services/shared/audit.py`, `services/ui_iot/middleware/auth.py` |
| 2 | `002-prometheus-http-metrics.md` | `feat(metrics): add HTTP request histograms and auth failure counters` | `services/shared/metrics.py`, `services/ui_iot/middleware/trace.py`, `services/ui_iot/middleware/auth.py` |
| 3 | `003-cross-service-trace.md` | `feat(trace): propagate X-Trace-ID across service boundaries` | `services/shared/http_client.py` (new), `services/ui_iot/app.py`, `services/ops_worker/health_monitor.py`, `services/ops_worker/metrics_collector.py`, `services/ops_worker/workers/escalation_worker.py`, `services/delivery_worker/worker.py` |
| 4 | `004-per-service-health-metrics.md` | `feat(metrics): add queue depth, processing duration, and pool gauges per service` | `services/shared/metrics.py`, `services/evaluator_iot/evaluator.py`, `services/dispatcher/dispatcher.py`, `services/delivery_worker/worker.py`, `services/ops_worker/main.py` |

## Key Existing Files

- `services/shared/audit.py` -- AuditLogger with buffered batch COPY inserts (423 lines). Has convenience methods for device, alert, delivery, config events. No auth event methods.
- `services/shared/metrics.py` -- Prometheus Counter/Gauge definitions (58 lines). No HTTP histograms, no auth failure counters, no per-service gauges.
- `services/shared/logging.py` -- `trace_id_var` ContextVar (line 11), `JsonFormatter` that includes `trace_id` in every log line.
- `services/ui_iot/middleware/auth.py` -- JWT validation with `validate_token()` (line 89) and `JWTBearer.__call__` (line 132). Catches `ExpiredSignatureError`, `JWTClaimsError`, `JWTError` at lines 117-125. Has `_get_client_ip()` helper (line 68). No audit logging.
- `services/ui_iot/middleware/trace.py` -- `TraceMiddleware` (42 lines). Sets `trace_id_var`, logs `http_request` with method/path/status/elapsed_ms. Does not emit Prometheus metrics.
- `services/ui_iot/app.py` -- Main FastAPI app. Audit logger initialized at line 318 (`app.state.audit`). TraceMiddleware added at line 132. `/metrics` endpoint at line 423.
- `services/evaluator_iot/evaluator.py` -- Main loop at line 1017. NOTIFY-driven with fallback poll. Has `COUNTERS` dict.
- `services/dispatcher/dispatcher.py` -- Main loop at line 410. NOTIFY-driven. Has `COUNTERS` dict.
- `services/delivery_worker/worker.py` -- Main loop at line 924. NOTIFY-driven. Has `COUNTERS` dict. Uses `httpx.AsyncClient` for webhook/slack/teams/pagerduty delivery.
- `services/ops_worker/main.py` -- Runs `worker_loop()` for multiple sub-workers. `run_health_monitor()` and `run_metrics_collector()` use `httpx.AsyncClient`.

## Verification (after all 4 tasks)

1. **Auth audit**: Make a request with an expired/invalid token. Query `SELECT * FROM audit_log WHERE event_type LIKE 'auth.%' ORDER BY timestamp DESC LIMIT 5;` -- should see `auth.login_failure` rows.
2. **HTTP metrics**: `curl localhost:8081/metrics | grep http_request_duration_seconds` -- should see histogram buckets with observations.
3. **Trace propagation**: Make a request to `ui_iot`, check downstream service logs for the same `trace_id` value.
4. **Service gauges**: `curl localhost:8082/metrics | grep pulse_processing_duration_seconds` (evaluator on port 8080) -- should see histogram buckets.
