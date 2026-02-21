# Prompt 001 — Backend: Operator User Management Endpoints

Read `services/ui_iot/routes/operator.py` fully.
Read `services/ui_iot/services/keycloak_admin.py` to understand the client API.

## Add User Management Endpoints

Add to `operator.py` (after existing endpoints):

```python
from services.keycloak_admin import get_keycloak_admin_client
# OR use however the existing operator.py imports it — check the file first
```

```python
# ── User list ──────────────────────────────────────────────────────────────
@router.get("/users", dependencies=[Depends(require_operator)])
async def list_users(search: Optional[str] = Query(None),
                     first: int = Query(0, ge=0),
                     max_results: int = Query(50, ge=1, le=200)):
    admin = get_keycloak_admin_client()
    users = await admin.list_users(search=search, first=first, max_results=max_results)
    return {"users": users, "total": len(users)}

# ── User detail ────────────────────────────────────────────────────────────
@router.get("/users/{user_id}", dependencies=[Depends(require_operator)])
async def get_user(user_id: str):
    admin = get_keycloak_admin_client()
    user = await admin.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    roles = await admin.get_user_roles(user_id)
    return {**user, "roles": roles}

# ── Create user ────────────────────────────────────────────────────────────
class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: str = Field(..., min_length=5)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    temporary_password: str = Field(..., min_length=8)
    enabled: bool = True

@router.post("/users", dependencies=[Depends(require_operator)])
async def create_user(body: CreateUserRequest):
    admin = get_keycloak_admin_client()
    result = await admin.create_user(
        username=body.username, email=body.email,
        first_name=body.first_name, last_name=body.last_name,
        enabled=body.enabled, email_verified=False,
        temporary_password=body.temporary_password
    )
    return result

# ── Update user ────────────────────────────────────────────────────────────
class UpdateUserRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    enabled: Optional[bool] = None
    email_verified: Optional[bool] = None

@router.patch("/users/{user_id}", dependencies=[Depends(require_operator)])
async def update_user(user_id: str, body: UpdateUserRequest):
    admin = get_keycloak_admin_client()
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    await admin.update_user(user_id, updates)
    return {"user_id": user_id, "updated": list(updates.keys())}

# ── Delete user ────────────────────────────────────────────────────────────
@router.delete("/users/{user_id}", dependencies=[Depends(require_operator)])
async def delete_user(user_id: str):
    admin = get_keycloak_admin_client()
    await admin.delete_user(user_id)
    return {"user_id": user_id, "deleted": True}

# ── Reset password ─────────────────────────────────────────────────────────
class ResetPasswordRequest(BaseModel):
    password: str = Field(..., min_length=8)
    temporary: bool = True

@router.post("/users/{user_id}/reset-password", dependencies=[Depends(require_operator)])
async def reset_password(user_id: str, body: ResetPasswordRequest):
    admin = get_keycloak_admin_client()
    await admin.set_user_password(user_id, body.password, temporary=body.temporary)
    return {"user_id": user_id, "password_reset": True}

# ── Send password reset email ──────────────────────────────────────────────
@router.post("/users/{user_id}/send-password-reset", dependencies=[Depends(require_operator)])
async def send_password_reset(user_id: str):
    admin = get_keycloak_admin_client()
    await admin.send_password_reset_email(user_id)
    return {"user_id": user_id, "email_sent": True}

# ── Role management ────────────────────────────────────────────────────────
@router.post("/users/{user_id}/roles/{role_name}", dependencies=[Depends(require_operator)])
async def assign_role(user_id: str, role_name: str):
    admin = get_keycloak_admin_client()
    await admin.assign_realm_role(user_id, role_name)
    return {"user_id": user_id, "role": role_name, "action": "assigned"}

@router.delete("/users/{user_id}/roles/{role_name}", dependencies=[Depends(require_operator)])
async def remove_role(user_id: str, role_name: str):
    admin = get_keycloak_admin_client()
    await admin.remove_realm_role(user_id, role_name)
    return {"user_id": user_id, "role": role_name, "action": "removed"}
```

Note: Look at how `keycloak_admin.py` is imported and instantiated in the existing operator.py — follow the same pattern.

## Acceptance Criteria

- [ ] All 9 endpoints added to operator.py
- [ ] All require `require_operator` dependency
- [ ] `pytest -m unit -v` passes
