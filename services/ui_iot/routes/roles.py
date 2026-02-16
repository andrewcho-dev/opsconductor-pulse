from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from starlette.requests import Request

from middleware.auth import JWTBearer
from middleware.permissions import get_permissions, inject_permissions, require_permission
from middleware.tenant import get_tenant_id, get_user, inject_tenant_context, is_operator
from db.pool import tenant_connection

logger = logging.getLogger(__name__)

router = APIRouter(tags=["roles"])


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
        severity=severity,
        tenant_id=tenant_id,
        actor_id=actor.get("sub"),
        actor_name=actor.get("preferred_username") or actor.get("email"),
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        details=details or {},
    )


class CreateRoleRequest(BaseModel):
    name: str
    description: str = ""
    permission_ids: list[int]


class UpdateRoleRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permission_ids: Optional[list[int]] = None


class AssignRolesRequest(BaseModel):
    role_ids: list[str]


@router.get(
    "/customer/permissions",
    dependencies=[Depends(JWTBearer()), Depends(inject_tenant_context)],
)
async def list_permissions(request: Request):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, action, category, description FROM permissions ORDER BY category, action"
        )
    return {
        "permissions": [
            {
                "id": row["id"],
                "action": row["action"],
                "category": row["category"],
                "description": row["description"],
            }
            for row in rows
        ]
    }


@router.get(
    "/customer/roles",
    dependencies=[Depends(JWTBearer()), require_permission("users.roles")],
)
async def list_roles(request: Request):
    tenant_id = get_tenant_id()
    pool = request.app.state.pool

    async with tenant_connection(pool, tenant_id) as conn:
        role_rows = await conn.fetch(
            """
            SELECT id, name, description, is_system, created_at, updated_at
            FROM roles
            ORDER BY is_system DESC, name ASC
            """
        )

        role_ids = [row["id"] for row in role_rows]
        perms_by_role: dict[str, list[dict[str, Any]]] = {str(rid): [] for rid in role_ids}
        if role_ids:
            perm_rows = await conn.fetch(
                """
                SELECT rp.role_id, p.id, p.action, p.category, p.description
                FROM role_permissions rp
                JOIN permissions p ON p.id = rp.permission_id
                WHERE rp.role_id = ANY($1::uuid[])
                ORDER BY p.category, p.action
                """,
                role_ids,
            )
            for pr in perm_rows:
                perms_by_role.setdefault(str(pr["role_id"]), []).append(
                    {
                        "id": pr["id"],
                        "action": pr["action"],
                        "category": pr["category"],
                        "description": pr["description"],
                    }
                )

    return {
        "roles": [
            {
                "id": str(row["id"]),
                "name": row["name"],
                "description": row["description"] or "",
                "is_system": bool(row["is_system"]),
                "permissions": perms_by_role.get(str(row["id"]), []),
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
            }
            for row in role_rows
        ]
    }


async def _validate_permission_ids(conn, permission_ids: list[int]) -> None:
    if not permission_ids:
        raise HTTPException(status_code=400, detail="permission_ids must not be empty")
    rows = await conn.fetch("SELECT id FROM permissions WHERE id = ANY($1::int[])", permission_ids)
    found = {int(r["id"]) for r in rows}
    missing = sorted(set(permission_ids) - found)
    if missing:
        raise HTTPException(status_code=400, detail=f"Unknown permission id(s): {missing}")


@router.post(
    "/customer/roles",
    dependencies=[Depends(JWTBearer()), require_permission("users.roles")],
)
async def create_role(payload: CreateRoleRequest, request: Request):
    tenant_id = get_tenant_id()
    if not payload.name or not payload.name.strip():
        raise HTTPException(status_code=400, detail="Role name is required")

    pool = request.app.state.pool
    async with tenant_connection(pool, tenant_id) as conn:
        await _validate_permission_ids(conn, payload.permission_ids)

        role_row = await conn.fetchrow(
            """
            INSERT INTO roles (tenant_id, name, description, is_system)
            VALUES ($1, $2, $3, false)
            RETURNING id
            """,
            tenant_id,
            payload.name.strip(),
            payload.description or "",
        )
        role_id = role_row["id"]

        await conn.execute(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT $1::uuid, unnest($2::int[])
            ON CONFLICT DO NOTHING
            """,
            role_id,
            payload.permission_ids,
        )

    _audit(
        request,
        tenant_id=tenant_id,
        event_type="role.created",
        category="security",
        action="create_role",
        message=f"Role {payload.name.strip()} created",
        entity_type="role",
        entity_id=str(role_id),
        entity_name=payload.name.strip(),
        details={"permission_ids": payload.permission_ids},
    )

    return {"id": str(role_id), "message": "Role created"}


@router.put(
    "/customer/roles/{role_id}",
    dependencies=[Depends(JWTBearer()), require_permission("users.roles")],
)
async def update_role(role_id: str, payload: UpdateRoleRequest, request: Request):
    tenant_id = get_tenant_id()
    pool = request.app.state.pool

    async with tenant_connection(pool, tenant_id) as conn:
        role = await conn.fetchrow(
            "SELECT id, tenant_id, name, is_system FROM roles WHERE id = $1::uuid", role_id
        )
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        if role["is_system"]:
            raise HTTPException(status_code=403, detail="Cannot modify system roles")
        if role["tenant_id"] != tenant_id:
            raise HTTPException(status_code=403, detail="Role is not in your tenant")

        new_name = payload.name.strip() if payload.name is not None else None
        new_desc = payload.description if payload.description is not None else None

        if new_name is not None and not new_name:
            raise HTTPException(status_code=400, detail="Role name must not be empty")

        if new_name is not None or new_desc is not None:
            await conn.execute(
                """
                UPDATE roles
                SET name = COALESCE($2, name),
                    description = COALESCE($3, description),
                    updated_at = NOW()
                WHERE id = $1::uuid
                """,
                role_id,
                new_name,
                new_desc,
            )

        if payload.permission_ids is not None:
            await _validate_permission_ids(conn, payload.permission_ids)
            await conn.execute("DELETE FROM role_permissions WHERE role_id = $1::uuid", role_id)
            await conn.execute(
                """
                INSERT INTO role_permissions (role_id, permission_id)
                SELECT $1::uuid, unnest($2::int[])
                ON CONFLICT DO NOTHING
                """,
                role_id,
                payload.permission_ids,
            )

    _audit(
        request,
        tenant_id=tenant_id,
        event_type="role.updated",
        category="security",
        action="update_role",
        message=f"Role {role['name']} updated",
        entity_type="role",
        entity_id=str(role_id),
        entity_name=role["name"],
        details={"role_id": role_id},
    )
    return {"message": "Role updated"}


@router.delete(
    "/customer/roles/{role_id}",
    dependencies=[Depends(JWTBearer()), require_permission("users.roles")],
)
async def delete_role(role_id: str, request: Request):
    tenant_id = get_tenant_id()
    pool = request.app.state.pool

    async with tenant_connection(pool, tenant_id) as conn:
        role = await conn.fetchrow(
            "SELECT id, tenant_id, name, is_system FROM roles WHERE id = $1::uuid", role_id
        )
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        if role["is_system"]:
            raise HTTPException(status_code=403, detail="Cannot delete system roles")
        if role["tenant_id"] != tenant_id:
            raise HTTPException(status_code=403, detail="Role is not in your tenant")

        await conn.execute("DELETE FROM roles WHERE id = $1::uuid", role_id)

    _audit(
        request,
        tenant_id=tenant_id,
        event_type="role.deleted",
        category="security",
        action="delete_role",
        message=f"Role {role['name']} deleted",
        severity="warning",
        entity_type="role",
        entity_id=str(role_id),
        entity_name=role["name"],
        details={"role_id": role_id},
    )
    return {"message": "Role deleted"}


@router.get(
    "/customer/users/{user_id}/assignments",
    dependencies=[Depends(JWTBearer()), require_permission("users.roles")],
)
async def list_user_assignments(user_id: str, request: Request):
    tenant_id = get_tenant_id()
    pool = request.app.state.pool
    async with tenant_connection(pool, tenant_id) as conn:
        rows = await conn.fetch(
            """
            SELECT ura.id, ura.role_id, ura.assigned_at, ura.assigned_by,
                   r.name as role_name, r.is_system
            FROM user_role_assignments ura
            JOIN roles r ON r.id = ura.role_id
            WHERE ura.tenant_id = $1 AND ura.user_id = $2
            ORDER BY ura.assigned_at
            """,
            tenant_id,
            user_id,
        )
    return {
        "assignments": [
            {
                "id": str(r["id"]),
                "role_id": str(r["role_id"]),
                "role_name": r["role_name"],
                "is_system": bool(r["is_system"]),
                "assigned_at": r["assigned_at"].isoformat() if r["assigned_at"] else None,
                "assigned_by": r["assigned_by"],
            }
            for r in rows
        ]
    }


@router.put(
    "/customer/users/{user_id}/assignments",
    dependencies=[Depends(JWTBearer()), require_permission("users.roles")],
)
async def replace_user_assignments(user_id: str, payload: AssignRolesRequest, request: Request):
    tenant_id = get_tenant_id()
    current_user = get_user()
    if user_id == current_user.get("sub"):
        raise HTTPException(status_code=400, detail="Cannot change your own roles")
    if not payload.role_ids:
        raise HTTPException(status_code=400, detail="At least one role is required")

    pool = request.app.state.pool
    async with tenant_connection(pool, tenant_id) as conn:
        old_rows = await conn.fetch(
            """
            SELECT r.name
            FROM user_role_assignments ura
            JOIN roles r ON r.id = ura.role_id
            WHERE ura.tenant_id = $1 AND ura.user_id = $2
            ORDER BY r.name
            """,
            tenant_id,
            user_id,
        )
        old_role_names = [r["name"] for r in old_rows]

        role_rows = await conn.fetch(
            """
            SELECT id, name
            FROM roles
            WHERE id = ANY($1::uuid[])
            """,
            payload.role_ids,
        )
        if len(role_rows) != len(set(payload.role_ids)):
            found = {str(r["id"]) for r in role_rows}
            missing = sorted(set(payload.role_ids) - found)
            raise HTTPException(status_code=400, detail=f"Unknown or inaccessible role id(s): {missing}")

        new_role_names = [r["name"] for r in sorted(role_rows, key=lambda x: x["name"])]

        # Replace assignments atomically (same transaction via tenant_connection()).
        await conn.execute(
            "DELETE FROM user_role_assignments WHERE tenant_id = $1 AND user_id = $2",
            tenant_id,
            user_id,
        )
        await conn.execute(
            """
            INSERT INTO user_role_assignments (tenant_id, user_id, role_id, assigned_by)
            SELECT $1, $2, unnest($3::uuid[]), $4
            ON CONFLICT (tenant_id, user_id, role_id) DO NOTHING
            """,
            tenant_id,
            user_id,
            payload.role_ids,
            current_user.get("sub"),
        )

    _audit(
        request,
        tenant_id=tenant_id,
        event_type="user.roles_updated",
        category="security",
        action="replace_assignments",
        message=f"User roles updated for user_id={user_id}",
        entity_type="user",
        entity_id=user_id,
        details={"old_roles": old_role_names, "new_roles": new_role_names, "role_ids": payload.role_ids},
    )
    return {"message": "Roles updated"}


@router.get(
    "/customer/me/permissions",
    dependencies=[Depends(JWTBearer()), Depends(inject_tenant_context)],
)
async def get_me_permissions(request: Request):
    # Operators bypass the permission system — return wildcard immediately.
    if is_operator():
        return {"permissions": ["*"], "roles": ["operator"]}

    tenant_id = get_tenant_id()
    user = get_user()
    user_id = user.get("sub")

    await inject_permissions(request)
    perms = sorted(get_permissions())

    role_names: list[str] = []
    if tenant_id and user_id:
        pool = request.app.state.pool
        async with tenant_connection(pool, tenant_id) as conn:
            rows = await conn.fetch(
                """
                SELECT r.name
                FROM user_role_assignments ura
                JOIN roles r ON r.id = ura.role_id
                WHERE ura.tenant_id = $1 AND ura.user_id = $2
                ORDER BY r.name
                """,
                tenant_id,
                str(user_id),
            )
        role_names = [r["name"] for r in rows]

    return {"permissions": perms, "roles": role_names}

