"""
Scheduled log cleanup for non-hypertable tables.
Run via: python -m services.maintenance.log_cleanup
Or: docker compose exec -T postgres psql ... (run SQL directly)
"""
import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict

import asyncpg
from shared.log import configure_root_logger, get_logger

configure_root_logger()
logger = get_logger(__name__)

RETENTION_DAYS: Dict[str, int] = {
    "operator_audit_log": 365,
    "subscription_audit": 730,
    "subscription_notifications": 90,
}


async def cleanup_table(
    conn: asyncpg.Connection,
    table_name: str,
    timestamp_column: str,
    retention_days: int,
) -> int:
    """Delete old rows in batches. Returns number of rows deleted."""
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    total_deleted = 0
    batch_size = 10000

    while True:
        result = await conn.execute(
            f"""
            DELETE FROM {table_name}
            WHERE ctid IN (
                SELECT ctid FROM {table_name}
                WHERE {timestamp_column} < $1
                LIMIT $2
            )
            """,
            cutoff,
            batch_size,
        )
        deleted = int(result.split()[-1])
        total_deleted += deleted
        if deleted < batch_size:
            break
        await asyncio.sleep(0.1)

    return total_deleted


async def run_cleanup(database_url: str) -> None:
    conn = await asyncpg.connect(database_url)
    job_id = None

    try:
        logger.info("Starting log cleanup...")

        if await conn.fetchval(
            "SELECT to_regclass('public.maintenance_log') IS NOT NULL"
        ):
            job_id = await conn.fetchval(
                """
                INSERT INTO maintenance_log (job_name, started_at, status)
                VALUES ('log_cleanup', now(), 'RUNNING')
                RETURNING id
                """
            )

        details: Dict = {}
        total_deleted = 0

        for table_name, retention_days in RETENTION_DAYS.items():
            try:
                ts_col = "created_at"
                if table_name == "subscription_notifications":
                    ts_col = "scheduled_at"
                deleted = await cleanup_table(
                    conn, table_name, ts_col, retention_days
                )
                total_deleted += deleted
                details[table_name] = deleted
                if deleted > 0:
                    logger.info(
                        "Cleaned %s: %s rows (retention: %s days)",
                        table_name, deleted, retention_days,
                    )
            except Exception as e:
                logger.error("Failed to clean %s: %s", table_name, e)
                details[table_name] = f"ERROR: {e}"

        if job_id is not None:
            await conn.execute(
                """
                UPDATE maintenance_log
                SET completed_at = now(), status = 'COMPLETED',
                    rows_affected = $2, details = $3
                WHERE id = $1
                """,
                job_id,
                total_deleted,
                json.dumps(details),
            )

        logger.info("Running VACUUM ANALYZE...")
        await conn.execute("VACUUM ANALYZE")
        logger.info("Log cleanup complete")
    except Exception as e:
        if job_id is not None:
            await conn.execute(
                """
                UPDATE maintenance_log
                SET completed_at = now(), status = 'FAILED', error_message = $2
                WHERE id = $1
                """,
                job_id,
                str(e),
            )
        raise
    finally:
        await conn.close()


async def main() -> None:
    url = os.environ["DATABASE_URL"]
    await run_cleanup(url)


if __name__ == "__main__":
    asyncio.run(main())
