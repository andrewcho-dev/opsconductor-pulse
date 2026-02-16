import asyncio
import json
import os
import logging
import uuid
from aiohttp import web
import socket
import time
from datetime import datetime, timezone
from ipaddress import ip_address, ip_network, IPv4Address, IPv6Address
from urllib.parse import urlparse

import asyncpg
import httpx

from snmp_sender import send_alert_trap, SNMPTrapResult, PYSNMP_AVAILABLE
from email_sender import (
    send_alert_email,
    EmailResult,
    AIOSMTPLIB_AVAILABLE,
    render_template,
    severity_label_for,
)
from mqtt_sender import publish_alert, MQTTResult, PAHO_MQTT_AVAILABLE
from shared.audit import init_audit_logger, get_audit_logger
from shared.http_client import traced_client
from shared.logging import trace_id_var
from shared.logging import configure_logging, log_event

PG_HOST = os.getenv("PG_HOST", "iot-postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "iotcloud")
PG_USER = os.getenv("PG_USER", "iot")
PG_PASS = os.environ["PG_PASS"]
DATABASE_URL = os.getenv("DATABASE_URL")

MODE = os.getenv("MODE", "DEV").upper()
WORKER_POLL_SECONDS = int(os.getenv("WORKER_POLL_SECONDS", "2"))
WORKER_BATCH_SIZE = int(os.getenv("WORKER_BATCH_SIZE", "10"))
WORKER_TIMEOUT_SECONDS = int(os.getenv("WORKER_TIMEOUT_SECONDS", "30"))
WORKER_MAX_ATTEMPTS = int(os.getenv("WORKER_MAX_ATTEMPTS", "5"))
WORKER_BACKOFF_BASE_SECONDS = int(os.getenv("WORKER_BACKOFF_BASE_SECONDS", "30"))
WORKER_BACKOFF_MAX_SECONDS = int(os.getenv("WORKER_BACKOFF_MAX_SECONDS", "7200"))
STUCK_JOB_MINUTES = int(os.getenv("STUCK_JOB_MINUTES", "5"))
configure_logging("delivery_worker")
logger = logging.getLogger("delivery_worker")

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

_notify_event = asyncio.Event()

async def health_handler(request: web.Request) -> web.Response:
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


async def start_health_server() -> None:
    app = web.Application()
    app.router.add_get("/health", health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    log_event(logger, "health server started", service_port=8080)

def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def normalize_config(
    value: dict | str | bytes | bytearray | None,
    defaults: dict | None = None,
) -> dict:
    """Normalize configuration from various storage formats."""
    if value is None:
        config = {}
    elif isinstance(value, dict):
        config = value
    elif isinstance(value, (bytes, bytearray)):
        try:
            config = json.loads(value.decode("utf-8"))
        except Exception:
            config = {}
    elif isinstance(value, str):
        try:
            config = json.loads(value)
        except Exception:
            config = {}
    else:
        config = {}

    if not isinstance(config, dict):
        config = {}

    if defaults:
        config = {**defaults, **config}

    return config


def is_blocked_ip(ip: IPv4Address | IPv6Address) -> bool:
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

    if parsed.hostname in ("localhost", "127.0.0.1", "::1"):
        if MODE == "DEV":
            logger.warning("Allowing localhost webhook in DEV mode: %s", url)
            return True, "ok"
        return False, "blocked_localhost"

    try:
        addr_info = socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
    except Exception:
        return False, "dns_resolution_failed"

    for info in addr_info:
        ip = ip_address(info[4][0])
        if MODE == "DEV" and ip.is_loopback:
            continue
        if is_blocked_ip(ip):
            return False, f"blocked_ip:{ip}"

    return True, "ok"


def backoff_seconds(attempt_no: int) -> int:
    delay = WORKER_BACKOFF_BASE_SECONDS * (2 ** max(0, attempt_no - 1))
    return min(delay, WORKER_BACKOFF_MAX_SECONDS)


async def get_pool() -> asyncpg.Pool:
    if DATABASE_URL:
        return await asyncpg.create_pool(dsn=DATABASE_URL, min_size=2, max_size=10, command_timeout=30)
    return await asyncpg.create_pool(
        host=PG_HOST,
        port=PG_PORT,
        database=PG_DB,
        user=PG_USER,
        password=PG_PASS,
        min_size=2,
        max_size=10,
        command_timeout=30,
    )


async def create_listener_conn(host, port, database, user, password):
    """Create a dedicated asyncpg connection for LISTEN (not from pool)."""
    return await asyncpg.connect(
        host=host, port=port, database=database, user=user, password=password
    )


def resolve_notify_dsn() -> str:
    return os.environ.get("NOTIFY_DATABASE_URL", os.environ.get("DATABASE_URL", ""))


async def init_notify_listener(channel: str, callback):
    notify_dsn = resolve_notify_dsn()
    if notify_dsn:
        conn = await asyncpg.connect(notify_dsn)
    else:
        conn = await create_listener_conn(PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASS)
    await conn.add_listener(channel, callback)
    return conn


def on_delivery_job_notify(conn, pid, channel, payload):
    _notify_event.set()


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


async def fetch_notification_jobs(
    conn: asyncpg.Connection,
    batch_size: int = 10,
) -> list[asyncpg.Record]:
    async with conn.transaction():
        rows = await conn.fetch(
            """
            SELECT job_id, tenant_id, alert_id, channel_id, rule_id, deliver_on_event, attempts, payload_json
            FROM notification_jobs
            WHERE status='PENDING' AND next_run_at <= now()
            ORDER BY next_run_at ASC
            FOR UPDATE SKIP LOCKED
            LIMIT $1
            """,
            batch_size,
        )
        if not rows:
            return []
        job_ids = [r["job_id"] for r in rows]
        await conn.execute(
            """
            UPDATE notification_jobs
            SET status='PROCESSING', updated_at=now()
            WHERE job_id = ANY($1::bigint[])
            """,
            job_ids,
        )
        return rows


async def complete_notification_job(conn: asyncpg.Connection, job_id: int, channel_id: int, alert_id: int) -> None:
    await conn.execute(
        "UPDATE notification_jobs SET status='COMPLETED', updated_at=now() WHERE job_id=$1",
        job_id,
    )
    await conn.execute(
        """
        INSERT INTO notification_log (channel_id, alert_id, job_id, success)
        VALUES ($1, $2, $3, TRUE)
        """,
        channel_id,
        alert_id,
        job_id,
    )


async def retry_notification_job(conn: asyncpg.Connection, job_id: int, attempts: int, error: str) -> None:
    delay = min(WORKER_BACKOFF_BASE_SECONDS * (2 ** attempts), WORKER_BACKOFF_MAX_SECONDS)
    await conn.execute(
        """
        UPDATE notification_jobs
        SET status='PENDING',
            attempts=$1,
            next_run_at=now() + ($2::int * interval '1 second'),
            last_error=$3,
            updated_at=now()
        WHERE job_id=$4
        """,
        attempts + 1,
        delay,
        error[:500],
        job_id,
    )


async def fail_notification_job(
    conn: asyncpg.Connection,
    job_id: int,
    channel_id: int,
    alert_id: int,
    error: str,
) -> None:
    await conn.execute(
        """
        UPDATE notification_jobs
        SET status='FAILED', last_error=$1, updated_at=now()
        WHERE job_id=$2
        """,
        error[:500],
        job_id,
    )
    await conn.execute(
        """
        INSERT INTO notification_log (channel_id, alert_id, job_id, success, error_msg)
        VALUES ($1, $2, $3, FALSE, $4)
        """,
        channel_id,
        alert_id,
        job_id,
        error[:500],
    )


async def fetch_notification_channel(conn: asyncpg.Connection, channel_id: int) -> dict | None:
    row = await conn.fetchrow(
        """
        SELECT channel_id, channel_type, config, is_enabled
        FROM notification_channels
        WHERE channel_id=$1
        """,
        channel_id,
    )
    return dict(row) if row else None


async def process_notification_job(conn: asyncpg.Connection, job: asyncpg.Record) -> None:
    job_id = int(job["job_id"])
    channel_id = int(job["channel_id"])
    alert_id = int(job["alert_id"])
    attempts = int(job["attempts"])
    max_attempts = int(os.getenv("WORKER_MAX_ATTEMPTS", "5"))
    payload = job["payload_json"]
    if isinstance(payload, str):
        payload = json.loads(payload)

    channel = await fetch_notification_channel(conn, channel_id)
    if not channel:
        await fail_notification_job(conn, job_id, channel_id, alert_id, "Channel not found")
        return
    if not channel["is_enabled"]:
        await fail_notification_job(conn, job_id, channel_id, alert_id, "Channel disabled")
        return

    try:
        ctype = channel["channel_type"]
        cfg = normalize_config(channel.get("config"))
        fake_job = {"payload_json": payload, "tenant_id": job["tenant_id"]}
        if ctype in ("webhook", "http"):
            webhook_integration = {"type": "webhook", "config_json": cfg}
            ok, _, err = await deliver_webhook(webhook_integration, fake_job)
            if not ok:
                raise RuntimeError(err or "delivery_failed")
        elif ctype == "slack":
            payload_msg = {
                "text": f"*[{severity_label_for(int(payload.get('severity') or 0))}]* {payload.get('device_id', '-')}: {payload.get('message', '')}",
                "attachments": [
                    {
                        "fields": [
                            {"title": "Type", "value": payload.get("alert_type", ""), "short": True},
                            {"title": "Event", "value": payload.get("event_type", "OPEN"), "short": True},
                        ]
                    }
                ],
            }
            async with traced_client(timeout=float(WORKER_TIMEOUT_SECONDS)) as client:
                resp = await client.post(cfg.get("webhook_url"), json=payload_msg)
                if resp.status_code >= 400:
                    raise RuntimeError(f"slack_http_{resp.status_code}")
        elif ctype == "teams":
            payload_msg = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "summary": payload.get("alert_type", "ALERT"),
                "sections": [
                    {
                        "activityTitle": payload.get("device_id", "-"),
                        "activityText": payload.get("message", ""),
                    }
                ],
            }
            async with traced_client(timeout=float(WORKER_TIMEOUT_SECONDS)) as client:
                resp = await client.post(cfg.get("webhook_url"), json=payload_msg)
                if resp.status_code >= 400:
                    raise RuntimeError(f"teams_http_{resp.status_code}")
        elif ctype == "pagerduty":
            severity = int(payload.get("severity") or 0)
            pd_sev = "critical" if severity >= 4 else "error" if severity >= 3 else "warning"
            pd_payload = {
                "routing_key": cfg.get("integration_key"),
                "event_action": "trigger",
                "dedup_key": f"alert-{payload.get('alert_id', 0)}",
                "payload": {
                    "summary": f"{payload.get('alert_type', 'ALERT')} on {payload.get('device_id', '-')}",
                    "severity": pd_sev,
                    "source": payload.get("device_id", "unknown"),
                    "custom_details": payload,
                },
            }
            async with traced_client(timeout=float(WORKER_TIMEOUT_SECONDS)) as client:
                resp = await client.post("https://events.pagerduty.com/v2/enqueue", json=pd_payload)
                if resp.status_code >= 400:
                    raise RuntimeError(f"pagerduty_http_{resp.status_code}")
        elif ctype == "email":
            integration = {
                "email_config": cfg.get("smtp", {}),
                "email_recipients": cfg.get("recipients", {}),
                "email_template": cfg.get("template", {}),
            }
            ok, err = await deliver_email(integration, fake_job)
            if not ok:
                raise RuntimeError(err or "delivery_failed")
        elif ctype == "snmp":
            integration = {
                "snmp_host": cfg.get("host"),
                "snmp_port": cfg.get("port", 162),
                "snmp_config": cfg.get("snmp_config", cfg),
                "snmp_oid_prefix": cfg.get("oid_prefix"),
            }
            ok, err = await deliver_snmp(integration, fake_job)
            if not ok:
                raise RuntimeError(err or "delivery_failed")
        elif ctype == "mqtt":
            integration = {
                "mqtt_topic": cfg.get("topic"),
                "mqtt_qos": cfg.get("qos", 1),
                "mqtt_retain": cfg.get("retain", False),
                "mqtt_config": cfg.get("mqtt_config", cfg),
            }
            ok, err = await deliver_mqtt(integration, fake_job)
            if not ok:
                raise RuntimeError(err or "delivery_failed")
        else:
            raise RuntimeError(f"Unknown channel_type: {ctype}")
        await complete_notification_job(conn, job_id, channel_id, alert_id)
        logger.info("notification_job %s completed (channel=%s)", job_id, channel_id)
    except Exception as exc:
        error = str(exc)
        logger.warning("notification_job %s failed attempt %d: %s", job_id, attempts + 1, error)
        if attempts + 1 >= max_attempts:
            await fail_notification_job(conn, job_id, channel_id, alert_id, error)
            logger.error("notification_job %s permanently failed", job_id)
        else:
            await retry_notification_job(conn, job_id, attempts, error)


async def fetch_integration(
    conn: asyncpg.Connection,
    tenant_id: str,
    integration_id: str,
) -> dict | None:
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
        destination = "unknown"
        if integration_type == "webhook":
            config = normalize_config(integration.get("config_json"))
            destination = config.get("url") or "unknown"
        elif integration_type == "snmp":
            snmp_host = integration.get("snmp_host") or "unknown"
            snmp_port = integration.get("snmp_port") or 162
            destination = f"{snmp_host}:{snmp_port}"
        elif integration_type == "email":
            recipients = normalize_config(integration.get("email_recipients"))
            destination = f"{len(recipients.get('to', []))} recipients"
        elif integration_type == "mqtt":
            destination = integration.get("mqtt_topic") or "unknown"

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

    audit = get_audit_logger()
    if audit and integration is not None and integration.get("enabled"):
        if ok:
            audit.delivery_succeeded(
                tenant_id,
                str(job_id),
                integration_type,
                destination,
                latency_ms,
            )
        else:
            audit.delivery_failed(
                tenant_id,
                str(job_id),
                integration_type,
                error or "failed",
                attempt_no,
            )

    if ok:
        COUNTERS["jobs_succeeded"] += 1
        log_event(
            logger,
            "delivery sent",
            job_id=str(job_id),
            integration_type=integration_type if integration is not None else "unknown",
            tenant_id=tenant_id,
            attempt=attempt_no,
        )
        await update_job_success(conn, job_id, attempt_no)
        return

    if attempt_no >= WORKER_MAX_ATTEMPTS:
        COUNTERS["jobs_failed"] += 1
        log_event(
            logger,
            "delivery failed",
            level="ERROR",
            job_id=str(job_id),
            tenant_id=tenant_id,
            attempt=attempt_no,
            error=error or "failed",
        )
        await update_job_failed(conn, job_id, attempt_no, error or "failed")
        return

    await update_job_retry(conn, job_id, attempt_no, error or "failed")


async def deliver_webhook(integration: dict, job: asyncpg.Record) -> tuple[bool, int | None, str | None]:
    """Deliver via webhook. Returns (ok, http_status, error)."""
    config = normalize_config(integration.get("config_json"))
    url = config.get("url")
    headers = config.get("headers") or {}
    body_template = config.get("body_template")

    if not url:
        return False, None, "missing_url"

    allowed, reason = validate_url(url)
    if not allowed:
        return False, None, f"url_blocked:{reason}"

    payload = job["payload_json"]
    if isinstance(payload, str):
        payload = json.loads(payload)
    request_body = payload
    if body_template:
        variables = {
            "alert_id": payload.get("alert_id"),
            "device_id": payload.get("device_id"),
            "site_id": payload.get("site_id", ""),
            "tenant_id": payload.get("tenant_id", job.get("tenant_id")),
            "severity": payload.get("severity", 3),
            "severity_label": severity_label_for(payload.get("severity", 3)),
            "alert_type": payload.get("alert_type", ""),
            "summary": payload.get("summary", payload.get("message", "")),
            "status": payload.get("status", "OPEN"),
            "created_at": payload.get("created_at", ""),
            "details": payload.get("details", {}),
        }
        rendered = render_template(body_template, variables)
        try:
            request_body = json.loads(rendered)
        except Exception:
            request_body = {"message": rendered}

    try:
        async with traced_client(timeout=float(WORKER_TIMEOUT_SECONDS)) as client:
            resp = await client.post(url, json=request_body, headers=headers)
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
    snmp_config = normalize_config(integration.get("snmp_config"), {"version": "2c"})
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

    email_config = normalize_config(integration.get("email_config"), {"port": 587})
    email_recipients = normalize_config(integration.get("email_recipients"))
    email_template = normalize_config(integration.get("email_template"))

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

    mqtt_config = normalize_config(integration.get("mqtt_config"))
    broker_url = mqtt_config.get("broker_url") or "mqtt://iot-mqtt:1883"
    mqtt_qos = integration.get("mqtt_qos") if integration.get("mqtt_qos") is not None else 1
    mqtt_retain = integration.get("mqtt_retain") if integration.get("mqtt_retain") is not None else False

    payload = job["payload_json"]
    if isinstance(payload, str):
        payload = json.loads(payload)

    # Add trace_id to MQTT payload
    trace_id = trace_id_var.get("")
    if trace_id:
        payload["trace_id"] = trace_id

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
    audit = init_audit_logger(pool, "delivery_worker")
    await audit.start()
    log_event(
        logger,
        "worker startup",
        mode=MODE,
        ssrf_strict=ssrf_strict,
        snmp_available=PYSNMP_AVAILABLE,
        email_available=AIOSMTPLIB_AVAILABLE,
        mqtt_available=PAHO_MQTT_AVAILABLE,
    )

    fallback_poll_seconds = int(os.getenv("FALLBACK_POLL_SECONDS", "15"))
    debounce_seconds = float(os.getenv("DEBOUNCE_SECONDS", "0.1"))
    async with pool.acquire() as conn:
        legacy_pipeline_enabled = bool(
            await conn.fetchval("SELECT to_regclass('public.delivery_jobs') IS NOT NULL")
        )

    listener_conn = None
    try:
        listener_conn = await init_notify_listener("new_delivery_job", on_delivery_job_notify)
        log_event(logger, "listen channel active", channel="new_delivery_job")
    except Exception as exc:
        log_event(
            logger,
            "listen setup failed, using poll-only mode",
            level="WARNING",
            error=str(exc),
        )
        listener_conn = None

    try:
        while True:
            trace_token = trace_id_var.set(str(uuid.uuid4()))
            try:
                log_event(logger, "tick_start", tick="delivery_worker")
                try:
                    await asyncio.wait_for(_notify_event.wait(), timeout=fallback_poll_seconds)
                except asyncio.TimeoutError:
                    log_event(
                        logger,
                        "fallback poll triggered",
                        level="WARNING",
                        reason="no notifications",
                    )

                _notify_event.clear()
                await asyncio.sleep(debounce_seconds)
                _notify_event.clear()

                async with pool.acquire() as conn:
                    if legacy_pipeline_enabled:
                        stuck = await requeue_stuck_jobs(conn)
                        if stuck:
                            log_event(logger, "stuck jobs requeued", count=stuck)

                        jobs = await fetch_jobs(conn)
                        COUNTERS["jobs_pending"] = len(jobs)
                        for job in jobs:
                            await process_job(conn, job)
                    notification_jobs = await fetch_notification_jobs(conn, WORKER_BATCH_SIZE)
                    for notification_job in notification_jobs:
                        await process_notification_job(conn, notification_job)
                log_event(logger, "tick_done", tick="delivery_worker")
            except Exception as exc:
                logger.error(
                    "delivery worker loop failed",
                    extra={"error_type": type(exc).__name__, "error": str(exc)},
                    exc_info=True,
                )
                await asyncio.sleep(1)
            finally:
                trace_id_var.reset(trace_token)
    finally:
        if listener_conn is not None:
            try:
                await listener_conn.remove_listener("new_delivery_job", on_delivery_job_notify)
            except Exception:
                pass
            await listener_conn.close()


if __name__ == "__main__":
    asyncio.run(run_worker())
