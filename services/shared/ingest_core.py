import asyncio
import hashlib
import time
import json
from datetime import datetime, timezone
from dateutil import parser as dtparser
from dataclasses import dataclass


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


@dataclass
class IngestResult:
    success: bool
    reason: str | None = None
    line_protocol: str | None = None


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
    try:
        payload_bytes = len(json.dumps(payload).encode("utf-8"))
    except Exception:
        payload_bytes = max_payload_bytes + 1
    if payload_bytes > max_payload_bytes:
        return IngestResult(False, "PAYLOAD_TOO_LARGE")

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

    event_ts = parse_ts(payload.get("ts"))
    line_protocol = _build_line_protocol(msg_type, device_id, site_id, payload, event_ts)
    return IngestResult(True, line_protocol=line_protocol)
