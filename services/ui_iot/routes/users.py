"""
User management routes for operators and tenant admins.

Operators can manage all users across tenants.
Tenant admins can only manage users in their own tenant.
"""

import logging
import secrets
from typing import Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from starlette.requests import Request

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
    get_user_by_username,
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

logger = logging.getLogger(__name__)

router = APIRouter(tags=["users"])


def _normalize_tenant_key(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip().lower().replace(" ", "-")


def _audit(
    request: Request,
    *,
    tenant_id: str | None,
    event_type: str,
    category: str,
    action: str,
    message: str,
    severity: str = "info",
    entity_type: str | None = None,
    entity_id: str | None = None,
    entity_name: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    audit = getattr(request.app.state, "audit", None)
    if not audit:
        return
    actor = get_user()
    audit.log(
        event_type,
        category,
        action,
        message,
        tenant_id=tenant_id,
        severity=severity,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        details=details,
        actor_type="user",
        actor_id=actor.get("sub"),
        actor_name=actor.get("preferred_username"),
    )


def _extract_primary_tenant(formatted_user: dict[str, Any]) -> str | None:
    tenant_id = formatted_user.get("tenant_id")
    if isinstance(tenant_id, str) and tenant_id:
        return tenant_id
    return None


async def _get_org_for_tenant(tenant_id: str) -> dict | None:
    orgs = await get_organizations()
    return next(
        (
            org
            for org in orgs
            if org.get("alias") == tenant_id or org.get("name") == tenant_id
        ),
        None,
    )


async def _tenant_member_ids(tenant_id: str) -> set[str]:
    org = await _get_org_for_tenant(tenant_id)
    if not org:
        return set()
    members = await get_organization_members(org["id"])
    return {str(member.get("id")) for member in members if member.get("id")}


async def _is_user_in_tenant(user: dict[str, Any], tenant_id: str) -> bool:
    formatted = format_user_response(user)
    if _extract_primary_tenant(formatted) == tenant_id:
        return True
    member_ids = await _tenant_member_ids(tenant_id)
    return str(user.get("id")) in member_ids


def _user_roles(user: dict[str, Any]) -> list[str]:
    realm_access = user.get("realm_access", {}) or {}
    roles = realm_access.get("roles", []) or []
    return roles if isinstance(roles, list) else []


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
    dependencies=[Depends(JWTBearer()), Depends(require_operator)],
)
async def list_all_users(
    search: Optional[str] = Query(None, description="Search by username, email, or name"),
    tenant_filter: Optional[str] = Query(None, description="Filter by tenant ID"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List all users across all tenants. Operator access required."""
    try:
        users = await list_users(search=search, first=offset, max_results=limit)
        logger.info("[tenant-badge] fetched %s users from Keycloak", len(users))
        org_memberships: dict[str, str] = {}
        try:
            orgs = await get_organizations()
            logger.info(
                "[tenant-badge] found %s orgs names=%s aliases=%s",
                len(orgs),
                [o.get("name") for o in orgs],
                [o.get("alias") for o in orgs],
            )
            for org in orgs:
                org_name = org.get("alias") or org.get("name")
                if not org_name:
                    continue
                try:
                    members = await get_organization_members(org["id"])
                    logger.info(
                        "[tenant-badge] org=%s id=%s members=%s",
                        org_name,
                        org.get("id"),
                        len(members),
                    )
                    for member in members:
                        member_id = (
                            member.get("id")
                            or member.get("userId")
                            or member.get("sub")
                            or ((member.get("user") or {}).get("id") if isinstance(member.get("user"), dict) else None)
                        )
                        logger.debug(
                            "[tenant-badge] org=%s member_keys=%s resolved_member_id=%s",
                            org_name,
                            list(member.keys()),
                            member_id,
                        )
                        if member_id:
                            org_memberships[str(member_id)] = org_name
                except Exception as exc:
                    logger.warning(
                        "[tenant-badge] failed members org=%s id=%s err=%s",
                        org_name,
                        org.get("id"),
                        exc,
                    )
                    continue
        except Exception as exc:
            logger.warning("Could not fetch organization memberships: %s", exc)

        logger.info(
            "[tenant-badge] built org membership map with %s entries",
            len(org_memberships),
        )

        formatted: list[dict[str, Any]] = []
        for user in users:
            formatted_user = format_user_response(user)
            user_id = str(user.get("id"))
            attr_tenant = _extract_primary_tenant(formatted_user)
            org_tenant = org_memberships.get(user_id)
            logger.debug(
                "[tenant-badge] user=%s id=%s attr_tenant=%s org_tenant=%s",
                user.get("username"),
                user_id,
                attr_tenant,
                org_tenant,
            )
            if not _extract_primary_tenant(formatted_user):
                fallback_tenant = org_tenant
                if fallback_tenant:
                    formatted_user["tenant_id"] = fallback_tenant
                    logger.info(
                        "[tenant-badge] applied fallback user=%s tenant=%s",
                        user.get("username"),
                        fallback_tenant,
                    )
            if tenant_filter:
                current_tenant = _extract_primary_tenant(formatted_user)
                if _normalize_tenant_key(current_tenant) != _normalize_tenant_key(tenant_filter):
                    continue
            try:
                roles = await get_user_roles(user["id"])
                formatted_user["roles"] = [r["name"] for r in roles]
            except Exception:
                formatted_user["roles"] = []
            formatted.append(formatted_user)

        return {"users": formatted, "total": len(formatted), "limit": limit, "offset": offset}
    except KeycloakAdminError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get(
    "/operator/users/{user_id}",
    dependencies=[Depends(JWTBearer()), Depends(require_operator)],
)
async def get_user_detail(user_id: str):
    """Get detailed user information. Operator access required."""
    try:
        user = await kc_get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        formatted = format_user_response(user)
        roles = await get_user_roles(user_id)
        formatted["roles"] = [r["name"] for r in roles]
        return formatted
    except KeycloakAdminError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post(
    "/operator/users",
    dependencies=[Depends(JWTBearer()), Depends(require_operator_admin)],
)
async def create_new_user(request: Request, payload: CreateUserRequest):
    """Create a new user. Operator admin access required."""
    try:
        attributes = {}
        if payload.tenant_id:
            attributes["tenant_id"] = [payload.tenant_id]

        created_user = await create_user(
            username=payload.username,
            email=payload.email,
            first_name=payload.first_name,
            last_name=payload.last_name,
            temporary_password=payload.temporary_password,
            attributes=attributes,
        )
        user_id = created_user.get("id")
        if not user_id:
            raise HTTPException(status_code=500, detail="Created user missing id")

        if payload.role:
            await assign_realm_role(user_id, payload.role)

        if payload.tenant_id:
            try:
                org = await _get_org_for_tenant(payload.tenant_id)
                if org:
                    await add_user_to_organization(user_id, org["id"])
            except Exception as exc:
                logger.warning("Could not add user to organization: %s", exc)

        _audit(
            request,
            tenant_id=payload.tenant_id or "__system__",
            event_type="user.created",
            category="security",
            action="create",
            message=f"User {payload.username} created",
            entity_type="user",
            entity_id=user_id,
            entity_name=payload.username,
            details={"email": payload.email, "role": payload.role},
        )
        return {
            "id": user_id,
            "username": created_user.get("username"),
            "email": created_user.get("email"),
            "first_name": created_user.get("firstName", ""),
            "last_name": created_user.get("lastName", ""),
            "message": "User created successfully",
        }
    except KeycloakAdminError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.put(
    "/operator/users/{user_id}",
    dependencies=[Depends(JWTBearer()), Depends(require_operator_admin)],
)
async def update_existing_user(user_id: str, payload: UpdateUserRequest, request: Request):
    """Update user details. Operator admin access required."""
    try:
        user = await kc_get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        updates = payload.model_dump(exclude_none=True)
        if updates:
            await update_user(user_id, updates)
        _audit(
            request,
            tenant_id="__system__",
            event_type="user.updated",
            category="security",
            action="update",
            message=f"User {user.get('username')} updated",
            entity_type="user",
            entity_id=user_id,
            entity_name=user.get("username"),
            details=updates,
        )
        return {"message": "User updated successfully"}
    except KeycloakAdminError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.delete(
    "/operator/users/{user_id}",
    dependencies=[Depends(JWTBearer()), Depends(require_operator_admin)],
)
async def delete_existing_user(user_id: str, request: Request):
    """Delete a user. Operator admin access required."""
    current_user = get_user()
    try:
        user = await kc_get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user_id == current_user.get("sub"):
            raise HTTPException(status_code=400, detail="Cannot delete your own account")
        username = user.get("username")
        await delete_user(user_id)
        _audit(
            request,
            tenant_id="__system__",
            event_type="user.deleted",
            category="security",
            action="delete",
            message=f"User {username} deleted",
            severity="warning",
            entity_type="user",
            entity_id=user_id,
            entity_name=username,
        )
        return {"message": "User deleted successfully"}
    except KeycloakAdminError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post(
    "/operator/users/{user_id}/enable",
    dependencies=[Depends(JWTBearer()), Depends(require_operator_admin)],
)
async def enable_user_account(user_id: str, request: Request):
    """Enable a disabled user account."""
    try:
        user = await kc_get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        await enable_user(user_id)
        _audit(
            request,
            tenant_id="__system__",
            event_type="user.enabled",
            category="security",
            action="enable",
            message=f"User {user.get('username')} enabled",
            entity_type="user",
            entity_id=user_id,
            entity_name=user.get("username"),
        )
        return {"message": "User enabled"}
    except KeycloakAdminError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post(
    "/operator/users/{user_id}/disable",
    dependencies=[Depends(JWTBearer()), Depends(require_operator_admin)],
)
async def disable_user_account(user_id: str, request: Request):
    """Disable a user account."""
    current_user = get_user()
    try:
        user = await kc_get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user_id == current_user.get("sub"):
            raise HTTPException(status_code=400, detail="Cannot disable your own account")
        await disable_user(user_id)
        _audit(
            request,
            tenant_id="__system__",
            event_type="user.disabled",
            category="security",
            action="disable",
            message=f"User {user.get('username')} disabled",
            severity="warning",
            entity_type="user",
            entity_id=user_id,
            entity_name=user.get("username"),
        )
        return {"message": "User disabled"}
    except KeycloakAdminError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post(
    "/operator/users/{user_id}/roles",
    dependencies=[Depends(JWTBearer()), Depends(require_operator_admin)],
)
async def assign_user_role(user_id: str, payload: AssignRoleRequest, request: Request):
    """Assign a realm role to a user."""
    valid_roles = ["customer", "tenant-admin", "operator", "operator-admin"]
    if payload.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")
    try:
        user = await kc_get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        await assign_realm_role(user_id, payload.role)
        _audit(
            request,
            tenant_id="__system__",
            event_type="user.role_assigned",
            category="security",
            action="assign_role",
            message=f"Role {payload.role} assigned to {user.get('username')}",
            entity_type="user",
            entity_id=user_id,
            entity_name=user.get("username"),
            details={"role": payload.role},
        )
        return {"message": f"Role {payload.role} assigned"}
    except KeycloakAdminError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.delete(
    "/operator/users/{user_id}/roles/{role_name}",
    dependencies=[Depends(JWTBearer()), Depends(require_operator_admin)],
)
async def remove_user_role(user_id: str, role_name: str, request: Request):
    """Remove a realm role from a user."""
    try:
        user = await kc_get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        await remove_realm_role(user_id, role_name)
        _audit(
            request,
            tenant_id="__system__",
            event_type="user.role_removed",
            category="security",
            action="remove_role",
            message=f"Role {role_name} removed from {user.get('username')}",
            entity_type="user",
            entity_id=user_id,
            entity_name=user.get("username"),
            details={"role": role_name},
        )
        return {"message": f"Role {role_name} removed"}
    except KeycloakAdminError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post(
    "/operator/users/{user_id}/tenant",
    dependencies=[Depends(JWTBearer()), Depends(require_operator_admin)],
)
async def assign_user_to_tenant(user_id: str, payload: AssignTenantRequest, request: Request):
    """Assign a user to a tenant."""
    try:
        user = await kc_get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        await update_user(user_id, {"attributes": {"tenant_id": [payload.tenant_id]}})
        logger.info(
            "[tenant-badge] assigned tenant attribute user=%s tenant=%s",
            user.get("username"),
            payload.tenant_id,
        )

        try:
            org = await _get_org_for_tenant(payload.tenant_id)
            if org:
                await add_user_to_organization(user_id, org["id"])
                logger.info(
                    "[tenant-badge] added org membership user=%s org_id=%s org_name=%s org_alias=%s",
                    user.get("username"),
                    org.get("id"),
                    org.get("name"),
                    org.get("alias"),
                )
            else:
                logger.warning(
                    "[tenant-badge] no organization matched tenant=%s for user=%s",
                    payload.tenant_id,
                    user.get("username"),
                )
        except Exception as exc:
            logger.warning("Could not add user to organization: %s", exc)

        _audit(
            request,
            tenant_id=payload.tenant_id,
            event_type="user.tenant_assigned",
            category="security",
            action="assign_tenant",
            message=f"User {user.get('username')} assigned to tenant {payload.tenant_id}",
            entity_type="user",
            entity_id=user_id,
            entity_name=user.get("username"),
            details={"tenant_id": payload.tenant_id},
        )
        return {"message": f"User assigned to tenant {payload.tenant_id}"}
    except KeycloakAdminError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post(
    "/operator/users/{user_id}/reset-password",
    dependencies=[Depends(JWTBearer()), Depends(require_operator_admin)],
)
async def send_password_reset(user_id: str, request: Request):
    """Send password reset email to user."""
    try:
        user = await kc_get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        await send_password_reset_email(user_id)
        _audit(
            request,
            tenant_id="__system__",
            event_type="user.password_reset_sent",
            category="security",
            action="password_reset",
            message=f"Password reset email sent to {user.get('username')}",
            entity_type="user",
            entity_id=user_id,
            entity_name=user.get("username"),
        )
        return {"message": "Password reset email sent"}
    except KeycloakAdminError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post(
    "/operator/users/{user_id}/password",
    dependencies=[Depends(JWTBearer()), Depends(require_operator_admin)],
)
async def set_user_password_endpoint(user_id: str, payload: SetPasswordRequest):
    """Set user password directly (optional admin operation)."""
    try:
        user = await kc_get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        await set_user_password(user_id, payload.password, payload.temporary)
        return {"message": "Password updated"}
    except KeycloakAdminError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get(
    "/operator/organizations",
    dependencies=[Depends(JWTBearer()), Depends(require_operator)],
)
async def list_organizations():
    """List all organizations (tenants) in Keycloak."""
    try:
        orgs = await get_organizations()
        return {"organizations": orgs}
    except KeycloakAdminError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


# ============== CUSTOMER/TENANT ROUTES ==============

@router.get(
    "/customer/users",
    dependencies=[Depends(JWTBearer()), Depends(inject_tenant_context)],
)
async def list_tenant_users(
    search: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    List users in the current tenant.

    Requires tenant-admin role (or operator).
    """
    current_user = get_user()
    tenant_id = get_tenant_id()
    roles = _user_roles(current_user)
    if "tenant-admin" not in roles and not is_operator():
        raise HTTPException(status_code=403, detail="Tenant admin access required")
    try:
        users = await list_users(search=search, first=0, max_results=1000)
        member_ids = await _tenant_member_ids(tenant_id)
        tenant_users: list[dict[str, Any]] = []
        for user in users:
            formatted = format_user_response(user)
            if _extract_primary_tenant(formatted) == tenant_id or str(user.get("id")) in member_ids:
                try:
                    user_roles = await get_user_roles(user["id"])
                    formatted["roles"] = [r["name"] for r in user_roles]
                except Exception:
                    formatted["roles"] = []
                tenant_users.append(formatted)
        total = len(tenant_users)
        return {"users": tenant_users[offset : offset + limit], "total": total, "limit": limit, "offset": offset}
    except KeycloakAdminError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get(
    "/customer/users/{user_id}",
    dependencies=[Depends(JWTBearer()), Depends(inject_tenant_context)],
)
async def get_tenant_user_detail(user_id: str):
    """Get user details (must be in same tenant). Requires tenant-admin role."""
    current_user = get_user()
    tenant_id = get_tenant_id()
    roles = _user_roles(current_user)
    if "tenant-admin" not in roles and not is_operator():
        raise HTTPException(status_code=403, detail="Tenant admin access required")
    try:
        user = await kc_get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if not await _is_user_in_tenant(user, tenant_id) and not is_operator():
            raise HTTPException(status_code=403, detail="User not in your tenant")
        formatted = format_user_response(user)
        user_roles = await get_user_roles(user_id)
        formatted["roles"] = [r["name"] for r in user_roles]
        return formatted
    except KeycloakAdminError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


class InviteUserRequest(BaseModel):
    email: EmailStr
    first_name: str = ""
    last_name: str = ""
    role: str = "customer"  # customer or tenant-admin only


@router.post(
    "/customer/users/invite",
    dependencies=[Depends(JWTBearer()), Depends(inject_tenant_context)],
)
async def invite_user_to_tenant(payload: InviteUserRequest, request: Request):
    """
    Invite a new user to the tenant.

    Creates user and sends password reset email.
    Requires tenant-admin role.
    """
    current_user = get_user()
    tenant_id = get_tenant_id()
    roles = _user_roles(current_user)
    if "tenant-admin" not in roles and not is_operator():
        raise HTTPException(status_code=403, detail="Tenant admin access required")
    valid_roles = ["customer", "tenant-admin"]
    if payload.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")
    try:
        existing = await get_user_by_email(payload.email)
        if existing:
            raise HTTPException(status_code=409, detail="User with this email already exists")
        username = payload.email.split("@")[0]
        if await get_user_by_username(username):
            username = f"{username}_{secrets.token_hex(3)}"

        created_user = await create_user(
            username=username,
            email=payload.email,
            first_name=payload.first_name,
            last_name=payload.last_name,
            email_verified=False,
            attributes={"tenant_id": [tenant_id]},
        )
        user_id = created_user.get("id")
        if not user_id:
            raise HTTPException(status_code=500, detail="Created user missing id")
        await assign_realm_role(user_id, payload.role)
        try:
            org = await _get_org_for_tenant(tenant_id)
            if org:
                await add_user_to_organization(user_id, org["id"])
        except Exception as exc:
            logger.warning("Could not add user to organization: %s", exc)
        try:
            await send_password_reset_email(user_id)
        except Exception as exc:
            logger.warning("Could not send password reset email: %s", exc)

        _audit(
            request,
            tenant_id=tenant_id,
            event_type="user.invited",
            category="security",
            action="invite",
            message=f"User {payload.email} invited to tenant {tenant_id}",
            entity_type="user",
            entity_id=user_id,
            entity_name=username,
            details={"email": payload.email, "role": payload.role},
        )
        return {
            "id": user_id,
            "username": created_user.get("username", username),
            "email": created_user.get("email", payload.email),
            "first_name": created_user.get("firstName", payload.first_name),
            "last_name": created_user.get("lastName", payload.last_name),
            "message": "User invited successfully. Password reset email sent.",
        }
    except KeycloakAdminError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.put(
    "/customer/users/{user_id}",
    dependencies=[Depends(JWTBearer()), Depends(inject_tenant_context)],
)
async def update_tenant_user(user_id: str, payload: UpdateUserRequest, request: Request):
    """Update user details (must be in same tenant). Requires tenant-admin role."""
    current_user = get_user()
    tenant_id = get_tenant_id()
    roles = _user_roles(current_user)
    if "tenant-admin" not in roles and not is_operator():
        raise HTTPException(status_code=403, detail="Tenant admin access required")
    try:
        user = await kc_get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if not await _is_user_in_tenant(user, tenant_id) and not is_operator():
            raise HTTPException(status_code=403, detail="User not in your tenant")
        updates = payload.model_dump(exclude_none=True)
        if updates:
            await update_user(user_id, updates)
        _audit(
            request,
            tenant_id=tenant_id,
            event_type="user.updated",
            category="security",
            action="update",
            message=f"User {user.get('username')} updated",
            entity_type="user",
            entity_id=user_id,
            entity_name=user.get("username"),
            details=updates,
        )
        return {"message": "User updated successfully"}
    except KeycloakAdminError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post(
    "/customer/users/{user_id}/role",
    dependencies=[Depends(JWTBearer()), Depends(inject_tenant_context)],
)
async def change_tenant_user_role(user_id: str, payload: AssignRoleRequest, request: Request):
    """Change user's role within the tenant."""
    current_user = get_user()
    tenant_id = get_tenant_id()
    roles = _user_roles(current_user)
    if "tenant-admin" not in roles and not is_operator():
        raise HTTPException(status_code=403, detail="Tenant admin access required")
    valid_roles = ["customer", "tenant-admin"]
    if payload.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")
    try:
        user = await kc_get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if not await _is_user_in_tenant(user, tenant_id) and not is_operator():
            raise HTTPException(status_code=403, detail="User not in your tenant")
        if user_id == current_user.get("sub"):
            raise HTTPException(status_code=400, detail="Cannot change your own role")
        existing_roles = await get_user_roles(user_id)
        for role in existing_roles:
            if role.get("name") in ["customer", "tenant-admin"]:
                await remove_realm_role(user_id, role["name"])
        await assign_realm_role(user_id, payload.role)
        _audit(
            request,
            tenant_id=tenant_id,
            event_type="user.role_changed",
            category="security",
            action="change_role",
            message=f"User {user.get('username')} role changed to {payload.role}",
            entity_type="user",
            entity_id=user_id,
            entity_name=user.get("username"),
            details={"new_role": payload.role},
        )
        return {"message": f"User role changed to {payload.role}"}
    except KeycloakAdminError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.delete(
    "/customer/users/{user_id}",
    dependencies=[Depends(JWTBearer()), Depends(inject_tenant_context)],
)
async def remove_user_from_tenant(user_id: str, request: Request):
    """
    Remove a user from the tenant.

    This removes tenant assignment but does not delete Keycloak account.
    """
    current_user = get_user()
    tenant_id = get_tenant_id()
    roles = _user_roles(current_user)
    if "tenant-admin" not in roles and not is_operator():
        raise HTTPException(status_code=403, detail="Tenant admin access required")
    try:
        user = await kc_get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if not await _is_user_in_tenant(user, tenant_id) and not is_operator():
            raise HTTPException(status_code=403, detail="User not in your tenant")
        if user_id == current_user.get("sub"):
            raise HTTPException(status_code=400, detail="Cannot remove yourself from tenant")

        user_attrs = user.get("attributes", {}) or {}
        user_attrs["tenant_id"] = []
        await update_user(user_id, {"attributes": user_attrs})
        try:
            org = await _get_org_for_tenant(tenant_id)
            if org:
                await remove_user_from_organization(user_id, org["id"])
        except Exception as exc:
            logger.warning("Could not remove user from organization: %s", exc)

        _audit(
            request,
            tenant_id=tenant_id,
            event_type="user.removed_from_tenant",
            category="security",
            action="remove_from_tenant",
            message=f"User {user.get('username')} removed from tenant {tenant_id}",
            severity="warning",
            entity_type="user",
            entity_id=user_id,
            entity_name=user.get("username"),
        )
        return {"message": "User removed from tenant"}
    except KeycloakAdminError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post(
    "/customer/users/{user_id}/reset-password",
    dependencies=[Depends(JWTBearer()), Depends(inject_tenant_context)],
)
async def send_tenant_user_password_reset(user_id: str, request: Request):
    """Send password reset email to a tenant user."""
    current_user = get_user()
    tenant_id = get_tenant_id()
    roles = _user_roles(current_user)
    if "tenant-admin" not in roles and not is_operator():
        raise HTTPException(status_code=403, detail="Tenant admin access required")
    try:
        user = await kc_get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if not await _is_user_in_tenant(user, tenant_id) and not is_operator():
            raise HTTPException(status_code=403, detail="User not in your tenant")
        await send_password_reset_email(user_id)
        _audit(
            request,
            tenant_id=tenant_id,
            event_type="user.password_reset_sent",
            category="security",
            action="password_reset",
            message=f"Password reset email sent to {user.get('username')}",
            entity_type="user",
            entity_id=user_id,
            entity_name=user.get("username"),
        )
        return {"message": "Password reset email sent"}
    except KeycloakAdminError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
