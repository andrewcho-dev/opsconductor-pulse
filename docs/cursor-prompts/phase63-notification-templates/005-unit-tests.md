# Prompt 005 — Unit Tests

## File: `tests/unit/test_notification_templates.py`

Tests using `@pytest.mark.unit` (synchronous where possible, asyncio where needed):

1. `test_render_template_basic` — `render_template("Hello {{ name }}", {"name": "World"})` returns "Hello World"
2. `test_render_template_all_vars` — render with all 11 standard variables, no exception
3. `test_render_template_error_fallback` — invalid Jinja2 syntax → returns raw template string (no exception)
4. `test_render_template_missing_var` — missing variable → Jinja2 `Undefined` → renders as empty string (default Jinja2 behavior)
5. `test_severity_label_mapping` — severity 0→CRITICAL, 2→WARNING, 3→INFO
6. `test_get_template_variables_endpoint` — GET /customer/integrations/{id}/template-variables returns 11 vars
7. `test_get_template_variables_not_found` — integration not found → 404
8. `test_webhook_uses_body_template_when_set` — config_json has body_template → rendered payload sent
9. `test_webhook_skips_body_template_when_absent` — no body_template → raw payload_json sent

All `@pytest.mark.unit`. Tests 1-5 are sync (no asyncio needed). Tests 6-9 use asyncio + FakeConn/FakePool.

## Acceptance Criteria

- [ ] 9 tests pass under `pytest -m unit -v`
- [ ] No existing tests broken
