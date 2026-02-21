# Prompt 007 — Unit Tests

## Backend Tests

### File: `tests/unit/test_alert_actions.py`

Use the existing FakeConn/FakePool pattern from `tests/unit/` (read a passing test file for the pattern).

Write tests for the three new endpoints using `httpx.AsyncClient` + `app` import from `services/ui_iot/app.py`:

1. `test_acknowledge_alert_success` — fetchrow returns a row → 200, status=ACKNOWLEDGED
2. `test_acknowledge_alert_not_found` — fetchrow returns None → 404
3. `test_close_alert_success` — fetchrow returns a row → 200, status=CLOSED
4. `test_close_already_closed` — fetchrow returns None → 404
5. `test_silence_alert_success` — fetchrow returns row with silenced_until → 200
6. `test_silence_alert_invalid_minutes` — minutes=0 → 422 (Pydantic validation)
7. `test_list_alerts_default_open` — no status param → WHERE status='OPEN'
8. `test_list_alerts_acknowledged` — `?status=ACKNOWLEDGED` → WHERE status='ACKNOWLEDGED'
9. `test_list_alerts_all` — `?status=ALL` → no status WHERE clause
10. `test_list_alerts_invalid_status` — `?status=BOGUS` → 400

All tests must use `@pytest.mark.unit` and `@pytest.mark.asyncio`.

### File: `tests/unit/test_evaluator_ack_silence.py`

Write tests for the evaluator changes:

1. `test_acknowledged_alert_not_reset_to_open` — simulate `open_or_update_alert()` with ACKNOWLEDGED existing row — verify status not updated to OPEN (xmax != 0, not inserted)
2. `test_silenced_alert_skipped` — `is_silenced()` returns True → `open_or_update_alert()` not called
3. `test_not_silenced_proceeds` — `is_silenced()` returns False → evaluation proceeds normally
4. `test_is_silenced_false_when_no_row` — no row in DB → returns False
5. `test_is_silenced_true_when_future` — row with silenced_until in future → returns True

All tests must use `@pytest.mark.unit` and `@pytest.mark.asyncio`.

## Acceptance Criteria

- [ ] All 15 new tests pass under `pytest -m unit -v`
- [ ] No existing tests broken
