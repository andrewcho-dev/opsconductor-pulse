import asyncio
import hashlib
import time
import json
import logging
from datetime import datetime, timezone
from dateutil import parser as dtparser
from dataclasses import dataclass
from typing import Optional

import asyncpg
from shared.metrics import ingest_records_dropped_total

logger = logging.getLogger(__name__)
SUPPORTED_ENVELOPE_VERSIONS = {"1"}

MAX_METRIC_KEY_LENGTH = 128
MAX_METRIC_KEYS = 50


def parse_ts(v):
    """
    Parse timestamp string to datetime.
    - Accepts ISO 8601 format (e.g., 2026-02-09T09:15:23.045Z)
    - If no timezone specified, assumes UTC
    - Returns None if parsing fails
    """
    if isinstance(v, str):
        try:
            dt = dtparser.isoparse(v)
            # If naive (no timezone), assume UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return None
    return None


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def normalize_metric(raw_value, multiplier=1.0, offset=0.0):
    if raw_value is None:
        return None
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return None
    try:
        mult = float(multiplier)
    except (TypeError, ValueError):
        mult = 1.0
    try:
        off = float(offset)
    except (TypeError, ValueError):
        off = 0.0
    return (value * mult) + off


class TokenBucket:
    def __init__(self):
        self.tokens = 0.0
        self.updated = time.time()


class DeviceAuthCache:
    def __init__(self, ttl_seconds=60, max_size=10000):
        self._ttl = ttl_seconds
        self._max_size = max_size
        self._cache = {}
        self._hits = 0
        self._misses = 0

    def get(self, tenant_id, device_id):
        key = (tenant_id, device_id)
        entry = self._cache.get(key)
        if entry and time.time() - entry["cached_at"] < self._ttl:
            self._hits += 1
            return entry
        self._misses += 1
        if entry:
            del self._cache[key]
        return None

    def put(self, tenant_id, device_id, token_hash, site_id, status):
        if self._max_size > 0 and len(self._cache) >= self._max_size:
            evict_count = max(1, int(len(self._cache) * 0.1))
            oldest = sorted(self._cache.items(), key=lambda item: item[1]["cached_at"])
            for key, _ in oldest[:evict_count]:
                del self._cache[key]
        self._cache[(tenant_id, device_id)] = {
            "token_hash": token_hash,
            "site_id": site_id,
            "status": status,
            "cached_at": time.time(),
        }

    def invalidate(self, tenant_id, device_id):
        self._cache.pop((tenant_id, device_id), None)

    def stats(self):
        return {"size": len(self._cache), "hits": self._hits, "misses": self._misses}


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
        max_buffer_size: int = 5000,
    ):
        self.pool = pool
        self.batch_size = batch_size
        self.flush_interval = flush_interval_ms / 1000.0
        self.max_buffer_size = max_buffer_size
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
        await self._flush()
        logger.info("TimescaleBatchWriter stopped")

    async def add(self, record: TelemetryRecord):
        """Add a record to the batch."""
        async with self._lock:
            if len(self.batch) >= self.max_buffer_size:
                dropped = self.batch.pop(0)
                ingest_records_dropped_total.labels(
                    tenant_id=dropped.tenant_id or "unknown"
                ).inc()
                logger.warning(
                    "batch writer buffer full, dropping oldest record",
                    extra={
                        "tenant_id": dropped.tenant_id,
                        "device_id": dropped.device_id,
                        "buffer_size": self.max_buffer_size,
                    },
                )
            self.batch.append(record)
            if len(self.batch) >= self.batch_size:
                await self._flush_locked()

    async def add_many(self, records: list[TelemetryRecord]):
        """Add multiple records to the batch."""
        async with self._lock:
            for record in records:
                if len(self.batch) >= self.max_buffer_size:
                    dropped = self.batch.pop(0)
                    ingest_records_dropped_total.labels(
                        tenant_id=dropped.tenant_id or "unknown"
                    ).inc()
                    logger.warning(
                        "batch writer buffer full, dropping oldest record",
                        extra={
                            "tenant_id": dropped.tenant_id,
                            "device_id": dropped.device_id,
                            "buffer_size": self.max_buffer_size,
                        },
                    )
                self.batch.append(record)
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
                if len(records_to_write) > 100:
                    await self._copy_insert(conn, records_to_write)
                else:
                    await self._batch_insert(conn, records_to_write)
                tenant_ids = sorted({r.tenant_id for r in records_to_write if r.tenant_id})
                notify_payload = json.dumps({"tenant_ids": tenant_ids})
                try:
                    await conn.execute("SELECT pg_notify('telemetry_inserted', $1)", notify_payload)
                except Exception as notify_err:
                    logger.warning("Failed to send telemetry_inserted notify: %s", notify_err)

            elapsed_ms = (time.time() - start_time) * 1000
            self.records_written += len(records_to_write)
            self.batches_flushed += 1
            self.last_flush_time = datetime.now(timezone.utc)
            self.last_flush_latency_ms = elapsed_ms

            if elapsed_ms > 100:
                logger.warning(
                    "Slow batch flush: %d records in %.1fms",
                    len(records_to_write),
                    elapsed_ms,
                )

        except Exception as e:
            self.write_errors += 1
            logger.error("Batch write failed: %s", e)

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
            "telemetry",
            records=rows,
            columns=["time", "tenant_id", "device_id", "site_id", "msg_type", "seq", "metrics"],
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


@dataclass
class IngestResult:
    success: bool
    reason: str | None = None


async def validate_and_prepare(
    pool,
    auth_cache: DeviceAuthCache,
    rate_buckets: dict,
    tenant_id: str,
    device_id: str,
    site_id: str,
    msg_type: str,
    provision_token: str | None,
    payload: dict,
    max_payload_bytes: int,
    rps: float,
    burst: float,
    require_token: bool,
) -> IngestResult:
    version = str((payload or {}).get("version", "1"))
    if version not in SUPPORTED_ENVELOPE_VERSIONS:
        return IngestResult(False, f"unsupported_envelope_version:{version}")

    try:
        payload_bytes = len(json.dumps(payload).encode("utf-8"))
    except Exception:
        payload_bytes = max_payload_bytes + 1
    if payload_bytes > max_payload_bytes:
        return IngestResult(False, "PAYLOAD_TOO_LARGE")

    # Validate metric key lengths and count
    metrics = (payload or {}).get("metrics", {})
    if isinstance(metrics, dict):
        if len(metrics) > MAX_METRIC_KEYS:
            return IngestResult(False, "TOO_MANY_METRICS")
        for key in metrics:
            if not isinstance(key, str) or len(key) > MAX_METRIC_KEY_LENGTH:
                return IngestResult(False, "METRIC_KEY_TOO_LONG")
            # Reject keys with control characters or null bytes
            if any(ord(c) < 32 for c in key):
                return IngestResult(False, "METRIC_KEY_INVALID")

    bucket_key = (tenant_id, device_id)
    bucket = rate_buckets.get(bucket_key)
    if bucket is None:
        bucket = TokenBucket()
        bucket.tokens = burst
        rate_buckets[bucket_key] = bucket

    now = time.time()
    elapsed = now - bucket.updated
    bucket.updated = now
    bucket.tokens = min(burst, bucket.tokens + elapsed * rps)
    if bucket.tokens < 1.0:
        return IngestResult(False, "RATE_LIMITED")
    bucket.tokens -= 1.0

    cached = auth_cache.get(tenant_id, device_id)
    if cached is None:
        assert pool is not None
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT site_id, status, provision_token_hash FROM device_registry WHERE tenant_id=$1 AND device_id=$2",
                tenant_id,
                device_id,
            )
        if not row:
            return IngestResult(False, "UNREGISTERED_DEVICE")
        auth_cache.put(tenant_id, device_id, row["provision_token_hash"], row["site_id"], row["status"])
        reg = {
            "token_hash": row["provision_token_hash"],
            "site_id": row["site_id"],
            "status": row["status"],
        }
    else:
        reg = cached

    if reg["status"] != "ACTIVE":
        return IngestResult(False, "DEVICE_REVOKED")

    if str(reg["site_id"]) != str(site_id):
        return IngestResult(False, "SITE_MISMATCH")

    if require_token:
        if provision_token is None:
            return IngestResult(False, "TOKEN_MISSING")
        expected = reg.get("token_hash")
        if sha256_hex(str(provision_token)) != expected:
            return IngestResult(False, "TOKEN_INVALID")

    return IngestResult(True)
