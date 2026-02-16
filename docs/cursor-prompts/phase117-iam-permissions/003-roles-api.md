# 003 — Roles & Permissions CRUD API

## Task

Create `services/ui_iot/routes/roles.py` with CRUD endpoints for roles and permissions, plus a self-service `/customer/me/permissions` endpoint. Mount it in `app.py`.

## Context

### Router pattern

From `services/ui_iot/routes/users.py`:
```python
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from middleware.auth import JWTBearer
from middleware.tenant import inject_tenant_context, get_tenant_id, get_user, is_operator
router = APIRouter()
```

### Pool access in routes

```python
pool = request.app.state.pool
async with pool.acquire() as conn:
    ...
```

Or using `tenant_connection(pool, tenant_id)` from `services/ui_iot/db/pool.py` for RLS-scoped queries.

### Audit logging pattern

From `users.py`:
```python
from db.audit import _audit  # or from shared.audit import ...
_audit(
    request,
    tenant_id=tenant_id,
    event_type="user.role_changed",
    category="security",
    action="change_role",
    message=f"...",
    entity_type="user",
    entity_id=user_id,
    entity_name=username,
    details={...},
)
```

Check the actual import path — look at the top of `users.py` for the audit import.

### Permission guard

From the newly created `middleware/permissions.py` (prompt 002):
```python
from middleware.permissions import require_permission, inject_permissions, get_permissions, has_permission
```

## Create File: `services/ui_iot/routes/roles.py`

### Pydantic Models

```python
from pydantic import BaseModel
from typing import Optional

class CreateRoleRequest(BaseModel):
    name: str
    description: str = ""
    permission_ids: list[int]  # list of permission.id values

class UpdateRoleRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permission_ids: Optional[list[int]] = None

class AssignRolesRequest(BaseModel):
    role_ids: list[str]  # list of role UUID strings
```

### Endpoints

#### 1. `GET /customer/permissions` — List all atomic permissions

- Dependencies: `[Depends(JWTBearer()), Depends(inject_tenant_context)]`
- No specific permission required — any authenticated customer can see the list (needed for role builder UI)
- Query: `SELECT id, action, category, description FROM permissions ORDER BY category, action`
- Use `pool.acquire()` (no RLS needed, permissions table is global)
- Response: `{"permissions": [{"id": 1, "action": "devices.read", "category": "devices", "description": "..."}]}`

#### 2. `GET /customer/roles` — List available roles

- Dependencies: `[Depends(JWTBearer()), require_permission("users.roles")]`
- Returns system roles (visible to all) + tenant's custom roles
- Query approach: Use `tenant_connection(pool, tenant_id)` which sets RLS. The RLS policy on `roles` allows seeing system roles (via `roles_system_visible` policy) and tenant's own custom roles (via `roles_tenant_isolation` policy).
- For each role, also fetch its permissions via JOIN to `role_permissions` + `permissions`
- Response:
```json
{
  "roles": [
    {
      "id": "uuid",
      "name": "Viewer",
      "description": "...",
      "is_system": true,
      "permissions": [
        {"id": 1, "action": "devices.read", "category": "devices", "description": "..."}
      ],
      "created_at": "...",
      "updated_at": "..."
    }
  ]
}
```

**Implementation note:** Fetch roles first, then batch-fetch permissions with:
```sql
SELECT rp.role_id, p.id, p.action, p.category, p.description
FROM role_permissions rp
JOIN permissions p ON p.id = rp.permission_id
WHERE rp.role_id = ANY($1)
```
Then group by role_id in Python.

#### 3. `POST /customer/roles` — Create custom role

- Dependencies: `[Depends(JWTBearer()), require_permission("users.roles")]`
- Body: `CreateRoleRequest`
- Validation: `name` must not be empty, `permission_ids` must all exist in `permissions` table
- Insert into `roles` with `tenant_id = get_tenant_id()`, `is_system = false`
- Insert into `role_permissions` for each permission_id
- Audit log the creation
- Response: `{"id": "uuid", "message": "Role created"}`

#### 4. `PUT /customer/roles/{role_id}` — Update custom role

- Dependencies: `[Depends(JWTBearer()), require_permission("users.roles")]`
- Body: `UpdateRoleRequest`
- **Guard:** Fetch the role first. If `is_system = true`, return 403 "Cannot modify system roles"
- **Guard:** If role's `tenant_id` doesn't match `get_tenant_id()`, return 403
- Update `roles` row (name, description, updated_at)
- If `permission_ids` provided: delete existing `role_permissions` for this role, insert new ones
- Audit log the update
- Response: `{"message": "Role updated"}`

#### 5. `DELETE /customer/roles/{role_id}` — Delete custom role

- Dependencies: `[Depends(JWTBearer()), require_permission("users.roles")]`
- **Guard:** If `is_system = true`, return 403 "Cannot delete system roles"
- **Guard:** If role's `tenant_id` doesn't match `get_tenant_id()`, return 403
- Delete from `roles` (CASCADE will clean up `role_permissions` and `user_role_assignments`)
- Audit log the deletion
- Response: `{"message": "Role deleted"}`

#### 6. `GET /customer/users/{user_id}/assignments` — List user's role assignments

- Dependencies: `[Depends(JWTBearer()), require_permission("users.roles")]`
- Query: Fetch assignments with role details for this user+tenant
```sql
SELECT ura.id, ura.role_id, ura.assigned_at, ura.assigned_by,
       r.name as role_name, r.is_system
FROM user_role_assignments ura
JOIN roles r ON r.id = ura.role_id
WHERE ura.tenant_id = $1 AND ura.user_id = $2
ORDER BY ura.assigned_at
```
- Response: `{"assignments": [{"id": "uuid", "role_id": "uuid", "role_name": "Viewer", "is_system": true, "assigned_at": "...", "assigned_by": "..."}]}`

#### 7. `PUT /customer/users/{user_id}/assignments` — Replace user's role assignments

- Dependencies: `[Depends(JWTBearer()), require_permission("users.roles")]`
- Body: `AssignRolesRequest`
- **Guard:** Cannot change own roles (compare `user_id` param with `get_user()["sub"]`) — return 400
- **Guard:** `role_ids` must not be empty — at least one role required
- **Guard:** All role_ids must exist and be either system roles or belong to the current tenant
- Transaction:
  1. Delete all existing assignments for this user+tenant
  2. Insert new assignments for each role_id
- Audit log the change with old and new role names
- Response: `{"message": "Roles updated"}`

#### 8. `GET /customer/me/permissions` — Current user's effective permissions

- Dependencies: `[Depends(JWTBearer()), Depends(inject_tenant_context)]`
- No permission check needed — any authenticated user can see their own permissions
- Call `inject_permissions(request)` then `get_permissions()`
- Response:
```json
{
  "permissions": ["dashboard.read", "devices.read", "devices.write", ...],
  "roles": ["Viewer", "Device Manager"]
}
```
- For the roles list, query `user_role_assignments` joined with `roles` for role names

## Mount in `app.py`

In `services/ui_iot/app.py`, add the import and router mount:

**At line ~44 (imports section):**
```python
from routes.roles import router as roles_router
```

**At line ~184 (after `app.include_router(jobs_router)`):**
```python
app.include_router(roles_router)
```

## Verification

- `GET /customer/permissions` returns 28 permissions grouped by category
- `GET /customer/roles` returns 6 system roles with correct permission counts
- `POST /customer/roles` with custom name + permission_ids creates a tenant-scoped role
- `PUT /customer/roles/{system_role_id}` returns 403
- `DELETE /customer/roles/{system_role_id}` returns 403
- `PUT /customer/users/{user_id}/assignments` with role_ids replaces assignments
- `GET /customer/me/permissions` returns effective permission set
