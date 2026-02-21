# Create Operator User Management Routes

Add backend API routes for operator-level user management (cross-tenant).

## File to Create

`services/ui_iot/routes/users.py`

## Implementation

```python
"""
User management routes for operators and tenant admins.

Operators can manage all users across tenants.
Tenant admins can only manage users in their own tenant.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr

from middleware.auth import JWTBearer
from middleware.tenant import (
    inject_tenant_context,
    require_operator,
    require_operator_admin,
    get_tenant_id,
    get_user,
    is_operator,
)
from services.keycloak_admin import (
    KeycloakAdminError,
    list_users,
    get_user as kc_get_user,
    get_user_by_email,
    create_user,
    update_user,
    delete_user,
    enable_user,
    disable_user,
    set_user_password,
    get_user_roles,
    assign_realm_role,
    remove_realm_role,
    get_organizations,
    get_organization_members,
    add_user_to_organization,
    remove_user_from_organization,
    send_password_reset_email,
    format_user_response,
)
from shared.audit import log_audit_event

logger = logging.getLogger(__name__)

router = APIRouter(tags=["users"])


# ============== PYDANTIC MODELS ==============

class CreateUserRequest(BaseModel):
    username: str
    email: EmailStr
    first_name: str = ""
    last_name: str = ""
    temporary_password: Optional[str] = None
    tenant_id: Optional[str] = None
    role: str = "customer"  # customer, tenant-admin, operator, operator-admin


class UpdateUserRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    enabled: Optional[bool] = None


class AssignRoleRequest(BaseModel):
    role: str  # customer, tenant-admin, operator, operator-admin


class AssignTenantRequest(BaseModel):
    tenant_id: str


class SetPasswordRequest(BaseModel):
    password: str
    temporary: bool = True


# ============== OPERATOR ROUTES ==============

@router.get(
    "/operator/users",
    dependencies=[Depends(JWTBearer()), Depends(require_operator)]
)
async def list_all_users(
    search: Optional[str] = Query(None, description="Search by username, email, or name"),
    tenant_filter: Optional[str] = Query(None, description="Filter by tenant ID"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """
    List all users across all tenants.

    Operator access required.
    """
    try:
        users = await list_users(search=search, first=offset, max_results=limit)

        # Format and optionally filter by tenant
        formatted = []
        for user in users:
            formatted_user = format_user_response(user)

            # Apply tenant filter if specified
            if tenant_filter:
                user_tenant = formatted_user.get("tenant_id")
                if user_tenant != tenant_filter:
                    continue

            # Get user roles
            try:
                roles = await get_user_roles(user["id"])
                formatted_user["roles"] = [r["name"] for r in roles]
            except Exception:
                formatted_user["roles"] = []

            formatted.append(formatted_user)

        return {
            "users": formatted,
            "total": len(formatted),
            "limit": limit,
            "offset": offset
        }
    except KeycloakAdminError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get(
    "/operator/users/{user_id}",
    dependencies=[Depends(JWTBearer()), Depends(require_operator)]
)
async def get_user_detail(user_id: str):
    """
    Get detailed user information.

    Operator access required.
    """
    try:
        user = await kc_get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        formatted = format_user_response(user)

        # Get roles
        roles = await get_user_roles(user_id)
        formatted["roles"] = [r["name"] for r in roles]

        return formatted
    except KeycloakAdminError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post(
    "/operator/users",
    dependencies=[Depends(JWTBearer()), Depends(require_operator_admin)]
)
async def create_new_user(request: CreateUserRequest):
    """
    Create a new user.

    Operator admin access required.
    """
    current_user = get_user()

    try:
        # Build attributes
        attributes = {}
        if request.tenant_id:
            attributes["tenant_id"] = [request.tenant_id]

        user_id = await create_user(
            username=request.username,
            email=request.email,
            first_name=request.first_name,
            last_name=request.last_name,
            temporary_password=request.temporary_password,
            attributes=attributes
        )

        # Assign role
        if request.role:
            await assign_realm_role(user_id, request.role)

        # If tenant specified and organizations available, add to org
        if request.tenant_id:
            try:
                orgs = await get_organizations()
                org = next((o for o in orgs if o.get("name") == request.tenant_id), None)
                if org:
                    await add_user_to_organization(user_id, org["id"])
            except Exception as e:
                logger.warning(f"Could not add user to organization: {e}")

        # Audit log
        await log_audit_event(
            tenant_id=request.tenant_id or "__system__",
            event_type="USER_CREATED",
            category="security",
            severity="INFO",
            entity_type="user",
            entity_id=user_id,
            entity_name=request.username,
            action="create",
            message=f"User {request.username} created",
            actor_type="user",
            actor_id=current_user.get("sub"),
            actor_name=current_user.get("preferred_username"),
            details={"email": request.email, "role": request.role}
        )

        return {"id": user_id, "username": request.username, "message": "User created successfully"}
    except KeycloakAdminError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.put(
    "/operator/users/{user_id}",
    dependencies=[Depends(JWTBearer()), Depends(require_operator_admin)]
)
async def update_existing_user(user_id: str, request: UpdateUserRequest):
    """
    Update user details.

    Operator admin access required.
    """
    current_user = get_user()

    try:
        # Check user exists
        user = await kc_get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        updates = request.model_dump(exclude_none=True)
        if updates:
            await update_user(user_id, updates)

        # Audit log
        await log_audit_event(
            tenant_id="__system__",
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


@router.delete(
    "/operator/users/{user_id}",
    dependencies=[Depends(JWTBearer()), Depends(require_operator_admin)]
)
async def delete_existing_user(user_id: str):
    """
    Delete a user.

    Operator admin access required.
    """
    current_user = get_user()

    try:
        # Check user exists
        user = await kc_get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Prevent self-deletion
        if user_id == current_user.get("sub"):
            raise HTTPException(status_code=400, detail="Cannot delete your own account")

        username = user.get("username")
        await delete_user(user_id)

        # Audit log
        await log_audit_event(
            tenant_id="__system__",
            event_type="USER_DELETED",
            category="security",
            severity="WARNING",
            entity_type="user",
            entity_id=user_id,
            entity_name=username,
            action="delete",
            message=f"User {username} deleted",
            actor_type="user",
            actor_id=current_user.get("sub"),
            actor_name=current_user.get("preferred_username")
        )

        return {"message": "User deleted successfully"}
    except KeycloakAdminError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post(
    "/operator/users/{user_id}/enable",
    dependencies=[Depends(JWTBearer()), Depends(require_operator_admin)]
)
async def enable_user_account(user_id: str):
    """Enable a disabled user account."""
    current_user = get_user()

    try:
        user = await kc_get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        await enable_user(user_id)

        await log_audit_event(
            tenant_id="__system__",
            event_type="USER_ENABLED",
            category="security",
            severity="INFO",
            entity_type="user",
            entity_id=user_id,
            entity_name=user.get("username"),
            action="enable",
            message=f"User {user.get('username')} enabled",
            actor_type="user",
            actor_id=current_user.get("sub"),
            actor_name=current_user.get("preferred_username")
        )

        return {"message": "User enabled"}
    except KeycloakAdminError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post(
    "/operator/users/{user_id}/disable",
    dependencies=[Depends(JWTBearer()), Depends(require_operator_admin)]
)
async def disable_user_account(user_id: str):
    """Disable a user account."""
    current_user = get_user()

    try:
        user = await kc_get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Prevent self-disabling
        if user_id == current_user.get("sub"):
            raise HTTPException(status_code=400, detail="Cannot disable your own account")

        await disable_user(user_id)

        await log_audit_event(
            tenant_id="__system__",
            event_type="USER_DISABLED",
            category="security",
            severity="WARNING",
            entity_type="user",
            entity_id=user_id,
            entity_name=user.get("username"),
            action="disable",
            message=f"User {user.get('username')} disabled",
            actor_type="user",
            actor_id=current_user.get("sub"),
            actor_name=current_user.get("preferred_username")
        )

        return {"message": "User disabled"}
    except KeycloakAdminError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post(
    "/operator/users/{user_id}/roles",
    dependencies=[Depends(JWTBearer()), Depends(require_operator_admin)]
)
async def assign_user_role(user_id: str, request: AssignRoleRequest):
    """Assign a realm role to a user."""
    current_user = get_user()

    valid_roles = ["customer", "tenant-admin", "operator", "operator-admin"]
    if request.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")

    try:
        user = await kc_get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        await assign_realm_role(user_id, request.role)

        await log_audit_event(
            tenant_id="__system__",
            event_type="USER_ROLE_ASSIGNED",
            category="security",
            severity="INFO",
            entity_type="user",
            entity_id=user_id,
            entity_name=user.get("username"),
            action="assign_role",
            message=f"Role {request.role} assigned to {user.get('username')}",
            actor_type="user",
            actor_id=current_user.get("sub"),
            actor_name=current_user.get("preferred_username"),
            details={"role": request.role}
        )

        return {"message": f"Role {request.role} assigned"}
    except KeycloakAdminError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.delete(
    "/operator/users/{user_id}/roles/{role_name}",
    dependencies=[Depends(JWTBearer()), Depends(require_operator_admin)]
)
async def remove_user_role(user_id: str, role_name: str):
    """Remove a realm role from a user."""
    current_user = get_user()

    try:
        user = await kc_get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        await remove_realm_role(user_id, role_name)

        await log_audit_event(
            tenant_id="__system__",
            event_type="USER_ROLE_REMOVED",
            category="security",
            severity="INFO",
            entity_type="user",
            entity_id=user_id,
            entity_name=user.get("username"),
            action="remove_role",
            message=f"Role {role_name} removed from {user.get('username')}",
            actor_type="user",
            actor_id=current_user.get("sub"),
            actor_name=current_user.get("preferred_username"),
            details={"role": role_name}
        )

        return {"message": f"Role {role_name} removed"}
    except KeycloakAdminError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post(
    "/operator/users/{user_id}/tenant",
    dependencies=[Depends(JWTBearer()), Depends(require_operator_admin)]
)
async def assign_user_to_tenant(user_id: str, request: AssignTenantRequest):
    """Assign a user to a tenant."""
    current_user = get_user()

    try:
        user = await kc_get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Update user attributes
        attributes = user.get("attributes", {})
        attributes["tenant_id"] = [request.tenant_id]
        await update_user(user_id, {"attributes": attributes})

        # Try to add to organization
        try:
            orgs = await get_organizations()
            org = next((o for o in orgs if o.get("name") == request.tenant_id), None)
            if org:
                await add_user_to_organization(user_id, org["id"])
        except Exception as e:
            logger.warning(f"Could not add user to organization: {e}")

        await log_audit_event(
            tenant_id=request.tenant_id,
            event_type="USER_TENANT_ASSIGNED",
            category="security",
            severity="INFO",
            entity_type="user",
            entity_id=user_id,
            entity_name=user.get("username"),
            action="assign_tenant",
            message=f"User {user.get('username')} assigned to tenant {request.tenant_id}",
            actor_type="user",
            actor_id=current_user.get("sub"),
            actor_name=current_user.get("preferred_username"),
            details={"tenant_id": request.tenant_id}
        )

        return {"message": f"User assigned to tenant {request.tenant_id}"}
    except KeycloakAdminError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post(
    "/operator/users/{user_id}/reset-password",
    dependencies=[Depends(JWTBearer()), Depends(require_operator_admin)]
)
async def send_password_reset(user_id: str):
    """Send password reset email to user."""
    current_user = get_user()

    try:
        user = await kc_get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        await send_password_reset_email(user_id)

        await log_audit_event(
            tenant_id="__system__",
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


@router.get(
    "/operator/organizations",
    dependencies=[Depends(JWTBearer()), Depends(require_operator)]
)
async def list_organizations():
    """List all organizations (tenants) in Keycloak."""
    try:
        orgs = await get_organizations()
        return {"organizations": orgs}
    except KeycloakAdminError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
```

## Register Routes

In `services/ui_iot/app.py`, add:

```python
from routes.users import router as users_router

# After other router includes
app.include_router(users_router)
```

## Notes

- All routes require operator role minimum
- Create/update/delete require operator-admin role
- All operations are audit logged
- User can't delete/disable their own account
- Tenant assignment updates both user attributes and Keycloak organizations
