# Prompt 006 — Unit Tests

## Backend Tests: `tests/unit/test_device_management.py`

Read a passing test file in `tests/unit/` to understand the FakeConn/FakePool pattern before writing.

Write tests using `@pytest.mark.unit` and `@pytest.mark.asyncio`:

1. `test_update_device_name_success` — fetchrow returns a row → 200, updated fields returned
2. `test_update_device_not_found` — fetchrow returns None → 404
3. `test_update_device_no_fields` — empty body (all None) → 400
4. `test_decommission_device_success` — fetchrow returns row → 200, decommissioned_at in response
5. `test_decommission_already_done` — fetchrow returns None → 404
6. `test_list_devices_excludes_decommissioned` — default query SQL includes `decommissioned_at IS NULL`
7. `test_list_devices_include_decommissioned` — `?include_decommissioned=true` omits that filter

All tests must use `@pytest.mark.unit` and `@pytest.mark.asyncio`.

## Acceptance Criteria

- [ ] 7 tests pass under `pytest -m unit -v`
- [ ] No existing tests broken
