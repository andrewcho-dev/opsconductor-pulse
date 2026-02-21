# Phase 64: Keycloak User Management UI

## What Exists

- `services/ui_iot/services/keycloak_admin.py` — complete Keycloak Admin API client with:
  - `list_users(search, first, max_results)`
  - `get_user(user_id)` / `get_user_by_username()` / `get_user_by_email()`
  - `create_user(username, email, first_name, last_name, enabled, temporary_password, ...)`
  - `update_user(user_id, updates)`
  - `delete_user(user_id)`
  - `set_user_password(user_id, password, temporary)`
  - `get_realm_roles()` / `get_user_roles()` / `assign_realm_role()` / `remove_realm_role()`
  - `send_verify_email()` / `send_password_reset_email()`
- Env vars: `KEYCLOAK_INTERNAL_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_ADMIN_USERNAME`, `KEYCLOAK_ADMIN_PASSWORD`
- Operator routes in `services/ui_iot/routes/operator.py`
- Phase 60 added TenantListPage / TenantDetailPage in frontend

## What This Phase Adds

Backend operator endpoints wrapping `keycloak_admin.py`:
1. `GET /operator/users` — list users (with search)
2. `GET /operator/users/{user_id}` — user detail + roles
3. `POST /operator/users` — create user
4. `PATCH /operator/users/{user_id}` — update user (name, enabled)
5. `DELETE /operator/users/{user_id}` — delete user
6. `POST /operator/users/{user_id}/reset-password` — set password
7. `POST /operator/users/{user_id}/send-password-reset` — trigger email
8. `POST /operator/users/{user_id}/roles/{role_name}` — assign role
9. `DELETE /operator/users/{user_id}/roles/{role_name}` — remove role

Frontend operator pages:
- `UserListPage.tsx` at `/operator/users` — searchable table of users
- `UserDetailPage.tsx` at `/operator/users/:userId` — profile + roles + password actions
- "Users" link in operator nav

## Execution Order

| Prompt | Description |
|--------|-------------|
| 001 | Backend: operator user management endpoints |
| 002 | Frontend: UserListPage |
| 003 | Frontend: UserDetailPage + role management |
| 004 | Frontend: nav + routes |
| 005 | Unit tests |
| 006 | Verify |

## Key Files

- `services/ui_iot/routes/operator.py` — prompts 001
- `services/ui_iot/services/keycloak_admin.py` — read for client pattern
- `frontend/src/features/operator/` — prompts 002–004
