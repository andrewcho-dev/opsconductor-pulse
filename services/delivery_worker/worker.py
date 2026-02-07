import asyncio
import json
import os
from aiohttp import web
import socket
import time
from datetime import datetime, timezone
from ipaddress import ip_address, ip_network
from urllib.parse import urlparse

import asyncpg
import httpx

from snmp_sender import send_alert_trap, SNMPTrapResult, PYSNMP_AVAILABLE
from email_sender import send_alert_email, EmailResult, AIOSMTPLIB_AVAILABLE
from mqtt_sender import publish_alert, MQTTResult, PAHO_MQTT_AVAILABLE

PG_HOST = os.getenv("PG_HOST", "iot-postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "iotcloud")
PG_USER = os.getenv("PG_USER", "iot")
PG_PASS = os.getenv("PG_PASS", "iot_dev")

MODE = os.getenv("MODE", "DEV").upper()
WORKER_POLL_SECONDS = int(os.getenv("WORKER_POLL_SECONDS", "2"))
WORKER_BATCH_SIZE = int(os.getenv("WORKER_BATCH_SIZE", "10"))
WORKER_TIMEOUT_SECONDS = int(os.getenv("WORKER_TIMEOUT_SECONDS", "30"))
WORKER_MAX_ATTEMPTS = int(os.getenv("WORKER_MAX_ATTEMPTS", "5"))
WORKER_BACKOFF_BASE_SECONDS = int(os.getenv("WORKER_BACKOFF_BASE_SECONDS", "30"))
WORKER_BACKOFF_MAX_SECONDS = int(os.getenv("WORKER_BACKOFF_MAX_SECONDS", "7200"))
STUCK_JOB_MINUTES = int(os.getenv("STUCK_JOB_MINUTES", "5"))

BLOCKED_NETWORKS = [
    ip_network("127.0.0.0/8"),
    ip_network("10.0.0.0/8"),
    ip_network("172.16.0.0/12"),
    ip_network("192.168.0.0/16"),
    ip_network("169.254.0.0/16"),
    ip_network("100.64.0.0/10"),
    ip_network("::1/128"),
]
BLOCKED_IPS = {ip_address("169.254.169.254")}

COUNTERS = {
    "jobs_processed": 0,
    "jobs_succeeded": 0,
    "jobs_failed": 0,
    "jobs_pending": 0,
    "last_delivery_at": None,
}

async def health_handler(request):
    return web.json_response(
        {
            "status": "healthy",
            "service": "delivery_worker",
            "counters": {
                "jobs_processed": COUNTERS["jobs_processed"],
                "jobs_succeeded": COUNTERS["jobs_succeeded"],
                "jobs_failed": COUNTERS["jobs_failed"],
                "jobs_pending": COUNTERS["jobs_pending"],
            },
            "last_delivery_at": COUNTERS["last_delivery_at"],
        }
    )


async def start_health_server():
    app = web.Application()
    app.router.add_get("/health", health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    print("[health] delivery worker health server started on port 8080")

def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def normalize_config_json(value) -> dict:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, (bytes, bytearray)):
        try:
            value = value.decode("utf-8")
        except Exception:
            return {}
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except Exception:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def normalize_snmp_config(value) -> dict:
    """Normalize snmp_config from various storage formats."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, (bytes, bytearray)):
        try:
            value = value.decode("utf-8")
        except Exception:
            return {}
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except Exception:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def normalize_email_config(value) -> dict:
    """Normalize email_config from various storage formats."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, (bytes, bytearray)):
        try:
            value = value.decode("utf-8")
        except Exception:
            return {}
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except Exception:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def normalize_mqtt_config(value) -> dict:
    """Normalize mqtt_config from various storage formats."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, (bytes, bytearray)):
        try:
            value = value.decode("utf-8")
        except Exception:
            return {}
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except Exception:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def is_blocked_ip(ip) -> bool:
    if ip in BLOCKED_IPS:
        return True
    if any(ip in net for net in BLOCKED_NETWORKS):
        return True
    if ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
        return True
    if ip.version == 6 and ip.is_site_local:
        return True
    if ip.is_private:
        return True
    return False


def validate_url(url: str) -> tuple[bool, str]:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.hostname:
        return False, "invalid_url"

    if MODE == "PROD" and parsed.scheme.lower() != "https":
        return False, "https_required"

    if MODE != "PROD":
        return True, "ok"

    try:
        addr_info = socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
    except Exception:
        return False, "dns_resolution_failed"

    for info in addr_info:
        ip = ip_address(info[4][0])
        if is_blocked_ip(ip):
            return False, f"blocked_ip:{ip}"

    return True, "ok"


def backoff_seconds(attempt_no: int) -> int:
    delay = WORKER_BACKOFF_BASE_SECONDS * (2 ** max(0, attempt_no - 1))
    return min(delay, WORKER_BACKOFF_MAX_SECONDS)


async def get_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(
        host=PG_HOST,
        port=PG_PORT,
        database=PG_DB,
        user=PG_USER,
        password=PG_PASS,
        min_size=1,
        max_size=5,
    )


async def requeue_stuck_jobs(conn: asyncpg.Connection) -> int:
    result = await conn.execute(
        """
        UPDATE delivery_jobs
        SET status='PENDING', next_run_at=now(), last_error='stuck_requeued', updated_at=now()
        WHERE status='PROCESSING'
          AND updated_at < (now() - ($1::int * interval '1 minute'))
        """,
        STUCK_JOB_MINUTES,
    )
    return int(result.split()[-1]) if result else 0


async def fetch_jobs(conn: asyncpg.Connection) -> list[asyncpg.Record]:
    async with conn.transaction():
        rows = await conn.fetch(
            """
            SELECT job_id, tenant_id, integration_id, payload_json, attempts
            FROM delivery_jobs
            WHERE status='PENDING' AND next_run_at <= now()
            ORDER BY next_run_at ASC, job_id ASC
            FOR UPDATE SKIP LOCKED
            LIMIT $1
            """,
            WORKER_BATCH_SIZE,
        )
        if not rows:
            return []

        job_ids = [r["job_id"] for r in rows]
        await conn.execute(
            """
            UPDATE delivery_jobs
            SET status='PROCESSING', updated_at=now()
            WHERE job_id = ANY($1::bigint[])
            """,
            job_ids,
        )
        return rows


async def fetch_integration(conn: asyncpg.Connection, tenant_id: str, integration_id) -> dict | None:
    row = await conn.fetchrow(
        """
        SELECT type, enabled, config_json,
               snmp_host, snmp_port, snmp_config, snmp_oid_prefix,
               email_config, email_recipients, email_template,
               mqtt_topic, mqtt_qos, mqtt_retain, mqtt_config
        FROM integrations
        WHERE tenant_id=$1 AND integration_id=$2
        """,
        tenant_id,
        integration_id,
    )
    if row is None:
        return None
    return dict(row)


async def record_attempt(
    conn: asyncpg.Connection,
    tenant_id: str,
    job_id: int,
    attempt_no: int,
    ok: bool,
    http_status: int | None,
    latency_ms: int,
    error: str | None,
    started_at: datetime,
    finished_at: datetime,
) -> None:
    await conn.execute(
        """
        INSERT INTO delivery_attempts (
          tenant_id, job_id, attempt_no, ok, http_status, latency_ms, error, started_at, finished_at
        )
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
        """,
        tenant_id,
        job_id,
        attempt_no,
        ok,
        http_status,
        latency_ms,
        error,
        started_at,
        finished_at,
    )


async def update_job_success(conn: asyncpg.Connection, job_id: int, attempt_no: int) -> None:
    await conn.execute(
        """
        UPDATE delivery_jobs
        SET status='COMPLETED', attempts=$2, last_error=NULL, updated_at=now()
        WHERE job_id=$1
        """,
        job_id,
        attempt_no,
    )


async def update_job_retry(conn: asyncpg.Connection, job_id: int, attempt_no: int, error: str) -> None:
    delay = backoff_seconds(attempt_no)
    await conn.execute(
        """
        UPDATE delivery_jobs
        SET status='PENDING', attempts=$2, next_run_at=now() + ($3::int * interval '1 second'), last_error=$4, updated_at=now()
        WHERE job_id=$1
        """,
        job_id,
        attempt_no,
        delay,
        error,
    )


async def update_job_failed(conn: asyncpg.Connection, job_id: int, attempt_no: int, error: str) -> None:
    await conn.execute(
        """
        UPDATE delivery_jobs
        SET status='FAILED', attempts=$2, last_error=$3, updated_at=now()
        WHERE job_id=$1
        """,
        job_id,
        attempt_no,
        error,
    )


async def process_job(conn: asyncpg.Connection, job: asyncpg.Record) -> None:
    COUNTERS["jobs_processed"] += 1
    job_id = job["job_id"]
    tenant_id = job["tenant_id"]
    integration_id = job["integration_id"]
    attempt_no = int(job["attempts"]) + 1

    started_at = now_utc()
    http_status = None
    error = None
    ok = False

    integration = await fetch_integration(conn, tenant_id, integration_id)
    if integration is None:
        error = "integration_not_found"
    elif not integration["enabled"]:
        error = "integration_disabled"
    else:
        integration_type = integration.get("type", "webhook")

        if integration_type == "snmp":
            ok, error = await deliver_snmp(integration, job)
        elif integration_type == "email":
            ok, error = await deliver_email(integration, job)
        elif integration_type == "mqtt":
            ok, error = await deliver_mqtt(integration, job)
        else:
            ok, http_status, error = await deliver_webhook(integration, job)

    finished_at = now_utc()
    latency_ms = int((finished_at - started_at).total_seconds() * 1000)
    COUNTERS["last_delivery_at"] = finished_at.isoformat()

    await record_attempt(
        conn,
        tenant_id,
        job_id,
        attempt_no,
        ok,
        http_status,
        latency_ms,
        error,
        started_at,
        finished_at,
    )

    if ok:
        COUNTERS["jobs_succeeded"] += 1
        await update_job_success(conn, job_id, attempt_no)
        return

    if attempt_no >= WORKER_MAX_ATTEMPTS:
        COUNTERS["jobs_failed"] += 1
        await update_job_failed(conn, job_id, attempt_no, error or "failed")
        return

    await update_job_retry(conn, job_id, attempt_no, error or "failed")


async def deliver_webhook(integration: dict, job: asyncpg.Record) -> tuple[bool, int | None, str | None]:
    """Deliver via webhook. Returns (ok, http_status, error)."""
    config = normalize_config_json(integration.get("config_json"))
    url = config.get("url")
    headers = config.get("headers") or {}

    if not url:
        return False, None, "missing_url"

    allowed, reason = validate_url(url)
    if not allowed:
        return False, None, f"url_blocked:{reason}"

    payload = job["payload_json"]
    if isinstance(payload, str):
        payload = json.loads(payload)

    try:
        timeout = httpx.Timeout(WORKER_TIMEOUT_SECONDS)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)
            http_status = resp.status_code
            ok = 200 <= resp.status_code < 300
            error = None if ok else f"http_{resp.status_code}"
            return ok, http_status, error
    except Exception as exc:
        return False, None, f"request_error:{type(exc).__name__}"


async def deliver_snmp(integration: dict, job: asyncpg.Record) -> tuple[bool, str | None]:
    """Deliver via SNMP trap. Returns (ok, error)."""
    if not PYSNMP_AVAILABLE:
        return False, "snmp_not_available"

    snmp_host = integration.get("snmp_host")
    snmp_port = integration.get("snmp_port") or 162
    snmp_config = normalize_snmp_config(integration.get("snmp_config"))
    oid_prefix = integration.get("snmp_oid_prefix") or "1.3.6.1.4.1.99999"

    if not snmp_host:
        return False, "missing_snmp_host"

    if not snmp_config:
        return False, "missing_snmp_config"

    payload = job["payload_json"]
    if isinstance(payload, str):
        payload = json.loads(payload)

    alert_id = str(payload.get("alert_id", "unknown"))
    device_id = payload.get("device_id", "unknown")
    tenant_id = job["tenant_id"]
    severity = str(payload.get("severity", "info"))
    message = payload.get("summary") or payload.get("message") or "Alert"

    ts_str = payload.get("created_at")
    if ts_str:
        try:
            timestamp = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except Exception:
            timestamp = now_utc()
    else:
        timestamp = now_utc()

    result = await send_alert_trap(
        host=snmp_host,
        port=snmp_port,
        config=snmp_config,
        alert_id=alert_id,
        device_id=device_id,
        tenant_id=tenant_id,
        severity=severity,
        message=message,
        timestamp=timestamp,
        oid_prefix=oid_prefix,
    )

    return result.success, result.error


async def deliver_email(integration: dict, job: asyncpg.Record) -> tuple[bool, str | None]:
    """Deliver via email. Returns (ok, error)."""
    if not AIOSMTPLIB_AVAILABLE:
        return False, "email_not_available"

    email_config = normalize_email_config(integration.get("email_config"))
    email_recipients = normalize_email_config(integration.get("email_recipients"))
    email_template = normalize_email_config(integration.get("email_template"))

    smtp_host = email_config.get("smtp_host")
    if not smtp_host:
        return False, "missing_smtp_host"

    if not email_recipients.get("to"):
        return False, "missing_recipients"

    payload = job["payload_json"]
    if isinstance(payload, str):
        payload = json.loads(payload)

    alert_id = str(payload.get("alert_id", "unknown"))
    device_id = payload.get("device_id", "unknown")
    tenant_id = job["tenant_id"]
    severity = str(payload.get("severity", "info"))
    message = payload.get("summary") or payload.get("message") or "Alert"
    alert_type = payload.get("alert_type", "ALERT")

    ts_str = payload.get("created_at")
    if ts_str:
        try:
            timestamp = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except Exception:
            timestamp = now_utc()
    else:
        timestamp = now_utc()

    result = await send_alert_email(
        smtp_host=smtp_host,
        smtp_port=email_config.get("smtp_port", 587),
        smtp_user=email_config.get("smtp_user"),
        smtp_password=email_config.get("smtp_password"),
        smtp_tls=email_config.get("smtp_tls", True),
        from_address=email_config.get("from_address", "alerts@example.com"),
        from_name=email_config.get("from_name", "OpsConductor Alerts"),
        recipients=email_recipients,
        alert_id=alert_id,
        device_id=device_id,
        tenant_id=tenant_id,
        severity=severity,
        message=message,
        alert_type=alert_type,
        timestamp=timestamp,
        subject_template=email_template.get("subject_template"),
        body_template=email_template.get("body_template"),
        body_format=email_template.get("format", "html"),
    )

    return result.success, result.error


async def deliver_mqtt(integration: dict, job: asyncpg.Record) -> tuple[bool, str | None]:
    """Deliver via MQTT. Returns (ok, error)."""
    if not PAHO_MQTT_AVAILABLE:
        return False, "paho_mqtt_not_available"

    mqtt_topic = integration.get("mqtt_topic")
    if not mqtt_topic:
        return False, "missing_mqtt_topic"

    mqtt_config = normalize_mqtt_config(integration.get("mqtt_config"))
    broker_url = mqtt_config.get("broker_url") or "mqtt://iot-mqtt:1883"
    mqtt_qos = integration.get("mqtt_qos") if integration.get("mqtt_qos") is not None else 1
    mqtt_retain = integration.get("mqtt_retain") if integration.get("mqtt_retain") is not None else False

    payload = job["payload_json"]
    if isinstance(payload, str):
        payload = json.loads(payload)

    resolved_topic = mqtt_topic
    replacements = {
        "tenant_id": payload.get("tenant_id"),
        "severity": payload.get("severity"),
        "site_id": payload.get("site_id"),
        "device_id": payload.get("device_id"),
        "alert_id": payload.get("alert_id"),
        "alert_type": payload.get("alert_type"),
    }
    for key, value in replacements.items():
        if value is not None:
            resolved_topic = resolved_topic.replace(f"{{{key}}}", str(value))

    payload_json = json.dumps(payload)
    result = await publish_alert(
        broker_url=broker_url,
        topic=resolved_topic,
        payload=payload_json,
        qos=mqtt_qos,
        retain=mqtt_retain,
    )

    return result.success, result.error


async def run_worker() -> None:
    pool = await get_pool()
    ssrf_strict = MODE == "PROD"
    await start_health_server()
    print(
        "[worker] startup mode={} ssrf_strict={} snmp_available={} email_available={} mqtt_available={}".format(
            MODE,
            ssrf_strict,
            PYSNMP_AVAILABLE,
            AIOSMTPLIB_AVAILABLE,
            PAHO_MQTT_AVAILABLE,
        )
    )

    while True:
        try:
            async with pool.acquire() as conn:
                stuck = await requeue_stuck_jobs(conn)
                if stuck:
                    print(f"[worker] requeued_stuck={stuck} ts={now_utc().isoformat()}")

                jobs = await fetch_jobs(conn)
                COUNTERS["jobs_pending"] = len(jobs)
                if not jobs:
                    await asyncio.sleep(WORKER_POLL_SECONDS)
                    continue

                for job in jobs:
                    await process_job(conn, job)
        except Exception as exc:
            print(f"[worker] error={type(exc).__name__} {exc}")
            await asyncio.sleep(WORKER_POLL_SECONDS)


if __name__ == "__main__":
    asyncio.run(run_worker())
