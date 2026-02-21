# Phase 108 — Device-Facing Jobs API (ingest_iot)

## Context

Devices poll for pending jobs and report execution outcomes. These endpoints
live in `services/ingest_iot` alongside the twin device API added in Phase 107.
Auth is `X-Provision-Token` header — use the same `resolve_device()` helper.

---

## Endpoint 1: GET /device/v1/jobs/pending

Device calls this on startup and periodically to get its pending job queue.
Returns all QUEUED executions for this device, ordered by queued_at ascending
(oldest first — FIFO processing).

```python
@router.get("/device/v1/jobs/pending")
async def device_get_pending_jobs(
    request: Request,
    pool=Depends(get_ingest_pool),
):
    token = request.headers.get("X-Provision-Token")
    if not token:
        raise HTTPException(401, "Missing provision token")
    tenant_id, device_id = await resolve_device(token, pool)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                e.job_id,
                e.execution_number,
                e.queued_at,
                j.document_type,
                j.document_params,
                j.expires_at
            FROM job_executions e
            JOIN jobs j USING (tenant_id, job_id)
            WHERE e.tenant_id = $1
              AND e.device_id = $2
              AND e.status = 'QUEUED'
              AND (j.expires_at IS NULL OR j.expires_at > NOW())
            ORDER BY e.queued_at ASC
            LIMIT 10
            """,
            tenant_id, device_id,
        )

    return {
        "jobs": [
            {
                "job_id": r["job_id"],
                "execution_number": r["execution_number"],
                "document": {
                    "type": r["document_type"],
                    "params": dict(r["document_params"]),
                },
                "queued_at": r["queued_at"].isoformat(),
                "expires_at": r["expires_at"].isoformat() if r["expires_at"] else None,
            }
            for r in rows
        ]
    }
```

---

## Endpoint 2: PUT /device/v1/jobs/{job_id}/execution

Device uses this to:
1. **Claim** a job (transition QUEUED → IN_PROGRESS)
2. **Complete** a job (transition IN_PROGRESS → SUCCEEDED | FAILED | REJECTED)

This is a single endpoint that handles all execution status transitions from
the device side — matching the AWS `UpdateJobExecution` API.

```python
from pydantic import BaseModel
from typing import Any, Optional

class JobExecutionUpdate(BaseModel):
    status: str   # IN_PROGRESS | SUCCEEDED | FAILED | REJECTED
    status_details: Optional[dict[str, Any]] = None
    execution_number: Optional[int] = None   # for optimistic locking


DEVICE_ALLOWED_TRANSITIONS = {
    "QUEUED":      {"IN_PROGRESS"},
    "IN_PROGRESS": {"SUCCEEDED", "FAILED", "REJECTED"},
}

TERMINAL_STATUSES = {"SUCCEEDED", "FAILED", "TIMED_OUT", "REJECTED"}


@router.put("/device/v1/jobs/{job_id}/execution")
async def device_update_job_execution(
    job_id: str,
    body: JobExecutionUpdate,
    request: Request,
    pool=Depends(get_ingest_pool),
):
    token = request.headers.get("X-Provision-Token")
    if not token:
        raise HTTPException(401, "Missing provision token")
    tenant_id, device_id = await resolve_device(token, pool)

    if body.status not in ("IN_PROGRESS", "SUCCEEDED", "FAILED", "REJECTED"):
        raise HTTPException(400, f"Invalid status: {body.status}")

    async with pool.acquire() as conn:
        execution = await conn.fetchrow(
            """
            SELECT status, execution_number
            FROM job_executions
            WHERE tenant_id=$1 AND job_id=$2 AND device_id=$3
            """,
            tenant_id, job_id, device_id,
        )
        if not execution:
            raise HTTPException(404, "Job execution not found")

        current_status = execution["status"]

        # Validate transition
        allowed = DEVICE_ALLOWED_TRANSITIONS.get(current_status, set())
        if body.status not in allowed:
            raise HTTPException(
                400,
                f"Cannot transition from {current_status} to {body.status}",
            )

        # Optimistic lock check
        if (body.execution_number is not None
                and body.execution_number != execution["execution_number"]):
            raise HTTPException(409, "Execution number mismatch — stale update")

        now_ts = "NOW()"
        started_at_update = ""
        if body.status == "IN_PROGRESS":
            started_at_update = ", started_at = NOW()"

        await conn.execute(
            f"""
            UPDATE job_executions
            SET status           = $1,
                status_details   = $2,
                execution_number = execution_number + 1,
                last_updated_at  = NOW()
                {started_at_update}
            WHERE tenant_id=$3 AND job_id=$4 AND device_id=$5
            """,
            body.status, body.status_details,
            tenant_id, job_id, device_id,
        )

        # If terminal, check whether all executions are done → advance job status
        if body.status in TERMINAL_STATUSES:
            remaining = await conn.fetchval(
                """
                SELECT COUNT(*) FROM job_executions
                WHERE tenant_id=$1 AND job_id=$2
                  AND status NOT IN ('SUCCEEDED','FAILED','TIMED_OUT','REJECTED')
                """,
                tenant_id, job_id,
            )
            if remaining == 0:
                await conn.execute(
                    "UPDATE jobs SET status='COMPLETED', updated_at=NOW() "
                    "WHERE tenant_id=$1 AND job_id=$2",
                    tenant_id, job_id,
                )

    return {
        "job_id": job_id,
        "device_id": device_id,
        "status": body.status,
    }
```

---

## Endpoint 3: GET /device/v1/jobs/{job_id}/execution

Device retrieves details of a specific execution (useful for resuming
an IN_PROGRESS job after a reboot).

```python
@router.get("/device/v1/jobs/{job_id}/execution")
async def device_get_job_execution(
    job_id: str,
    request: Request,
    pool=Depends(get_ingest_pool),
):
    token = request.headers.get("X-Provision-Token")
    if not token:
        raise HTTPException(401, "Missing provision token")
    tenant_id, device_id = await resolve_device(token, pool)

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                e.status, e.status_details, e.execution_number,
                e.queued_at, e.started_at, e.last_updated_at,
                j.document_type, j.document_params, j.expires_at
            FROM job_executions e
            JOIN jobs j USING (tenant_id, job_id)
            WHERE e.tenant_id=$1 AND e.job_id=$2 AND e.device_id=$3
            """,
            tenant_id, job_id, device_id,
        )
    if not row:
        raise HTTPException(404, "Execution not found")

    return {
        "job_id": job_id,
        "device_id": device_id,
        "status": row["status"],
        "status_details": row["status_details"],
        "execution_number": row["execution_number"],
        "document": {
            "type": row["document_type"],
            "params": dict(row["document_params"]),
        },
        "queued_at": row["queued_at"].isoformat(),
        "started_at": row["started_at"].isoformat() if row["started_at"] else None,
        "expires_at": row["expires_at"].isoformat() if row["expires_at"] else None,
    }
```

---

## Register new endpoints

Add the three endpoints to the existing ingest_iot router/app alongside
the twin endpoints added in Phase 107. Confirm in OpenAPI:

```bash
curl -s http://localhost:<ingest_port>/openapi.json | \
  python3 -c "import sys,json; [print(p) for p in json.load(sys.stdin)['paths'] if 'jobs' in p]"
```

Expected:
```
/device/v1/jobs/pending
/device/v1/jobs/{job_id}/execution  (GET + PUT)
```
