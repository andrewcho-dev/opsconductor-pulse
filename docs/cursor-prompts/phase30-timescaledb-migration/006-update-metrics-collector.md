# Phase 30.6: Update Metrics Collector

## Task

Update the system metrics collector to write to PostgreSQL/TimescaleDB instead of InfluxDB.

---

## Update Metrics Collector

**File:** `services/ui_iot/metrics_collector.py`

Replace InfluxDB writes with PostgreSQL inserts:

```python
import os
import asyncio
import logging
import time
from datetime import datetime
from typing import Optional

import httpx
import asyncpg

logger = logging.getLogger(__name__)

# Configuration
COLLECTION_INTERVAL = int(os.getenv("METRICS_COLLECTION_INTERVAL", "5"))

# PostgreSQL config
PG_HOST = os.getenv("PG_HOST", "iot-postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "iotcloud")
PG_USER = os.getenv("PG_USER", "iot")
PG_PASS = os.getenv("PG_PASS", "iot_dev")

# Service URLs
INGEST_URL = os.getenv("INGEST_HEALTH_URL", "http://iot-ingest:8080")
EVALUATOR_URL = os.getenv("EVALUATOR_HEALTH_URL", "http://iot-evaluator:8080")
DISPATCHER_URL = os.getenv("DISPATCHER_HEALTH_URL", "http://iot-dispatcher:8080")
DELIVERY_URL = os.getenv("DELIVERY_HEALTH_URL", "http://iot-delivery-worker:8080")


class MetricsCollector:
    """Collects system metrics and writes to TimescaleDB."""

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._pool: Optional[asyncpg.Pool] = None

    async def start(self):
        """Start the background collection loop."""
        if self._running:
            return
        self._running = True
        self._pool = await asyncpg.create_pool(
            host=PG_HOST,
            port=PG_PORT,
            database=PG_DB,
            user=PG_USER,
            password=PG_PASS,
            min_size=1,
            max_size=3,
        )
        self._task = asyncio.create_task(self._collection_loop())
        logger.info("Metrics collector started (interval=%ds)", COLLECTION_INTERVAL)

    async def stop(self):
        """Stop the collection loop."""
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
        """Main collection loop."""
        while self._running:
            try:
                await self._collect_and_write()
            except Exception as e:
                logger.error("Metrics collection error: %s", e)
            await asyncio.sleep(COLLECTION_INTERVAL)

    async def _collect_and_write(self):
        """Collect all metrics and write to TimescaleDB."""
        now = datetime.utcnow()
        metrics = []

        # Collect service health/counters
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Ingest metrics
            ingest_data = await self._fetch_service_health(client, "ingest", INGEST_URL)
            if ingest_data:
                counters = ingest_data.get("counters", {})
                metrics.extend([
                    (now, "messages_received", "ingest", {}, counters.get("messages_received", 0)),
                    (now, "messages_written", "ingest", {}, counters.get("messages_written", 0)),
                    (now, "messages_rejected", "ingest", {}, counters.get("messages_rejected", 0)),
                    (now, "queue_depth", "ingest", {}, counters.get("queue_depth", 0)),
                    (now, "healthy", "ingest", {}, 1),
                ])
            else:
                metrics.append((now, "healthy", "ingest", {}, 0))

            # Evaluator metrics
            evaluator_data = await self._fetch_service_health(client, "evaluator", EVALUATOR_URL)
            if evaluator_data:
                counters = evaluator_data.get("counters", {})
                metrics.extend([
                    (now, "rules_evaluated", "evaluator", {}, counters.get("rules_evaluated", 0)),
                    (now, "alerts_created", "evaluator", {}, counters.get("alerts_created", 0)),
                    (now, "healthy", "evaluator", {}, 1),
                ])
            else:
                metrics.append((now, "healthy", "evaluator", {}, 0))

            # Dispatcher metrics
            dispatcher_data = await self._fetch_service_health(client, "dispatcher", DISPATCHER_URL)
            if dispatcher_data:
                counters = dispatcher_data.get("counters", {})
                metrics.extend([
                    (now, "alerts_processed", "dispatcher", {}, counters.get("alerts_processed", 0)),
                    (now, "routes_matched", "dispatcher", {}, counters.get("routes_matched", 0)),
                    (now, "healthy", "dispatcher", {}, 1),
                ])
            else:
                metrics.append((now, "healthy", "dispatcher", {}, 0))

            # Delivery metrics
            delivery_data = await self._fetch_service_health(client, "delivery", DELIVERY_URL)
            if delivery_data:
                counters = delivery_data.get("counters", {})
                metrics.extend([
                    (now, "jobs_succeeded", "delivery", {}, counters.get("jobs_succeeded", 0)),
                    (now, "jobs_failed", "delivery", {}, counters.get("jobs_failed", 0)),
                    (now, "jobs_pending", "delivery", {}, counters.get("jobs_pending", 0)),
                    (now, "healthy", "delivery", {}, 1),
                ])
            else:
                metrics.append((now, "healthy", "delivery", {}, 0))

        # Collect Postgres metrics
        try:
            async with self._pool.acquire() as conn:
                # Connection count
                connections = await conn.fetchval(
                    "SELECT count(*) FROM pg_stat_activity WHERE datname = $1",
                    PG_DB,
                )
                # Database size
                db_size = await conn.fetchval(
                    "SELECT pg_database_size($1)", PG_DB
                )
                metrics.extend([
                    (now, "connections", "postgres", {}, connections),
                    (now, "db_size_bytes", "postgres", {}, db_size),
                    (now, "healthy", "postgres", {}, 1),
                ])

                # Platform aggregate counts
                counts = await conn.fetchrow(
                    """
                    SELECT
                        (SELECT COUNT(*) FROM device_state WHERE status = 'ONLINE') as devices_online,
                        (SELECT COUNT(*) FROM device_state WHERE status = 'STALE') as devices_stale,
                        (SELECT COUNT(*) FROM fleet_alert WHERE status = 'OPEN') as alerts_open,
                        (SELECT COUNT(*) FROM delivery_jobs WHERE status = 'PENDING') as deliveries_pending
                    """
                )
                metrics.extend([
                    (now, "devices_online", "platform", {}, counts["devices_online"] or 0),
                    (now, "devices_stale", "platform", {}, counts["devices_stale"] or 0),
                    (now, "alerts_open", "platform", {}, counts["alerts_open"] or 0),
                    (now, "deliveries_pending", "platform", {}, counts["deliveries_pending"] or 0),
                ])

        except Exception as e:
            logger.warning("Failed to collect Postgres metrics: %s", e)
            metrics.append((now, "healthy", "postgres", {}, 0))

        # Write all metrics to TimescaleDB
        if metrics:
            await self._write_metrics(metrics)

    async def _fetch_service_health(
        self, client: httpx.AsyncClient, name: str, url: str
    ) -> Optional[dict]:
        """Fetch health data from a service."""
        try:
            resp = await client.get(f"{url}/health")
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.debug("Failed to fetch %s health: %s", name, e)
        return None

    async def _write_metrics(self, metrics: list[tuple]):
        """Write metrics batch to TimescaleDB."""
        try:
            async with self._pool.acquire() as conn:
                await conn.executemany(
                    """
                    INSERT INTO system_metrics (time, metric_name, service, tags, value)
                    VALUES ($1, $2, $3, $4::jsonb, $5)
                    """,
                    [
                        (m[0], m[1], m[2], "{}" if not m[3] else str(m[3]), m[4])
                        for m in metrics
                    ],
                )
        except Exception as e:
            logger.error("Failed to write metrics: %s", e)


# Global instance
collector = MetricsCollector()
```

---

## Update System Routes for History

**File:** `services/ui_iot/routes/system.py`

Update history endpoints to query PostgreSQL:

```python
@router.get("/metrics/history")
async def get_metrics_history(
    request: Request,
    metric: str = Query(..., description="Metric name"),
    minutes: int = Query(15, ge=1, le=1440),
    service: Optional[str] = Query(None, description="Filter by service"),
):
    """Get historical time-series for a metric."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        if service:
            rows = await conn.fetch(
                """
                SELECT time, value
                FROM system_metrics
                WHERE metric_name = $1
                  AND service = $2
                  AND time > now() - make_interval(mins => $3)
                ORDER BY time ASC
                """,
                metric,
                service,
                minutes,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT time, value
                FROM system_metrics
                WHERE metric_name = $1
                  AND time > now() - make_interval(mins => $3)
                ORDER BY time ASC
                """,
                metric,
                minutes,
            )

    points = [
        {"time": row["time"].isoformat(), "value": row["value"]}
        for row in rows
    ]

    return {
        "metric": metric,
        "service": service,
        "points": points,
        "minutes": minutes,
    }


@router.get("/metrics/latest")
async def get_latest_metrics(request: Request):
    """Get most recent value for all metrics."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT DISTINCT ON (metric_name, service)
                metric_name,
                service,
                value,
                time
            FROM system_metrics
            ORDER BY metric_name, service, time DESC
            """
        )

    result = {}
    for row in rows:
        service = row["service"] or "system"
        if service not in result:
            result[service] = {}
        result[service][row["metric_name"]] = row["value"]

    return result
```

---

## Verification

```bash
# Rebuild and restart UI
cd /home/opsconductor/simcloud/compose
docker compose build ui
docker compose up -d ui

# Wait for metrics collection
sleep 30

# Query metrics from database
docker compose exec postgres psql -U iot -d iotcloud -c "
SELECT metric_name, service, value, time
FROM system_metrics
ORDER BY time DESC
LIMIT 20;
"

# Test API endpoint
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8080/operator/system/metrics/history?metric=queue_depth&minutes=5"
```

---

## Files

| Action | File |
|--------|------|
| MODIFY | `services/ui_iot/metrics_collector.py` |
| MODIFY | `services/ui_iot/routes/system.py` |
