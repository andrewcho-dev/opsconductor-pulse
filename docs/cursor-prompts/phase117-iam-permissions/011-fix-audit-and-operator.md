# 011 — Fix Custom Role CREATE 500 + Operator /me/permissions 401

## Bug 1: Custom Role CREATE returns 500

### Symptom
`POST /customer/roles` returns 500 with traceback:
```
File "/app/routes/roles.py", line 38, in _audit
    audit.log(
TypeError: AuditLogger.log() got an unexpected keyword argument 'actor_username'
```

### Root Cause
`_audit()` in `routes/roles.py` line 46 passes `actor_username=...` but `AuditLogger.log()` uses `actor_name`, not `actor_username`.

### Fix: `services/ui_iot/routes/roles.py` line 46

```python
# FROM:
        actor_username=actor.get("preferred_username") or actor.get("email"),

# TO:
        actor_name=actor.get("preferred_username") or actor.get("email"),
```

Single word change: `actor_username` → `actor_name`.

---

## Bug 2: Operator gets 401 on /customer/me/permissions

### Symptom
`GET /customer/me/permissions` as operator1 returns 401 "Tenant context not established".

### Root Cause
The endpoint has `Depends(inject_tenant_context)` which sets `tenant_context` to `None` for operators (since they have no tenant). Then line 428 calls `get_tenant_id()` which raises 401 when tenant_context is None.

### Fix: `services/ui_iot/routes/roles.py` lines 427-452

Add an operator early-return before `get_tenant_id()`:

```python
# FROM:
async def get_me_permissions(request: Request):
    tenant_id = get_tenant_id()
    user = get_user()
    user_id = user.get("sub")

    await inject_permissions(request)
    perms = sorted(get_permissions())

    role_names: list[str] = []
    if tenant_id and user_id and not is_operator():
        pool = request.app.state.pool
        async with tenant_connection(pool, tenant_id) as conn:
            rows = await conn.fetch(
                """
                SELECT r.name
                FROM user_role_assignments ura
                JOIN roles r ON r.id = ura.role_id
                WHERE ura.tenant_id = $1 AND ura.user_id = $2
                ORDER BY r.name
                """,
                tenant_id,
                str(user_id),
            )
        role_names = [r["name"] for r in rows]

    return {"permissions": perms, "roles": role_names}

# TO:
async def get_me_permissions(request: Request):
    # Operators bypass the permission system — return wildcard immediately.
    if is_operator():
        return {"permissions": ["*"], "roles": ["operator"]}

    tenant_id = get_tenant_id()
    user = get_user()
    user_id = user.get("sub")

    await inject_permissions(request)
    perms = sorted(get_permissions())

    role_names: list[str] = []
    if tenant_id and user_id:
        pool = request.app.state.pool
        async with tenant_connection(pool, tenant_id) as conn:
            rows = await conn.fetch(
                """
                SELECT r.name
                FROM user_role_assignments ura
                JOIN roles r ON r.id = ura.role_id
                WHERE ura.tenant_id = $1 AND ura.user_id = $2
                ORDER BY r.name
                """,
                tenant_id,
                str(user_id),
            )
        role_names = [r["name"] for r in rows]

    return {"permissions": perms, "roles": role_names}
```

Key changes:
1. Added `if is_operator(): return {"permissions": ["*"], "roles": ["operator"]}` before `get_tenant_id()`
2. Removed the now-redundant `and not is_operator()` from the `if tenant_id and user_id` check

## Verification

After both fixes:

```
POST /customer/roles (create custom role) → 200/201
PUT /customer/roles/{id} (update custom role) → 200
DELETE /customer/roles/{id} (delete custom role) → 200
GET /customer/me/permissions (as operator) → 200 {"permissions": ["*"], "roles": ["operator"]}
```
