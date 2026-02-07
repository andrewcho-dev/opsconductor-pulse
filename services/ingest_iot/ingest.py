import asyncio
import json
import os
import time
from datetime import datetime, timezone
from typing import Optional
import asyncpg
import paho.mqtt.client as mqtt
from aiohttp import web
from shared.ingest_core import (
    parse_ts,
    sha256_hex,
    TokenBucket,
    DeviceAuthCache,
    TimescaleBatchWriter,
    TelemetryRecord,
)

MQTT_HOST = os.getenv("MQTT_HOST", "iot-mqtt")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "tenant/+/device/+/+")

PG_HOST = os.getenv("PG_HOST", "iot-postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB   = os.getenv("PG_DB", "iotcloud")
PG_USER = os.getenv("PG_USER", "iot")
PG_PASS = os.getenv("PG_PASS", "iot_dev")

AUTO_PROVISION = os.getenv("AUTO_PROVISION", "0") == "1"
REQUIRE_TOKEN  = os.getenv("REQUIRE_TOKEN", "1") == "1"

COUNTERS_ENABLED = os.getenv("COUNTERS_ENABLED", "1") == "1"
SETTINGS_POLL_SECONDS = int(os.getenv("SETTINGS_POLL_SECONDS", "5"))
LOG_STATS_EVERY_SECONDS = int(os.getenv("LOG_STATS_EVERY_SECONDS", "30"))
AUTH_CACHE_TTL = int(os.getenv("AUTH_CACHE_TTL_SECONDS", "60"))
AUTH_CACHE_MAX_SIZE = int(os.getenv("AUTH_CACHE_MAX_SIZE", "10000"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "500"))
FLUSH_INTERVAL_MS = int(os.getenv("FLUSH_INTERVAL_MS", "1000"))
INGEST_WORKER_COUNT = int(os.getenv("INGEST_WORKER_COUNT", "4"))
INGEST_QUEUE_SIZE = int(os.getenv("INGEST_QUEUE_SIZE", "50000"))

COUNTERS = {
    "messages_received": 0,
    "messages_written": 0,
    "messages_rejected": 0,
    "queue_depth": 0,
    "last_write_at": None,
}
INGESTOR_REF: Optional["Ingestor"] = None

def utcnow():
    return datetime.now(timezone.utc)


def _counter_inc(key: str, delta: int = 1) -> None:
    if not COUNTERS_ENABLED:
        return
    COUNTERS[key] += delta


async def health_handler(request):
    """Health check endpoint with metrics."""
    if INGESTOR_REF is not None:
        COUNTERS["messages_received"] = INGESTOR_REF.msg_received
        COUNTERS["messages_rejected"] = INGESTOR_REF.msg_dropped
        COUNTERS["queue_depth"] = INGESTOR_REF.queue.qsize()
        if INGESTOR_REF.batch_writer is not None:
            stats = INGESTOR_REF.batch_writer.get_stats()
            COUNTERS["messages_written"] = stats.get("records_written", 0)
    return web.json_response(
        {
            "status": "healthy",
            "service": "ingest",
            "counters": {
                "messages_received": COUNTERS["messages_received"],
                "messages_written": COUNTERS["messages_written"],
                "messages_rejected": COUNTERS["messages_rejected"],
                "queue_depth": COUNTERS["queue_depth"],
            },
            "last_write_at": COUNTERS["last_write_at"],
        }
    )


async def start_health_server():
    app = web.Application()
    app.router.add_get("/health", health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    print("[health] ingest health server started on port 8080")

def topic_extract(topic: str):
    parts = topic.split("/")
    tenant_id = device_id = msg_type = None
    if len(parts) >= 5 and parts[0] == "tenant" and parts[2] == "device":
        tenant_id = parts[1]
        device_id = parts[3]
        msg_type = parts[4]
    return tenant_id, device_id, msg_type

DDL = """
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS app_settings (
  key        TEXT PRIMARY KEY,
  value      TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO app_settings (key, value)
VALUES
  ('MODE','PROD'),
  ('STORE_REJECTS','0'),
  ('MIRROR_REJECTS_TO_RAW','0'),
  ('MAX_PAYLOAD_BYTES','8192'),
  ('RATE_LIMIT_RPS','5'),
  ('RATE_LIMIT_BURST','20')
ON CONFLICT (key) DO NOTHING;

CREATE TABLE IF NOT EXISTS device_registry (
  tenant_id            TEXT NOT NULL,
  device_id            TEXT NOT NULL,
  site_id              TEXT NOT NULL,
  status               TEXT NOT NULL DEFAULT 'ACTIVE',
  provisioned_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  provision_token_hash TEXT NULL,
  device_pubkey        TEXT NULL,
  fw_version           TEXT NULL,
  metadata             JSONB NOT NULL DEFAULT '{}'::jsonb,
  PRIMARY KEY (tenant_id, device_id)
);

ALTER TABLE device_registry
  ADD COLUMN IF NOT EXISTS provision_token_hash TEXT,
  ADD COLUMN IF NOT EXISTS device_pubkey TEXT,
  ADD COLUMN IF NOT EXISTS fw_version TEXT;

CREATE TABLE IF NOT EXISTS quarantine_events (
  id          BIGSERIAL PRIMARY KEY,
  ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  event_ts    TIMESTAMPTZ NULL,
  topic       TEXT NOT NULL,
  tenant_id   TEXT NULL,
  site_id     TEXT NULL,
  device_id   TEXT NULL,
  msg_type    TEXT NULL,
  reason      TEXT NOT NULL,
  payload     JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS quarantine_counters_minute (
  bucket_minute TIMESTAMPTZ NOT NULL,
  tenant_id     TEXT NOT NULL,
  reason        TEXT NOT NULL,
  cnt           BIGINT NOT NULL DEFAULT 0,
  PRIMARY KEY (bucket_minute, tenant_id, reason)
);
"""

class Ingestor:
    def __init__(self):
        self.pool: asyncpg.Pool | None = None
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=INGEST_QUEUE_SIZE)
        self.loop: asyncio.AbstractEventLoop | None = None
        self._workers = []

        self.msg_received = 0
        self.msg_enqueued = 0
        self.msg_dropped = 0

        # settings (runtime)
        self.mode = "PROD"                # PROD|DEV
        self.store_rejects = False
        self.mirror_rejects = False
        self.max_payload_bytes = 8192
        self.rps = 5.0
        self.burst = 20.0

        # per-device buckets
        self.buckets: dict[tuple[str, str], TokenBucket] = {}
        self.auth_cache = DeviceAuthCache(ttl_seconds=AUTH_CACHE_TTL, max_size=AUTH_CACHE_MAX_SIZE)
        self.batch_writer: TimescaleBatchWriter | None = None

    async def init_db(self):
        for attempt in range(60):
            try:
                self.pool = await asyncpg.create_pool(
                    host=PG_HOST, port=PG_PORT, database=PG_DB, user=PG_USER, password=PG_PASS,
                    min_size=2, max_size=10
                )
                async with self.pool.acquire() as conn:
                    for stmt in DDL.strip().split(";"):
                        s = stmt.strip()
                        if s:
                            await conn.execute(s + ";")
                return
            except Exception:
                if attempt == 59:
                    raise
                await asyncio.sleep(1)

    async def settings_worker(self):
        while True:
            try:
                assert self.pool is not None
                async with self.pool.acquire() as conn:
                    rows = await conn.fetch(
                        "SELECT key, value FROM app_settings WHERE key IN "
                        "('MODE','STORE_REJECTS','MIRROR_REJECTS_TO_RAW','MAX_PAYLOAD_BYTES','RATE_LIMIT_RPS','RATE_LIMIT_BURST')"
                    )
                    kv = {r["key"]: r["value"] for r in rows}

                    mode = kv.get("MODE", "PROD").upper()
                    if mode not in ("PROD", "DEV"):
                        mode = "PROD"
                    self.mode = mode

                    # Base values from settings
                    store_rejects = (kv.get("STORE_REJECTS", "0") == "1")
                    mirror_rejects = (kv.get("MIRROR_REJECTS_TO_RAW", "0") == "1")

                    # PROD lock: cannot store/mirror in PROD
                    if self.mode == "PROD":
                        self.store_rejects = False
                        self.mirror_rejects = False
                    else:
                        self.store_rejects = store_rejects
                        self.mirror_rejects = mirror_rejects

                    try:
                        self.max_payload_bytes = int(kv.get("MAX_PAYLOAD_BYTES", "8192"))
                    except Exception:
                        self.max_payload_bytes = 8192

                    try:
                        self.rps = float(kv.get("RATE_LIMIT_RPS", "5"))
                    except Exception:
                        self.rps = 5.0
                    try:
                        self.burst = float(kv.get("RATE_LIMIT_BURST", "20"))
                    except Exception:
                        self.burst = 20.0

            except Exception:
                # keep previous values
                pass

            await asyncio.sleep(SETTINGS_POLL_SECONDS)

    async def stats_worker(self):
        while True:
            await asyncio.sleep(LOG_STATS_EVERY_SECONDS)
            cache_stats = self.auth_cache.stats()
            batch_stats = {
                "records_written": 0,
                "write_errors": 0,
                "batches_flushed": 0,
                "pending_records": 0,
            }
            if self.batch_writer is not None:
                batch_stats = self.batch_writer.get_stats()
            print(
                f"[stats] received={self.msg_received} enqueued={self.msg_enqueued} dropped={self.msg_dropped} "
                f"qsize={self.queue.qsize()} mode={self.mode} store_rejects={int(self.store_rejects)} mirror_rejects={int(self.mirror_rejects)} "
                f"max_payload_bytes={self.max_payload_bytes} rps={self.rps} burst={self.burst} "
                f"auth_cache_hits={cache_stats['hits']} auth_cache_misses={cache_stats['misses']} auth_cache_size={cache_stats['size']} "
                f"ts_written={batch_stats['records_written']} ts_errors={batch_stats['write_errors']} "
                f"ts_flushes={batch_stats['batches_flushed']} ts_pending={batch_stats['pending_records']} "
                f"workers={INGEST_WORKER_COUNT} queue_max={INGEST_QUEUE_SIZE} queue_depth={self.queue.qsize()}"
            )

    async def _inc_counter(self, tenant_id: str | None, reason: str):
        if not COUNTERS_ENABLED or not tenant_id:
            return
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO quarantine_counters_minute (bucket_minute, tenant_id, reason, cnt)
                VALUES (date_trunc('minute', now()), $1, $2, 1)
                ON CONFLICT (bucket_minute, tenant_id, reason)
                DO UPDATE SET cnt = quarantine_counters_minute.cnt + 1
                """,
                tenant_id, reason
            )

    async def _insert_quarantine(self, topic, tenant_id, site_id, device_id, msg_type, reason, payload, event_ts):
        _counter_inc("messages_rejected")
        await self._inc_counter(tenant_id, reason)

        if self.store_rejects:
            assert self.pool is not None
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO quarantine_events (event_ts, topic, tenant_id, site_id, device_id, msg_type, reason, payload)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8::jsonb)
                    """,
                    event_ts, topic, tenant_id, site_id, device_id, msg_type, reason, json.dumps(payload)
                )

    def _rate_limit_ok(self, tenant_id: str, device_id: str) -> bool:
        # token bucket: refill at rps, cap at burst
        key = (tenant_id, device_id)
        b = self.buckets.get(key)
        if b is None:
            b = TokenBucket()
            b.tokens = self.burst
            self.buckets[key] = b

        now = time.time()
        elapsed = now - b.updated
        b.updated = now

        b.tokens = min(self.burst, b.tokens + elapsed * self.rps)
        if b.tokens >= 1.0:
            b.tokens -= 1.0
            return True
        return False

    async def db_worker(self):
        while True:
            topic, payload = await self.queue.get()
            try:
                t_tenant, t_device, msg_type = topic_extract(topic)
                event_ts = parse_ts(payload.get("ts"))

                tenant_id = t_tenant
                device_id = t_device
                site_id = payload.get("site_id") or None
                p_tenant = payload.get("tenant_id") or None

                # payload size guard (DoS hardening)
                try:
                    payload_bytes = len(json.dumps(payload).encode("utf-8"))
                except Exception:
                    payload_bytes = self.max_payload_bytes + 1
                if payload_bytes > self.max_payload_bytes:
                    await self._insert_quarantine(topic, tenant_id or "unknown", site_id, device_id, msg_type, "PAYLOAD_TOO_LARGE", payload, event_ts)
                    continue

                if tenant_id is None or device_id is None or msg_type is None:
                    await self._insert_quarantine(topic, None, site_id, None, None, "BAD_TOPIC_FORMAT", payload, event_ts)
                    continue

                if not self._rate_limit_ok(tenant_id, device_id):
                    await self._insert_quarantine(topic, tenant_id, site_id, device_id, msg_type, "RATE_LIMITED", payload, event_ts)
                    continue

                if p_tenant is not None and str(p_tenant) != str(tenant_id):
                    await self._insert_quarantine(topic, tenant_id, site_id, device_id, msg_type, "TENANT_MISMATCH_TOPIC_VS_PAYLOAD", payload, event_ts)
                    continue

                if site_id is None:
                    await self._insert_quarantine(topic, tenant_id, None, device_id, msg_type, "MISSING_SITE_ID", payload, event_ts)
                    continue

                token = payload.get("provision_token") or None
                token_hash = sha256_hex(str(token)) if token is not None else None

                cached = self.auth_cache.get(tenant_id, device_id)
                reg = None
                if cached:
                    reg = {
                        "site_id": cached["site_id"],
                        "status": cached["status"],
                        "provision_token_hash": cached["token_hash"],
                    }
                else:
                    assert self.pool is not None
                    async with self.pool.acquire() as conn:
                        reg = await conn.fetchrow(
                            """
                            SELECT site_id, status, provision_token_hash
                            FROM device_registry
                            WHERE tenant_id=$1 AND device_id=$2
                            """,
                            tenant_id, device_id
                        )

                        if reg is None:
                            if AUTO_PROVISION:
                                await conn.execute(
                                    """
                                    INSERT INTO device_registry (tenant_id, device_id, site_id, status)
                                    VALUES ($1,$2,$3,'ACTIVE')
                                    """,
                                    tenant_id, device_id, site_id
                                )
                            await self._insert_quarantine(topic, tenant_id, site_id, device_id, msg_type, "UNREGISTERED_DEVICE", payload, event_ts)
                            continue

                    self.auth_cache.put(
                        tenant_id,
                        device_id,
                        reg["provision_token_hash"],
                        reg["site_id"],
                        reg["status"],
                    )

                if reg["status"] != "ACTIVE":
                    await self._insert_quarantine(topic, tenant_id, site_id, device_id, msg_type, "DEVICE_REVOKED", payload, event_ts)
                    continue

                if str(reg["site_id"]) != str(site_id):
                    await self._insert_quarantine(topic, tenant_id, site_id, device_id, msg_type, "SITE_MISMATCH_REGISTRY_VS_PAYLOAD", payload, event_ts)
                    continue

                if REQUIRE_TOKEN:
                    expected = reg["provision_token_hash"]
                    if expected is None:
                        await self._insert_quarantine(topic, tenant_id, site_id, device_id, msg_type, "TOKEN_NOT_SET_IN_REGISTRY", payload, event_ts)
                        continue
                    if token is None:
                        await self._insert_quarantine(topic, tenant_id, site_id, device_id, msg_type, "TOKEN_MISSING", payload, event_ts)
                        continue
                    if token_hash != expected:
                        await self._insert_quarantine(topic, tenant_id, site_id, device_id, msg_type, "TOKEN_INVALID", payload, event_ts)
                        continue

                # Primary write: TimescaleDB (batched)
                ts = event_ts or utcnow()
                record = TelemetryRecord(
                    time=ts,
                    tenant_id=tenant_id,
                    device_id=device_id,
                    site_id=site_id or payload.get("site_id"),
                    msg_type=msg_type,
                    seq=payload.get("seq", 0),
                    metrics=payload.get("metrics", {}) or {},
                )
                COUNTERS["last_write_at"] = utcnow().isoformat()
                await self.batch_writer.add(record)

            except Exception as e:
                await self._insert_quarantine(
                    topic, None, None, None, None,
                    f"INGEST_EXCEPTION:{type(e).__name__}",
                    {"error": str(e), "payload": payload},
                    None
                )
            finally:
                self.queue.task_done()

    def on_connect(self, client, userdata, flags, rc):
        print(f"[mqtt] connected rc={rc} subscribe={MQTT_TOPIC}")
        client.subscribe(MQTT_TOPIC)

    def on_message(self, client, userdata, msg):
        self.msg_received += 1
        _counter_inc("messages_received")
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            if "ts" not in payload:
                payload["ts"] = utcnow().isoformat()
        except Exception:
            payload = {"ts": utcnow().isoformat(), "parse_error": True, "raw": msg.payload.decode("utf-8", errors="replace")}

        if self.loop is None:
            self.msg_dropped += 1
            _counter_inc("messages_rejected")
            return

        def _enqueue():
            try:
                self.queue.put_nowait((msg.topic, payload))
                self.msg_enqueued += 1
            except asyncio.QueueFull:
                self.msg_dropped += 1
                _counter_inc("messages_rejected")

        self.loop.call_soon_threadsafe(_enqueue)

    async def run(self):
        await self.init_db()
        await start_health_server()
        self.loop = asyncio.get_running_loop()
        assert self.pool is not None
        self.batch_writer = TimescaleBatchWriter(
            pool=self.pool,
            batch_size=BATCH_SIZE,
            flush_interval_ms=FLUSH_INTERVAL_MS,
        )
        await self.batch_writer.start()

        asyncio.create_task(self.settings_worker())
        self._workers = []
        for i in range(INGEST_WORKER_COUNT):
            task = asyncio.create_task(self.db_worker())
            self._workers.append(task)
        asyncio.create_task(self.stats_worker())

        client = mqtt.Client()
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
        client.loop_start()

        while True:
            await asyncio.sleep(5)

async def main():
    ing = Ingestor()
    global INGESTOR_REF
    INGESTOR_REF = ing
    await ing.run()

if __name__ == "__main__":
    asyncio.run(main())
