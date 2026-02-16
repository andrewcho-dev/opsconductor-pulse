# 002 — Backend Permissions Middleware

## Task

Create `services/ui_iot/middleware/permissions.py` — the permission loading, caching, and guard system.

## Context

### Existing middleware pattern

File: `services/ui_iot/middleware/tenant.py`

Key functions to understand:
- `tenant_context: ContextVar[Optional[str]]` and `user_context: ContextVar[Optional[dict]]` — per-request context vars
- `inject_tenant_context(request: Request)` — FastAPI dependency that extracts user from `request.state.user` (set by auth middleware), extracts tenant_id, calls `set_tenant_context()`
- `get_tenant_id()` → str — reads from ContextVar
- `get_user()` → dict — reads from ContextVar (the decoded JWT claims)
- `is_operator()` → bool — checks for `operator` or `operator-admin` in realm_access.roles
- `get_user_roles()` → list[str] — realm roles from token

### DB pool access pattern

File: `services/ui_iot/db/pool.py`

```python
async with tenant_connection(pool, tenant_id) as conn:
    rows = await conn.fetch("SELECT ...")
```

The pool is available as `request.app.state.pool` (set in `app.py` startup, line 309).

### How routes use dependencies

From `services/ui_iot/routes/users.py`:
```python
@router.get(
    "/customer/users",
    dependencies=[Depends(JWTBearer()), Depends(inject_tenant_context)],
)
```

## Create File: `services/ui_iot/middleware/permissions.py`

### 1. ContextVar

```python
from contextvars import ContextVar

permissions_context: ContextVar[set[str]] = ContextVar("permissions_context", default=set())
```

### 2. `load_user_permissions(pool, tenant_id, user_id) -> set[str]`

SQL query that gets the union of all permission actions from all roles assigned to this user+tenant:

```sql
SELECT DISTINCT p.action
FROM user_role_assignments ura
JOIN role_permissions rp ON rp.role_id = ura.role_id
JOIN permissions p ON p.id = rp.permission_id
WHERE ura.tenant_id = $1 AND ura.user_id = $2
```

**Important:** This query must NOT use `tenant_connection` (which sets RLS role). Use a plain `pool.acquire()` connection because:
- `user_role_assignments` has RLS on `pulse_app`, which is fine
- But we need to also read system roles' permissions from `role_permissions`, and system roles have `tenant_id = NULL`
- Actually, `role_permissions` does NOT have RLS, and this JOIN through `roles` is fine since `role_permissions` only references role_id directly

Use `pool.acquire()` directly with `SET LOCAL ROLE pulse_app` and `set_config('app.tenant_id', tenant_id, true)`:

```python
async def load_user_permissions(pool, tenant_id: str, user_id: str) -> set[str]:
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("SET LOCAL ROLE pulse_app")
            await conn.execute("SELECT set_config('app.tenant_id', $1, true)", tenant_id)
            rows = await conn.fetch("""
                SELECT DISTINCT p.action
                FROM user_role_assignments ura
                JOIN role_permissions rp ON rp.role_id = ura.role_id
                JOIN permissions p ON p.id = rp.permission_id
                WHERE ura.tenant_id = $1 AND ura.user_id = $2
            """, tenant_id, user_id)
    return {row["action"] for row in rows}
```

### 3. Auto-bootstrap: `bootstrap_user_roles(pool, tenant_id, user_id, realm_roles)`

Called when `load_user_permissions` returns an empty set AND the user has Keycloak realm roles. This provides backward compatibility — existing users get auto-assigned.

Logic:
1. Check if user has ANY rows in `user_role_assignments` for this tenant (even if permissions resolve to empty, if they have assignments they were deliberately configured)
2. If zero assignment rows exist:
   - If `"tenant-admin"` in realm_roles → find the "Full Admin" system role → insert assignment
   - Else if `"customer"` in realm_roles → find the "Viewer" system role → insert assignment
3. Return the permissions from the newly assigned role

```python
async def bootstrap_user_roles(pool, tenant_id: str, user_id: str, realm_roles: list[str]) -> set[str]:
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("SET LOCAL ROLE pulse_app")
            await conn.execute("SELECT set_config('app.tenant_id', $1, true)", tenant_id)

            # Check if user already has any assignments
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM user_role_assignments WHERE tenant_id = $1 AND user_id = $2",
                tenant_id, user_id,
            )
            if count > 0:
                return set()  # User was deliberately configured, don't override

            # Determine which system role to assign
            if "tenant-admin" in realm_roles:
                role_name = "Full Admin"
            elif "customer" in realm_roles:
                role_name = "Viewer"
            else:
                return set()  # No applicable role

            # Find system role (tenant_id IS NULL, is_system = true)
            # Must bypass RLS for this since system roles have NULL tenant_id
            await conn.execute("SET LOCAL ROLE pulse_operator")
            role_row = await conn.fetchrow(
                "SELECT id FROM roles WHERE name = $1 AND is_system = true AND tenant_id IS NULL",
                role_name,
            )
            if not role_row:
                return set()

            role_id = role_row["id"]

            # Switch back to pulse_app for the insert (RLS scoped)
            await conn.execute("SET LOCAL ROLE pulse_app")
            await conn.execute("SELECT set_config('app.tenant_id', $1, true)", tenant_id)

            await conn.execute(
                """INSERT INTO user_role_assignments (tenant_id, user_id, role_id, assigned_by)
                   VALUES ($1, $2, $3, 'system-bootstrap')
                   ON CONFLICT (tenant_id, user_id, role_id) DO NOTHING""",
                tenant_id, user_id, role_id,
            )

    # Now load the actual permissions
    return await load_user_permissions(pool, tenant_id, user_id)
```

### 4. `inject_permissions(request: Request)`

FastAPI dependency. Must be called AFTER `inject_tenant_context` so that `get_tenant_id()` and `get_user()` are available.

```python
from middleware.tenant import get_tenant_id, get_user, is_operator, get_user_roles

async def inject_permissions(request: Request) -> None:
    # Operators bypass permission system entirely
    if is_operator():
        permissions_context.set({"*"})  # Wildcard = all permissions
        return

    tenant_id = get_tenant_id()
    user = get_user()
    user_id = user.get("sub")
    if not tenant_id or not user_id:
        permissions_context.set(set())
        return

    pool = request.app.state.pool
    perms = await load_user_permissions(pool, tenant_id, user_id)

    # Auto-bootstrap if no permissions found
    if not perms:
        realm_roles = get_user_roles()
        perms = await bootstrap_user_roles(pool, tenant_id, user_id, realm_roles)

    permissions_context.set(perms)
```

### 5. `get_permissions() -> set[str]`

Simple accessor for the ContextVar.

```python
def get_permissions() -> set[str]:
    return permissions_context.get()
```

### 6. `has_permission(action: str) -> bool`

```python
def has_permission(action: str) -> bool:
    perms = get_permissions()
    return "*" in perms or action in perms
```

### 7. `require_permission(action: str) -> Depends`

Factory that returns a FastAPI dependency function. When the dependency is evaluated, it checks the ContextVar.

```python
from fastapi import Depends, HTTPException

def require_permission(action: str):
    async def _check(request: Request, _: None = Depends(inject_tenant_context)) -> None:
        # Ensure permissions are loaded
        await inject_permissions(request)
        if not has_permission(action):
            raise HTTPException(
                status_code=403,
                detail=f"Permission required: {action}",
            )
    return Depends(_check)
```

**Usage in routes:**
```python
@router.get(
    "/customer/users",
    dependencies=[Depends(JWTBearer()), require_permission("users.read")],
)
```

This replaces the previous pattern:
```python
dependencies=[Depends(JWTBearer()), Depends(inject_tenant_context)]
# + inline check: if "tenant-admin" not in roles and not is_operator(): raise 403
```

### 8. Imports / Exports

Make sure the module exports:
- `permissions_context`
- `load_user_permissions`
- `bootstrap_user_roles`
- `inject_permissions`
- `get_permissions`
- `has_permission`
- `require_permission`

### 9. Update `services/ui_iot/middleware/__init__.py`

Add the new module to any existing exports if the `__init__.py` does barrel exports. If it's empty, leave it empty (the routes import directly from the module path).

## Verification

- Import `require_permission` from `middleware.permissions` in a Python shell — no import errors
- The `inject_permissions` dependency correctly chains through `inject_tenant_context` (the `Depends(inject_tenant_context)` in `_check`)
- Operator users get `{"*"}` in permissions_context (bypass)
- First-time customer with `tenant-admin` realm role gets auto-bootstrapped to Full Admin
- First-time customer with `customer` realm role gets auto-bootstrapped to Viewer
