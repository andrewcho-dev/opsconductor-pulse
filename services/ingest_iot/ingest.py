import asyncio
import json
import os
import hashlib
import time
from datetime import datetime, timezone
from dateutil import parser as dtparser
import asyncpg
import httpx
import paho.mqtt.client as mqtt

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
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://iot-influxdb:8181")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "influx-dev-token-change-me")
AUTH_CACHE_TTL = int(os.getenv("AUTH_CACHE_TTL_SECONDS", "60"))
AUTH_CACHE_MAX_SIZE = int(os.getenv("AUTH_CACHE_MAX_SIZE", "10000"))
INFLUX_BATCH_SIZE = int(os.getenv("INFLUX_BATCH_SIZE", "500"))
INFLUX_FLUSH_INTERVAL_MS = int(os.getenv("INFLUX_FLUSH_INTERVAL_MS", "1000"))

def utcnow():
    return datetime.now(timezone.utc)

def parse_ts(v):
    if isinstance(v, str):
        try:
            return dtparser.isoparse(v)
        except Exception:
            return None
    return None

def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def _escape_tag_value(v: str) -> str:
    """Escape commas, equals, and spaces in InfluxDB line protocol tag values."""
    return v.replace("\\", "\\\\").replace(",", "\\,").replace("=", "\\=").replace(" ", "\\ ")


def _escape_field_key(key):
    """Escape field key for InfluxDB line protocol."""
    return str(key).replace("\\", "\\\\").replace(",", "\\,").replace("=", "\\=").replace(" ", "\\ ")


def _build_line_protocol(msg_type: str, device_id: str, site_id: str, payload: dict, event_ts) -> str:
    """Build InfluxDB line protocol string for a heartbeat or telemetry event."""
    escaped_device = _escape_tag_value(device_id)
    escaped_site = _escape_tag_value(site_id)

    if event_ts is not None:
        ns_ts = int(event_ts.timestamp() * 1_000_000_000)
    else:
        ns_ts = int(time.time() * 1_000_000_000)

    if msg_type == "heartbeat":
        seq = payload.get("seq", 0)
        return f"heartbeat,device_id={escaped_device},site_id={escaped_site} seq={seq}i {ns_ts}"

    elif msg_type == "telemetry":
        metrics = payload.get("metrics") or {}
        fields = []
        seq = payload.get("seq", 0)
        fields.append(f"seq={seq}i")

        for key, value in metrics.items():
            if value is None:
                continue
            escaped_key = _escape_field_key(key)
            if isinstance(value, bool):
                fields.append(f"{escaped_key}={'true' if value else 'false'}")
            elif isinstance(value, int):
                fields.append(f"{escaped_key}={value}i")
            elif isinstance(value, float):
                fields.append(f"{escaped_key}={value}")
            elif isinstance(value, str):
                continue

        field_str = ",".join(fields)
        return f"telemetry,device_id={escaped_device},site_id={escaped_site} {field_str} {ns_ts}"

    return ""

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


class InfluxBatchWriter:
    def __init__(self, http_client, influx_url, influx_token, batch_size=500, flush_interval_ms=1000):
        self._http = http_client
        self._influx_url = influx_url
        self._influx_token = influx_token
        self._batch_size = batch_size
        self._flush_interval_ms = flush_interval_ms
        self._buffers = {}
        self._flush_task = None
        self.writes_ok = 0
        self.writes_err = 0
        self.flushes = 0

    async def start(self):
        self._flush_task = asyncio.create_task(self._periodic_flush())

    async def stop(self):
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        await self.flush_all()

    async def add(self, tenant_id, line):
        self._buffers.setdefault(tenant_id, []).append(line)
        if len(self._buffers[tenant_id]) >= self._batch_size:
            lines = self._buffers[tenant_id]
            self._buffers[tenant_id] = []
            await self._write_batch(tenant_id, lines)

    async def _periodic_flush(self):
        while True:
            try:
                await asyncio.sleep(self._flush_interval_ms / 1000.0)
                await self.flush_all()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[ingest] InfluxDB batch flush error: {e}")

    async def flush_all(self):
        to_flush = self._buffers
        self._buffers = {}
        for tenant_id, lines in to_flush.items():
            if lines:
                await self._write_batch(tenant_id, lines)

    async def _write_batch(self, tenant_id, lines):
        db_name = f"telemetry_{tenant_id}"
        body = "\n".join(lines)
        headers = {
            "Authorization": f"Bearer {self._influx_token}",
            "Content-Type": "text/plain",
        }
        for attempt in range(2):
            try:
                resp = await self._http.post(
                    f"{self._influx_url}/api/v3/write_lp?db={db_name}",
                    content=body,
                    headers=headers,
                )
                if resp.status_code < 300:
                    self.writes_ok += len(lines)
                    self.flushes += 1
                    return
                print(f"[ingest] InfluxDB batch write failed ({attempt + 1}/2): {resp.status_code} {resp.text}")
            except Exception as e:
                print(f"[ingest] InfluxDB batch write exception ({attempt + 1}/2): {e}")
        self.writes_err += len(lines)

    def stats(self):
        buffer_depth = sum(len(v) for v in self._buffers.values())
        return {
            "writes_ok": self.writes_ok,
            "writes_err": self.writes_err,
            "flushes": self.flushes,
            "buffer_depth": buffer_depth,
        }

class Ingestor:
    def __init__(self):
        self.pool: asyncpg.Pool | None = None
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=20000)
        self.loop: asyncio.AbstractEventLoop | None = None

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
        self.influx_client: httpx.AsyncClient | None = None
        self.influx_ok = 0
        self.influx_err = 0
        self.auth_cache = DeviceAuthCache(ttl_seconds=AUTH_CACHE_TTL, max_size=AUTH_CACHE_MAX_SIZE)
        self.batch_writer: InfluxBatchWriter | None = None

    async def init_db(self):
        for attempt in range(60):
            try:
                self.pool = await asyncpg.create_pool(
                    host=PG_HOST, port=PG_PORT, database=PG_DB, user=PG_USER, password=PG_PASS,
                    min_size=1, max_size=5
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
                "writes_ok": 0,
                "writes_err": 0,
                "flushes": 0,
                "buffer_depth": 0,
            }
            if self.batch_writer is not None:
                batch_stats = self.batch_writer.stats()
            print(
                f"[stats] received={self.msg_received} enqueued={self.msg_enqueued} dropped={self.msg_dropped} "
                f"qsize={self.queue.qsize()} mode={self.mode} store_rejects={int(self.store_rejects)} mirror_rejects={int(self.mirror_rejects)} "
                f"max_payload_bytes={self.max_payload_bytes} rps={self.rps} burst={self.burst} "
                f"influx_ok={self.influx_ok} influx_err={self.influx_err} "
                f"auth_cache_hits={cache_stats['hits']} auth_cache_misses={cache_stats['misses']} auth_cache_size={cache_stats['size']} "
                f"influx_batch_ok={batch_stats['writes_ok']} influx_batch_err={batch_stats['writes_err']} "
                f"influx_flushes={batch_stats['flushes']} influx_buffer={batch_stats['buffer_depth']}"
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

    async def _write_influxdb(self, tenant_id, device_id, site_id, msg_type, payload, event_ts):
        """Write event to InfluxDB. Best-effort: failures are counted but don't raise."""
        if self.influx_client is None:
            return

        line = _build_line_protocol(msg_type, device_id, site_id, payload, event_ts)
        if not line:
            return

        db_name = f"telemetry_{tenant_id}"
        headers = {
            "Authorization": f"Bearer {INFLUXDB_TOKEN}",
            "Content-Type": "text/plain",
        }
        for attempt in range(2):
            try:
                resp = await self.influx_client.post(
                    f"{INFLUXDB_URL}/api/v3/write_lp?db={db_name}",
                    content=line,
                    headers=headers,
                )
                if resp.status_code < 300:
                    self.influx_ok += 1
                    return
                print(f"[ingest] InfluxDB write failed ({attempt + 1}/2): {resp.status_code} {resp.text}")
            except Exception as e:
                print(f"[ingest] InfluxDB write exception ({attempt + 1}/2): {e}")
        self.influx_err += 1

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

                # Primary write: InfluxDB (batched)
                line = _build_line_protocol(msg_type, device_id, site_id, payload, event_ts)
                if line:
                    await self.batch_writer.add(tenant_id, line)

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
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            if "ts" not in payload:
                payload["ts"] = utcnow().isoformat()
        except Exception:
            payload = {"ts": utcnow().isoformat(), "parse_error": True, "raw": msg.payload.decode("utf-8", errors="replace")}

        if self.loop is None:
            self.msg_dropped += 1
            return

        def _enqueue():
            try:
                self.queue.put_nowait((msg.topic, payload))
                self.msg_enqueued += 1
            except asyncio.QueueFull:
                self.msg_dropped += 1

        self.loop.call_soon_threadsafe(_enqueue)

    async def run(self):
        await self.init_db()
        self.loop = asyncio.get_running_loop()
        self.influx_client = httpx.AsyncClient(timeout=10.0)
        self.batch_writer = InfluxBatchWriter(
            self.influx_client, INFLUXDB_URL, INFLUXDB_TOKEN,
            INFLUX_BATCH_SIZE, INFLUX_FLUSH_INTERVAL_MS
        )
        await self.batch_writer.start()

        asyncio.create_task(self.settings_worker())
        asyncio.create_task(self.db_worker())
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
    await ing.run()

if __name__ == "__main__":
    asyncio.run(main())
