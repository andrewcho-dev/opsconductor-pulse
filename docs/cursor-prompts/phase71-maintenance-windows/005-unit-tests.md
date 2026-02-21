# Prompt 005 — Unit Tests

## File: `tests/unit/test_maintenance_windows.py`

Tests using `@pytest.mark.unit` and `@pytest.mark.asyncio`:

### Backend CRUD (FakeConn/FakePool)
1. `test_list_windows_returns_list` — fetch returns rows → 200
2. `test_create_window_success` — fetchrow returns row → 200
3. `test_update_window_not_found` — fetchrow returns None → 404
4. `test_delete_window_success` — fetchrow returns row → 200

### Evaluator logic (pure Python, no DB needed)
5. `test_is_in_maintenance_active_window` — row returned with matching window → True
6. `test_is_in_maintenance_no_windows` — no rows → False
7. `test_is_in_maintenance_site_filter_miss` — window has site_ids=[X], device site_id=Y → False
8. `test_is_in_maintenance_recurring_outside_hours` — recurring window, current hour outside range → False
9. `test_is_in_maintenance_recurring_inside_hours` — current hour inside range, correct dow → True

All `@pytest.mark.unit` and `@pytest.mark.asyncio`.

## Acceptance Criteria

- [ ] 9 tests pass under `pytest -m unit -v`
- [ ] No existing tests broken
