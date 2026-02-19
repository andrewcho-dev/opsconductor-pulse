import asyncio
import logging
import os
import time
import uuid

import asyncpg
from aiohttp import web
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from health_monitor import run_health_monitor
from metrics_collector import run_metrics_collector
from shared.logging import configure_logging
from workers.commands_worker import run_commands_expiry_tick
from workers.certificate_worker import run_certificate_tick
from workers.escalation_worker import run_escalation_tick
from workers.export_worker import run_export_cleanup, run_export_tick
from workers.jobs_worker import run_jobs_expiry_tick
from workers.ota_worker import run_ota_campaign_tick
from workers.ota_status_worker import run_ota_status_listener
from workers.report_worker import run_report_tick
from shared.logging import trace_id_var
from shared.metrics import (
    pulse_processing_duration_seconds,
    pulse_db_pool_size,
    pulse_db_pool_free,
)

configure_logging("ops_worker")
logger = logging.getLogger(__name__)

PG_HOST = os.getenv("PG_HOST", "iot-postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "iotcloud")
PG_USER = os.getenv("PG_USER", "iot")
PG_PASS = os.getenv("PG_PASS", "iot_dev")
DATABASE_URL = os.getenv("DATABASE_URL")
PG_POOL_MIN = int(os.getenv("PG_POOL_MIN", "2"))
PG_POOL_MAX = int(os.getenv("PG_POOL_MAX", "10"))

_pool: asyncpg.Pool | None = None


async def start_health_server(pool_obj: asyncpg.Pool) -> None:
    async def health_handler(_request):
        return web.json_response({"status": "ok", "service": "ops_worker"})

    async def ready_handler(_request):
        if pool_obj is not None:
            return web.json_response({"status": "ready"})
        return web.json_response({"status": "not_ready"}, status=503)

    async def metrics_handler(_request):
        return web.Response(body=generate_latest(), content_type=CONTENT_TYPE_LATEST.split(";")[0])

    app = web.Application()
    app.router.add_get("/health", health_handler)
    app.router.add_get("/ready", ready_handler)
    app.router.add_get("/metrics", metrics_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()


async def _init_db_connection(conn: asyncpg.Connection) -> None:
    # Avoid passing statement_timeout as a startup parameter (PgBouncer rejects it).
    await conn.execute("SET statement_timeout TO 30000")


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        if DATABASE_URL:
            _pool = await asyncpg.create_pool(
                dsn=DATABASE_URL,
                min_size=PG_POOL_MIN,
                max_size=PG_POOL_MAX,
                command_timeout=30,
                init=_init_db_connection,
            )
        else:
            _pool = await asyncpg.create_pool(
                host=PG_HOST,
                port=PG_PORT,
                database=PG_DB,
                user=PG_USER,
                password=PG_PASS,
                min_size=PG_POOL_MIN,
                max_size=PG_POOL_MAX,
                command_timeout=30,
                init=_init_db_connection,
            )
    return _pool


async def worker_loop(fn, pool_obj, interval: int) -> None:
    while True:
        trace_token = trace_id_var.set(str(uuid.uuid4()))
        try:
            worker_name = getattr(fn, "__name__", "unknown")
            logger.info("tick_start", extra={"tick": worker_name})
            tick_start = time.monotonic()

            await fn(pool_obj)

            tick_duration = time.monotonic() - tick_start
            pulse_processing_duration_seconds.labels(
                service="ops_worker",
                operation=worker_name,
            ).observe(tick_duration)

            logger.info("tick_done", extra={"tick": worker_name})
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Worker loop failed", extra={"worker": getattr(fn, "__name__", "unknown")})
        finally:
            trace_id_var.reset(trace_token)

        # Report pool stats after each tick
        pulse_db_pool_size.labels(service="ops_worker").set(pool_obj.get_size())
        pulse_db_pool_free.labels(service="ops_worker").set(pool_obj.get_idle_size())
        await asyncio.sleep(interval)


async def main() -> None:
    pool = await get_pool()
    await start_health_server(pool)
    await asyncio.gather(
        run_health_monitor(),
        run_metrics_collector(),
        worker_loop(run_escalation_tick, pool, interval=60),
        worker_loop(run_jobs_expiry_tick, pool, interval=60),
        worker_loop(run_commands_expiry_tick, pool, interval=60),
        worker_loop(run_report_tick, pool, interval=86400),
        worker_loop(run_export_tick, pool, interval=5),
        worker_loop(run_export_cleanup, pool, interval=3600),
        worker_loop(run_certificate_tick, pool, interval=3600),  # hourly: CRL + expiry
        worker_loop(run_ota_campaign_tick, pool, interval=10),   # NEW: OTA rollout
        run_ota_status_listener(pool),                           # NEW: OTA status ingestion
    )


if __name__ == "__main__":
    asyncio.run(main())
