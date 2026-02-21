# Prompt 003 — Unit Tests

## File: `tests/unit/test_telemetry_history.py`

Read a passing test file in `tests/unit/` for FakeConn/FakePool pattern.

Tests using `@pytest.mark.unit` and `@pytest.mark.asyncio`:

1. `test_telemetry_history_returns_points` — fetch returns rows → 200, points list with avg/min/max/count/time
2. `test_telemetry_history_empty` — no rows → 200, points=[]
3. `test_telemetry_history_invalid_range` — range="99y" → 400
4. `test_telemetry_history_default_range_24h` — no range param → uses "24h" bucket config
5. `test_telemetry_history_uses_time_bucket` — verify SQL contains "time_bucket" (check the query string passed to conn.fetch)
6. `test_telemetry_history_tenant_isolation` — verify WHERE clause includes tenant_id=$1

All `@pytest.mark.unit` and `@pytest.mark.asyncio`.

## Acceptance Criteria

- [ ] 6 tests pass under `pytest -m unit -v`
- [ ] No existing tests broken
