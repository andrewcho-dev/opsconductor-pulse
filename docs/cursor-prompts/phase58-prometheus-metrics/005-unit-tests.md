# Prompt 005 — Unit Tests

## File: `tests/unit/test_prometheus_metrics.py`

Read `services/shared/metrics.py`. Use `prometheus_client` test utilities.

Tests using `@pytest.mark.unit`:

1. `test_shared_metrics_importable` — `from shared.metrics import ingest_messages_total` succeeds
2. `test_ingest_counter_increment` — increment `ingest_messages_total` with labels, verify value via `.labels(...).get()`  (use `REGISTRY` or collector `_value`)
3. `test_fleet_alerts_gauge_set` — set `fleet_active_alerts` gauge, verify value
4. `test_fleet_devices_gauge_set` — set `fleet_devices_by_status` with status labels, verify
5. `test_evaluator_counter_increment` — increment `evaluator_rules_evaluated_total`, verify
6. `test_ui_iot_metrics_endpoint` — GET /metrics on ui_iot app returns 200 and `Content-Type: text/plain`

Note: For test 6, mock the DB pool so no real DB call is made. Use FakePool/FakeConn pattern.

All `@pytest.mark.unit`.

## Acceptance Criteria

- [ ] 6 tests pass under `pytest -m unit -v`
- [ ] No existing tests broken
