# Prompt 004 — Unit Tests

Read a passing test in `tests/unit/` to understand the FakeConn/FakePool pattern.

Create `tests/unit/test_device_api_tokens.py` with `@pytest.mark.unit` and `@pytest.mark.asyncio`:

1. `test_list_tokens_returns_active_only` — fetchrow list has 2 rows, 1 revoked → only 1 returned
2. `test_revoke_token_success` — fetchrow returns row → execute called, 204
3. `test_revoke_token_not_found` — fetchrow returns None → 404
4. `test_rotate_generates_new_credentials` — fetchrow returns None (no existing) → 201 with client_id and password
5. `test_rotate_revokes_existing_first` — fetchrow returns existing token → execute called to revoke → new credentials returned

All tests must pass under `pytest -m unit -v`.
