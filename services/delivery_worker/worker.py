import asyncio
import json
import os
import socket
import time
from datetime import datetime, timezone
from ipaddress import ip_address, ip_network
from urllib.parse import urlparse

import asyncpg
import httpx

from snmp_sender import send_alert_trap, SNMPTrapResult, PYSNMP_AVAILABLE

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
        SELECT type, enabled, config_json, snmp_host, snmp_port, snmp_config, snmp_oid_prefix
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
        else:
            ok, http_status, error = await deliver_webhook(integration, job)

    finished_at = now_utc()
    latency_ms = int((finished_at - started_at).total_seconds() * 1000)

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
        await update_job_success(conn, job_id, attempt_no)
        return

    if attempt_no >= WORKER_MAX_ATTEMPTS:
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


async def run_worker() -> None:
    pool = await get_pool()
    ssrf_strict = MODE == "PROD"
    print(
        "[worker] startup mode={} ssrf_strict={} timeout_seconds={} max_attempts={} snmp_available={}".format(
            MODE,
            ssrf_strict,
            WORKER_TIMEOUT_SECONDS,
            WORKER_MAX_ATTEMPTS,
            PYSNMP_AVAILABLE,
        )
    )

    while True:
        try:
            async with pool.acquire() as conn:
                stuck = await requeue_stuck_jobs(conn)
                if stuck:
                    print(f"[worker] requeued_stuck={stuck} ts={now_utc().isoformat()}")

                jobs = await fetch_jobs(conn)
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
