# 002: Operator User Management API

## Task

Add operator endpoints for system-wide user management.

## File to Modify

`services/ui_iot/routes/operator.py`

## New Endpoints

### 1. List Users (System-Wide)

```python
from services.keycloak_admin import get_keycloak_client, KeycloakUser
from pydantic import BaseModel, EmailStr
from typing import Optional, List


class UserResponse(BaseModel):
    id: str
    username: str
    email: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    enabled: bool
    tenant_id: Optional[str]
    tenant_name: Optional[str]
    roles: List[str]
    created_at: Optional[str]


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    tenant_id: Optional[str] = None
    password: Optional[str] = None
    temporary_password: bool = True
    roles: List[str] = []


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    enabled: Optional[bool] = None
    tenant_id: Optional[str] = None


class PasswordReset(BaseModel):
    password: str
    temporary: bool = False


@router.get("/users")
async def list_users(
    request: Request,
    tenant_id: Optional[str] = Query(None, description="Filter by tenant"),
    search: Optional[str] = Query(None, description="Search username/email"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List all users (operators can see all tenants)."""
    client = await get_keycloak_client()
    pool = await get_pool()

    users = await client.list_users(
        tenant_id=tenant_id,
        search=search,
        first=offset,
        max_results=limit,
    )

    # Enrich with tenant names
    async with operator_connection(pool) as conn:
        tenant_map = {}
        if users:
            tenant_ids = list(set(u.tenant_id for u in users if u.tenant_id))
            if tenant_ids:
                rows = await conn.fetch(
                    "SELECT tenant_id, name FROM tenants WHERE tenant_id = ANY($1)",
                    tenant_ids
                )
                tenant_map = {r["tenant_id"]: r["name"] for r in rows}

    # Get roles for each user
    result = []
    for user in users:
        roles = await client.get_user_roles(user.id)
        result.append(UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            enabled=user.enabled,
            tenant_id=user.tenant_id,
            tenant_name=tenant_map.get(user.tenant_id),
            roles=roles,
            created_at=user.created_at.isoformat() if user.created_at else None,
        ))

    return {"users": result, "count": len(result)}
```

### 2. Get User by ID

```python
@router.get("/users/{user_id}")
async def get_user(user_id: str, request: Request):
    """Get user details by ID."""
    client = await get_keycloak_client()

    user = await client.get_user(user_id)
    if not user:
        raise HTTPException(404, "User not found")

    roles = await client.get_user_roles(user_id)

    # Get tenant name
    tenant_name = None
    if user.tenant_id:
        pool = await get_pool()
        async with operator_connection(pool) as conn:
            tenant_name = await conn.fetchval(
                "SELECT name FROM tenants WHERE tenant_id = $1",
                user.tenant_id
            )

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        enabled=user.enabled,
        tenant_id=user.tenant_id,
        tenant_name=tenant_name,
        roles=roles,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )
```

### 3. Create User

```python
@router.post("/users", status_code=201)
async def create_user(data: UserCreate, request: Request):
    """Create a new user."""
    client = await get_keycloak_client()
    user = get_user()
    ip, _ = get_request_metadata(request)

    # Validate tenant exists if specified
    if data.tenant_id:
        pool = await get_pool()
        async with operator_connection(pool) as conn:
            tenant = await conn.fetchval(
                "SELECT 1 FROM tenants WHERE tenant_id = $1",
                data.tenant_id
            )
            if not tenant:
                raise HTTPException(400, "Tenant not found")

    # Validate roles
    valid_roles = {"operator", "operator-admin", "tenant-admin", "customer"}
    for role in data.roles:
        if role not in valid_roles:
            raise HTTPException(400, f"Invalid role: {role}")

    # Create user in Keycloak
    try:
        user_id = await client.create_user(
            username=data.username,
            email=data.email,
            first_name=data.first_name,
            last_name=data.last_name,
            tenant_id=data.tenant_id,
            password=data.password,
            temporary_password=data.temporary_password,
            roles=data.roles,
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 409:
            raise HTTPException(409, "Username or email already exists")
        raise HTTPException(500, f"Failed to create user: {e}")

    # Audit log
    pool = await get_pool()
    async with operator_connection(pool) as conn:
        await conn.execute(
            """
            INSERT INTO operator_audit_log
                (actor_id, action, target_type, target_id, details, ip_address)
            VALUES ($1, 'USER_CREATED', 'user', $2, $3, $4)
            """,
            user.get('sub') if user else None,
            user_id,
            json.dumps({
                "username": data.username,
                "tenant_id": data.tenant_id,
                "roles": data.roles,
            }),
            ip,
        )

    return {"user_id": user_id, "username": data.username}
```

### 4. Update User

```python
@router.patch("/users/{user_id}")
async def update_user(user_id: str, data: UserUpdate, request: Request):
    """Update user details."""
    client = await get_keycloak_client()
    user = get_user()
    ip, _ = get_request_metadata(request)

    # Verify user exists
    existing = await client.get_user(user_id)
    if not existing:
        raise HTTPException(404, "User not found")

    # Validate tenant if changing
    if data.tenant_id:
        pool = await get_pool()
        async with operator_connection(pool) as conn:
            tenant = await conn.fetchval(
                "SELECT 1 FROM tenants WHERE tenant_id = $1",
                data.tenant_id
            )
            if not tenant:
                raise HTTPException(400, "Tenant not found")

    await client.update_user(
        user_id=user_id,
        email=data.email,
        first_name=data.first_name,
        last_name=data.last_name,
        enabled=data.enabled,
        tenant_id=data.tenant_id,
    )

    # Audit log
    pool = await get_pool()
    async with operator_connection(pool) as conn:
        await conn.execute(
            """
            INSERT INTO operator_audit_log
                (actor_id, action, target_type, target_id, details, ip_address)
            VALUES ($1, 'USER_UPDATED', 'user', $2, $3, $4)
            """,
            user.get('sub') if user else None,
            user_id,
            json.dumps(data.dict(exclude_none=True)),
            ip,
        )

    return {"user_id": user_id, "updated": True}
```

### 5. Delete User

```python
@router.delete("/users/{user_id}")
async def delete_user(user_id: str, request: Request):
    """Delete a user."""
    client = await get_keycloak_client()
    user = get_user()
    ip, _ = get_request_metadata(request)

    # Verify user exists
    existing = await client.get_user(user_id)
    if not existing:
        raise HTTPException(404, "User not found")

    # Prevent deleting yourself
    if user and user.get('sub') == user_id:
        raise HTTPException(400, "Cannot delete yourself")

    await client.delete_user(user_id)

    # Audit log
    pool = await get_pool()
    async with operator_connection(pool) as conn:
        await conn.execute(
            """
            INSERT INTO operator_audit_log
                (actor_id, action, target_type, target_id, details, ip_address)
            VALUES ($1, 'USER_DELETED', 'user', $2, $3, $4)
            """,
            user.get('sub') if user else None,
            user_id,
            json.dumps({"username": existing.username}),
            ip,
        )

    return {"user_id": user_id, "deleted": True}
```

### 6. Reset Password

```python
@router.post("/users/{user_id}/password")
async def reset_password(user_id: str, data: PasswordReset, request: Request):
    """Reset user password."""
    client = await get_keycloak_client()
    user = get_user()
    ip, _ = get_request_metadata(request)

    # Verify user exists
    existing = await client.get_user(user_id)
    if not existing:
        raise HTTPException(404, "User not found")

    await client.set_password(user_id, data.password, data.temporary)

    # Audit log
    pool = await get_pool()
    async with operator_connection(pool) as conn:
        await conn.execute(
            """
            INSERT INTO operator_audit_log
                (actor_id, action, target_type, target_id, details, ip_address)
            VALUES ($1, 'PASSWORD_RESET', 'user', $2, $3, $4)
            """,
            user.get('sub') if user else None,
            user_id,
            json.dumps({"username": existing.username, "temporary": data.temporary}),
            ip,
        )

    return {"user_id": user_id, "password_reset": True}
```

### 7. Manage Roles

```python
class RoleAssignment(BaseModel):
    role: str


@router.post("/users/{user_id}/roles")
async def assign_role(user_id: str, data: RoleAssignment, request: Request):
    """Assign a role to a user."""
    client = await get_keycloak_client()
    user = get_user()
    ip, _ = get_request_metadata(request)

    valid_roles = {"operator", "operator-admin", "tenant-admin", "customer"}
    if data.role not in valid_roles:
        raise HTTPException(400, f"Invalid role: {data.role}")

    # Only operator-admin can assign operator roles
    if data.role in {"operator", "operator-admin"}:
        actor_roles = await client.get_user_roles(user.get('sub'))
        if "operator-admin" not in actor_roles:
            raise HTTPException(403, "Only operator-admin can assign operator roles")

    try:
        await client.assign_role(user_id, data.role)
    except ValueError as e:
        raise HTTPException(400, str(e))

    # Audit log
    pool = await get_pool()
    async with operator_connection(pool) as conn:
        await conn.execute(
            """
            INSERT INTO operator_audit_log
                (actor_id, action, target_type, target_id, details, ip_address)
            VALUES ($1, 'ROLE_ASSIGNED', 'user', $2, $3, $4)
            """,
            user.get('sub') if user else None,
            user_id,
            json.dumps({"role": data.role}),
            ip,
        )

    return {"user_id": user_id, "role": data.role, "assigned": True}


@router.delete("/users/{user_id}/roles/{role}")
async def remove_role(user_id: str, role: str, request: Request):
    """Remove a role from a user."""
    client = await get_keycloak_client()
    user = get_user()
    ip, _ = get_request_metadata(request)

    await client.remove_role(user_id, role)

    # Audit log
    pool = await get_pool()
    async with operator_connection(pool) as conn:
        await conn.execute(
            """
            INSERT INTO operator_audit_log
                (actor_id, action, target_type, target_id, details, ip_address)
            VALUES ($1, 'ROLE_REMOVED', 'user', $2, $3, $4)
            """,
            user.get('sub') if user else None,
            user_id,
            json.dumps({"role": role}),
            ip,
        )

    return {"user_id": user_id, "role": role, "removed": True}
```

### 8. List Available Roles

```python
@router.get("/roles")
async def list_roles(request: Request):
    """List available roles."""
    client = await get_keycloak_client()
    roles = await client.get_realm_roles()

    # Filter to application roles only
    app_roles = [r for r in roles if r["name"] in {
        "operator", "operator-admin", "tenant-admin", "customer"
    }]

    return {"roles": app_roles}
```

## Verification

```bash
# List users
curl -X GET "https://localhost/operator/users" \
  -H "Authorization: Bearer $TOKEN"

# Create user
curl -X POST "https://localhost/operator/users" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "newuser@example.com",
    "tenant_id": "acme-corp",
    "roles": ["customer"]
  }'
```
