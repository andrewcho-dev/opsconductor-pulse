# Fix User Creation Data Preservation

## Problem

Newly created users have `email: null` and empty names in the operator user list. The data is either not being sent to Keycloak correctly, or not being fetched back properly after creation.

## Root Cause

The `create_user()` function in `keycloak_admin.py` returns only the user ID extracted from the Location header. The route handler then returns minimal data without fetching the complete user record.

## Fix

### 1. Update `services/ui_iot/services/keycloak_admin.py`

In the `create_user()` function, after successfully creating the user, fetch the complete user record and return it:

```python
async def create_user(
    username: str,
    email: str,
    first_name: str = "",
    last_name: str = "",
    enabled: bool = True,
    email_verified: bool = False,
    temporary_password: str = None,
    attributes: dict = None
) -> dict:
    """
    Create a new user in Keycloak.

    Returns the complete user record if successful.
    """
    user_data = {
        "username": username,
        "email": email,
        "firstName": first_name,
        "lastName": last_name,
        "enabled": enabled,
        "emailVerified": email_verified,
        "attributes": attributes or {}
    }

    if temporary_password:
        user_data["credentials"] = [{
            "type": "password",
            "value": temporary_password,
            "temporary": True
        }]

    token = await _get_admin_token()
    url = f"{KEYCLOAK_INTERNAL_URL}/admin/realms/{KEYCLOAK_REALM}/users"

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            url,
            headers={"Authorization": f"Bearer {token}"},
            json=user_data
        )

        if response.status_code == 409:
            raise KeycloakAdminError("User with this username or email already exists", 409)

        response.raise_for_status()

        # Extract user ID from Location header
        location = response.headers.get("Location", "")
        user_id = location.split("/")[-1] if location else None

        if not user_id:
            # Fetch user to get ID
            user = await get_user_by_username(username)
            if user:
                return user
            raise KeycloakAdminError("User created but could not retrieve details", 500)

        # Fetch complete user record
        created_user = await get_user(user_id)
        if created_user:
            return created_user

        # Fallback: return minimal data
        return {
            "id": user_id,
            "username": username,
            "email": email,
            "firstName": first_name,
            "lastName": last_name,
            "enabled": enabled,
            "attributes": attributes or {}
        }
```

### 2. Update `services/ui_iot/routes/users.py`

In the `create_new_user()` route handler, use the full user record in the response:

```python
@router.post(
    "/operator/users",
    dependencies=[Depends(JWTBearer()), Depends(require_operator_admin)]
)
async def create_new_user(request: CreateUserRequest):
    """Create a new user."""
    current_user = get_user()

    try:
        attributes = {}
        if request.tenant_id:
            attributes["tenant_id"] = [request.tenant_id]

        created_user = await create_user(
            username=request.username,
            email=request.email,
            first_name=request.first_name,
            last_name=request.last_name,
            temporary_password=request.temporary_password,
            attributes=attributes
        )

        user_id = created_user.get("id")

        # Assign role
        if request.role:
            await assign_realm_role(user_id, request.role)

        # If tenant specified, add to organization
        if request.tenant_id:
            try:
                orgs = await get_organizations()
                org = next((o for o in orgs if o.get("name") == request.tenant_id), None)
                if org:
                    await add_user_to_organization(user_id, org["id"])
            except Exception as e:
                logger.warning(f"Could not add user to organization: {e}")

        # Audit log
        await log_audit_event(...)

        # Return formatted user response
        return {
            "id": user_id,
            "username": created_user.get("username"),
            "email": created_user.get("email"),
            "first_name": created_user.get("firstName", ""),
            "last_name": created_user.get("lastName", ""),
            "message": "User created successfully"
        }
    except KeycloakAdminError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
```

### 3. Similarly update `invite_user_to_tenant()` in the customer routes

Ensure the invite response includes the full user data from the created user record.

## Verification

1. Create user via operator UI with email and names filled in
2. Check `/operator/users` list - user should show email and name
3. Check Keycloak admin console - user should have all fields populated
