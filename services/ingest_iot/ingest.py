import asyncio
import json
import os
import re
import signal
import time
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional
import asyncpg
from aiohttp import web
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from shared.ingest_core import (
    parse_ts,
    sha256_hex,
    TokenBucket,
    DeviceAuthCache,
    TimescaleBatchWriter,
    TelemetryRecord,
)
from shared.audit import init_audit_logger, get_audit_logger
from shared.logging import trace_id_var
from shared.logging import configure_logging, log_event
from shared.metrics import ingest_messages_total, ingest_queue_depth
try:
    # Package import (e.g. `import services.ingest_iot.ingest`)
    from .topic_matcher import mqtt_topic_matches, evaluate_payload_filter
except ImportError:  # pragma: no cover
    # Script/legacy import when `services/ingest_iot` is on sys.path
    from topic_matcher import mqtt_topic_matches, evaluate_payload_filter

NATS_URL = os.getenv("NATS_URL", "nats://iot-nats:4222")
SHADOW_REPORTED_TOPIC = "tenant/+/device/+/shadow/reported"
COMMAND_ACK_TOPIC = "tenant/+/device/+/commands/ack"
COMMAND_ACK_RE = re.compile(r"^tenant/(?P<tenant_id>[^/]+)/device/(?P<device_id>[^/]+)/commands/ack$")

PG_HOST = os.getenv("PG_HOST", "iot-postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB   = os.getenv("PG_DB", "iotcloud")
PG_USER = os.getenv("PG_USER", "iot")
PG_PASS = os.getenv("PG_PASS", "iot_dev")
DATABASE_URL = os.getenv("DATABASE_URL")
PG_POOL_MIN = int(os.getenv("PG_POOL_MIN", "2"))
PG_POOL_MAX = int(os.getenv("PG_POOL_MAX", "10"))

AUTO_PROVISION = os.getenv("AUTO_PROVISION", "0") == "1"
REQUIRE_TOKEN  = os.getenv("REQUIRE_TOKEN", "1") == "1"
CERT_AUTH_ENABLED = os.getenv("CERT_AUTH_ENABLED", "0") == "1"

COUNTERS_ENABLED = os.getenv("COUNTERS_ENABLED", "1") == "1"
SETTINGS_POLL_SECONDS = int(os.getenv("SETTINGS_POLL_SECONDS", "5"))
LOG_STATS_EVERY_SECONDS = int(os.getenv("LOG_STATS_EVERY_SECONDS", "30"))
AUTH_CACHE_TTL = int(os.getenv("AUTH_CACHE_TTL_SECONDS", "60"))
AUTH_CACHE_MAX_SIZE = int(os.getenv("AUTH_CACHE_MAX_SIZE", "10000"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "500"))
FLUSH_INTERVAL_MS = int(os.getenv("FLUSH_INTERVAL_MS", "1000"))
INGEST_WORKER_COUNT = int(os.getenv("INGEST_WORKER_COUNT", "4"))
BUCKET_TTL_SECONDS = int(os.getenv("BUCKET_TTL_SECONDS", "3600"))
BUCKET_CLEANUP_INTERVAL = int(os.getenv("BUCKET_CLEANUP_INTERVAL", "300"))

COUNTERS = {
    "messages_received": 0,
    "messages_written": 0,
    "messages_rejected": 0,
    "nats_telemetry_pending": 0,
    "nats_shadow_pending": 0,
    "nats_commands_pending": 0,
    "last_write_at": None,
}
INGESTOR_REF: Optional["Ingestor"] = None
logger = logging.getLogger(__name__)
configure_logging("ingest")
logger = logging.getLogger("ingest")

def utcnow():
    return datetime.now(timezone.utc)


def _counter_inc(key: str, delta: int = 1) -> None:
    if not COUNTERS_ENABLED:
        return
    COUNTERS[key] += delta


def _as_json_dict(value) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _infer_sensor_type(metric_name: str) -> str:
    """Infer sensor type from metric name using common patterns."""
    name = metric_name.lower()
    if "temp" in name:
        return "temperature"
    if "humid" in name:
        return "humidity"
    if "press" in name:
        return "pressure"
    if "vibrat" in name:
        return "vibration"
    if "flow" in name:
        return "flow"
    if "level" in name:
        return "level"
    if "power" in name or "kw" in name or "watt" in name:
        return "power"
    if "volt" in name:
        return "electrical"
    if "current" in name or "amp" in name:
        return "electrical"
    if "battery" in name or "batt" in name:
        return "battery"
    if "speed" in name or "rpm" in name:
        return "speed"
    if "weight" in name or "mass" in name or "load" in name:
        return "weight"
    if "ph" == name or name.startswith("ph_"):
        return "chemical"
    if "co2" in name or "gas" in name or "air" in name:
        return "air_quality"
    return "unknown"


def _infer_unit(metric_name: str, sensor_type: str) -> str | None:
    """Infer measurement unit from metric name and type."""
    name = metric_name.lower()
    unit_hints = {
        "temperature": "°C",
        "humidity": "%RH",
        "pressure": "hPa",
        "vibration": "mm/s",
        "flow": "L/min",
        "level": "%",
        "battery": "%",
    }
    if "pct" in name or "percent" in name:
        return "%"
    if "celsius" in name or "_c" in name:
        return "°C"
    if "fahrenheit" in name or "_f" in name:
        return "°F"
    if "_kw" in name or name.endswith("_kw"):
        return "kW"
    if "volt" in name:
        return "V"
    if "amp" in name or "current" in name:
        return "A"
    return unit_hints.get(sensor_type)


def _humanize_metric_name(metric_name: str) -> str:
    """Convert snake_case metric name to human-readable label."""
    return metric_name.replace("_", " ").title()


DEVICE_ALLOWED_TRANSITIONS = {
    "QUEUED": {"IN_PROGRESS"},
    "IN_PROGRESS": {"SUCCEEDED", "FAILED", "REJECTED"},
}
TERMINAL_STATUSES = {"SUCCEEDED", "FAILED", "TIMED_OUT", "REJECTED"}


async def health_handler(request):
    """Health check endpoint with metrics."""
    if INGESTOR_REF is not None:
        COUNTERS["messages_received"] = INGESTOR_REF.msg_received
        COUNTERS["messages_rejected"] = INGESTOR_REF.msg_dropped
        COUNTERS["nats_telemetry_pending"] = getattr(INGESTOR_REF, "_nats_pending_telemetry", 0)
        COUNTERS["nats_shadow_pending"] = getattr(INGESTOR_REF, "_nats_pending_shadow", 0)
        COUNTERS["nats_commands_pending"] = getattr(INGESTOR_REF, "_nats_pending_commands", 0)
        ingest_queue_depth.set(COUNTERS["nats_telemetry_pending"])
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
                "nats_telemetry_pending": COUNTERS["nats_telemetry_pending"],
                "nats_shadow_pending": COUNTERS["nats_shadow_pending"],
                "nats_commands_pending": COUNTERS["nats_commands_pending"],
            },
            "last_write_at": COUNTERS["last_write_at"],
        }
    )


async def metrics_handler(_request):
    return web.Response(body=generate_latest(), content_type=CONTENT_TYPE_LATEST.split(";")[0])


async def _resolve_device_by_token(token: str, pool: asyncpg.Pool) -> tuple[str, str]:
    token_hash = sha256_hex(token)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT tenant_id, device_id
            FROM device_registry
            WHERE provision_token_hash = $1
              AND status != 'REVOKED'
            LIMIT 1
            """,
            token_hash,
        )
    if row is None:
        raise web.HTTPUnauthorized(
            text=json.dumps({"detail": "Invalid provision token"}),
            content_type="application/json",
        )
    return row["tenant_id"], row["device_id"]


async def device_get_shadow(request: web.Request):
    if INGESTOR_REF is None or INGESTOR_REF.pool is None:
        raise web.HTTPServiceUnavailable(text="ingestor unavailable")
    token = request.headers.get("X-Provision-Token")
    if not token:
        raise web.HTTPUnauthorized(
            text=json.dumps({"detail": "Missing provision token"}),
            content_type="application/json",
        )
    tenant_id, device_id = await _resolve_device_by_token(token, INGESTOR_REF.pool)

    async with INGESTOR_REF.pool.acquire() as conn:
        await _set_tenant_write_context(conn, tenant_id)
        row = await conn.fetchrow(
            """
            SELECT desired_state, desired_version
            FROM device_state
            WHERE tenant_id = $1 AND device_id = $2
            """,
            tenant_id,
            device_id,
        )
    if row is None:
        raise web.HTTPNotFound(
            text=json.dumps({"detail": "Device not found"}),
            content_type="application/json",
        )

    return web.json_response(
        {
            "desired": _as_json_dict(row["desired_state"]),
            "version": row["desired_version"],
        }
    )


async def device_report_shadow(request: web.Request):
    if INGESTOR_REF is None or INGESTOR_REF.pool is None:
        raise web.HTTPServiceUnavailable(text="ingestor unavailable")
    token = request.headers.get("X-Provision-Token")
    if not token:
        raise web.HTTPUnauthorized(
            text=json.dumps({"detail": "Missing provision token"}),
            content_type="application/json",
        )
    tenant_id, device_id = await _resolve_device_by_token(token, INGESTOR_REF.pool)

    try:
        body = await request.json()
    except Exception:
        raise web.HTTPBadRequest(
            text=json.dumps({"detail": "Invalid JSON body"}),
            content_type="application/json",
        )
    reported = body.get("reported", {})
    version = body.get("version")
    if not isinstance(reported, dict) or not isinstance(version, int):
        raise web.HTTPBadRequest(
            text=json.dumps({"detail": "Payload must include reported object and version integer"}),
            content_type="application/json",
        )

    async with INGESTOR_REF.pool.acquire() as conn:
        await _set_tenant_write_context(conn, tenant_id)
        await conn.execute(
            """
            UPDATE device_state
            SET reported_state = $1::jsonb,
                reported_version = GREATEST(reported_version, $2),
                last_seen_at = NOW()
            WHERE tenant_id = $3 AND device_id = $4
            """,
            json.dumps(reported),
            version,
            tenant_id,
            device_id,
        )

    return web.json_response({"accepted": True, "version": version})


async def device_get_pending_jobs(request: web.Request):
    if INGESTOR_REF is None or INGESTOR_REF.pool is None:
        raise web.HTTPServiceUnavailable(text="ingestor unavailable")
    token = request.headers.get("X-Provision-Token")
    if not token:
        raise web.HTTPUnauthorized(
            text=json.dumps({"detail": "Missing provision token"}),
            content_type="application/json",
        )
    tenant_id, device_id = await _resolve_device_by_token(token, INGESTOR_REF.pool)

    async with INGESTOR_REF.pool.acquire() as conn:
        await _set_tenant_write_context(conn, tenant_id)
        rows = await conn.fetch(
            """
            SELECT
                e.job_id,
                e.execution_number,
                e.queued_at,
                j.document_type,
                j.document_params,
                j.expires_at
            FROM job_executions e
            JOIN jobs j USING (tenant_id, job_id)
            WHERE e.tenant_id = $1
              AND e.device_id = $2
              AND e.status = 'QUEUED'
              AND (j.expires_at IS NULL OR j.expires_at > NOW())
            ORDER BY e.queued_at ASC
            LIMIT 10
            """,
            tenant_id,
            device_id,
        )
    return web.json_response(
        {
            "jobs": [
                {
                    "job_id": r["job_id"],
                    "execution_number": r["execution_number"],
                    "document": {
                        "type": r["document_type"],
                        "params": _as_json_dict(r["document_params"]),
                    },
                    "queued_at": r["queued_at"].isoformat(),
                    "expires_at": r["expires_at"].isoformat() if r["expires_at"] else None,
                }
                for r in rows
            ]
        }
    )


async def device_get_pending_commands(request: web.Request):
    if INGESTOR_REF is None or INGESTOR_REF.pool is None:
        raise web.HTTPServiceUnavailable(text="ingestor unavailable")
    token = request.headers.get("X-Provision-Token")
    if not token:
        raise web.HTTPUnauthorized(
            text=json.dumps({"detail": "Missing provision token"}),
            content_type="application/json",
        )
    tenant_id, device_id = await _resolve_device_by_token(token, INGESTOR_REF.pool)

    async with INGESTOR_REF.pool.acquire() as conn:
        async with conn.transaction():
            await _set_tenant_write_context(conn, tenant_id)
            rows = await conn.fetch(
                """
                SELECT command_id, command_type, command_params, expires_at, created_at
                FROM device_commands
                WHERE tenant_id = $1
                  AND device_id = $2
                  AND status = 'queued'
                  AND expires_at > NOW()
                ORDER BY created_at ASC
                LIMIT 20
                """,
                tenant_id,
                device_id,
            )

    return web.json_response(
        {
            "commands": [
                {
                    "command_id": row["command_id"],
                    "type": row["command_type"],
                    "params": _as_json_dict(row["command_params"]),
                    "expires_at": row["expires_at"].isoformat(),
                }
                for row in rows
            ]
        }
    )


async def device_ack_command(request: web.Request):
    if INGESTOR_REF is None or INGESTOR_REF.pool is None:
        raise web.HTTPServiceUnavailable(text="ingestor unavailable")
    token = request.headers.get("X-Provision-Token")
    if not token:
        raise web.HTTPUnauthorized(
            text=json.dumps({"detail": "Missing provision token"}),
            content_type="application/json",
        )
    tenant_id, device_id = await _resolve_device_by_token(token, INGESTOR_REF.pool)
    command_id = request.match_info.get("command_id")
    if not command_id:
        raise web.HTTPBadRequest(
            text=json.dumps({"detail": "Missing command_id"}),
            content_type="application/json",
        )
    try:
        body = await request.json()
    except Exception:
        raise web.HTTPBadRequest(
            text=json.dumps({"detail": "Invalid JSON body"}),
            content_type="application/json",
        )

    status = body.get("status", "ok")
    details = body.get("details")
    if details is not None and not isinstance(details, dict):
        raise web.HTTPBadRequest(
            text=json.dumps({"detail": "details must be an object"}),
            content_type="application/json",
        )

    async with INGESTOR_REF.pool.acquire() as conn:
        async with conn.transaction():
            await _set_tenant_write_context(conn, tenant_id)
            updated = await conn.execute(
                """
                UPDATE device_commands
                SET status = 'delivered',
                    acked_at = NOW(),
                    ack_details = $1::jsonb
                WHERE tenant_id = $2
                  AND command_id = $3
                  AND device_id = $4
                  AND status = 'queued'
                """,
                json.dumps({"status": status, "details": details}),
                tenant_id,
                command_id,
                device_id,
            )
    if updated == "UPDATE 0":
        raise web.HTTPNotFound(
            text=json.dumps({"detail": "Command not found or already acknowledged"}),
            content_type="application/json",
        )
    return web.json_response({"command_id": command_id, "acknowledged": True})


async def device_update_job_execution(request: web.Request):
    if INGESTOR_REF is None or INGESTOR_REF.pool is None:
        raise web.HTTPServiceUnavailable(text="ingestor unavailable")
    token = request.headers.get("X-Provision-Token")
    if not token:
        raise web.HTTPUnauthorized(
            text=json.dumps({"detail": "Missing provision token"}),
            content_type="application/json",
        )
    tenant_id, device_id = await _resolve_device_by_token(token, INGESTOR_REF.pool)
    job_id = request.match_info.get("job_id")
    if not job_id:
        raise web.HTTPBadRequest(
            text=json.dumps({"detail": "Missing job_id"}),
            content_type="application/json",
        )

    try:
        body = await request.json()
    except Exception:
        raise web.HTTPBadRequest(
            text=json.dumps({"detail": "Invalid JSON body"}),
            content_type="application/json",
        )
    new_status = body.get("status")
    status_details = body.get("status_details")
    execution_number = body.get("execution_number")

    if new_status not in ("IN_PROGRESS", "SUCCEEDED", "FAILED", "REJECTED"):
        raise web.HTTPBadRequest(
            text=json.dumps({"detail": f"Invalid status: {new_status}"}),
            content_type="application/json",
        )
    if status_details is not None and not isinstance(status_details, dict):
        raise web.HTTPBadRequest(
            text=json.dumps({"detail": "status_details must be an object"}),
            content_type="application/json",
        )
    if execution_number is not None and not isinstance(execution_number, int):
        raise web.HTTPBadRequest(
            text=json.dumps({"detail": "execution_number must be an integer"}),
            content_type="application/json",
        )

    async with INGESTOR_REF.pool.acquire() as conn:
        await _set_tenant_write_context(conn, tenant_id)
        execution = await conn.fetchrow(
            """
            SELECT status, execution_number
            FROM job_executions
            WHERE tenant_id=$1 AND job_id=$2 AND device_id=$3
            """,
            tenant_id,
            job_id,
            device_id,
        )
        if not execution:
            raise web.HTTPNotFound(
                text=json.dumps({"detail": "Job execution not found"}),
                content_type="application/json",
            )
        current_status = execution["status"]
        allowed = DEVICE_ALLOWED_TRANSITIONS.get(current_status, set())
        if new_status not in allowed:
            raise web.HTTPBadRequest(
                text=json.dumps({"detail": f"Cannot transition from {current_status} to {new_status}"}),
                content_type="application/json",
            )
        if execution_number is not None and execution_number != execution["execution_number"]:
            raise web.HTTPConflict(
                text=json.dumps({"detail": "Execution number mismatch - stale update"}),
                content_type="application/json",
            )

        started_fragment = ", started_at = NOW()" if new_status == "IN_PROGRESS" else ""
        await conn.execute(
            f"""
            UPDATE job_executions
            SET status = $1,
                status_details = $2::jsonb,
                execution_number = execution_number + 1,
                last_updated_at = NOW()
                {started_fragment}
            WHERE tenant_id=$3 AND job_id=$4 AND device_id=$5
            """,
            new_status,
            json.dumps(status_details) if status_details is not None else None,
            tenant_id,
            job_id,
            device_id,
        )

        if new_status in TERMINAL_STATUSES:
            remaining = await conn.fetchval(
                """
                SELECT COUNT(*) FROM job_executions
                WHERE tenant_id=$1 AND job_id=$2
                  AND status NOT IN ('SUCCEEDED','FAILED','TIMED_OUT','REJECTED')
                """,
                tenant_id,
                job_id,
            )
            if remaining == 0:
                await conn.execute(
                    "UPDATE jobs SET status='COMPLETED', updated_at=NOW() WHERE tenant_id=$1 AND job_id=$2",
                    tenant_id,
                    job_id,
                )
    return web.json_response({"job_id": job_id, "device_id": device_id, "status": new_status})


async def device_get_job_execution(request: web.Request):
    if INGESTOR_REF is None or INGESTOR_REF.pool is None:
        raise web.HTTPServiceUnavailable(text="ingestor unavailable")
    token = request.headers.get("X-Provision-Token")
    if not token:
        raise web.HTTPUnauthorized(
            text=json.dumps({"detail": "Missing provision token"}),
            content_type="application/json",
        )
    tenant_id, device_id = await _resolve_device_by_token(token, INGESTOR_REF.pool)
    job_id = request.match_info.get("job_id")
    if not job_id:
        raise web.HTTPBadRequest(
            text=json.dumps({"detail": "Missing job_id"}),
            content_type="application/json",
        )
    async with INGESTOR_REF.pool.acquire() as conn:
        await _set_tenant_write_context(conn, tenant_id)
        row = await conn.fetchrow(
            """
            SELECT
                e.status, e.status_details, e.execution_number,
                e.queued_at, e.started_at, e.last_updated_at,
                j.document_type, j.document_params, j.expires_at
            FROM job_executions e
            JOIN jobs j USING (tenant_id, job_id)
            WHERE e.tenant_id=$1 AND e.job_id=$2 AND e.device_id=$3
            """,
            tenant_id,
            job_id,
            device_id,
        )
    if not row:
        raise web.HTTPNotFound(
            text=json.dumps({"detail": "Execution not found"}),
            content_type="application/json",
        )
    return web.json_response(
        {
            "job_id": job_id,
            "device_id": device_id,
            "status": row["status"],
            "status_details": _as_json_dict(row["status_details"]) if row["status_details"] is not None else None,
            "execution_number": row["execution_number"],
            "document": {
                "type": row["document_type"],
                "params": _as_json_dict(row["document_params"]),
            },
            "queued_at": row["queued_at"].isoformat(),
            "started_at": row["started_at"].isoformat() if row["started_at"] else None,
            "expires_at": row["expires_at"].isoformat() if row["expires_at"] else None,
        }
    )


async def start_health_server():
    app = web.Application()
    app.router.add_get("/health", health_handler)
    app.router.add_get("/metrics", metrics_handler)
    app.router.add_get("/device/v1/shadow", device_get_shadow)
    app.router.add_post("/device/v1/shadow/reported", device_report_shadow)
    app.router.add_get("/device/v1/commands/pending", device_get_pending_commands)
    app.router.add_post("/device/v1/commands/{command_id}/ack", device_ack_command)
    app.router.add_get("/device/v1/jobs/pending", device_get_pending_jobs)
    app.router.add_put("/device/v1/jobs/{job_id}/execution", device_update_job_execution)
    app.router.add_get("/device/v1/jobs/{job_id}/execution", device_get_job_execution)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    log_event(logger, "health server started", service_port=8080)

def topic_extract(topic: str):
    parts = topic.split("/")
    tenant_id = device_id = msg_type = None
    if len(parts) >= 5 and parts[0] == "tenant" and parts[2] == "device":
        tenant_id = parts[1]
        device_id = parts[3]
        msg_type = parts[4]
    return tenant_id, device_id, msg_type

class DeviceSubscriptionCache:
    """Cache device subscription status to avoid DB lookups on every message."""

    def __init__(self, ttl_seconds: int = 60, max_size: int = 50000):
        self.ttl = ttl_seconds
        self.max_size = max_size
        self._cache: dict[tuple[str, str], dict] = {}
        self._lock = asyncio.Lock()

    async def get(self, tenant_id: str, device_id: str) -> dict | None:
        key = (tenant_id, device_id)
        entry = self._cache.get(key)
        if entry and time.time() < entry["expires_at"]:
            return entry
        return None

    async def put(
        self,
        tenant_id: str,
        device_id: str,
        subscription_id: str | None,
        status: str | None,
    ) -> None:
        key = (tenant_id, device_id)
        async with self._lock:
            if len(self._cache) >= self.max_size:
                now = time.time()
                self._cache = {k: v for k, v in self._cache.items() if v["expires_at"] > now}
            self._cache[key] = {
                "subscription_id": subscription_id,
                "status": status,
                "expires_at": time.time() + self.ttl,
            }

    def invalidate(self, tenant_id: str, device_id: str) -> None:
        self._cache.pop((tenant_id, device_id), None)

    def invalidate_subscription(self, subscription_id: str) -> None:
        to_remove = [
            k for k, v in list(self._cache.items())
            if v.get("subscription_id") == subscription_id
        ]
        for key in to_remove:
            self._cache.pop(key, None)


class CertificateAuthCache:
    """Cache certificate authentication status to avoid DB lookups on every message."""

    def __init__(self, ttl_seconds: int = 300, max_size: int = 50000):
        self.ttl = ttl_seconds
        self.max_size = max_size
        self._cache: dict[str, dict] = {}  # key = "tenant_id/device_id"
        self._lock = asyncio.Lock()

    async def get(self, cn: str) -> dict | None:
        entry = self._cache.get(cn)
        if entry and time.time() < entry["expires_at"]:
            return entry
        return None

    async def put(self, cn: str, has_active_cert: bool) -> None:
        async with self._lock:
            if len(self._cache) >= self.max_size:
                now = time.time()
                self._cache = {k: v for k, v in self._cache.items() if v["expires_at"] > now}
            self._cache[cn] = {
                "has_active_cert": has_active_cert,
                "expires_at": time.time() + self.ttl,
            }

    def invalidate(self, cn: str) -> None:
        self._cache.pop(cn, None)


async def auto_provision_device(
    conn: asyncpg.Connection,
    tenant_id: str,
    device_id: str,
    site_id: str | None,
) -> bool:
    lock_key = hash(f"{tenant_id}:{device_id}") & 0x7FFFFFFF
    await conn.execute("SELECT pg_advisory_xact_lock($1)", lock_key)

    existing = await conn.fetchval(
        "SELECT 1 FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
        tenant_id,
        device_id,
    )
    if existing:
        return True

    sub = await conn.fetchrow(
        """
        SELECT subscription_id, device_limit, active_device_count
        FROM subscriptions
        WHERE tenant_id = $1
          AND status = 'ACTIVE'
          AND subscription_type = 'MAIN'
        ORDER BY created_at
        FOR UPDATE
        LIMIT 1
        """,
        tenant_id,
    )
    if not sub:
        return False
    if sub["active_device_count"] >= sub["device_limit"]:
        return False

    await conn.execute(
        """
        INSERT INTO device_registry (tenant_id, device_id, site_id, subscription_id, status)
        VALUES ($1, $2, $3, $4, 'ACTIVE')
        """,
        tenant_id,
        device_id,
        site_id,
        sub["subscription_id"],
    )
    await conn.execute(
        """
        UPDATE subscriptions
        SET active_device_count = active_device_count + 1, updated_at = now()
        WHERE subscription_id = $1
        """,
        sub["subscription_id"],
    )
    return True


async def _set_tenant_write_context(conn: asyncpg.Connection, tenant_id: str | None) -> None:
    """
    Set DB role + tenant context for write operations.
    """
    await conn.execute("SET LOCAL ROLE pulse_app")
    await conn.execute(
        "SELECT set_config('app.tenant_id', $1, true)",
        str(tenant_id or "__unknown__"),
    )


class Ingestor:
    def __init__(self):
        self.pool: asyncpg.Pool | None = None
        self._nc = None        # NATS connection
        self._js = None        # JetStream context
        self._telemetry_sub = None  # Pull subscription (TELEMETRY)
        self._shadow_sub = None     # Pull subscription (SHADOW)
        self._commands_sub = None   # Pull subscription (COMMANDS)
        self.loop: asyncio.AbstractEventLoop | None = None
        self._workers = []
        self._shutting_down = False
        self._nats_pending_telemetry = 0
        self._nats_pending_shadow = 0
        self._nats_pending_commands = 0

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
        self._last_bucket_cleanup = 0.0
        self.auth_cache = DeviceAuthCache(ttl_seconds=AUTH_CACHE_TTL, max_size=AUTH_CACHE_MAX_SIZE)
        self.device_subscription_cache = DeviceSubscriptionCache(ttl_seconds=60, max_size=50000)
        self.cert_auth_cache = CertificateAuthCache(ttl_seconds=300, max_size=50000)
        self.batch_writer: TimescaleBatchWriter | None = None
        self._message_routes_cache: dict[str, list] = {}  # tenant_id -> [route_rows]
        self._routes_cache_ts: dict[str, float] = {}  # tenant_id -> last_refresh_time
        self._routes_cache_ttl = 30  # seconds
        # Sensor auto-discovery cache: set of (tenant_id, device_id, metric_name) tuples
        # that are known to exist. Avoids DB lookup on every telemetry message.
        self._known_sensors: set[tuple[str, str, str]] = set()

    async def _ensure_sensors(self, tenant_id: str, device_id: str, metrics: dict, ts):
        """Auto-discover sensors from telemetry metric keys.

        For each metric key in the payload, ensure a sensor record exists.
        Uses an in-memory cache to avoid DB hits on known sensors.
        Respects the device's sensor_limit.
        """
        if not metrics:
            return

        new_keys: list[str] = []
        for key in metrics:
            if (tenant_id, device_id, key) not in self._known_sensors:
                new_keys.append(key)

        if not new_keys:
            # All metric keys are already known — just update last_value/last_seen
            try:
                assert self.pool is not None
                async with self.pool.acquire() as conn:
                    async with conn.transaction():
                        await _set_tenant_write_context(conn, tenant_id)
                        for key in metrics:
                            value = metrics[key]
                            if isinstance(value, (int, float)):
                                await conn.execute(
                                    """
                                    UPDATE sensors
                                    SET last_value = $1, last_seen_at = $2, updated_at = now()
                                    WHERE tenant_id = $3 AND device_id = $4 AND metric_name = $5
                                    """,
                                    float(value),
                                    ts,
                                    tenant_id,
                                    device_id,
                                    key,
                                )
            except Exception as e:
                logger.debug("sensor_last_value_update_failed: %s", e)
            return

        # Some new keys found — check DB for existing sensors and auto-create missing ones
        try:
            assert self.pool is not None
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    await _set_tenant_write_context(conn, tenant_id)

                    # Fetch all existing sensors for this device
                    existing = await conn.fetch(
                        "SELECT metric_name FROM sensors WHERE tenant_id = $1 AND device_id = $2",
                        tenant_id,
                        device_id,
                    )
                    existing_names = {row["metric_name"] for row in existing}

                    # Cache all existing
                    for name in existing_names:
                        self._known_sensors.add((tenant_id, device_id, name))

                    # Find truly new metric keys
                    to_create = [k for k in new_keys if k not in existing_names]

                    if to_create:
                        # Check sensor limit
                        limit_row = await conn.fetchrow(
                            """
                            SELECT dr.sensor_limit, dt.default_sensor_limit
                            FROM device_registry dr
                            LEFT JOIN device_tiers dt ON dt.tier_id = dr.tier_id
                            WHERE dr.tenant_id = $1 AND dr.device_id = $2
                            """,
                            tenant_id,
                            device_id,
                        )
                        effective_limit = 20
                        if limit_row:
                            effective_limit = (
                                limit_row["sensor_limit"] or limit_row["default_sensor_limit"] or 20
                            )

                        current_count = len(existing_names)
                        available_slots = max(0, effective_limit - current_count)

                        if available_slots == 0:
                            logger.warning(
                                "sensor_limit_reached",
                                extra={
                                    "tenant_id": tenant_id,
                                    "device_id": device_id,
                                    "limit": effective_limit,
                                    "new_keys": to_create,
                                },
                            )
                        else:
                            # Create sensors up to the available slots
                            for key in to_create[:available_slots]:
                                sensor_type = _infer_sensor_type(key)
                                unit = _infer_unit(key, sensor_type)
                                value = metrics.get(key)
                                numeric_value = (
                                    float(value) if isinstance(value, (int, float)) else None
                                )

                                await conn.execute(
                                    """
                                    INSERT INTO sensors (
                                        tenant_id, device_id, metric_name, sensor_type,
                                        label, unit, auto_discovered, last_value, last_seen_at, status
                                    ) VALUES ($1, $2, $3, $4, $5, $6, true, $7, $8, 'active')
                                    ON CONFLICT (tenant_id, device_id, metric_name) DO NOTHING
                                    """,
                                    tenant_id,
                                    device_id,
                                    key,
                                    sensor_type,
                                    _humanize_metric_name(key),
                                    unit,
                                    numeric_value,
                                    ts,
                                )
                                self._known_sensors.add((tenant_id, device_id, key))
                                logger.info(
                                    "sensor_auto_discovered",
                                    extra={
                                        "tenant_id": tenant_id,
                                        "device_id": device_id,
                                        "metric_name": key,
                                        "sensor_type": sensor_type,
                                    },
                                )

                            if len(to_create) > available_slots:
                                logger.warning(
                                    "sensor_limit_partial",
                                    extra={
                                        "tenant_id": tenant_id,
                                        "device_id": device_id,
                                        "created": available_slots,
                                        "skipped": to_create[available_slots:],
                                    },
                                )

                    # Update last_value for all known sensors
                    for key in metrics:
                        value = metrics[key]
                        if isinstance(value, (int, float)):
                            await conn.execute(
                                """
                                UPDATE sensors
                                SET last_value = $1, last_seen_at = $2, updated_at = now()
                                WHERE tenant_id = $3 AND device_id = $4 AND metric_name = $5
                                """,
                                float(value),
                                ts,
                                tenant_id,
                                device_id,
                                key,
                            )

        except Exception as e:
            # Sensor auto-discovery failure should NOT block telemetry ingestion
            logger.warning("sensor_autodiscovery_failed: %s", e)

    async def _get_device_subscription_status(
        self,
        tenant_id: str,
        device_id: str,
    ) -> tuple[str | None, str | None]:
        """
        Get device's subscription status.
        Returns: (subscription_id, status)
        Returns (None, None) if device has no subscription (legacy or unassigned).
        """
        cached = await self.device_subscription_cache.get(tenant_id, device_id)
        if cached:
            return cached["subscription_id"], cached["status"]

        assert self.pool is not None
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT d.subscription_id, s.status
                FROM device_registry d
                LEFT JOIN subscriptions s ON d.subscription_id = s.subscription_id
                WHERE d.tenant_id = $1 AND d.device_id = $2
                """,
                tenant_id,
                device_id,
            )

        if row:
            subscription_id = row["subscription_id"]
            status = row["status"]
        else:
            subscription_id = None
            status = None

        await self.device_subscription_cache.put(tenant_id, device_id, subscription_id, status)
        return subscription_id, status

    async def init_pool(self):
        for attempt in range(60):
            try:
                async def _init_db_connection(conn: asyncpg.Connection) -> None:
                    # Avoid passing statement_timeout as a startup parameter (PgBouncer rejects it).
                    await conn.execute("SET statement_timeout TO 30000")

                if DATABASE_URL:
                    self.pool = await asyncpg.create_pool(
                        dsn=DATABASE_URL,
                        min_size=PG_POOL_MIN,
                        max_size=PG_POOL_MAX,
                        command_timeout=30,
                        init=_init_db_connection,
                    )
                else:
                    self.pool = await asyncpg.create_pool(
                        host=PG_HOST, port=PG_PORT, database=PG_DB, user=PG_USER, password=PG_PASS,
                        min_size=PG_POOL_MIN,
                        max_size=PG_POOL_MAX,
                        command_timeout=30,
                        init=_init_db_connection,
                    )
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
            # Evict sensor cache periodically to prevent unbounded growth and pick up manual deletions.
            if self._known_sensors and len(self._known_sensors) > 10000:
                self._known_sensors.clear()
            cache_stats = self.auth_cache.stats()
            batch_stats = {
                "records_written": 0,
                "write_errors": 0,
                "batches_flushed": 0,
                "pending_records": 0,
            }
            if self.batch_writer is not None:
                batch_stats = self.batch_writer.get_stats()

            # Best-effort: update pending counts from JetStream consumer state.
            if self._js:
                try:
                    info = await self._js.consumer_info("TELEMETRY", "ingest-workers")
                    self._nats_pending_telemetry = getattr(info, "num_pending", 0)
                except Exception:
                    pass
                try:
                    info = await self._js.consumer_info("SHADOW", "ingest-shadow")
                    self._nats_pending_shadow = getattr(info, "num_pending", 0)
                except Exception:
                    pass
                try:
                    info = await self._js.consumer_info("COMMANDS", "ingest-commands")
                    self._nats_pending_commands = getattr(info, "num_pending", 0)
                except Exception:
                    pass

            ingest_queue_depth.set(self._nats_pending_telemetry)
            log_event(
                logger,
                "ingest stats",
                level="DEBUG",
                received=self.msg_received,
                enqueued=self.msg_enqueued,
                dropped=self.msg_dropped,
                nats_telemetry_pending=self._nats_pending_telemetry,
                nats_shadow_pending=self._nats_pending_shadow,
                nats_commands_pending=self._nats_pending_commands,
                mode=self.mode,
                store_rejects=int(self.store_rejects),
                mirror_rejects=int(self.mirror_rejects),
                max_payload_bytes=self.max_payload_bytes,
                rps=self.rps,
                burst=self.burst,
                auth_cache_hits=cache_stats["hits"],
                auth_cache_misses=cache_stats["misses"],
                auth_cache_size=cache_stats["size"],
                ts_written=batch_stats["records_written"],
                ts_errors=batch_stats["write_errors"],
                ts_flushes=batch_stats["batches_flushed"],
                ts_pending=batch_stats["pending_records"],
                workers=INGEST_WORKER_COUNT,
                nats_url=NATS_URL,
            )

    async def _inc_counter(self, tenant_id: str | None, reason: str):
        if not COUNTERS_ENABLED or not tenant_id:
            return
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await _set_tenant_write_context(conn, tenant_id)
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
        result = "rate_limited" if reason == "RATE_LIMITED" else "rejected"
        ingest_messages_total.labels(tenant_id=tenant_id or "unknown", result=result).inc()
        try:
            await self._inc_counter(tenant_id, reason)
        except Exception:
            # Counter writes must never break ingestion.
            logger.warning("quarantine_counter_write_failed", exc_info=True)
        log_event(
            logger,
            "message quarantined",
            level="WARNING",
            reason=reason,
            tenant_id=tenant_id,
            device_id=device_id,
            msg_type=msg_type,
        )

        audit = get_audit_logger()
        if audit and tenant_id:
            audit.device_rejected(
                tenant_id,
                device_id or "unknown",
                reason,
                {"site_id": site_id, "msg_type": msg_type},
            )

        # Only persist reject events when we know the tenant context; otherwise
        # RLS will reject the insert and break ingestion.
        if self.store_rejects and tenant_id:
            try:
                assert self.pool is not None
                async with self.pool.acquire() as conn:
                    async with conn.transaction():
                        await _set_tenant_write_context(conn, tenant_id)
                        await conn.execute(
                            """
                            INSERT INTO quarantine_events (event_ts, topic, tenant_id, site_id, device_id, msg_type, reason, payload, envelope_version)
                            VALUES ($1,$2,$3,$4,$5,$6,$7,$8::jsonb,$9)
                            """,
                            event_ts,
                            topic,
                            tenant_id,
                            site_id,
                            device_id,
                            msg_type,
                            reason,
                            json.dumps(payload),
                            str((payload or {}).get("version", "1")),
                        )
            except Exception:
                # Reject persistence is best-effort; do not fail processing.
                logger.warning("quarantine_event_store_failed", exc_info=True)

    def _rate_limit_ok(self, tenant_id: str, device_id: str) -> bool:
        now = time.time()
        if now - self._last_bucket_cleanup >= BUCKET_CLEANUP_INTERVAL:
            cutoff = now - BUCKET_TTL_SECONDS
            stale_keys = [
                key
                for key, bucket in list(self.buckets.items())
                if getattr(bucket, "last_access", getattr(bucket, "updated", 0.0)) < cutoff
            ]
            for key in stale_keys:
                self.buckets.pop(key, None)
            if stale_keys:
                logger.info("Cleaned up %s stale token buckets", len(stale_keys))
            self._last_bucket_cleanup = now

        # token bucket: refill at rps, cap at burst
        key = (tenant_id, device_id)
        b = self.buckets.get(key)
        if b is None:
            b = TokenBucket()
            b.tokens = self.burst
            b.updated = now
            b.last_access = now
            self.buckets[key] = b

        b.last_access = now
        elapsed = now - b.updated
        b.updated = now

        b.tokens = min(self.burst, b.tokens + elapsed * self.rps)
        if b.tokens >= 1.0:
            b.tokens -= 1.0
            return True
        return False

    async def _get_message_routes(self, tenant_id: str) -> list:
        """Get enabled message routes for a tenant (cached)."""
        now = time.time()
        last_refresh = self._routes_cache_ts.get(tenant_id, 0)
        if now - last_refresh < self._routes_cache_ttl:
            return self._message_routes_cache.get(tenant_id, [])

        assert self.pool is not None
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await _set_tenant_write_context(conn, tenant_id)
                rows = await conn.fetch(
                    """
                    SELECT id, topic_filter, destination_type, destination_config, payload_filter
                    FROM message_routes
                    WHERE tenant_id = $1 AND is_enabled = TRUE
                    """,
                    tenant_id,
                )
        routes = [dict(r) for r in rows]
        self._message_routes_cache[tenant_id] = routes
        self._routes_cache_ts[tenant_id] = now
        return routes

    async def _validate_cert_auth(self, mqtt_username: str, topic_tenant: str, topic_device: str) -> bool:
        """
        Validate a certificate-authenticated device.
        mqtt_username = cert CN = "{tenant_id}/{device_id}"
        Returns True if auth passes.
        """
        if not mqtt_username or "/" not in mqtt_username:
            return False

        parts = mqtt_username.split("/", 1)
        if len(parts) != 2:
            return False

        cert_tenant, cert_device = parts

        if cert_tenant != topic_tenant or cert_device != topic_device:
            return False

        cached = await self.cert_auth_cache.get(mqtt_username)
        if cached is not None:
            return bool(cached.get("has_active_cert"))

        assert self.pool is not None
        async with self.pool.acquire() as conn:
            has_cert = await conn.fetchval(
                """
                SELECT 1 FROM device_certificates
                WHERE tenant_id = $1
                  AND device_id = $2
                  AND status = 'ACTIVE'
                  AND not_after > now()
                LIMIT 1
                """,
                cert_tenant,
                cert_device,
            )

        result = has_cert is not None
        await self.cert_auth_cache.put(mqtt_username, result)
        return result

    async def init_nats(self):
        """Connect to NATS JetStream."""
        import nats

        self._nc = await nats.connect(NATS_URL)
        self._js = self._nc.jetstream()
        logger.info("nats_connected", extra={"url": NATS_URL})

    async def _process_telemetry(
        self,
        topic: str,
        payload: dict,
        tenant_id: str,
        device_id: str,
        msg_type: str,
        mqtt_username: str = "",
    ) -> None:
        """Process a single telemetry message through the validation pipeline."""
        try:
            event_ts = parse_ts(payload.get("ts"))

            site_id = payload.get("site_id") or None
            p_tenant = payload.get("tenant_id") or None

            # payload size guard (DoS hardening)
            try:
                payload_bytes = len(json.dumps(payload).encode("utf-8"))
            except Exception:
                payload_bytes = self.max_payload_bytes + 1
            if payload_bytes > self.max_payload_bytes:
                await self._insert_quarantine(
                    topic,
                    tenant_id or "unknown",
                    site_id,
                    device_id,
                    msg_type,
                    "PAYLOAD_TOO_LARGE",
                    payload,
                    event_ts,
                )
                return

            if tenant_id is None or device_id is None or msg_type is None:
                await self._insert_quarantine(
                    topic, None, site_id, None, None, "BAD_TOPIC_FORMAT", payload, event_ts
                )
                return

            if not self._rate_limit_ok(tenant_id, device_id):
                await self._insert_quarantine(
                    topic, tenant_id, site_id, device_id, msg_type, "RATE_LIMITED", payload, event_ts
                )
                return

            if p_tenant is not None and str(p_tenant) != str(tenant_id):
                await self._insert_quarantine(
                    topic,
                    tenant_id,
                    site_id,
                    device_id,
                    msg_type,
                    "TENANT_MISMATCH_TOPIC_VS_PAYLOAD",
                    payload,
                    event_ts,
                )
                return

            if site_id is None:
                await self._insert_quarantine(
                    topic, tenant_id, None, device_id, msg_type, "MISSING_SITE_ID", payload, event_ts
                )
                return

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
                        tenant_id,
                        device_id,
                    )

                    if reg is None:
                        if AUTO_PROVISION:
                            async with conn.transaction():
                                await _set_tenant_write_context(conn, tenant_id)
                                success = await auto_provision_device(
                                    conn,
                                    tenant_id,
                                    device_id,
                                    site_id,
                                )
                                if success:
                                    self.device_subscription_cache.invalidate(tenant_id, device_id)
                                    reg = await conn.fetchrow(
                                        """
                                        SELECT site_id, status, provision_token_hash
                                        FROM device_registry
                                        WHERE tenant_id=$1 AND device_id=$2
                                        """,
                                        tenant_id,
                                        device_id,
                                    )
                                else:
                                    await self._insert_quarantine(
                                        topic,
                                        tenant_id,
                                        site_id,
                                        device_id,
                                        msg_type,
                                        "NO_SUBSCRIPTION_CAPACITY",
                                        payload,
                                        event_ts,
                                    )
                                    return

                        if reg is None:
                            await self._insert_quarantine(
                                topic,
                                tenant_id,
                                site_id,
                                device_id,
                                msg_type,
                                "UNREGISTERED_DEVICE",
                                payload,
                                event_ts,
                            )
                            return

                self.auth_cache.put(
                    tenant_id,
                    device_id,
                    reg["provision_token_hash"],
                    reg["site_id"],
                    reg["status"],
                )

            subscription_id, sub_status = await self._get_device_subscription_status(tenant_id, device_id)
            if subscription_id and sub_status in ("SUSPENDED", "EXPIRED"):
                await self._insert_quarantine(
                    topic,
                    tenant_id,
                    site_id,
                    device_id,
                    msg_type,
                    f"SUBSCRIPTION_{sub_status}",
                    payload,
                    event_ts,
                )
                return

            if reg["status"] != "ACTIVE":
                await self._insert_quarantine(
                    topic, tenant_id, site_id, device_id, msg_type, "DEVICE_REVOKED", payload, event_ts
                )
                return

            if str(reg["site_id"]) != str(site_id):
                await self._insert_quarantine(
                    topic,
                    tenant_id,
                    site_id,
                    device_id,
                    msg_type,
                    "SITE_MISMATCH_REGISTRY_VS_PAYLOAD",
                    payload,
                    event_ts,
                )
                return

            device_authenticated = False

            # Certificate-based authentication (if enabled)
            if CERT_AUTH_ENABLED and not device_authenticated:
                cn = mqtt_username or f"{tenant_id}/{device_id}"
                has_active_cert = await self._validate_cert_auth(cn, tenant_id, device_id)
                if has_active_cert:
                    device_authenticated = True

            # Token-based authentication (fallback / legacy)
            if REQUIRE_TOKEN and not device_authenticated:
                expected = reg["provision_token_hash"]
                if expected is None:
                    await self._insert_quarantine(
                        topic,
                        tenant_id,
                        site_id,
                        device_id,
                        msg_type,
                        "TOKEN_NOT_SET_IN_REGISTRY",
                        payload,
                        event_ts,
                    )
                    return
                if token is None:
                    await self._insert_quarantine(
                        topic, tenant_id, site_id, device_id, msg_type, "TOKEN_MISSING", payload, event_ts
                    )
                    return
                if token_hash != expected:
                    await self._insert_quarantine(
                        topic, tenant_id, site_id, device_id, msg_type, "TOKEN_INVALID", payload, event_ts
                    )
                    return
                device_authenticated = True

            if REQUIRE_TOKEN and not device_authenticated:
                await self._insert_quarantine(
                    topic, tenant_id, site_id, device_id, msg_type, "AUTH_FAILED", payload, event_ts
                )
                return

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

            # Sensor auto-discovery
            await self._ensure_sensors(tenant_id, device_id, record.metrics, ts)

            # Message route fan-out (publish to NATS for async delivery)
            if self._nc:
                try:
                    routes = await self._get_message_routes(tenant_id)
                    for route in routes:
                        try:
                            if not mqtt_topic_matches(route["topic_filter"], topic):
                                continue
                            if route.get("payload_filter"):
                                pf = route["payload_filter"]
                                if isinstance(pf, str):
                                    pf = json.loads(pf)
                                if not evaluate_payload_filter(pf, payload):
                                    continue
                            if route["destination_type"] == "postgresql":
                                continue  # Already written

                            await self._nc.publish(
                                f"routes.{tenant_id}",
                                json.dumps(
                                    {
                                        "route": route,
                                        "topic": topic,
                                        "payload": payload,
                                        "tenant_id": tenant_id,
                                    },
                                    default=str,
                                ).encode(),
                            )
                        except Exception as route_match_exc:
                            logger.warning(
                                "route_match_error",
                                extra={"route_id": route.get("id"), "error": str(route_match_exc)},
                            )
                except Exception as route_fan_exc:
                    logger.warning("route_fanout_error", extra={"error": str(route_fan_exc)})

            ingest_messages_total.labels(tenant_id=tenant_id, result="accepted").inc()
            metrics = payload.get("metrics", {}) or {}
            log_event(
                logger,
                "telemetry accepted",
                tenant_id=tenant_id,
                device_id=device_id,
                msg_type=msg_type,
                metrics_count=len(metrics),
            )

            lat_value = payload.get("lat")
            if lat_value is None:
                lat_value = payload.get("latitude")
            lng_value = payload.get("lng")
            if lng_value is None:
                lng_value = payload.get("longitude")

            if lat_value is not None and lng_value is not None:
                try:
                    lat = float(lat_value)
                    lng = float(lng_value)
                except (TypeError, ValueError):
                    lat = None
                    lng = None
                if lat is not None and lng is not None:
                    assert self.pool is not None
                    async with self.pool.acquire() as conn:
                        async with conn.transaction():
                            await _set_tenant_write_context(conn, tenant_id)
                            await conn.execute(
                                """
                                UPDATE device_registry
                                SET latitude = $3,
                                    longitude = $4,
                                    location_source = COALESCE(location_source, 'auto')
                                WHERE tenant_id = $1 AND device_id = $2
                                  AND (location_source = 'auto' OR location_source IS NULL)
                                """,
                                tenant_id,
                                device_id,
                                lat,
                                lng,
                            )
            audit = get_audit_logger()
            if audit:
                audit.device_telemetry(
                    tenant_id,
                    device_id,
                    msg_type,
                    list(metrics.keys()),
                )

        except Exception as e:
            await self._insert_quarantine(
                topic,
                tenant_id,
                payload.get("site_id") if isinstance(payload, dict) else None,
                device_id,
                msg_type,
                f"INGEST_EXCEPTION:{type(e).__name__}",
                {"error": str(e), "payload": payload},
                None,
            )

    async def _nats_telemetry_worker(self, worker_id: int):
        """Pull messages from NATS TELEMETRY stream and process them."""
        logger.info("nats_worker_started", extra={"worker_id": worker_id})
        while not self._shutting_down:
            try:
                msgs = await self._telemetry_sub.fetch(batch=50, timeout=1.0)
            except Exception as fetch_err:
                if "timeout" in str(fetch_err).lower():
                    continue
                logger.warning("nats_fetch_error", extra={"error": str(fetch_err)})
                await asyncio.sleep(0.5)
                continue

            for msg in msgs:
                try:
                    self.msg_received += 1
                    envelope = json.loads(msg.data.decode())
                    topic = envelope.get("topic", "")
                    payload = envelope.get("payload", {}) or {}
                    mqtt_username = envelope.get("username", "") or ""
                    if isinstance(payload, str):
                        payload = json.loads(payload)

                    t_tenant, t_device, msg_type = topic_extract(topic)
                    if t_tenant is None or t_device is None or msg_type is None:
                        await self._insert_quarantine(
                            topic, None, None, None, None, "BAD_TOPIC_FORMAT", payload, None
                        )
                        await msg.ack()
                        continue

                    await self._process_telemetry(
                        topic, payload, t_tenant, t_device, msg_type, mqtt_username
                    )
                    await msg.ack()
                except Exception as proc_err:
                    logger.error(
                        "nats_process_error",
                        extra={"error": str(proc_err), "worker_id": worker_id},
                    )
                    await msg.nak()

    async def _nats_shadow_worker(self):
        """Process shadow/reported updates from NATS."""
        while not self._shutting_down:
            try:
                msgs = await self._shadow_sub.fetch(batch=20, timeout=1.0)
            except Exception:
                await asyncio.sleep(0.5)
                continue
            for msg in msgs:
                try:
                    envelope = json.loads(msg.data.decode())
                    topic = envelope.get("topic", "")
                    payload = envelope.get("payload", {}) or {}
                    if isinstance(payload, str):
                        payload = json.loads(payload)
                    await self.handle_shadow_reported(topic, payload)
                    await msg.ack()
                except Exception as e:
                    logger.error("shadow_process_error", extra={"error": str(e)})
                    await msg.nak()

    async def _nats_commands_worker(self):
        """Process command ack updates from NATS."""
        while not self._shutting_down:
            try:
                msgs = await self._commands_sub.fetch(batch=20, timeout=1.0)
            except Exception:
                await asyncio.sleep(0.5)
                continue
            for msg in msgs:
                try:
                    envelope = json.loads(msg.data.decode())
                    topic = envelope.get("topic", "")
                    payload = envelope.get("payload", {}) or {}
                    if isinstance(payload, str):
                        payload = json.loads(payload)
                    await self.handle_command_ack(topic, payload)
                    await msg.ack()
                except Exception as e:
                    logger.error("commands_process_error", extra={"error": str(e)})
                    await msg.nak()

    async def handle_shadow_reported(self, topic: str, payload: dict) -> None:
        trace_token = trace_id_var.set(str(uuid.uuid4()))
        try:
            parts = topic.split("/")
            if (
                len(parts) != 6
                or parts[0] != "tenant"
                or parts[2] != "device"
                or parts[4] != "shadow"
                or parts[5] != "reported"
            ):
                return
            if self.pool is None:
                return
            tenant_id = parts[1]
            device_id = parts[3]

            reported = payload.get("reported", {})
            version = payload.get("version", 0)
            if not isinstance(reported, dict):
                logger.warning("shadow_reported_invalid_payload", extra={"topic": topic})
                return
            if not isinstance(version, int):
                try:
                    version = int(version)
                except (TypeError, ValueError):
                    version = 0

            async with self.pool.acquire() as conn:
                await _set_tenant_write_context(conn, tenant_id)
                await conn.execute(
                    """
                    UPDATE device_state
                    SET reported_state = $1::jsonb,
                        reported_version = GREATEST(reported_version, $2),
                        last_seen_at = NOW()
                    WHERE tenant_id = $3 AND device_id = $4
                    """,
                    json.dumps(reported),
                    version,
                    tenant_id,
                    device_id,
                )
            logger.info(
                "shadow_reported_accepted",
                extra={"tenant_id": tenant_id, "device_id": device_id, "version": version},
            )
        finally:
            trace_id_var.reset(trace_token)

    async def handle_command_ack(self, topic: str, payload: dict) -> None:
        trace_token = trace_id_var.set(str(uuid.uuid4()))
        try:
            match = COMMAND_ACK_RE.match(topic)
            if not match:
                return
            if self.pool is None:
                return

            tenant_id = match.group("tenant_id")
            device_id = match.group("device_id")
            command_id = payload.get("command_id")
            if not command_id:
                logger.warning("command_ack_missing_id", extra={"topic": topic})
                return

            ack_status = payload.get("status", "ok")
            ack_details = payload.get("details")
            if ack_details is not None and not isinstance(ack_details, dict):
                logger.warning("command_ack_invalid_details", extra={"topic": topic})
                return

            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    await _set_tenant_write_context(conn, tenant_id)
                    updated = await conn.execute(
                        """
                        UPDATE device_commands
                        SET status = 'delivered',
                            acked_at = NOW(),
                            ack_details = $1::jsonb
                        WHERE tenant_id = $2
                          AND command_id = $3
                          AND device_id = $4
                          AND status = 'queued'
                        """,
                        json.dumps({"status": ack_status, "details": ack_details}),
                        tenant_id,
                        command_id,
                        device_id,
                    )
            logger.info(
                "command_acked",
                extra={
                    "tenant_id": tenant_id,
                    "device_id": device_id,
                    "command_id": command_id,
                    "ack_status": ack_status,
                    "db_updated": updated != "UPDATE 0",
                },
            )
        finally:
            trace_id_var.reset(trace_token)

    async def shutdown(self):
        """Graceful shutdown: stop workers, flush writes, close connections."""
        logger.info("shutdown_initiated")
        self._shutting_down = True

        # 1. Cancel worker tasks and wait for in-flight work to finish
        for task in self._workers:
            task.cancel()
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
            logger.info("workers_stopped")

        # 2. Flush the batch writer (critical: writes buffered telemetry)
        if self.batch_writer:
            await self.batch_writer.stop()
            logger.info(
                "batch_writer_flushed",
                extra={
                    "records_written": self.batch_writer.records_written,
                    "batches_flushed": self.batch_writer.batches_flushed,
                },
            )

        # 3. Close NATS connection
        if self._nc:
            try:
                await self._nc.drain()
            except Exception:
                pass
            logger.info("nats_connection_closed")

        # 4. Close DB pool
        if self.pool:
            await self.pool.close()
            logger.info("db_pool_closed")

        logger.info("shutdown_complete")

    async def run(self):
        await self.init_pool()
        await start_health_server()
        self.loop = asyncio.get_running_loop()
        assert self.pool is not None
        # SECURITY: telemetry batch writes may include multiple tenants per flush.
        # Tenant isolation is enforced before enqueue by topic_extract() + device auth cache
        # validation (tenant/device/token/site checks), so the writer accepts only validated rows.
        self.batch_writer = TimescaleBatchWriter(
            pool=self.pool,
            batch_size=BATCH_SIZE,
            flush_interval_ms=FLUSH_INTERVAL_MS,
        )
        await self.batch_writer.start()
        audit = init_audit_logger(self.pool, "ingest")
        await audit.start()

        asyncio.create_task(self.settings_worker())

        # Connect to NATS + JetStream and start consumer workers.
        await self.init_nats()
        self._telemetry_sub = await self._js.pull_subscribe(
            subject="telemetry.>",
            durable="ingest-workers",
            stream="TELEMETRY",
        )
        self._shadow_sub = await self._js.pull_subscribe(
            subject="shadow.>",
            durable="ingest-shadow",
            stream="SHADOW",
        )
        self._commands_sub = await self._js.pull_subscribe(
            subject="commands.>",
            durable="ingest-commands",
            stream="COMMANDS",
        )

        self._workers = []
        for i in range(INGEST_WORKER_COUNT):
            self._workers.append(asyncio.create_task(self._nats_telemetry_worker(i)))
        self._workers.append(asyncio.create_task(self._nats_shadow_worker()))
        self._workers.append(asyncio.create_task(self._nats_commands_worker()))

        asyncio.create_task(self.stats_worker())

        # Wait for shutdown signal
        shutdown_event = asyncio.Event()

        def _signal_handler():
            logger.info("signal_received")
            shutdown_event.set()

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, _signal_handler)

        await shutdown_event.wait()
        await self.shutdown()

async def main():
    ing = Ingestor()
    global INGESTOR_REF
    INGESTOR_REF = ing
    await ing.run()

if __name__ == "__main__":
    asyncio.run(main())
