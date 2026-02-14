import asyncio
import logging
import os

import asyncpg
from health_monitor import run_health_monitor
from metrics_collector import run_metrics_collector
from shared.logging import configure_logging
from workers.escalation_worker import run_escalation_tick
from workers.report_worker import run_report_tick

configure_logging("ops_worker")
logger = logging.getLogger(__name__)

PG_HOST = os.getenv("PG_HOST", "iot-postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "iotcloud")
PG_USER = os.getenv("PG_USER", "iot")
PG_PASS = os.getenv("PG_PASS", "iot_dev")
DATABASE_URL = os.getenv("DATABASE_URL")

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        if DATABASE_URL:
            _pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=2, max_size=10, command_timeout=30)
        else:
            _pool = await asyncpg.create_pool(
                host=PG_HOST,
                port=PG_PORT,
                database=PG_DB,
                user=PG_USER,
                password=PG_PASS,
                min_size=2,
                max_size=10,
                command_timeout=30,
            )
    return _pool


async def worker_loop(fn, pool_obj, interval: int) -> None:
    while True:
        try:
            await fn(pool_obj)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Worker loop failed", extra={"worker": getattr(fn, "__name__", "unknown")})
        await asyncio.sleep(interval)


async def main() -> None:
    pool = await get_pool()
    await asyncio.gather(
        run_health_monitor(),
        run_metrics_collector(),
        worker_loop(run_escalation_tick, pool, interval=60),
        worker_loop(run_report_tick, pool, interval=86400),
    )


if __name__ == "__main__":
    asyncio.run(main())
