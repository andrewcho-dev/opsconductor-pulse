import logging
import json

from reports.sla_report import generate_sla_report

logger = logging.getLogger(__name__)


async def run_report_tick(pool):
    """
    Called daily. Generates 30-day SLA report snapshots per tenant.
    """
    async with pool.acquire() as conn:
        tenant_rows = await conn.fetch(
            """
            SELECT DISTINCT tenant_id
            FROM device_state
            WHERE status IN ('ONLINE', 'STALE', 'OFFLINE')
            """
        )

    processed = 0
    for row in tenant_rows:
        tenant_id = row["tenant_id"]
        try:
            report = await generate_sla_report(pool, tenant_id, days=30)
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO report_runs (
                        tenant_id, report_type, status, triggered_by, parameters, row_count, completed_at
                    ) VALUES ($1, 'sla_summary', 'done', 'scheduled', $2::jsonb, NULL, NOW())
                    """,
                    tenant_id,
                    json.dumps(report),
                )
            processed += 1
        except Exception:
            logger.exception("Scheduled SLA report failed", extra={"tenant_id": tenant_id})

    logger.info("Scheduled report tick complete", extra={"tenants_processed": processed})
