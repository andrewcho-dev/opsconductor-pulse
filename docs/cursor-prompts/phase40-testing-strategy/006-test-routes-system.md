# 006: Unit Tests for routes/system.py

## Why
`services/ui_iot/routes/system.py` (859 LOC) has 16 endpoints with ZERO test coverage. These are the operator system monitoring endpoints — health checks, capacity metrics, aggregates, and error reporting. Operators rely on these to monitor the platform.

## Source File
Read: `services/ui_iot/routes/system.py`

## Pattern to Follow
Read: `tests/unit/test_customer_route_handlers.py` (first 80 lines) for FakeConn/FakePool, `_mock_customer_deps`, and `httpx.ASGITransport` pattern.

For operator routes, you'll need to mock operator auth instead of customer auth:
- Set role to `"operator"` or `"operator-admin"` in the mock user
- Set `tenant_id` to empty string or None
- Use `operator_connection` instead of `tenant_connection` (check how `routes/system.py` gets its DB connection)

## Test File to Create/Expand
`tests/unit/test_system_routes.py`

(This file may already exist with a few tests — read it first and expand.)

## Test Scenarios (~20 tests)

### Health Endpoint (5 tests)
```
test_system_health_returns_all_components
  - Mock all service health checks (postgres, mqtt, keycloak, ingest, evaluator, dispatcher, delivery)
  - All return healthy → overall status = "healthy"
  - Response includes component list with status + latency_ms

test_system_health_degraded_when_service_down
  - Mock ingest health check to fail
  - Overall status = "degraded"
  - Ingest component shows status = "unhealthy"

test_system_health_postgres_check
  - Mock pg connection success → postgres healthy
  - Mock pg connection failure → postgres unhealthy

test_system_health_mqtt_check
  - Mock socket connect success → mqtt healthy
  - Mock socket connect failure → mqtt unhealthy

test_system_health_requires_operator_role
  - Call with customer auth → 403
  - Call with operator auth → 200
```

### Metrics Endpoints (5 tests)
```
test_system_metrics_returns_throughput
  - Mock system_metrics table query → return sample rows
  - Response includes throughput data

test_system_metrics_history_returns_time_series
  - Mock query for time-bucketed metrics
  - Returns array of {time, value} pairs

test_system_metrics_history_batch_returns_multiple
  - Request multiple metric names
  - Returns data for each

test_system_metrics_latest_returns_current_values
  - Mock query for latest metric values
  - Returns dict of metric_name → value

test_ingest_rate_calculation
  - Mock telemetry count query (last 60s)
  - Returns calculated messages/second
```

### Capacity Endpoint (3 tests)
```
test_capacity_returns_db_size
  - Mock pg_database_size query
  - Returns size in bytes + human-readable

test_capacity_returns_connection_count
  - Mock pg_stat_activity query
  - Returns active/max connections

test_capacity_returns_top_tables
  - Mock table size query
  - Returns sorted list of table names + sizes
```

### Aggregates Endpoint (3 tests)
```
test_aggregates_returns_platform_counts
  - Mock COUNT queries for tenants, devices, alerts, integrations
  - Returns counts dict

test_aggregates_returns_alert_breakdown
  - Mock alert count by status (OPEN, CLOSED, ACKNOWLEDGED)
  - Returns breakdown

test_aggregates_requires_operator_role
  - Customer auth → 403
```

### Errors Endpoint (4 tests)
```
test_errors_returns_recent_failures
  - Mock delivery_jobs query (status=FAILED)
  - Returns recent errors list

test_errors_returns_quarantine_events
  - Mock quarantine_events query
  - Returns rejected message stats

test_errors_returns_rate_limit_events
  - Mock rate limit events
  - Returns rate limit stats

test_errors_empty_when_no_failures
  - All queries return empty → empty errors list
```

## Implementation Notes

The system routes are at `services/ui_iot/routes/system.py` with these exact endpoints:
```
GET /operator/system/health
GET /operator/system/metrics
GET /operator/system/metrics/history     (params: metric, minutes, service?, rate?)
GET /operator/system/metrics/history/batch (params: metrics, minutes)
GET /operator/system/metrics/latest
GET /operator/system/capacity
GET /operator/system/aggregates
GET /operator/system/errors              (params: hours, limit)
```

**Helper functions to mock:**
- `check_postgres() -> dict` — asyncpg connection test
- `check_keycloak() -> dict` — HTTP GET to Keycloak
- `check_service(name: str, url: str) -> dict` — HTTP GET to service `/health` endpoints
- `check_mqtt() -> dict` — socket connect to MQTT broker
- `fetch_service_counters(url: str) -> dict` — HTTP GET for counter values
- `calculate_ingest_rate(pool) -> float` — DB query for messages/second
- `get_postgres_capacity() -> dict` — pg_database_size query
- `get_disk_capacity() -> dict` — shutil.disk_usage call

**Mocking requirements:**
- `httpx.AsyncClient` for service health checks (5s timeout default)
- `asyncpg.Pool` and query results
- `socket` module for MQTT connectivity check
- `shutil.disk_usage` for disk capacity
- Use `monkeypatch` to set service URL env vars
- For operator auth, mock the JWT with `role="operator"` and `tenant_id=None`
- Follow `tests/unit/test_customer_route_handlers.py` for FakeConn/FakePool and `httpx.ASGITransport` patterns
- Use `pytestmark = [pytest.mark.unit, pytest.mark.asyncio]`
- Check if `tests/unit/test_system_routes.py` already exists — if so, **expand** it rather than creating a new file

## Verify
```bash
pytest tests/unit/test_system_routes.py -v
```
