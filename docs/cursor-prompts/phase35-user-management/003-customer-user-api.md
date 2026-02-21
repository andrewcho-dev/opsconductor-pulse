# 003: Customer User Management API

## Task

Add customer endpoints for tenant-level user management. Only tenant-admin users can manage users within their tenant.

## File to Modify

`services/ui_iot/routes/customer.py`

## New Endpoints

### Middleware: Require Tenant Admin

```python
from services.keycloak_admin import get_keycloak_client


async def require_tenant_admin():
    """Verify current user has tenant-admin role."""
    user = get_user()
    tenant_id = get_tenant_id()

    if not user:
        raise HTTPException(401, "Not authenticated")

    client = await get_keycloak_client()
    roles = await client.get_user_roles(user.get('sub'))

    # Operators can also manage tenant users
    if "operator" in roles or "operator-admin" in roles:
        return True

    if "tenant-admin" not in roles:
        raise HTTPException(403, "Tenant admin role required")

    return True
```

### 1. List Tenant Users

```python
from pydantic import BaseModel, EmailStr
from typing import Optional, List


class TenantUserResponse(BaseModel):
    id: str
    username: str
    email: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    enabled: bool
    roles: List[str]
    created_at: Optional[str]


class TenantUserCreate(BaseModel):
    username: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    password: Optional[str] = None
    temporary_password: bool = True
    is_admin: bool = False  # Whether to grant tenant-admin role


class TenantUserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    enabled: Optional[bool] = None


@router.get("/users")
async def list_tenant_users(
    request: Request,
    search: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _: bool = Depends(require_tenant_admin),
):
    """List users in the current tenant."""
    tenant_id = get_tenant_id()
    client = await get_keycloak_client()

    users = await client.list_users(
        tenant_id=tenant_id,
        search=search,
        first=offset,
        max_results=limit,
    )

    result = []
    for user in users:
        roles = await client.get_user_roles(user.id)
        # Only show tenant-relevant roles
        tenant_roles = [r for r in roles if r in {"tenant-admin", "customer"}]

        result.append(TenantUserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            enabled=user.enabled,
            roles=tenant_roles,
            created_at=user.created_at.isoformat() if user.created_at else None,
        ))

    return {"users": result, "count": len(result)}
```

### 2. Get Tenant User

```python
@router.get("/users/{user_id}")
async def get_tenant_user(
    user_id: str,
    request: Request,
    _: bool = Depends(require_tenant_admin),
):
    """Get a user in the current tenant."""
    tenant_id = get_tenant_id()
    client = await get_keycloak_client()

    user = await client.get_user(user_id)
    if not user:
        raise HTTPException(404, "User not found")

    # Verify user belongs to this tenant
    if user.tenant_id != tenant_id:
        raise HTTPException(404, "User not found")

    roles = await client.get_user_roles(user_id)
    tenant_roles = [r for r in roles if r in {"tenant-admin", "customer"}]

    return TenantUserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        enabled=user.enabled,
        roles=tenant_roles,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )
```

### 3. Create Tenant User

```python
@router.post("/users", status_code=201)
async def create_tenant_user(
    data: TenantUserCreate,
    request: Request,
    _: bool = Depends(require_tenant_admin),
):
    """Create a user in the current tenant."""
    tenant_id = get_tenant_id()
    current_user = get_user()
    ip, _ = get_request_metadata(request)
    client = await get_keycloak_client()

    # Determine roles
    roles = ["customer"]
    if data.is_admin:
        roles.append("tenant-admin")

    try:
        user_id = await client.create_user(
            username=data.username,
            email=data.email,
            first_name=data.first_name,
            last_name=data.last_name,
            tenant_id=tenant_id,
            password=data.password,
            temporary_password=data.temporary_password,
            roles=roles,
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 409:
            raise HTTPException(409, "Username or email already exists")
        raise HTTPException(500, f"Failed to create user: {e}")

    # Audit log
    pool = await get_pool()
    async with tenant_connection(pool, tenant_id) as conn:
        await conn.execute(
            """
            INSERT INTO subscription_audit
                (tenant_id, event_type, actor_type, actor_id, details, ip_address)
            VALUES ($1, 'USER_CREATED', 'user', $2, $3, $4)
            """,
            tenant_id,
            current_user.get('sub') if current_user else None,
            json.dumps({
                "user_id": user_id,
                "username": data.username,
                "is_admin": data.is_admin,
            }),
            ip,
        )

    return {"user_id": user_id, "username": data.username}
```

### 4. Update Tenant User

```python
@router.patch("/users/{user_id}")
async def update_tenant_user(
    user_id: str,
    data: TenantUserUpdate,
    request: Request,
    _: bool = Depends(require_tenant_admin),
):
    """Update a user in the current tenant."""
    tenant_id = get_tenant_id()
    current_user = get_user()
    ip, _ = get_request_metadata(request)
    client = await get_keycloak_client()

    # Verify user belongs to this tenant
    user = await client.get_user(user_id)
    if not user or user.tenant_id != tenant_id:
        raise HTTPException(404, "User not found")

    await client.update_user(
        user_id=user_id,
        email=data.email,
        first_name=data.first_name,
        last_name=data.last_name,
        enabled=data.enabled,
    )

    # Audit log
    pool = await get_pool()
    async with tenant_connection(pool, tenant_id) as conn:
        await conn.execute(
            """
            INSERT INTO subscription_audit
                (tenant_id, event_type, actor_type, actor_id, details, ip_address)
            VALUES ($1, 'USER_UPDATED', 'user', $2, $3, $4)
            """,
            tenant_id,
            current_user.get('sub') if current_user else None,
            json.dumps({
                "user_id": user_id,
                "changes": data.dict(exclude_none=True),
            }),
            ip,
        )

    return {"user_id": user_id, "updated": True}
```

### 5. Delete Tenant User

```python
@router.delete("/users/{user_id}")
async def delete_tenant_user(
    user_id: str,
    request: Request,
    _: bool = Depends(require_tenant_admin),
):
    """Delete a user from the current tenant."""
    tenant_id = get_tenant_id()
    current_user = get_user()
    ip, _ = get_request_metadata(request)
    client = await get_keycloak_client()

    # Verify user belongs to this tenant
    user = await client.get_user(user_id)
    if not user or user.tenant_id != tenant_id:
        raise HTTPException(404, "User not found")

    # Prevent deleting yourself
    if current_user and current_user.get('sub') == user_id:
        raise HTTPException(400, "Cannot delete yourself")

    await client.delete_user(user_id)

    # Audit log
    pool = await get_pool()
    async with tenant_connection(pool, tenant_id) as conn:
        await conn.execute(
            """
            INSERT INTO subscription_audit
                (tenant_id, event_type, actor_type, actor_id, details, ip_address)
            VALUES ($1, 'USER_DELETED', 'user', $2, $3, $4)
            """,
            tenant_id,
            current_user.get('sub') if current_user else None,
            json.dumps({"user_id": user_id, "username": user.username}),
            ip,
        )

    return {"user_id": user_id, "deleted": True}
```

### 6. Toggle Admin Role

```python
class AdminToggle(BaseModel):
    is_admin: bool


@router.patch("/users/{user_id}/admin")
async def toggle_admin_role(
    user_id: str,
    data: AdminToggle,
    request: Request,
    _: bool = Depends(require_tenant_admin),
):
    """Toggle tenant-admin role for a user."""
    tenant_id = get_tenant_id()
    current_user = get_user()
    ip, _ = get_request_metadata(request)
    client = await get_keycloak_client()

    # Verify user belongs to this tenant
    user = await client.get_user(user_id)
    if not user or user.tenant_id != tenant_id:
        raise HTTPException(404, "User not found")

    # Prevent removing your own admin role
    if current_user and current_user.get('sub') == user_id and not data.is_admin:
        raise HTTPException(400, "Cannot remove your own admin role")

    if data.is_admin:
        await client.assign_role(user_id, "tenant-admin")
    else:
        await client.remove_role(user_id, "tenant-admin")

    # Audit log
    pool = await get_pool()
    async with tenant_connection(pool, tenant_id) as conn:
        await conn.execute(
            """
            INSERT INTO subscription_audit
                (tenant_id, event_type, actor_type, actor_id, details, ip_address)
            VALUES ($1, $2, 'user', $3, $4, $5)
            """,
            tenant_id,
            "ADMIN_GRANTED" if data.is_admin else "ADMIN_REVOKED",
            current_user.get('sub') if current_user else None,
            json.dumps({"user_id": user_id, "username": user.username}),
            ip,
        )

    return {"user_id": user_id, "is_admin": data.is_admin}
```

### 7. Reset User Password

```python
class PasswordReset(BaseModel):
    password: str
    temporary: bool = True


@router.post("/users/{user_id}/password")
async def reset_user_password(
    user_id: str,
    data: PasswordReset,
    request: Request,
    _: bool = Depends(require_tenant_admin),
):
    """Reset password for a tenant user."""
    tenant_id = get_tenant_id()
    current_user = get_user()
    ip, _ = get_request_metadata(request)
    client = await get_keycloak_client()

    # Verify user belongs to this tenant
    user = await client.get_user(user_id)
    if not user or user.tenant_id != tenant_id:
        raise HTTPException(404, "User not found")

    await client.set_password(user_id, data.password, data.temporary)

    # Audit log
    pool = await get_pool()
    async with tenant_connection(pool, tenant_id) as conn:
        await conn.execute(
            """
            INSERT INTO subscription_audit
                (tenant_id, event_type, actor_type, actor_id, details, ip_address)
            VALUES ($1, 'PASSWORD_RESET', 'user', $2, $3, $4)
            """,
            tenant_id,
            current_user.get('sub') if current_user else None,
            json.dumps({"user_id": user_id, "username": user.username}),
            ip,
        )

    return {"user_id": user_id, "password_reset": True}
```

## Verification

```bash
# List tenant users (as tenant-admin)
curl -X GET "https://localhost/customer/users" \
  -H "Authorization: Bearer $TENANT_ADMIN_TOKEN"

# Create tenant user
curl -X POST "https://localhost/customer/users" \
  -H "Authorization: Bearer $TENANT_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newemployee",
    "email": "employee@acme.com",
    "first_name": "New",
    "last_name": "Employee"
  }'
```
