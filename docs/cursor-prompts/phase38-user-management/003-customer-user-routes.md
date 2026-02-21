# Create Tenant-Level User Management Routes

Add backend API routes for tenant admins to manage users within their own tenant.

## File to Modify

`services/ui_iot/routes/users.py` (append to existing file from 002)

## Implementation

Add to the bottom of `services/ui_iot/routes/users.py`:

```python
# ============== CUSTOMER/TENANT ROUTES ==============

@router.get(
    "/customer/users",
    dependencies=[Depends(JWTBearer()), Depends(inject_tenant_context)]
)
async def list_tenant_users(
    search: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """
    List users in the current tenant.

    Requires authenticated user with tenant context.
    """
    current_user = get_user()
    tenant_id = get_tenant_id()

    # Only tenant-admin can list users, or operators viewing a tenant
    user_roles = current_user.get("realm_access", {}).get("roles", [])
    is_admin = "tenant-admin" in user_roles or is_operator()

    if not is_admin:
        raise HTTPException(status_code=403, detail="Tenant admin access required")

    try:
        # Get all users and filter by tenant
        users = await list_users(search=search, first=0, max_results=1000)

        tenant_users = []
        for user in users:
            formatted = format_user_response(user)
            user_tenant = formatted.get("tenant_id")

            if user_tenant == tenant_id:
                # Get roles
                try:
                    roles = await get_user_roles(user["id"])
                    formatted["roles"] = [r["name"] for r in roles]
                except Exception:
                    formatted["roles"] = []
                tenant_users.append(formatted)

        # Apply pagination
        total = len(tenant_users)
        paginated = tenant_users[offset:offset + limit]

        return {
            "users": paginated,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except KeycloakAdminError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get(
    "/customer/users/{user_id}",
    dependencies=[Depends(JWTBearer()), Depends(inject_tenant_context)]
)
async def get_tenant_user_detail(user_id: str):
    """
    Get user details (must be in same tenant).

    Requires tenant-admin role.
    """
    current_user = get_user()
    tenant_id = get_tenant_id()

    user_roles = current_user.get("realm_access", {}).get("roles", [])
    if "tenant-admin" not in user_roles and not is_operator():
        raise HTTPException(status_code=403, detail="Tenant admin access required")

    try:
        user = await kc_get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        formatted = format_user_response(user)

        # Verify user belongs to same tenant
        user_tenant = formatted.get("tenant_id")
        if user_tenant != tenant_id and not is_operator():
            raise HTTPException(status_code=403, detail="User not in your tenant")

        roles = await get_user_roles(user_id)
        formatted["roles"] = [r["name"] for r in roles]

        return formatted
    except KeycloakAdminError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


class InviteUserRequest(BaseModel):
    email: EmailStr
    first_name: str = ""
    last_name: str = ""
    role: str = "customer"  # customer or tenant-admin only


@router.post(
    "/customer/users/invite",
    dependencies=[Depends(JWTBearer()), Depends(inject_tenant_context)]
)
async def invite_user_to_tenant(request: InviteUserRequest):
    """
    Invite a new user to the tenant.

    Creates user with temporary password and sends password reset email.
    Requires tenant-admin role.
    """
    current_user = get_user()
    tenant_id = get_tenant_id()

    user_roles = current_user.get("realm_access", {}).get("roles", [])
    if "tenant-admin" not in user_roles and not is_operator():
        raise HTTPException(status_code=403, detail="Tenant admin access required")

    # Tenant admins can only assign customer or tenant-admin roles
    valid_roles = ["customer", "tenant-admin"]
    if request.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")

    try:
        # Check if user already exists
        existing = await get_user_by_email(request.email)
        if existing:
            raise HTTPException(status_code=409, detail="User with this email already exists")

        # Generate username from email
        username = request.email.split("@")[0]

        # Check for username collision
        existing_username = await get_user_by_username(username)
        if existing_username:
            # Append random suffix
            import secrets
            username = f"{username}_{secrets.token_hex(3)}"

        # Create user
        user_id = await create_user(
            username=username,
            email=request.email,
            first_name=request.first_name,
            last_name=request.last_name,
            email_verified=False,
            attributes={"tenant_id": [tenant_id]}
        )

        # Assign role
        await assign_realm_role(user_id, request.role)

        # Try to add to organization
        try:
            orgs = await get_organizations()
            org = next((o for o in orgs if o.get("name") == tenant_id), None)
            if org:
                await add_user_to_organization(user_id, org["id"])
        except Exception as e:
            logger.warning(f"Could not add user to organization: {e}")

        # Send password reset email
        try:
            await send_password_reset_email(user_id)
        except Exception as e:
            logger.warning(f"Could not send password reset email: {e}")

        # Audit log
        await log_audit_event(
            tenant_id=tenant_id,
            event_type="USER_INVITED",
            category="security",
            severity="INFO",
            entity_type="user",
            entity_id=user_id,
            entity_name=username,
            action="invite",
            message=f"User {request.email} invited to tenant {tenant_id}",
            actor_type="user",
            actor_id=current_user.get("sub"),
            actor_name=current_user.get("preferred_username"),
            details={"email": request.email, "role": request.role}
        )

        return {
            "id": user_id,
            "username": username,
            "email": request.email,
            "message": "User invited successfully. Password reset email sent."
        }
    except KeycloakAdminError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.put(
    "/customer/users/{user_id}",
    dependencies=[Depends(JWTBearer()), Depends(inject_tenant_context)]
)
async def update_tenant_user(user_id: str, request: UpdateUserRequest):
    """
    Update user details (must be in same tenant).

    Requires tenant-admin role.
    """
    current_user = get_user()
    tenant_id = get_tenant_id()

    user_roles = current_user.get("realm_access", {}).get("roles", [])
    if "tenant-admin" not in user_roles and not is_operator():
        raise HTTPException(status_code=403, detail="Tenant admin access required")

    try:
        user = await kc_get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Verify user belongs to same tenant
        user_attrs = user.get("attributes", {})
        user_tenant = user_attrs.get("tenant_id", [None])[0] if user_attrs.get("tenant_id") else None

        if user_tenant != tenant_id and not is_operator():
            raise HTTPException(status_code=403, detail="User not in your tenant")

        updates = request.model_dump(exclude_none=True)
        if updates:
            await update_user(user_id, updates)

        await log_audit_event(
            tenant_id=tenant_id,
            event_type="USER_UPDATED",
            category="security",
            severity="INFO",
            entity_type="user",
            entity_id=user_id,
            entity_name=user.get("username"),
            action="update",
            message=f"User {user.get('username')} updated",
            actor_type="user",
            actor_id=current_user.get("sub"),
            actor_name=current_user.get("preferred_username"),
            details=updates
        )

        return {"message": "User updated successfully"}
    except KeycloakAdminError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post(
    "/customer/users/{user_id}/role",
    dependencies=[Depends(JWTBearer()), Depends(inject_tenant_context)]
)
async def change_tenant_user_role(user_id: str, request: AssignRoleRequest):
    """
    Change user's role within the tenant.

    Tenant admins can only assign customer or tenant-admin roles.
    """
    current_user = get_user()
    tenant_id = get_tenant_id()

    user_roles = current_user.get("realm_access", {}).get("roles", [])
    if "tenant-admin" not in user_roles and not is_operator():
        raise HTTPException(status_code=403, detail="Tenant admin access required")

    # Tenant admins can only assign customer or tenant-admin
    valid_roles = ["customer", "tenant-admin"]
    if request.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")

    try:
        user = await kc_get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Verify user belongs to same tenant
        user_attrs = user.get("attributes", {})
        user_tenant = user_attrs.get("tenant_id", [None])[0] if user_attrs.get("tenant_id") else None

        if user_tenant != tenant_id and not is_operator():
            raise HTTPException(status_code=403, detail="User not in your tenant")

        # Can't change own role
        if user_id == current_user.get("sub"):
            raise HTTPException(status_code=400, detail="Cannot change your own role")

        # Remove existing customer/tenant-admin roles
        existing_roles = await get_user_roles(user_id)
        for role in existing_roles:
            if role["name"] in ["customer", "tenant-admin"]:
                await remove_realm_role(user_id, role["name"])

        # Assign new role
        await assign_realm_role(user_id, request.role)

        await log_audit_event(
            tenant_id=tenant_id,
            event_type="USER_ROLE_CHANGED",
            category="security",
            severity="INFO",
            entity_type="user",
            entity_id=user_id,
            entity_name=user.get("username"),
            action="change_role",
            message=f"User {user.get('username')} role changed to {request.role}",
            actor_type="user",
            actor_id=current_user.get("sub"),
            actor_name=current_user.get("preferred_username"),
            details={"new_role": request.role}
        )

        return {"message": f"User role changed to {request.role}"}
    except KeycloakAdminError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.delete(
    "/customer/users/{user_id}",
    dependencies=[Depends(JWTBearer()), Depends(inject_tenant_context)]
)
async def remove_user_from_tenant(user_id: str):
    """
    Remove a user from the tenant.

    This removes the tenant assignment but doesn't delete the Keycloak account.
    Requires tenant-admin role.
    """
    current_user = get_user()
    tenant_id = get_tenant_id()

    user_roles = current_user.get("realm_access", {}).get("roles", [])
    if "tenant-admin" not in user_roles and not is_operator():
        raise HTTPException(status_code=403, detail="Tenant admin access required")

    try:
        user = await kc_get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Verify user belongs to same tenant
        user_attrs = user.get("attributes", {})
        user_tenant = user_attrs.get("tenant_id", [None])[0] if user_attrs.get("tenant_id") else None

        if user_tenant != tenant_id and not is_operator():
            raise HTTPException(status_code=403, detail="User not in your tenant")

        # Can't remove self
        if user_id == current_user.get("sub"):
            raise HTTPException(status_code=400, detail="Cannot remove yourself from tenant")

        # Clear tenant assignment (set to empty)
        user_attrs["tenant_id"] = []
        await update_user(user_id, {"attributes": user_attrs})

        # Try to remove from organization
        try:
            orgs = await get_organizations()
            org = next((o for o in orgs if o.get("name") == tenant_id), None)
            if org:
                await remove_user_from_organization(user_id, org["id"])
        except Exception as e:
            logger.warning(f"Could not remove user from organization: {e}")

        await log_audit_event(
            tenant_id=tenant_id,
            event_type="USER_REMOVED_FROM_TENANT",
            category="security",
            severity="WARNING",
            entity_type="user",
            entity_id=user_id,
            entity_name=user.get("username"),
            action="remove_from_tenant",
            message=f"User {user.get('username')} removed from tenant {tenant_id}",
            actor_type="user",
            actor_id=current_user.get("sub"),
            actor_name=current_user.get("preferred_username")
        )

        return {"message": "User removed from tenant"}
    except KeycloakAdminError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post(
    "/customer/users/{user_id}/reset-password",
    dependencies=[Depends(JWTBearer()), Depends(inject_tenant_context)]
)
async def send_tenant_user_password_reset(user_id: str):
    """
    Send password reset email to a tenant user.

    Requires tenant-admin role.
    """
    current_user = get_user()
    tenant_id = get_tenant_id()

    user_roles = current_user.get("realm_access", {}).get("roles", [])
    if "tenant-admin" not in user_roles and not is_operator():
        raise HTTPException(status_code=403, detail="Tenant admin access required")

    try:
        user = await kc_get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Verify user belongs to same tenant
        user_attrs = user.get("attributes", {})
        user_tenant = user_attrs.get("tenant_id", [None])[0] if user_attrs.get("tenant_id") else None

        if user_tenant != tenant_id and not is_operator():
            raise HTTPException(status_code=403, detail="User not in your tenant")

        await send_password_reset_email(user_id)

        await log_audit_event(
            tenant_id=tenant_id,
            event_type="PASSWORD_RESET_SENT",
            category="security",
            severity="INFO",
            entity_type="user",
            entity_id=user_id,
            entity_name=user.get("username"),
            action="password_reset",
            message=f"Password reset email sent to {user.get('username')}",
            actor_type="user",
            actor_id=current_user.get("sub"),
            actor_name=current_user.get("preferred_username")
        )

        return {"message": "Password reset email sent"}
    except KeycloakAdminError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
```

## Notes

- Tenant routes verify user belongs to the same tenant before any operation
- Tenant admins can only assign `customer` or `tenant-admin` roles (not operator roles)
- Removing a user from tenant doesn't delete the Keycloak account, just clears the tenant assignment
- Invite creates a new user and sends a password reset email
- All operations are audit logged with the tenant context
