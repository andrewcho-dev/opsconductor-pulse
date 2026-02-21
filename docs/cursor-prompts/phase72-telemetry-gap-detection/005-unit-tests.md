# Prompt 005 — Unit Tests

## File: `tests/unit/test_telemetry_gap.py`

Tests using `@pytest.mark.unit` and `@pytest.mark.asyncio`:

1. `test_check_telemetry_gap_no_data` — fetchrow returns row with last_seen=None → True (gap)
2. `test_check_telemetry_gap_data_present` — fetchrow returns row with last_seen=recent → False (no gap)
3. `test_check_telemetry_gap_no_row` — fetchrow returns None → True (gap)
4. `test_create_gap_rule_success` — POST with rule_type=telemetry_gap + gap_conditions → 200
5. `test_create_gap_rule_missing_conditions` — rule_type=telemetry_gap without gap_conditions → 422
6. `test_gap_alert_uses_no_telemetry_type` — verify alert_type="NO_TELEMETRY" in open_or_update_alert call
7. `test_gap_respects_maintenance_window` — is_in_maintenance returns True → open_or_update_alert not called

All `@pytest.mark.unit` and `@pytest.mark.asyncio`.

## Acceptance Criteria

- [ ] 7 tests pass under `pytest -m unit -v`
- [ ] No existing tests broken
