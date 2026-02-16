# 004 — Replace Inline Role Checks with Permission Guards

## Task

Replace all 7 inline `"tenant-admin" not in roles and not is_operator()` checks in `services/ui_iot/routes/users.py` with `require_permission()` dependency guards.

## Context

### Current pattern (repeated 7 times in users.py)

Each customer-facing route in `users.py` follows this pattern:

```python
@router.get(
    "/customer/users",
    dependencies=[Depends(JWTBearer()), Depends(inject_tenant_context)],
)
async def list_tenant_users(...):
    current_user = get_user()
    tenant_id = get_tenant_id()
    roles = _user_roles(current_user)
    if "tenant-admin" not in roles and not is_operator():
        raise HTTPException(status_code=403, detail="Tenant admin access required")
    # ... rest of handler
```

### New pattern

```python
from middleware.permissions import require_permission

@router.get(
    "/customer/users",
    dependencies=[Depends(JWTBearer()), require_permission("users.read")],
)
async def list_tenant_users(...):
    # No inline role check needed — permission guard handles it
    tenant_id = get_tenant_id()
    # ... rest of handler
```

The `require_permission()` dependency internally calls `inject_tenant_context` (it's chained via `Depends`), so removing `Depends(inject_tenant_context)` from the route's `dependencies` is safe — `require_permission` handles it.

However, be careful: some handlers still call `get_tenant_id()` or `get_user()` in their body, which requires `inject_tenant_context` to have been run. Since `require_permission` internally chains `inject_tenant_context`, this is covered.

## Exact Changes in `services/ui_iot/routes/users.py`

### Add import at top of file

```python
from middleware.permissions import require_permission
```

### Route 1: `list_tenant_users` (line ~641-676)

**Change dependencies:**
```python
# FROM:
dependencies=[Depends(JWTBearer()), Depends(inject_tenant_context)]
# TO:
dependencies=[Depends(JWTBearer()), require_permission("users.read")]
```

**Remove lines ~655-659:**
```python
# DELETE these lines:
    current_user = get_user()
    ...
    roles = _user_roles(current_user)
    if "tenant-admin" not in roles and not is_operator():
        raise HTTPException(status_code=403, detail="Tenant admin access required")
```

Keep `tenant_id = get_tenant_id()` since it's still needed in the handler body.

### Route 2: `get_tenant_user_detail` (line ~679-701)

**Change dependencies:**
```python
dependencies=[Depends(JWTBearer()), require_permission("users.read")]
```

**Remove inline check** (lines ~685-689). Keep `tenant_id = get_tenant_id()` and the `_is_user_in_tenant` check.

### Route 3: `invite_user_to_tenant` (line ~711-782)

**Change dependencies:**
```python
dependencies=[Depends(JWTBearer()), require_permission("users.invite")]
```

**Remove inline check** (lines ~722-726).

### Route 4: `update_tenant_user` (line ~785-819)

**Change dependencies:**
```python
dependencies=[Depends(JWTBearer()), require_permission("users.edit")]
```

**Remove inline check** (lines ~791-795).

### Route 5: `change_tenant_user_role` (line ~822-863)

**Change dependencies:**
```python
dependencies=[Depends(JWTBearer()), require_permission("users.roles")]
```

**Remove inline check** (lines ~828-832).

### Route 6: `remove_user_from_tenant` (line ~866-914)

**Change dependencies:**
```python
dependencies=[Depends(JWTBearer()), require_permission("users.remove")]
```

**Remove inline check** (lines ~876-880).

### Route 7: `send_tenant_user_password_reset` (line ~917-948)

**Change dependencies:**
```python
dependencies=[Depends(JWTBearer()), require_permission("users.edit")]
```

**Remove inline check** (lines ~923-927).

## Important: What NOT to change

- **Operator routes** (everything under `/operator/...`) — leave these unchanged. They already use `require_operator` or `require_operator_admin` dependencies which are Keycloak role checks for the operator portal. The IAM permission system only applies to customer/tenant scope.
- **The `_user_roles()` helper function** — keep it, it may still be used elsewhere or in the `change_tenant_user_role` handler body for Keycloak role manipulation.
- **The `_is_user_in_tenant()` check** — keep these. They verify the target user belongs to the same tenant, which is a different concern from permissions.
- **Self-modification guards** (`user_id == current_user.get("sub")`) — keep these in `change_tenant_user_role` and `remove_user_from_tenant`.

## Summary of permission mappings

| Route | Old check | New permission |
|-------|-----------|---------------|
| `GET /customer/users` | tenant-admin | `users.read` |
| `GET /customer/users/{id}` | tenant-admin | `users.read` |
| `POST /customer/users/invite` | tenant-admin | `users.invite` |
| `PUT /customer/users/{id}` | tenant-admin | `users.edit` |
| `POST /customer/users/{id}/role` | tenant-admin | `users.roles` |
| `DELETE /customer/users/{id}` | tenant-admin | `users.remove` |
| `POST /customer/users/{id}/reset-password` | tenant-admin | `users.edit` |

## Verification

- Existing tenant-admin users (auto-bootstrapped to Full Admin) should still have access to all these endpoints
- A user with only Viewer role should get 403 on all of these
- A user with Team Admin role should have access to all user management endpoints
- Operators should have access to everything (wildcard bypass)
