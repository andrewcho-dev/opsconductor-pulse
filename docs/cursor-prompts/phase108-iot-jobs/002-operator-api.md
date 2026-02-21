# Phase 108 — Operator Jobs API (ui_iot)

## File to create
`services/ui_iot/routes/jobs.py`

Create a new router file — do not add these endpoints to devices.py.

## Pydantic models

```python
import uuid
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime


class JobCreate(BaseModel):
    job_id: Optional[str] = Field(default=None)   # auto-generated if absent
    document_type: str = Field(..., min_length=1, max_length=100)
    document_params: dict[str, Any] = Field(default_factory=dict)

    # Exactly one of these must be set — validated below
    target_device_id: Optional[str] = None
    target_group_id: Optional[str] = None
    target_all: bool = False

    expires_in_hours: Optional[int] = Field(default=24, ge=1, le=720)

    @validator("target_device_id", always=True)
    def validate_target(cls, v, values):
        targets = [
            bool(v),
            bool(values.get("target_group_id")),
            bool(values.get("target_all")),
        ]
        if sum(targets) != 1:
            raise ValueError("Exactly one of target_device_id, target_group_id, target_all must be set")
        return v


class JobCancelRequest(BaseModel):
    reason: Optional[str] = None
```

## Endpoint 1: POST /customer/jobs — create a job

```python
@router.post("/jobs", status_code=201)
async def create_job(
    body: JobCreate,
    pool=Depends(get_db_pool),
    user=Depends(require_auth),
):
    tenant_id = user["tenant_id"]
    job_id = body.job_id or str(uuid.uuid4())
    from datetime import datetime, timezone, timedelta
    expires_at = (
        datetime.now(timezone.utc) + timedelta(hours=body.expires_in_hours)
        if body.expires_in_hours else None
    )

    # Resolve target devices (snapshot semantics)
    async with pool.acquire() as conn:
        await set_tenant_context(conn, tenant_id)

        if body.target_device_id:
            # Verify device belongs to tenant
            exists = await conn.fetchval(
                "SELECT 1 FROM device_state WHERE tenant_id=$1 AND device_id=$2",
                tenant_id, body.target_device_id,
            )
            if not exists:
                raise HTTPException(404, "Device not found")
            device_ids = [body.target_device_id]

        elif body.target_group_id:
            rows = await conn.fetch(
                "SELECT device_id FROM device_group_members WHERE tenant_id=$1 AND group_id=$2",
                tenant_id, body.target_group_id,
            )
            device_ids = [r["device_id"] for r in rows]
            if not device_ids:
                raise HTTPException(400, "Group has no members")

        else:  # target_all
            rows = await conn.fetch(
                "SELECT device_id FROM device_state WHERE tenant_id=$1",
                tenant_id,
            )
            device_ids = [r["device_id"] for r in rows]
            if not device_ids:
                raise HTTPException(400, "No devices in tenant")

        # Insert job
        await conn.execute(
            """
            INSERT INTO jobs
              (job_id, tenant_id, document_type, document_params,
               target_device_id, target_group_id, target_all,
               expires_at, created_by)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
            """,
            job_id, tenant_id,
            body.document_type, body.document_params,
            body.target_device_id, body.target_group_id, body.target_all,
            expires_at, user.get("sub") or user.get("user_id"),
        )

        # Insert one execution per device
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
```

## Endpoint 2: GET /customer/jobs — list jobs

```python
@router.get("/jobs")
async def list_jobs(
    status: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    pool=Depends(get_db_pool),
    user=Depends(require_auth),
):
    tenant_id = user["tenant_id"]
    async with pool.acquire() as conn:
        await set_tenant_context(conn, tenant_id)
        conditions = ["tenant_id = $1"]
        params: list = [tenant_id]
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
            LIMIT ${len(params)-1} OFFSET ${len(params)}
            """,
            *params,
        )
    return [dict(r) for r in rows]
```

## Endpoint 3: GET /customer/jobs/{job_id} — job detail with executions

```python
@router.get("/jobs/{job_id}")
async def get_job(
    job_id: str,
    pool=Depends(get_db_pool),
    user=Depends(require_auth),
):
    tenant_id = user["tenant_id"]
    async with pool.acquire() as conn:
        await set_tenant_context(conn, tenant_id)
        job = await conn.fetchrow(
            "SELECT * FROM jobs WHERE tenant_id=$1 AND job_id=$2",
            tenant_id, job_id,
        )
        if not job:
            raise HTTPException(404, "Job not found")
        executions = await conn.fetch(
            """
            SELECT device_id, status, status_details,
                   queued_at, started_at, last_updated_at, execution_number
            FROM job_executions
            WHERE tenant_id=$1 AND job_id=$2
            ORDER BY device_id
            """,
            tenant_id, job_id,
        )
    return {
        **dict(job),
        "executions": [dict(e) for e in executions],
    }
```

## Endpoint 4: DELETE /customer/jobs/{job_id} — cancel a job

```python
@router.delete("/jobs/{job_id}")
async def cancel_job(
    job_id: str,
    body: JobCancelRequest = JobCancelRequest(),
    pool=Depends(get_db_pool),
    user=Depends(require_auth),
):
    tenant_id = user["tenant_id"]
    async with pool.acquire() as conn:
        await set_tenant_context(conn, tenant_id)
        job = await conn.fetchrow(
            "SELECT status FROM jobs WHERE tenant_id=$1 AND job_id=$2",
            tenant_id, job_id,
        )
        if not job:
            raise HTTPException(404, "Job not found")
        if job["status"] not in ("IN_PROGRESS",):
            raise HTTPException(400, f"Cannot cancel job in status {job['status']}")

        # Reject all QUEUED executions
        details = {"reason": body.reason or "canceled by operator"}
        await conn.execute(
            """
            UPDATE job_executions
            SET status='REJECTED', status_details=$1, last_updated_at=NOW()
            WHERE tenant_id=$2 AND job_id=$3 AND status='QUEUED'
            """,
            details, tenant_id, job_id,
        )
        await conn.execute(
            "UPDATE jobs SET status='CANCELED', updated_at=NOW() WHERE tenant_id=$1 AND job_id=$2",
            tenant_id, job_id,
        )
    return {"job_id": job_id, "status": "CANCELED"}
```

## Register router in app.py

In `services/ui_iot/app.py`, import and register the new router:

```python
from routes.jobs import router as jobs_router
app.include_router(jobs_router, prefix="/customer", tags=["jobs"])
```
