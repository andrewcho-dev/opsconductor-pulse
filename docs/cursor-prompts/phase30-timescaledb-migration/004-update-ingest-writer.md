# Phase 30.4: Update Ingest Service Writer

## Task

Replace the InfluxDB batch writer with a PostgreSQL/TimescaleDB batch writer in the ingest service.

---

## Update Shared Ingest Core

**File:** `services/shared/ingest_core.py`

Replace `InfluxBatchWriter` with `TimescaleBatchWriter`:

```python
import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import json

import asyncpg

logger = logging.getLogger(__name__)


@dataclass
class TelemetryRecord:
    """A single telemetry record to be written."""
    time: datetime
    tenant_id: str
    device_id: str
    site_id: Optional[str]
    msg_type: str
    seq: int
    metrics: dict


class TimescaleBatchWriter:
    """
    Batched writer for TimescaleDB telemetry table.
    Collects records and flushes periodically or when batch is full.
    """

    def __init__(
        self,
        pool: asyncpg.Pool,
        batch_size: int = 500,
        flush_interval_ms: int = 1000,
    ):
        self.pool = pool
        self.batch_size = batch_size
        self.flush_interval = flush_interval_ms / 1000.0
        self.batch: list[TelemetryRecord] = []
        self._lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False

        # Metrics
        self.records_written = 0
        self.batches_flushed = 0
        self.write_errors = 0
        self.last_flush_time: Optional[datetime] = None
        self.last_flush_latency_ms: float = 0

    async def start(self):
        """Start the background flush loop."""
        if self._running:
            return
        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info(
            "TimescaleBatchWriter started (batch_size=%d, flush_interval=%.1fs)",
            self.batch_size,
            self.flush_interval,
        )

    async def stop(self):
        """Stop the flush loop and flush remaining records."""
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        # Final flush
        await self._flush()
        logger.info("TimescaleBatchWriter stopped")

    async def add(self, record: TelemetryRecord):
        """Add a record to the batch."""
        async with self._lock:
            self.batch.append(record)
            if len(self.batch) >= self.batch_size:
                await self._flush_locked()

    async def add_many(self, records: list[TelemetryRecord]):
        """Add multiple records to the batch."""
        async with self._lock:
            self.batch.extend(records)
            if len(self.batch) >= self.batch_size:
                await self._flush_locked()

    async def _flush_loop(self):
        """Background loop that flushes periodically."""
        while self._running:
            await asyncio.sleep(self.flush_interval)
            await self._flush()

    async def _flush(self):
        """Flush the current batch."""
        async with self._lock:
            await self._flush_locked()

    async def _flush_locked(self):
        """Flush while holding the lock."""
        if not self.batch:
            return

        records_to_write = self.batch
        self.batch = []

        start_time = time.time()
        try:
            async with self.pool.acquire() as conn:
                # Use COPY for best performance with large batches
                if len(records_to_write) > 100:
                    await self._copy_insert(conn, records_to_write)
                else:
                    await self._batch_insert(conn, records_to_write)

            elapsed_ms = (time.time() - start_time) * 1000
            self.records_written += len(records_to_write)
            self.batches_flushed += 1
            self.last_flush_time = datetime.utcnow()
            self.last_flush_latency_ms = elapsed_ms

            if elapsed_ms > 100:  # Log slow flushes
                logger.warning(
                    "Slow batch flush: %d records in %.1fms",
                    len(records_to_write),
                    elapsed_ms,
                )

        except Exception as e:
            self.write_errors += 1
            logger.error("Batch write failed: %s", e)
            # Re-add failed records to batch for retry (optional)
            # self.batch = records_to_write + self.batch

    async def _batch_insert(self, conn: asyncpg.Connection, records: list[TelemetryRecord]):
        """Insert using executemany (good for small batches)."""
        await conn.executemany(
            """
            INSERT INTO telemetry (time, tenant_id, device_id, site_id, msg_type, seq, metrics)
            VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
            """,
            [
                (
                    r.time,
                    r.tenant_id,
                    r.device_id,
                    r.site_id,
                    r.msg_type,
                    r.seq,
                    json.dumps(r.metrics),
                )
                for r in records
            ],
        )

    async def _copy_insert(self, conn: asyncpg.Connection, records: list[TelemetryRecord]):
        """Insert using COPY (best for large batches)."""
        # Prepare data as tuples
        rows = [
            (
                r.time,
                r.tenant_id,
                r.device_id,
                r.site_id,
                r.msg_type,
                r.seq,
                json.dumps(r.metrics),
            )
            for r in records
        ]

        await conn.copy_records_to_table(
            'telemetry',
            records=rows,
            columns=['time', 'tenant_id', 'device_id', 'site_id', 'msg_type', 'seq', 'metrics'],
        )

    def get_stats(self) -> dict:
        """Get writer statistics."""
        return {
            "records_written": self.records_written,
            "batches_flushed": self.batches_flushed,
            "write_errors": self.write_errors,
            "pending_records": len(self.batch),
            "last_flush_time": self.last_flush_time.isoformat() if self.last_flush_time else None,
            "last_flush_latency_ms": self.last_flush_latency_ms,
        }
```

---

## Update Ingest Service

**File:** `services/ingest_iot/ingest.py`

Replace InfluxDB writer initialization with TimescaleDB:

```python
# Remove InfluxDB imports
# import httpx  # for InfluxDB

# Add TimescaleDB writer import
from shared.ingest_core import TimescaleBatchWriter, TelemetryRecord

# Remove InfluxDB configuration
# INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://iot-influxdb:8181")
# INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "")

# Initialization (in main or startup)
async def create_writer(pool: asyncpg.Pool) -> TimescaleBatchWriter:
    batch_size = int(os.getenv("BATCH_SIZE", "500"))
    flush_interval = int(os.getenv("FLUSH_INTERVAL_MS", "1000"))

    writer = TimescaleBatchWriter(
        pool=pool,
        batch_size=batch_size,
        flush_interval_ms=flush_interval,
    )
    await writer.start()
    return writer


# In message handler, replace InfluxDB write with:
async def handle_telemetry_message(
    writer: TimescaleBatchWriter,
    tenant_id: str,
    device_id: str,
    site_id: str,
    msg_type: str,
    payload: dict,
):
    """Process and queue a telemetry message."""
    # Parse timestamp
    ts_str = payload.get("ts")
    if ts_str:
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except ValueError:
            ts = datetime.utcnow()
    else:
        ts = datetime.utcnow()

    # Create record
    record = TelemetryRecord(
        time=ts,
        tenant_id=tenant_id,
        device_id=device_id,
        site_id=site_id or payload.get("site_id"),
        msg_type=msg_type,
        seq=payload.get("seq", 0),
        metrics=payload.get("metrics", {}),
    )

    # Queue for batch write
    await writer.add(record)
```

---

## Update Environment Variables

**File:** `compose/docker-compose.yml`

Update `ingest` service - remove InfluxDB vars, ensure Postgres vars:

```yaml
  ingest:
    build: ../services/ingest_iot
    container_name: iot-ingest
    environment:
      MQTT_HOST: iot-mqtt
      MQTT_PORT: "1883"
      MQTT_TOPIC: "tenant/+/device/+/+"
      PG_HOST: iot-postgres
      PG_PORT: "5432"
      PG_DB: iotcloud
      PG_USER: iot
      PG_PASS: iot_dev
      AUTO_PROVISION: "0"
      REQUIRE_TOKEN: "1"
      BATCH_SIZE: "500"
      FLUSH_INTERVAL_MS: "1000"
      # Remove INFLUXDB_* variables
    depends_on:
      mqtt:
        condition: service_started
      postgres:
        condition: service_healthy
      # Remove influxdb dependency
```

---

## Verification

```bash
# Rebuild ingest service
cd /home/opsconductor/simcloud/compose
docker compose build ingest
docker compose up -d ingest

# Check logs
docker compose logs ingest --tail=20

# Send test message via MQTT
docker compose exec mqtt mosquitto_pub \
  -t "tenant/enabled/device/test-001/telemetry" \
  -m '{"ts":"2024-01-15T10:00:00Z","site_id":"lab-1","seq":1,"metrics":{"temp":25.5}}'

# Verify in database
docker compose exec postgres psql -U iot -d iotcloud -c "
SELECT time, tenant_id, device_id, metrics
FROM telemetry
ORDER BY time DESC
LIMIT 5;
"
```

---

## Files

| Action | File |
|--------|------|
| MODIFY | `services/shared/ingest_core.py` |
| MODIFY | `services/ingest_iot/ingest.py` |
| MODIFY | `compose/docker-compose.yml` |
