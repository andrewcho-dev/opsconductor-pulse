import asyncio
import json
import logging
import os
import time

import asyncpg
import httpx

from shared.http_client import traced_client

logger = logging.getLogger(__name__)

PG_HOST = os.getenv("PG_HOST", "iot-postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "iotcloud")
PG_USER = os.getenv("PG_USER", "iot")
PG_PASS = os.getenv("PG_PASS", "iot_dev")
DATABASE_URL = os.getenv("DATABASE_URL")
PG_POOL_MIN = int(os.getenv("PG_POOL_MIN", "2"))
PG_POOL_MAX = int(os.getenv("PG_POOL_MAX", "10"))

INGEST_URL = os.getenv("INGEST_HEALTH_URL", "http://iot-ingest:8080")
EVALUATOR_URL = os.getenv("EVALUATOR_HEALTH_URL", "http://iot-evaluator:8080")

HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "60"))
SYSTEM_ALERT_ENABLED = os.getenv("SYSTEM_ALERT_ENABLED", "true").lower() in {"1", "true", "yes", "on"}

HEALTH_MONITOR_ENDPOINTS = {
    "ingest": INGEST_URL,
    "evaluator": EVALUATOR_URL,
}

_pool: asyncpg.Pool | None = None
_service_health_ready = False


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        if DATABASE_URL:
            _pool = await asyncpg.create_pool(
                dsn=DATABASE_URL,
                min_size=PG_POOL_MIN,
                max_size=PG_POOL_MAX,
                command_timeout=30,
            )
        else:
            _pool = await asyncpg.create_pool(
                host=PG_HOST,
                port=PG_PORT,
                database=PG_DB,
                user=PG_USER,
                password=PG_PASS,
                min_size=PG_POOL_MIN,
                max_size=PG_POOL_MAX,
                command_timeout=30,
            )
    return _pool


def _system_alert_fingerprint(service_name: str) -> str:
    return f"system-health:{service_name}"


async def get_open_system_alert(conn: asyncpg.Connection, service_name: str) -> dict | None:
    fingerprint = _system_alert_fingerprint(service_name)
    row = await conn.fetchrow(
        """
        SELECT id, created_at, tenant_id, alert_type, fingerprint, status, severity, summary, details
        FROM fleet_alert
        WHERE tenant_id = '__system__'
          AND fingerprint = $1
          AND status = 'OPEN'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        fingerprint,
    )
    return dict(row) if row else None


async def create_system_alert(conn: asyncpg.Connection, service_name: str, message: str) -> None:
    fingerprint = _system_alert_fingerprint(service_name)
    await conn.execute(
        """
        INSERT INTO tenants (tenant_id, name, status, metadata)
        VALUES ('__system__', 'System Alerts', 'ACTIVE', '{"kind":"system"}'::jsonb)
        ON CONFLICT (tenant_id) DO NOTHING
        """
    )
    await conn.execute(
        """
        INSERT INTO fleet_alert (
            tenant_id, site_id, device_id, alert_type, fingerprint,
            status, severity, confidence, summary, details
        )
        VALUES (
            '__system__', '__system__', '__system__', 'SYSTEM_HEALTH', $1,
            'OPEN', 5, 1.0, $2, $3::jsonb
        )
        ON CONFLICT DO NOTHING
        """,
        fingerprint,
        message,
        json.dumps({"service": service_name, "kind": "system_health"}),
    )


async def resolve_system_alert(conn: asyncpg.Connection, service_name: str) -> None:
    fingerprint = _system_alert_fingerprint(service_name)
    await conn.execute(
        """
        UPDATE fleet_alert
        SET status = 'CLOSED',
            closed_at = now(),
            details = jsonb_set(
                COALESCE(details, '{}'::jsonb),
                '{resolved_at}',
                to_jsonb(now()::text),
                true
            )
        WHERE tenant_id = '__system__'
          AND fingerprint = $1
          AND status = 'OPEN'
        """,
        fingerprint,
    )


async def check_service(name: str, url: str) -> dict:
    start = time.time()
    try:
        async with traced_client(timeout=5.0) as client:
            resp = await client.get(f"{url}/health")
            latency = int((time.time() - start) * 1000)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "status": "healthy",
                    "latency_ms": latency,
                    "counters": data.get("counters", {}),
                }
            return {
                "status": "degraded",
                "latency_ms": latency,
                "http_status": resp.status_code,
            }
    except httpx.ConnectError:
        return {"status": "down", "error": "Connection refused"}
    except Exception as exc:
        logger.error("%s health check failed: %s", name, exc)
        return {"status": "unknown", "error": str(exc)}


def _health_failure_reason(health: dict) -> str:
    if not isinstance(health, dict):
        return "unknown"
    if health.get("error"):
        return str(health["error"])
    if health.get("http_status"):
        return f"http {health['http_status']}"
    return health.get("status", "unknown")


async def run_health_monitor_cycle() -> None:
    global _service_health_ready
    current_pool = await get_pool()
    async with current_pool.acquire() as conn:
        if not _service_health_ready:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS service_health (
                    service TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    latency_ms INTEGER,
                    details JSONB NOT NULL DEFAULT '{}'::jsonb,
                    checked_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            _service_health_ready = True

        for service_name, service_url in HEALTH_MONITOR_ENDPOINTS.items():
            health = await check_service(service_name, service_url)
            is_healthy = health.get("status") == "healthy"
            await conn.execute(
                """
                INSERT INTO service_health (service, status, latency_ms, details, checked_at)
                VALUES ($1, $2, $3, $4::jsonb, now())
                ON CONFLICT (service)
                DO UPDATE SET
                    status = EXCLUDED.status,
                    latency_ms = EXCLUDED.latency_ms,
                    details = EXCLUDED.details,
                    checked_at = EXCLUDED.checked_at
                """,
                service_name,
                "healthy" if is_healthy else "unhealthy",
                health.get("latency_ms"),
                json.dumps(health),
            )
            open_alert = await get_open_system_alert(conn, service_name)

            if not is_healthy and not open_alert:
                reason = _health_failure_reason(health)
                message = f"Service unhealthy: {service_name} ({reason})"
                await create_system_alert(conn, service_name, message)
                logger.warning("[health-monitor] created alert for %s: %s", service_name, reason)
            elif is_healthy and open_alert:
                await resolve_system_alert(conn, service_name)
                logger.info("[health-monitor] resolved alert for %s", service_name)


async def run_health_monitor() -> None:
    if not SYSTEM_ALERT_ENABLED:
        logger.info("System health monitor disabled (SYSTEM_ALERT_ENABLED=false)")
        while True:
            await asyncio.sleep(max(5, HEALTH_CHECK_INTERVAL))

    logger.info("System health monitor started (interval=%ss)", HEALTH_CHECK_INTERVAL)
    while True:
        try:
            await run_health_monitor_cycle()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Health monitor loop failed")
        await asyncio.sleep(max(5, HEALTH_CHECK_INTERVAL))
