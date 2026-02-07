# Phase 29.9: Background Metrics Collector

## Task

Create a background task that collects system metrics every 5 seconds and writes them to InfluxDB for historical charting.

---

## Add Metrics Collector to UI Service

The UI service already has access to all components. Add a background task that runs on startup.

**File:** `services/ui_iot/metrics_collector.py`

```python
import os
import asyncio
import logging
import time
from datetime import datetime

import httpx
import asyncpg

logger = logging.getLogger(__name__)

# Configuration
COLLECTION_INTERVAL = int(os.getenv("METRICS_COLLECTION_INTERVAL", "5"))  # seconds
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://iot-influxdb:8181")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "")
METRICS_DATABASE = "system_metrics"

# Service URLs
POSTGRES_HOST = os.getenv("PG_HOST", "iot-postgres")
POSTGRES_PORT = int(os.getenv("PG_PORT", "5432"))
POSTGRES_DB = os.getenv("PG_DB", "iotcloud")
POSTGRES_USER = os.getenv("PG_USER", "iot")
POSTGRES_PASS = os.getenv("PG_PASS", "iot_dev")

INGEST_URL = os.getenv("INGEST_HEALTH_URL", "http://iot-ingest:8080")
EVALUATOR_URL = os.getenv("EVALUATOR_HEALTH_URL", "http://iot-evaluator:8080")
DISPATCHER_URL = os.getenv("DISPATCHER_HEALTH_URL", "http://iot-dispatcher:8080")
DELIVERY_URL = os.getenv("DELIVERY_HEALTH_URL", "http://iot-delivery-worker:8080")


class MetricsCollector:
    """Collects system metrics and writes to InfluxDB."""

    def __init__(self):
        self._running = False
        self._task = None
        self._pool = None

    async def start(self):
        """Start the background collection loop."""
        if self._running:
            return
        self._running = True
        self._pool = await asyncpg.create_pool(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASS,
            min_size=1,
            max_size=2,
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
        """Collect all metrics and write to InfluxDB."""
        timestamp = int(time.time() * 1_000_000_000)  # nanoseconds
        lines = []

        # Collect service health/counters
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Ingest metrics
            try:
                resp = await client.get(f"{INGEST_URL}/health")
                if resp.status_code == 200:
                    data = resp.json()
                    counters = data.get("counters", {})
                    lines.append(
                        f"service_metrics,service=ingest "
                        f"messages_received={counters.get('messages_received', 0)}i,"
                        f"messages_written={counters.get('messages_written', 0)}i,"
                        f"messages_rejected={counters.get('messages_rejected', 0)}i,"
                        f"queue_depth={counters.get('queue_depth', 0)}i,"
                        f"healthy=1i "
                        f"{timestamp}"
                    )
                else:
                    lines.append(f"service_metrics,service=ingest healthy=0i {timestamp}")
            except Exception:
                lines.append(f"service_metrics,service=ingest healthy=0i {timestamp}")

            # Evaluator metrics
            try:
                resp = await client.get(f"{EVALUATOR_URL}/health")
                if resp.status_code == 200:
                    data = resp.json()
                    counters = data.get("counters", {})
                    lines.append(
                        f"service_metrics,service=evaluator "
                        f"rules_evaluated={counters.get('rules_evaluated', 0)}i,"
                        f"alerts_created={counters.get('alerts_created', 0)}i,"
                        f"healthy=1i "
                        f"{timestamp}"
                    )
                else:
                    lines.append(f"service_metrics,service=evaluator healthy=0i {timestamp}")
            except Exception:
                lines.append(f"service_metrics,service=evaluator healthy=0i {timestamp}")

            # Dispatcher metrics
            try:
                resp = await client.get(f"{DISPATCHER_URL}/health")
                if resp.status_code == 200:
                    data = resp.json()
                    counters = data.get("counters", {})
                    lines.append(
                        f"service_metrics,service=dispatcher "
                        f"alerts_processed={counters.get('alerts_processed', 0)}i,"
                        f"routes_matched={counters.get('routes_matched', 0)}i,"
                        f"healthy=1i "
                        f"{timestamp}"
                    )
                else:
                    lines.append(f"service_metrics,service=dispatcher healthy=0i {timestamp}")
            except Exception:
                lines.append(f"service_metrics,service=dispatcher healthy=0i {timestamp}")

            # Delivery metrics
            try:
                resp = await client.get(f"{DELIVERY_URL}/health")
                if resp.status_code == 200:
                    data = resp.json()
                    counters = data.get("counters", {})
                    lines.append(
                        f"service_metrics,service=delivery "
                        f"jobs_succeeded={counters.get('jobs_succeeded', 0)}i,"
                        f"jobs_failed={counters.get('jobs_failed', 0)}i,"
                        f"jobs_pending={counters.get('jobs_pending', 0)}i,"
                        f"healthy=1i "
                        f"{timestamp}"
                    )
                else:
                    lines.append(f"service_metrics,service=delivery healthy=0i {timestamp}")
            except Exception:
                lines.append(f"service_metrics,service=delivery healthy=0i {timestamp}")

        # Collect Postgres metrics
        try:
            async with self._pool.acquire() as conn:
                # Connection count
                connections = await conn.fetchval(
                    "SELECT count(*) FROM pg_stat_activity WHERE datname = $1",
                    POSTGRES_DB,
                )
                # Database size
                db_size = await conn.fetchval(
                    "SELECT pg_database_size($1)", POSTGRES_DB
                )
                lines.append(
                    f"postgres_metrics "
                    f"connections={connections}i,"
                    f"db_size_bytes={db_size}i,"
                    f"healthy=1i "
                    f"{timestamp}"
                )

                # Aggregate counts (less frequent metrics)
                counts = await conn.fetchrow(
                    """
                    SELECT
                        (SELECT COUNT(*) FROM device_state WHERE status = 'ONLINE') as devices_online,
                        (SELECT COUNT(*) FROM device_state WHERE status = 'STALE') as devices_stale,
                        (SELECT COUNT(*) FROM fleet_alert WHERE status = 'OPEN') as alerts_open,
                        (SELECT COUNT(*) FROM delivery_jobs WHERE status = 'PENDING') as deliveries_pending
                    """
                )
                lines.append(
                    f"platform_metrics "
                    f"devices_online={counts['devices_online'] or 0}i,"
                    f"devices_stale={counts['devices_stale'] or 0}i,"
                    f"alerts_open={counts['alerts_open'] or 0}i,"
                    f"deliveries_pending={counts['deliveries_pending'] or 0}i "
                    f"{timestamp}"
                )
        except Exception as e:
            logger.warning("Failed to collect Postgres metrics: %s", e)
            lines.append(f"postgres_metrics healthy=0i {timestamp}")

        # Write to InfluxDB
        if lines:
            await self._write_to_influx(lines)

    async def _write_to_influx(self, lines: list[str]):
        """Write line protocol to InfluxDB."""
        body = "\n".join(lines)
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    f"{INFLUXDB_URL}/api/v3/write_lp?db={METRICS_DATABASE}",
                    content=body,
                    headers={
                        "Authorization": f"Bearer {INFLUXDB_TOKEN}",
                        "Content-Type": "text/plain",
                    },
                )
                if resp.status_code >= 300:
                    logger.warning("InfluxDB write failed: %s", resp.text)
        except Exception as e:
            logger.warning("Failed to write metrics to InfluxDB: %s", e)


# Global instance
collector = MetricsCollector()
```

---

## Start Collector on App Startup

**File:** `services/ui_iot/app.py`

Add startup/shutdown hooks:

```python
from metrics_collector import collector

@app.on_event("startup")
async def start_metrics_collector():
    await collector.start()

@app.on_event("shutdown")
async def stop_metrics_collector():
    await collector.stop()
```

Or if using lifespan:

```python
from contextlib import asynccontextmanager
from metrics_collector import collector

@asynccontextmanager
async def lifespan(app: FastAPI):
    await collector.start()
    yield
    await collector.stop()

app = FastAPI(lifespan=lifespan)
```

---

## Add Environment Variable

**File:** `compose/docker-compose.yml`

Add to `ui` service:

```yaml
  ui:
    environment:
      # ... existing ...
      METRICS_COLLECTION_INTERVAL: "5"
```

---

## Verification

```bash
# Rebuild and restart UI
cd /home/opsconductor/simcloud/compose
docker compose restart ui

# Check logs for collector startup
docker compose logs ui | grep -i "metrics collector"

# After 30 seconds, query the metrics
docker compose exec iot-influxdb influxdb3 query \
  --database system_metrics \
  "SELECT * FROM service_metrics ORDER BY time DESC LIMIT 10"
```

---

## Files

| Action | File |
|--------|------|
| CREATE | `services/ui_iot/metrics_collector.py` |
| MODIFY | `services/ui_iot/app.py` |
| MODIFY | `compose/docker-compose.yml` |
