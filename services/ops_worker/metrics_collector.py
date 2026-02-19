import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import asyncpg
import httpx

from shared.http_client import traced_client

logger = logging.getLogger(__name__)

COLLECTION_INTERVAL = int(os.getenv("METRICS_COLLECTION_INTERVAL", "5"))

PG_HOST = os.getenv("PG_HOST", "iot-postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "iotcloud")
PG_USER = os.getenv("PG_USER", "iot")
PG_PASS = os.getenv("PG_PASS", "iot_dev")
DATABASE_URL = os.getenv("DATABASE_URL")
PG_POOL_MIN = int(os.getenv("PG_POOL_MIN", "2"))
PG_POOL_MAX = int(os.getenv("PG_POOL_MAX", "10"))

INGEST_URL = os.getenv("INGEST_HEALTH_URL", "http://iot-ingest:8080")
EVALUATOR_URL = os.getenv("EVALUATOR_HEALTH_URL", "http://iot-evaluator:8080")


class MetricsCollector:
    """Collects system metrics and writes to TimescaleDB."""

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._pool: Optional[asyncpg.Pool] = None

    async def start(self):
        if self._running:
            return
        self._running = True
        if DATABASE_URL:
            self._pool = await asyncpg.create_pool(
                dsn=DATABASE_URL,
                min_size=PG_POOL_MIN,
                max_size=PG_POOL_MAX,
                command_timeout=30,
            )
        else:
            self._pool = await asyncpg.create_pool(
                host=PG_HOST,
                port=PG_PORT,
                database=PG_DB,
                user=PG_USER,
                password=PG_PASS,
                min_size=PG_POOL_MIN,
                max_size=PG_POOL_MAX,
                command_timeout=30,
            )
        self._task = asyncio.create_task(self._collection_loop())
        logger.info("Metrics collector started (interval=%ds)", COLLECTION_INTERVAL)

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._pool:
            await self._pool.close()
        logger.info("Metrics collector stopped")

    async def _collection_loop(self):
        while self._running:
            try:
                await self._collect_and_write()
            except Exception as exc:
                logger.error("Metrics collection error: %s", exc)
            await asyncio.sleep(COLLECTION_INTERVAL)

    async def _collect_and_write(self):
        now = datetime.now(timezone.utc)
        metrics = []

        async with traced_client(timeout=5.0) as client:
            ingest_data = await self._fetch_service_health(client, "ingest", INGEST_URL)
            if ingest_data:
                counters = ingest_data.get("counters", {})
                metrics.extend(
                    [
                        (now, "messages_received", "ingest", {}, counters.get("messages_received", 0)),
                        (now, "messages_written", "ingest", {}, counters.get("messages_written", 0)),
                        (now, "messages_rejected", "ingest", {}, counters.get("messages_rejected", 0)),
                        (now, "queue_depth", "ingest", {}, counters.get("queue_depth", 0)),
                        (now, "healthy", "ingest", {}, 1),
                    ]
                )
            else:
                metrics.append((now, "healthy", "ingest", {}, 0))

            evaluator_data = await self._fetch_service_health(client, "evaluator", EVALUATOR_URL)
            if evaluator_data:
                counters = evaluator_data.get("counters", {})
                metrics.extend(
                    [
                        (now, "rules_evaluated", "evaluator", {}, counters.get("rules_evaluated", 0)),
                        (now, "alerts_created", "evaluator", {}, counters.get("alerts_created", 0)),
                        (now, "healthy", "evaluator", {}, 1),
                    ]
                )
            else:
                metrics.append((now, "healthy", "evaluator", {}, 0))

        try:
            async with self._pool.acquire() as conn:
                connections = await conn.fetchval(
                    "SELECT count(*) FROM pg_stat_activity WHERE datname = $1",
                    PG_DB,
                )
                db_size = await conn.fetchval("SELECT pg_database_size($1)", PG_DB)
                metrics.extend(
                    [
                        (now, "connections", "postgres", {}, connections),
                        (now, "db_size_bytes", "postgres", {}, db_size),
                        (now, "healthy", "postgres", {}, 1),
                    ]
                )

                counts = await conn.fetchrow(
                    """
                    SELECT
                        (SELECT COUNT(*) FROM device_state WHERE status = 'ONLINE') as devices_online,
                        (SELECT COUNT(*) FROM device_state WHERE status = 'STALE') as devices_stale,
                        (SELECT COUNT(*) FROM fleet_alert WHERE status = 'OPEN') as alerts_open,
                        (SELECT COUNT(*) FROM delivery_jobs WHERE status = 'PENDING') as deliveries_pending
                    """
                )
                metrics.extend(
                    [
                        (now, "devices_online", "platform", {}, counts["devices_online"] or 0),
                        (now, "devices_stale", "platform", {}, counts["devices_stale"] or 0),
                        (now, "alerts_open", "platform", {}, counts["alerts_open"] or 0),
                        (now, "deliveries_pending", "platform", {}, counts["deliveries_pending"] or 0),
                    ]
                )

        except Exception as exc:
            logger.warning("Failed to collect Postgres metrics: %s", exc)
            metrics.append((now, "healthy", "postgres", {}, 0))

        if metrics:
            await self._write_metrics(metrics)

    async def _fetch_service_health(self, client: httpx.AsyncClient, name: str, url: str) -> Optional[dict]:
        try:
            resp = await client.get(f"{url}/health")
            if resp.status_code == 200:
                return resp.json()
        except Exception as exc:
            logger.debug("Failed to fetch %s health: %s", name, exc)
        return None

    async def _write_metrics(self, metrics: list[tuple]):
        try:
            async with self._pool.acquire() as conn:
                await conn.executemany(
                    """
                    INSERT INTO system_metrics (time, metric_name, service, tags, value)
                    VALUES ($1, $2, $3, $4::jsonb, $5)
                    """,
                    [(m[0], m[1], m[2], "{}" if not m[3] else str(m[3]), m[4]) for m in metrics],
                )
        except Exception as exc:
            logger.error("Failed to write metrics: %s", exc)


collector = MetricsCollector()


async def run_metrics_collector_cycle() -> None:
    if collector._pool is None:
        if DATABASE_URL:
            collector._pool = await asyncpg.create_pool(
                dsn=DATABASE_URL,
                min_size=PG_POOL_MIN,
                max_size=PG_POOL_MAX,
                command_timeout=30,
            )
        else:
            collector._pool = await asyncpg.create_pool(
                host=PG_HOST,
                port=PG_PORT,
                database=PG_DB,
                user=PG_USER,
                password=PG_PASS,
                min_size=PG_POOL_MIN,
                max_size=PG_POOL_MAX,
                command_timeout=30,
            )
    await collector._collect_and_write()


async def run_metrics_collector() -> None:
    logger.info("Metrics collector started (interval=%ss)", COLLECTION_INTERVAL)
    while True:
        try:
            await run_metrics_collector_cycle()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("metrics_collector error: %s", exc)
        await asyncio.sleep(COLLECTION_INTERVAL)
