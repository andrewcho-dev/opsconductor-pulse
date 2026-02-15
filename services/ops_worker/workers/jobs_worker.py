import uuid

from shared.log import get_logger, trace_id_var

logger = get_logger("pulse.jobs_worker")


async def run_jobs_expiry_tick(pool) -> None:
    """
    Mark expired queued executions as TIMED_OUT and close terminal jobs.
    """
    token = trace_id_var.set(str(uuid.uuid4()))
    try:
        async with pool.acquire() as conn:
            expired_jobs = await conn.fetch(
                """
                SELECT tenant_id, job_id
                FROM jobs
                WHERE status = 'IN_PROGRESS'
                  AND expires_at IS NOT NULL
                  AND expires_at <= NOW()
                """
            )
            logger.info("jobs_expiry_tick", extra={"expired_count": len(expired_jobs)})

            for job in expired_jobs:
                tenant_id = job["tenant_id"]
                job_id = job["job_id"]
                await conn.execute("SET LOCAL ROLE pulse_app")
                await conn.execute(
                    "SELECT set_config('app.tenant_id', $1, true)",
                    tenant_id,
                )

                timed_out = await conn.execute(
                    """
                    UPDATE job_executions
                    SET status = 'TIMED_OUT',
                        status_details = $1::jsonb,
                        last_updated_at = NOW()
                    WHERE tenant_id = $2
                      AND job_id = $3
                      AND status = 'QUEUED'
                    """,
                    '{"reason":"job_expired"}',
                    tenant_id,
                    job_id,
                )

                remaining = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM job_executions
                    WHERE tenant_id = $1 AND job_id = $2
                      AND status NOT IN ('SUCCEEDED','FAILED','TIMED_OUT','REJECTED')
                    """,
                    tenant_id,
                    job_id,
                )
                new_job_status = "COMPLETED" if remaining == 0 else "IN_PROGRESS"
                await conn.execute(
                    """
                    UPDATE jobs
                    SET status = $1, updated_at = NOW()
                    WHERE tenant_id = $2 AND job_id = $3
                    """,
                    new_job_status,
                    tenant_id,
                    job_id,
                )
                logger.info(
                    "job_expired",
                    extra={
                        "tenant_id": tenant_id,
                        "job_id": job_id,
                        "timed_out_executions": timed_out,
                        "job_status": new_job_status,
                    },
                )
    except Exception as exc:
        logger.exception("jobs_expiry_tick_error", extra={"error": str(exc)})
    finally:
        trace_id_var.reset(token)
