from contextvars import ContextVar
from typing import Optional

from fastapi import Depends, HTTPException, Request

tenant_context: ContextVar[Optional[str]] = ContextVar("tenant_context", default=None)
user_context: ContextVar[Optional[dict]] = ContextVar("user_context", default=None)


def set_tenant_context(tenant_id: str | None, user: dict) -> None:
    tenant_context.set(tenant_id)
    user_context.set(user)


def get_tenant_id() -> str:
    tenant_id = tenant_context.get()
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant context not established")
    return tenant_id


def get_user() -> dict:
    user = user_context.get()
    if not user:
        raise HTTPException(status_code=401, detail="User context not established")
    return user


def get_user_roles() -> list[str]:
    """Get user's realm roles from token claims."""
    user = get_user()
    realm_access = user.get("realm_access", {}) or {}
    roles = realm_access.get("roles", []) or []
    return [str(role) for role in roles]


def has_role(role: str) -> bool:
    return role in get_user_roles()


def is_operator() -> bool:
    roles = get_user_roles()
    return "operator" in roles or "operator-admin" in roles


def get_user_organizations() -> dict:
    user = get_user()
    orgs = user.get("organization", {}) or {}
    if isinstance(orgs, dict):
        return orgs
    if isinstance(orgs, list):
        # Normalize array form like ["acme-industrial"] to dict-like shape.
        return {str(org): {} for org in orgs if isinstance(org, str)}
    return {}


def _extract_tenant_id_from_user(user: dict) -> Optional[str]:
    # New standard claim shape can be dict or array, depending on mapper config.
    orgs = user.get("organization", {}) or {}
    if isinstance(orgs, dict) and orgs:
        return next(iter(orgs.keys()))
    if isinstance(orgs, list):
        for org in orgs:
            if isinstance(org, str) and org:
                return org

    # Temporary fallback for older tokens while migrating.
    legacy_tenant = user.get("tenant_id")
    if isinstance(legacy_tenant, str) and legacy_tenant:
        return legacy_tenant
    return None


async def inject_tenant_context(request: Request) -> None:
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Missing authorization")

    tenant_id = _extract_tenant_id_from_user(user)
    set_tenant_context(tenant_id, user)


async def require_customer(request: Request, _: None = Depends(inject_tenant_context)) -> None:
    if is_operator():
        return
    tenant_id = tenant_context.get()
    roles = get_user_roles()
    if not tenant_id:
        raise HTTPException(status_code=403, detail="No organization membership")
    if not any(role in roles for role in ("customer", "tenant-admin")):
        raise HTTPException(status_code=403, detail="Customer access required")



async def require_operator(request: Request, _: None = Depends(inject_tenant_context)) -> None:
    if not is_operator():
        raise HTTPException(status_code=403, detail="Operator access required")


async def require_operator_admin(request: Request, _: None = Depends(inject_tenant_context)) -> None:
    if not has_role("operator-admin"):
        raise HTTPException(status_code=403, detail="Operator admin access required")
