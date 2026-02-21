# Prompt 005 — Unit Tests

## File: `tests/unit/test_sites_endpoints.py`

Read a passing test file in `tests/unit/` for FakeConn/FakePool pattern.

Write tests using `@pytest.mark.unit` and `@pytest.mark.asyncio`:

1. `test_list_sites_returns_all` — fetch returns rows → 200, sites list populated with rollup fields
2. `test_list_sites_empty` — no sites → 200, empty list, total=0
3. `test_get_site_summary_success` — site found, devices and alerts returned
4. `test_get_site_summary_not_found` — fetchrow returns None for site → 404
5. `test_get_site_summary_alerts_capped` — verify alert query uses LIMIT 20
6. `test_list_sites_only_tenant_sites` — verify WHERE tenant_id = $1 in query

All `@pytest.mark.unit` and `@pytest.mark.asyncio`.

## Acceptance Criteria

- [ ] 6 tests pass under `pytest -m unit -v`
- [ ] No existing tests broken
