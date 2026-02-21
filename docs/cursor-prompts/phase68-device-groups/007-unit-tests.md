# Prompt 007 — Unit Tests

## File: `tests/unit/test_device_groups.py`

Read a passing test in `tests/unit/` for FakeConn/FakePool pattern.

Tests using `@pytest.mark.unit` and `@pytest.mark.asyncio`:

1. `test_list_groups_returns_groups` — fetch returns rows → 200, groups list with member_count
2. `test_list_groups_empty` — no groups → 200, empty list
3. `test_create_group_success` — fetchrow returns row → 200, group_id in response
4. `test_create_group_conflict` — fetchrow returns None (conflict) → 409
5. `test_update_group_success` — fetchrow returns row → 200
6. `test_update_group_not_found` — fetchrow returns None → 404
7. `test_delete_group_success` — fetchrow returns row → 200
8. `test_delete_group_not_found` — fetchrow returns None → 404
9. `test_add_group_member_success` — group found, insert executed → 200
10. `test_remove_group_member_success` — fetchrow returns row → 200
11. `test_remove_group_member_not_found` — fetchrow returns None → 404

All `@pytest.mark.unit` and `@pytest.mark.asyncio`.

## Acceptance Criteria

- [ ] 11 tests pass under `pytest -m unit -v`
- [ ] No existing tests broken
