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
        raise RuntimeError("Tenant context not set — this is a bug")
    return tenant_id


def get_tenant_id_or_none() -> str | None:
    return tenant_context.get()


def get_user() -> dict:
    user = user_context.get()
    if not user:
        raise RuntimeError("User context not set — this is a bug")
    return user


def is_operator() -> bool:
    user = user_context.get()
    if not user:
        return False
    return user.get("role") in ("operator", "operator_admin")


def is_operator_admin() -> bool:
    user = user_context.get()
    if not user:
        return False
    return user.get("role") == "operator_admin"


async def inject_tenant_context(request: Request) -> None:
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Missing authorization")

    tenant_id = user.get("tenant_id")
    set_tenant_context(tenant_id, user)


async def require_customer(request: Request, _: None = Depends(inject_tenant_context)) -> None:
    user = get_user()
    if user.get("role") not in ("customer_viewer", "customer_admin"):
        raise HTTPException(status_code=403, detail="Customer access required")


async def require_operator(request: Request, _: None = Depends(inject_tenant_context)) -> None:
    if not is_operator():
        raise HTTPException(status_code=403, detail="Operator access required")


async def require_operator_admin(request: Request, _: None = Depends(inject_tenant_context)) -> None:
    if not is_operator_admin():
        raise HTTPException(status_code=403, detail="Operator admin access required")
