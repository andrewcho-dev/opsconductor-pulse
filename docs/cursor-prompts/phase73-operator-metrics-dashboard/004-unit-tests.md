# Prompt 004 — Unit Tests

## Note

This phase is frontend-only. Backend system metrics endpoints already exist. Unit tests verify the existing backend endpoints return expected shapes.

## File: `tests/unit/test_system_metrics_endpoints.py`

Use FakeConn/FakePool pattern. Tests using `@pytest.mark.unit` and `@pytest.mark.asyncio`:

1. `test_system_metrics_latest_returns_snapshot` — GET /operator/system/metrics/latest returns dict with expected keys
2. `test_system_metrics_history_returns_points` — GET /operator/system/metrics/history returns points list
3. `test_system_metrics_requires_operator` — unauthenticated request → 401 or 403

All `@pytest.mark.unit` and `@pytest.mark.asyncio`.

## Acceptance Criteria

- [ ] 3 tests pass under `pytest -m unit -v`
- [ ] No existing tests broken
