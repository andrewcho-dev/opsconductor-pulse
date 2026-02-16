import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from middleware.auth import JWTBearer
from middleware.tenant import inject_tenant_context, require_customer, get_tenant_id
from middleware.permissions import require_permission
from db.pool import tenant_connection
from dependencies import get_db_pool
from routes.customer import limiter

logger = logging.getLogger(__name__)


class EscalationLevelIn(BaseModel):
    level_number: int = Field(..., ge=1, le=5)
    delay_minutes: int = Field(default=15, ge=1)
    notify_email: Optional[str] = None
    notify_webhook: Optional[str] = None
    oncall_schedule_id: Optional[int] = None


class EscalationPolicyIn(BaseModel):
    name: str
    description: Optional[str] = None
    is_default: bool = False
    levels: List[EscalationLevelIn] = []


class EscalationLevelOut(EscalationLevelIn):
    level_id: int


class EscalationPolicyOut(BaseModel):
    policy_id: int
    tenant_id: str
    name: str
    description: Optional[str]
    is_default: bool
    levels: List[EscalationLevelOut]
    created_at: datetime
    updated_at: datetime


router = APIRouter(
    prefix="/api/v1/customer",
    tags=["escalation"],
    dependencies=[
        Depends(JWTBearer()),
        Depends(inject_tenant_context),
        Depends(require_customer),
    ],
)


async def _fetch_policy(conn, tenant_id: str, policy_id: int):
    policy = await conn.fetchrow(
        """
        SELECT policy_id, tenant_id, name, description, is_default, created_at, updated_at
        FROM escalation_policies
        WHERE tenant_id = $1 AND policy_id = $2
        """,
        tenant_id,
        policy_id,
    )
    if not policy:
        return None
    levels = await conn.fetch(
        """
        SELECT level_id, level_number, delay_minutes, notify_email, notify_webhook, oncall_schedule_id
        FROM escalation_levels
        WHERE policy_id = $1
        ORDER BY level_number
        """,
        policy_id,
    )
    payload = dict(policy)
    payload["levels"] = [dict(level) for level in levels]
    return payload


@router.get("/escalation-policies")
async def list_escalation_policies(pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        policies = await conn.fetch(
            """
            SELECT policy_id
            FROM escalation_policies
            WHERE tenant_id = $1
            ORDER BY created_at DESC
            """,
            tenant_id,
        )
        result = []
        for row in policies:
            policy = await _fetch_policy(conn, tenant_id, row["policy_id"])
            if policy:
                result.append(policy)
    return {"policies": result}


@router.post(
    "/escalation-policies",
    response_model=EscalationPolicyOut,
    status_code=201,
    dependencies=[require_permission("escalation.create")],
)
@limiter.limit("20/minute")
async def create_escalation_policy(request: Request, body: EscalationPolicyIn, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        async with conn.transaction():
            if body.is_default:
                await conn.execute(
                    "UPDATE escalation_policies SET is_default = FALSE, updated_at = NOW() WHERE tenant_id = $1",
                    tenant_id,
                )
            row = await conn.fetchrow(
                """
                INSERT INTO escalation_policies (tenant_id, name, description, is_default)
                VALUES ($1, $2, $3, $4)
                RETURNING policy_id
                """,
                tenant_id,
                body.name.strip(),
                body.description,
                body.is_default,
            )
            policy_id = row["policy_id"]
            for level in body.levels:
                await conn.execute(
                    """
                    INSERT INTO escalation_levels (
                        policy_id, level_number, delay_minutes, notify_email, notify_webhook, oncall_schedule_id
                    )
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    policy_id,
                    level.level_number,
                    level.delay_minutes,
                    level.notify_email,
                    level.notify_webhook,
                    level.oncall_schedule_id,
                )
        policy = await _fetch_policy(conn, tenant_id, policy_id)
    return policy


@router.get("/escalation-policies/{policy_id}", response_model=EscalationPolicyOut)
async def get_escalation_policy(policy_id: int, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        policy = await _fetch_policy(conn, tenant_id, policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Escalation policy not found")
    return policy


@router.put(
    "/escalation-policies/{policy_id}",
    response_model=EscalationPolicyOut,
    dependencies=[require_permission("escalation.update")],
)
@limiter.limit("20/minute")
async def update_escalation_policy(
    request: Request, policy_id: int, body: EscalationPolicyIn, pool=Depends(get_db_pool)
):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        exists = await conn.fetchval(
            "SELECT 1 FROM escalation_policies WHERE tenant_id = $1 AND policy_id = $2",
            tenant_id,
            policy_id,
        )
        if not exists:
            raise HTTPException(status_code=404, detail="Escalation policy not found")
        async with conn.transaction():
            if body.is_default:
                await conn.execute(
                    """
                    UPDATE escalation_policies
                    SET is_default = FALSE, updated_at = NOW()
                    WHERE tenant_id = $1 AND policy_id <> $2
                    """,
                    tenant_id,
                    policy_id,
                )
            await conn.execute(
                """
                UPDATE escalation_policies
                SET name = $3, description = $4, is_default = $5, updated_at = NOW()
                WHERE tenant_id = $1 AND policy_id = $2
                """,
                tenant_id,
                policy_id,
                body.name.strip(),
                body.description,
                body.is_default,
            )
            await conn.execute("DELETE FROM escalation_levels WHERE policy_id = $1", policy_id)
            for level in body.levels:
                await conn.execute(
                    """
                    INSERT INTO escalation_levels (
                        policy_id, level_number, delay_minutes, notify_email, notify_webhook, oncall_schedule_id
                    )
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    policy_id,
                    level.level_number,
                    level.delay_minutes,
                    level.notify_email,
                    level.notify_webhook,
                    level.oncall_schedule_id,
                )
        policy = await _fetch_policy(conn, tenant_id, policy_id)
    return policy


@router.delete(
    "/escalation-policies/{policy_id}",
    status_code=204,
    dependencies=[require_permission("escalation.delete")],
)
@limiter.limit("20/minute")
async def delete_escalation_policy(request: Request, policy_id: int, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        deleted = await conn.execute(
            "DELETE FROM escalation_policies WHERE tenant_id = $1 AND policy_id = $2",
            tenant_id,
            policy_id,
        )
    if deleted.endswith("0"):
        raise HTTPException(status_code=404, detail="Escalation policy not found")
    return Response(status_code=204)
