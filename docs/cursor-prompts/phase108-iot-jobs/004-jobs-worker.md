# Phase 108 — Jobs Expiry Worker (ops_worker)

## Context

The jobs worker runs a periodic tick that:
1. Marks `QUEUED` executions as `TIMED_OUT` when their job's `expires_at` has passed.
2. Advances the parent job to `COMPLETED` when all its executions are in a terminal state.

This runs in `services/ops_worker` alongside the existing escalation and
report worker ticks. Follow the same pattern as those workers.

## File to modify
`services/ops_worker/main.py` (or wherever the ops_worker tick loop lives)

## Step 1: Read the existing worker structure

Read `services/ops_worker/main.py` to understand:
- How `run_escalation_tick` and `run_report_worker_tick` are defined and scheduled
- The DB pool setup (how `pool` is passed to ticks)
- The main loop / scheduling pattern (asyncio.sleep interval)

## Step 2: Add the jobs expiry tick

Add this function in the same file or as a new module
`services/ops_worker/jobs_worker.py` (import it if separate):

```python
from shared.log import get_logger, trace_id_var
import uuid

logger = get_logger("pulse.jobs_worker")

TERMINAL_STATUSES = ("SUCCEEDED", "FAILED", "TIMED_OUT", "REJECTED")


async def run_jobs_expiry_tick(pool) -> None:
    """
    1. Find all jobs where expires_at <= NOW() and status = 'IN_PROGRESS'.
    2. For each, mark QUEUED executions as TIMED_OUT.
    3. If all executions are now terminal, mark job as COMPLETED.

    Runs as a background tick — non-fatal exceptions are logged and swallowed.
    """
    token = trace_id_var.set(str(uuid.uuid4()))
    try:
        async with pool.acquire() as conn:
            # Step 1: find expired jobs
            expired_jobs = await conn.fetch(
                """
                SELECT tenant_id, job_id FROM jobs
                WHERE status = 'IN_PROGRESS'
                  AND expires_at IS NOT NULL
                  AND expires_at <= NOW()
                """,
            )

            if not expired_jobs:
                return

            logger.info(
                "jobs_expiry_tick",
                extra={"expired_count": len(expired_jobs)},
            )

            for job in expired_jobs:
                tenant_id = job["tenant_id"]
                job_id = job["job_id"]

                # Step 2: time out all QUEUED executions for this job
                timed_out = await conn.execute(
                    """
                    UPDATE job_executions
                    SET status = 'TIMED_OUT',
                        status_details = '{"reason": "job_expired"}',
                        last_updated_at = NOW()
                    WHERE tenant_id = $1
                      AND job_id = $2
                      AND status = 'QUEUED'
                    """,
                    tenant_id, job_id,
                )

                # Step 3: check if all executions are now terminal
                remaining = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM job_executions
                    WHERE tenant_id = $1 AND job_id = $2
                      AND status NOT IN ('SUCCEEDED','FAILED','TIMED_OUT','REJECTED')
                    """,
                    tenant_id, job_id,
                )

                new_job_status = "COMPLETED" if remaining == 0 else "IN_PROGRESS"
                await conn.execute(
                    "UPDATE jobs SET status=$1, updated_at=NOW() "
                    "WHERE tenant_id=$2 AND job_id=$3",
                    new_job_status, tenant_id, job_id,
                )

                logger.info(
                    "job_expired",
                    extra={
                        "job_id": job_id,
                        "timed_out_executions": timed_out,
                        "job_status": new_job_status,
                    },
                )

    except Exception as exc:
        logger.exception(
            "jobs_expiry_tick_error",
            extra={"error": str(exc)},
        )
    finally:
        trace_id_var.reset(token)
```

## Step 3: Schedule the tick in the main loop

In the ops_worker main loop, add `run_jobs_expiry_tick` alongside the
existing ticks. Run it every **60 seconds** — the same cadence as the
escalation tick:

```python
# In the main async loop, alongside existing ticks:
await run_jobs_expiry_tick(pool)
```

If the worker uses `asyncio.sleep` between tick invocations, the jobs
expiry tick can share the same 60-second sleep cycle. No separate
scheduling needed.

## Step 4: Verify tick is running

```bash
docker logs iot-ops-worker --tail=20 | grep jobs
```

Expected after the next tick fires (within 60s):
- Either `jobs_expiry_tick` with `expired_count: 0` (no expired jobs) — which is correct
- Or `job_expired` entries if any jobs have expired

No log line at all means the tick was not registered — check step 3.
