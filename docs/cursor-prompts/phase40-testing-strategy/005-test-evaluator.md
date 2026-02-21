# 005: Unit Tests for evaluator_iot/evaluator.py

## Why
`services/evaluator_iot/evaluator.py` (580 LOC) has ZERO tests. This is the alert evaluation engine that determines when alerts fire. It runs every 5 seconds in production. A bug here means silent alert failures — customers don't get notified of device problems.

## Source File
Read: `services/evaluator_iot/evaluator.py`

## Test File to Create
`tests/unit/test_evaluator.py`

(There may already be a file with this name — check first. If so, expand it.)

## Test Scenarios (~20 tests)

### Threshold Rule Evaluation (8 tests)
```
test_threshold_gt_fires_when_exceeded
  - Rule: metric=temp_c, operator=">", threshold=40
  - Device state: temp_c=45
  - Result: alert created

test_threshold_gt_does_not_fire_when_below
  - Rule: metric=temp_c, operator=">", threshold=40
  - Device state: temp_c=35
  - Result: no alert

test_threshold_lt_fires_when_below
  - Rule: metric=battery_pct, operator="<", threshold=20
  - Device state: battery_pct=15
  - Result: alert created

test_threshold_gte_boundary
  - Rule: metric=temp_c, operator=">=", threshold=40
  - Device state: temp_c=40 (exactly at boundary)
  - Result: alert created

test_threshold_eq_exact_match
  - Rule: operator="==", threshold=100
  - Device state: metric=100 → fires
  - Device state: metric=99 → doesn't fire

test_threshold_ne_fires_on_difference
  - Rule: operator="!=", threshold=0
  - Device state: metric=1 → fires
  - Device state: metric=0 → doesn't fire

test_disabled_rule_not_evaluated
  - Rule: enabled=False
  - Even with matching metric → no alert

test_site_filter_respects_scope
  - Rule: site_ids=["site-a"]
  - Device in site-a → evaluated
  - Device in site-b → skipped
```

### Metric Normalization (4 tests)
```
test_metric_mapping_applied
  - Raw metric "temp_f" maps to "temp_c" with multiplier=0.5556, offset=-17.78
  - Rule targets "temp_c"
  - Raw value 212 → normalized 100 → exceeds threshold

test_metric_mapping_not_found_uses_raw
  - No mapping exists for metric
  - Raw value used directly for comparison

test_metric_mapping_with_zero_multiplier
  - Edge case: multiplier=0 → normalized value is offset_value

test_metric_not_in_device_state_skipped
  - Rule targets "humidity" but device has no humidity metric
  - No alert, no error
```

### Heartbeat / Status Detection (4 tests)
```
test_stale_device_creates_no_heartbeat_alert
  - Device last_heartbeat_at > HEARTBEAT_STALE_SECONDS ago
  - Status set to STALE
  - NO_HEARTBEAT alert created with severity=4

test_online_device_no_heartbeat_alert
  - Device last_heartbeat_at within HEARTBEAT_STALE_SECONDS
  - Status stays ONLINE
  - No alert

test_stale_to_online_closes_alert
  - Device was STALE, heartbeat received
  - Status → ONLINE
  - Existing NO_HEARTBEAT alert closed

test_status_change_logged
  - Device transitions ONLINE → STALE
  - last_state_change_at updated
  - If unchanged, last_state_change_at NOT updated
```

### Alert Deduplication (4 tests)
```
test_duplicate_open_alert_not_created
  - Alert with fingerprint "RULE:r1:d1" already OPEN
  - Same rule fires again → no new alert (dedup by unique index)

test_closed_alert_allows_new_one
  - Alert was OPEN, then CLOSED
  - Same rule fires → new OPEN alert created

test_fingerprint_format_rule
  - Rule alert fingerprint = "RULE:{rule_id}:{device_id}"

test_fingerprint_format_heartbeat
  - Heartbeat alert fingerprint = "NO_HEARTBEAT:{device_id}"
```

## Implementation Notes

The evaluator at `services/evaluator_iot/evaluator.py` is **function-based** (no classes). Key functions to test:

**Pure functions (test directly, no mocks needed):**
- `evaluate_threshold(value: float, operator: str, threshold: float) -> bool` — checks GT, LT, GTE, LTE using `OPERATOR_SYMBOLS = {"GT": ">", "LT": "<", "GTE": ">=", "LTE": "<="}`
- `normalize_value(raw_value, multiplier, offset_value) -> float | None` — applies `(raw_value * multiplier) + offset`

**Async functions (need FakeConn mocks):**
- `open_or_update_alert(conn, tenant_id, site_id, device_id, alert_type, fingerprint, severity, confidence, summary, details) -> Tuple[id, inserted]` — INSERT ... ON CONFLICT ... DO UPDATE
- `close_alert(conn, tenant_id, fingerprint) -> None`
- `fetch_tenant_rules(pg_conn, tenant_id) -> list[dict]` — queries alert_rules table
- `fetch_metric_mappings(pg_conn, tenant_id) -> dict[str, list[dict]]` — maps normalized metric names
- `fetch_rollup_timescaledb(pg_conn) -> list[dict]` — complex join: device_registry + latest telemetry + heartbeats

**Global state:**
```python
COUNTERS = {"rules_evaluated": 0, "alerts_created": 0, "evaluation_errors": 0, "last_evaluation_at": None}
```

- Use `pytestmark = [pytest.mark.unit, pytest.mark.asyncio]`
- `evaluate_threshold` and `normalize_value` are pure — test these first as quick wins
- For DB functions, use FakeConn pattern from `tests/unit/test_dispatcher_logic.py` (it has a `FakeConn` class with `fetch`, `fetchval`, `fetchrow` methods)
- Mock `asyncpg` pool and connections
- The evaluator imports from `services/shared/` — PYTHONPATH must include both service directories
- Health endpoint uses `aiohttp` — can skip testing `start_health_server` and `handle_health`

## Verify
```bash
pytest tests/unit/test_evaluator.py -v
```
