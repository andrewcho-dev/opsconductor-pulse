# Prompt 004 — Unit Tests

## Note

This phase is frontend-only. Backend endpoints used (POST /customer/devices, POST /customer/alert-rule-templates/apply) are already tested. These tests verify the wizard's backend dependencies still work.

## File: `tests/unit/test_device_wizard.py`

Use FakeConn/FakePool pattern. Tests using `@pytest.mark.unit` and `@pytest.mark.asyncio`:

1. `test_provision_device_returns_credentials` — POST /customer/devices returns device_id, client_id, password, broker_url
2. `test_provision_device_missing_name` — no name → 422
3. `test_apply_template_after_provision` — POST /customer/alert-rule-templates/apply with template_ids → created list returned
4. `test_wizard_backend_flow` — sequential: provision → apply template → both succeed

All `@pytest.mark.unit` and `@pytest.mark.asyncio`.

## Acceptance Criteria

- [ ] 4 tests pass under `pytest -m unit -v`
- [ ] No existing tests broken
