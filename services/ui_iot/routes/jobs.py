"""Operator jobs routes."""

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from routes.customer import *  # noqa: F401,F403


router = APIRouter(
    prefix="/customer",
    tags=["jobs"],
    dependencies=[
        Depends(JWTBearer()),
        Depends(inject_tenant_context),
        Depends(require_customer),
    ],
)


class JobCreate(BaseModel):
    job_id: str | None = None
    document_type: str = Field(..., min_length=1, max_length=100)
    document_params: dict[str, Any] = Field(default_factory=dict)
    target_device_id: str | None = None
    target_group_id: str | None = None
    target_all: bool = False
    expires_in_hours: int | None = Field(default=24, ge=1, le=720)


class JobCancelRequest(BaseModel):
    reason: str | None = None


TERMINAL_STATUSES = {"SUCCEEDED", "FAILED", "TIMED_OUT", "REJECTED"}


def _jsonb_to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


@router.post("/jobs", status_code=201)
async def create_job(body: JobCreate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    user = get_user()

    targets = [bool(body.target_device_id), bool(body.target_group_id), bool(body.target_all)]
    if sum(targets) != 1:
        raise HTTPException(
            status_code=400,
            detail="Exactly one of target_device_id, target_group_id, target_all must be set",
        )

    job_id = body.job_id or str(uuid.uuid4())
    expires_at = (
        datetime.now(timezone.utc) + timedelta(hours=body.expires_in_hours)
        if body.expires_in_hours
        else None
    )

    async with tenant_connection(pool, tenant_id) as conn:
        if body.target_device_id:
            exists = await conn.fetchval(
                "SELECT 1 FROM device_state WHERE tenant_id=$1 AND device_id=$2",
                tenant_id,
                body.target_device_id,
            )
            if not exists:
                raise HTTPException(status_code=404, detail="Device not found")
            device_ids = [body.target_device_id]
        elif body.target_group_id:
            rows = await conn.fetch(
                "SELECT device_id FROM device_group_members WHERE tenant_id=$1 AND group_id=$2",
                tenant_id,
                body.target_group_id,
            )
            device_ids = [r["device_id"] for r in rows]
            if not device_ids:
                raise HTTPException(status_code=400, detail="Group has no members")
        else:
            rows = await conn.fetch(
                "SELECT device_id FROM device_state WHERE tenant_id=$1",
                tenant_id,
            )
            device_ids = [r["device_id"] for r in rows]
            if not device_ids:
                raise HTTPException(status_code=400, detail="No devices in tenant")

        await conn.execute(
            """
            INSERT INTO jobs
              (job_id, tenant_id, document_type, document_params,
               target_device_id, target_group_id, target_all,
               expires_at, created_by)
            VALUES ($1,$2,$3,$4::jsonb,$5,$6,$7,$8,$9)
            """,
            job_id,
            tenant_id,
            body.document_type,
            json.dumps(body.document_params),
            body.target_device_id,
            body.target_group_id,
            body.target_all,
            expires_at,
            user.get("sub") or user.get("user_id"),
        )

        await conn.executemany(
            """
            INSERT INTO job_executions (job_id, tenant_id, device_id)
            VALUES ($1, $2, $3)
            ON CONFLICT DO NOTHING
            """,
            [(job_id, tenant_id, did) for did in device_ids],
        )

    return {
        "job_id": job_id,
        "status": "IN_PROGRESS",
        "execution_count": len(device_ids),
        "expires_at": expires_at.isoformat() if expires_at else None,
    }


@router.get("/jobs")
async def list_jobs(
    status: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        conditions = ["tenant_id = $1"]
        params: list[Any] = [tenant_id]
        if status:
            params.append(status)
            conditions.append(f"status = ${len(params)}")
        where = " AND ".join(conditions)
        params.extend([limit, offset])
        rows = await conn.fetch(
            f"""
            SELECT job_id, document_type, document_params, status,
                   target_device_id, target_group_id, target_all,
                   expires_at, created_by, created_at,
                   (SELECT COUNT(*) FROM job_executions e
                    WHERE e.tenant_id=j.tenant_id AND e.job_id=j.job_id) AS total_executions,
                   (SELECT COUNT(*) FROM job_executions e
                    WHERE e.tenant_id=j.tenant_id AND e.job_id=j.job_id
                    AND e.status='SUCCEEDED') AS succeeded_count,
                   (SELECT COUNT(*) FROM job_executions e
                    WHERE e.tenant_id=j.tenant_id AND e.job_id=j.job_id
                    AND e.status IN ('FAILED','TIMED_OUT','REJECTED')) AS failed_count
            FROM jobs j
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT ${len(params) - 1} OFFSET ${len(params)}
            """,
            *params,
        )
    return [
        {
            **dict(r),
            "document_params": _jsonb_to_dict(r["document_params"]),
        }
        for r in rows
    ]


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        job = await conn.fetchrow(
            "SELECT * FROM jobs WHERE tenant_id=$1 AND job_id=$2",
            tenant_id,
            job_id,
        )
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        executions = await conn.fetch(
            """
            SELECT device_id, status, status_details,
                   queued_at, started_at, last_updated_at, execution_number
            FROM job_executions
            WHERE tenant_id=$1 AND job_id=$2
            ORDER BY device_id
            """,
            tenant_id,
            job_id,
        )

    return {
        **dict(job),
        "document_params": _jsonb_to_dict(job["document_params"]),
        "executions": [
            {
                **dict(e),
                "status_details": _jsonb_to_dict(e["status_details"]) if e["status_details"] is not None else None,
            }
            for e in executions
        ],
    }


@router.delete("/jobs/{job_id}")
async def cancel_job(
    job_id: str,
    body: JobCancelRequest | None = None,
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        job = await conn.fetchrow(
            "SELECT status FROM jobs WHERE tenant_id=$1 AND job_id=$2",
            tenant_id,
            job_id,
        )
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        if job["status"] != "IN_PROGRESS":
            raise HTTPException(status_code=400, detail=f"Cannot cancel job in status {job['status']}")

        details = {"reason": (body.reason if body else None) or "canceled by operator"}
        await conn.execute(
            """
            UPDATE job_executions
            SET status='REJECTED', status_details=$1::jsonb, last_updated_at=NOW()
            WHERE tenant_id=$2 AND job_id=$3 AND status='QUEUED'
            """,
            json.dumps(details),
            tenant_id,
            job_id,
        )
        await conn.execute(
            "UPDATE jobs SET status='CANCELED', updated_at=NOW() WHERE tenant_id=$1 AND job_id=$2",
            tenant_id,
            job_id,
        )
    return {"job_id": job_id, "status": "CANCELED"}
