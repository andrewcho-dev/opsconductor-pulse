from __future__ import annotations

from contextvars import ContextVar

from fastapi import Depends, HTTPException
from starlette.requests import Request

from middleware.tenant import get_tenant_id, get_user, get_user_roles, inject_tenant_context, is_operator


permissions_context: ContextVar[set[str]] = ContextVar("permissions_context", default=set())


async def load_user_permissions(pool, tenant_id: str, user_id: str) -> set[str]:
    """Load the union of permission actions across all assigned roles."""
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("SET LOCAL ROLE pulse_app")
            await conn.execute("SELECT set_config('app.tenant_id', $1, true)", tenant_id)
            rows = await conn.fetch(
                """
                SELECT DISTINCT p.action
                FROM user_role_assignments ura
                JOIN role_permissions rp ON rp.role_id = ura.role_id
                JOIN permissions p ON p.id = rp.permission_id
                WHERE ura.tenant_id = $1 AND ura.user_id = $2
                """,
                tenant_id,
                user_id,
            )
    return {row["action"] for row in rows}


async def bootstrap_user_roles(pool, tenant_id: str, user_id: str, realm_roles: list[str]) -> set[str]:
    """
    Backward compatibility: if a user has realm roles but no DB assignments yet,
    auto-assign a system role and return the resulting permissions.
    """
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("SET LOCAL ROLE pulse_app")
            await conn.execute("SELECT set_config('app.tenant_id', $1, true)", tenant_id)

            count = await conn.fetchval(
                "SELECT COUNT(*) FROM user_role_assignments WHERE tenant_id = $1 AND user_id = $2",
                tenant_id,
                user_id,
            )
            if count > 0:
                return set()

            if "tenant-admin" in realm_roles:
                role_name = "Full Admin"
            elif "customer" in realm_roles:
                role_name = "Viewer"
            else:
                return set()

            # Find the system role (tenant_id IS NULL). Use operator role to bypass RLS.
            await conn.execute("SET LOCAL ROLE pulse_operator")
            role_row = await conn.fetchrow(
                "SELECT id FROM roles WHERE name = $1 AND is_system = true AND tenant_id IS NULL",
                role_name,
            )
            if not role_row:
                return set()

            role_id = role_row["id"]

            # Switch back to pulse_app for the insert (RLS scoped).
            await conn.execute("SET LOCAL ROLE pulse_app")
            await conn.execute("SELECT set_config('app.tenant_id', $1, true)", tenant_id)
            await conn.execute(
                """
                INSERT INTO user_role_assignments (tenant_id, user_id, role_id, assigned_by)
                VALUES ($1, $2, $3, 'system-bootstrap')
                ON CONFLICT (tenant_id, user_id, role_id) DO NOTHING
                """,
                tenant_id,
                user_id,
                role_id,
            )

    return await load_user_permissions(pool, tenant_id, user_id)


async def inject_permissions(request: Request) -> None:
    # Operators bypass permission system entirely.
    if is_operator():
        permissions_context.set({"*"})
        return

    tenant_id = get_tenant_id()
    user = get_user()
    user_id = user.get("sub")
    if not tenant_id or not user_id:
        permissions_context.set(set())
        return

    pool = request.app.state.pool
    perms = await load_user_permissions(pool, tenant_id, str(user_id))

    if not perms:
        realm_roles = get_user_roles()
        perms = await bootstrap_user_roles(pool, tenant_id, str(user_id), realm_roles)

    permissions_context.set(perms)


def get_permissions() -> set[str]:
    return permissions_context.get()


def has_permission(action: str) -> bool:
    perms = get_permissions()
    return "*" in perms or action in perms


def require_permission(action: str):
    async def _check(request: Request, _: None = Depends(inject_tenant_context)) -> None:
        await inject_permissions(request)
        if not has_permission(action):
            raise HTTPException(status_code=403, detail=f"Permission required: {action}")

    return Depends(_check)

