# Prompt 005 — Unit Tests

## File: `tests/unit/test_anomaly_detection.py`

Read `services/evaluator_iot/evaluator.py` — import `compute_z_score` and `compute_rolling_stats`.

Tests using `@pytest.mark.unit`:

1. `test_compute_z_score_above_threshold` — value=10, mean=5, stddev=1 → z=5.0
2. `test_compute_z_score_below_threshold` — value=5.5, mean=5, stddev=1 → z=0.5
3. `test_compute_z_score_zero_stddev` — stddev=0 → returns None
4. `test_compute_z_score_negative_deviation` — value=2, mean=5, stddev=1 → z=3.0 (abs)

Tests using `@pytest.mark.unit` and `@pytest.mark.asyncio`:

5. `test_compute_rolling_stats_returns_stats` — FakeConn fetchrow returns row with mean/stddev/count/latest → dict returned
6. `test_compute_rolling_stats_insufficient_data` — count < 2 → returns None
7. `test_compute_rolling_stats_null_result` — fetchrow returns None → returns None
8. `test_create_anomaly_rule_api` — POST with rule_type=anomaly + anomaly_conditions → conditions stored
9. `test_create_anomaly_rule_missing_conditions` — rule_type=anomaly without anomaly_conditions → 422

All `@pytest.mark.unit`.

## Acceptance Criteria

- [ ] 9 tests pass under `pytest -m unit -v`
- [ ] No existing tests broken
