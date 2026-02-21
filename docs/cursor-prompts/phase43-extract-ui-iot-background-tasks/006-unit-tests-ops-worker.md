# Prompt 006 — Unit Tests for `ops_worker`

## Context

The `ops_worker` service is running. This prompt adds unit tests to lock in the health monitor and metrics collector behavior so regressions are caught.

## Your Task

Create `tests/unit/test_ops_worker.py`. Follow the existing unit test patterns exactly:
- `pytestmark = [pytest.mark.unit, pytest.mark.asyncio]`
- Use `FakeConn` / `FakePool` for DB mocking
- Use `monkeypatch` and `AsyncMock`
- Reference: `tests/unit/test_customer_route_handlers.py`

### Tests for health monitor

1. **`test_health_monitor_writes_service_health_row`**
   — Mock the HTTP calls to service endpoints (all return 200), mock DB. Assert that after one cycle, an INSERT/UPSERT is called on the `service_health` table with `status = 'healthy'`

2. **`test_health_monitor_writes_unhealthy_on_http_error`**
   — Mock one service endpoint to raise `httpx.ConnectError`. Assert that the health row for that service has `status = 'unhealthy'` (or equivalent)

3. **`test_health_monitor_crash_does_not_kill_metrics_collector`**
   — Run both coroutines with `asyncio.gather()`. Make the health monitor raise an unhandled exception. Assert the metrics collector coroutine continues running (crash isolation from prompt 003)

4. **`test_health_monitor_loop_respects_interval`**
   — Mock `asyncio.sleep`. Assert it is called with the correct interval value after each cycle

### Tests for metrics collector

5. **`test_metrics_collector_queries_db_aggregates`**
   — Mock FakeConn to return aggregate rows. Assert the metrics collector calls the expected SELECT queries

6. **`test_metrics_collector_writes_summary_row`**
   — Assert that after one cycle, an INSERT/UPSERT is called on the metrics summary table with the correct data shape

7. **`test_metrics_collector_loop_respects_interval`**
   — Mock `asyncio.sleep`. Assert it is called with the correct interval value

## Acceptance Criteria

- [ ] `tests/unit/test_ops_worker.py` exists with all 7 tests
- [ ] All tests use `pytest.mark.unit` and `pytest.mark.asyncio`
- [ ] `pytest -m unit -v` passes with 0 failures
- [ ] No real DB or HTTP connections — all mocked
- [ ] Each test has a docstring
