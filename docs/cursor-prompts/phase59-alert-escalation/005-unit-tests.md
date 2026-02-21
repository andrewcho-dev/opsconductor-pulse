# Prompt 005 — Unit Tests

## File: `tests/unit/test_alert_escalation.py`

Read `services/evaluator_iot/evaluator.py` and `services/dispatcher/dispatcher.py`.
Use FakeConn/FakePool pattern from existing unit tests.

Tests using `@pytest.mark.unit` and `@pytest.mark.asyncio`:

1. `test_check_escalations_escalates_overdue_alert` — fetch returns row (overdue OPEN alert) → UPDATE called, returns count=1
2. `test_check_escalations_skips_acknowledged` — alert is ACKNOWLEDGED → not escalated
3. `test_check_escalations_skips_already_escalated` — escalation_level=1 → not updated again
4. `test_check_escalations_skips_silenced` — silenced_until in future → skipped
5. `test_check_escalations_no_escalation_minutes` — rule has escalation_minutes=NULL → no escalation
6. `test_check_escalations_severity_floor` — alert severity=0, bump → stays at 0 (GREATEST(...,0))
7. `test_dispatch_escalated_alerts_creates_job` — escalated alert found → delivery_job created
8. `test_dispatch_escalated_no_duplicates` — delivery_job already exists post-escalation → no new job

All `@pytest.mark.unit` and `@pytest.mark.asyncio`.

## Acceptance Criteria

- [ ] 8 tests pass under `pytest -m unit -v`
- [ ] No existing tests broken
