# Prompt 004 — Unit Tests

## File: `tests/unit/test_alert_rule_templates.py`

Read a passing test file in `tests/unit/` for FakeConn/FakePool pattern.

Write tests using `@pytest.mark.unit` and `@pytest.mark.asyncio`:

1. `test_list_templates_returns_all` — GET /customer/alert-rule-templates returns 12 items
2. `test_list_templates_filter_by_device_type` — `?device_type=temperature` returns 2 items
3. `test_list_templates_unknown_device_type` — `?device_type=unknown` returns 0 items
4. `test_apply_templates_creates_rules` — fetchval returns None (no existing), fetchrow returns row → created list populated
5. `test_apply_templates_skips_existing` — fetchval returns existing id → skipped list populated
6. `test_apply_templates_invalid_ids_ignored` — template_ids with unknown ids → silently skipped
7. `test_apply_templates_empty_valid_ids` — all template_ids invalid → 400
8. `test_apply_templates_partial_skip` — 2 templates, 1 exists, 1 new → 1 created, 1 skipped

All `@pytest.mark.unit` and `@pytest.mark.asyncio`.

## Acceptance Criteria

- [ ] 8 tests pass under `pytest -m unit -v`
- [ ] No existing tests broken
