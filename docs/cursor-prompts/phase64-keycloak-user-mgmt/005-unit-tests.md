# Prompt 005 — Unit Tests

## File: `tests/unit/test_keycloak_user_mgmt.py`

Mock `get_keycloak_admin_client()` (or the admin client methods) using `unittest.mock.AsyncMock`.

Tests using `@pytest.mark.unit` and `@pytest.mark.asyncio`:

1. `test_list_users_returns_list` — admin.list_users returns list → 200, users key
2. `test_get_user_with_roles` — admin.get_user returns user, admin.get_user_roles returns roles → 200, roles in response
3. `test_get_user_not_found` — admin.get_user returns None → 404
4. `test_create_user_success` — admin.create_user called → 200
5. `test_create_user_weak_password` — password < 8 chars → 422 (Pydantic)
6. `test_update_user_success` — admin.update_user called → 200
7. `test_update_user_no_fields` — empty body → 400
8. `test_delete_user_success` — admin.delete_user called → 200
9. `test_reset_password_success` — admin.set_user_password called → 200
10. `test_assign_role_success` — admin.assign_realm_role called → 200
11. `test_remove_role_success` — admin.remove_realm_role called → 200

All `@pytest.mark.unit` and `@pytest.mark.asyncio`.

## Acceptance Criteria

- [ ] 11 tests pass under `pytest -m unit -v`
- [ ] No existing tests broken
