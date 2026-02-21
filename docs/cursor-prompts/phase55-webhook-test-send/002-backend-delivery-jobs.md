# Prompt 002 — Backend: GET /customer/delivery-jobs

Read `services/ui_iot/routes/customer.py`.
The `delivery_jobs` table has: job_id, tenant_id, alert_id, integration_id, route_id, status, attempts, last_error, created_at, updated_at, deliver_on_event.
The `delivery_attempts` table has: attempt_id, job_id, attempt_no, ok, http_status, latency_ms, error, started_at.

## Add Endpoints

```python
@router.get("/delivery-jobs", dependencies=[Depends(require_customer)])
async def list_delivery_jobs(
    status: Optional[str] = Query(None),  # PENDING|PROCESSING|COMPLETED|FAILED
    integration_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    pool=Depends(get_db_pool)
):
    tenant_id = get_tenant_id()
    conditions = ["tenant_id = $1"]
    params = [tenant_id]

    if status:
        VALID_STATUSES = {"PENDING", "PROCESSING", "COMPLETED", "FAILED"}
        if status.upper() not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid status")
        params.append(status.upper())
        conditions.append(f"status = ${len(params)}")

    if integration_id:
        params.append(integration_id)
        conditions.append(f"integration_id = ${len(params)}")

    where = " AND ".join(conditions)

    async with tenant_connection(pool, tenant_id) as conn:
        rows = await conn.fetch(
            f"""
            SELECT job_id, alert_id, integration_id, route_id, status,
                   attempts, last_error, deliver_on_event, created_at, updated_at
            FROM delivery_jobs
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT {limit} OFFSET {offset}
            """,
            *params
        )
        total = await conn.fetchval(f"SELECT COUNT(*) FROM delivery_jobs WHERE {where}", *params)

    return {"jobs": [dict(r) for r in rows], "total": total}


@router.get("/delivery-jobs/{job_id}/attempts", dependencies=[Depends(require_customer)])
async def get_delivery_job_attempts(job_id: int, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        # Verify job belongs to tenant
        job = await conn.fetchrow(
            "SELECT job_id FROM delivery_jobs WHERE tenant_id = $1 AND job_id = $2",
            tenant_id, job_id
        )
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        attempts = await conn.fetch(
            """
            SELECT attempt_no, ok, http_status, latency_ms, error, started_at, finished_at
            FROM delivery_attempts
            WHERE job_id = $1
            ORDER BY attempt_no ASC
            """,
            job_id
        )
    return {"job_id": job_id, "attempts": [dict(a) for a in attempts]}
```

## Acceptance Criteria

- [ ] GET /customer/delivery-jobs returns paginated jobs
- [ ] `?status=FAILED` filters correctly
- [ ] `?integration_id=...` filters correctly
- [ ] GET /customer/delivery-jobs/{id}/attempts returns attempt history
- [ ] 404 if job not found for tenant
- [ ] `pytest -m unit -v` passes
