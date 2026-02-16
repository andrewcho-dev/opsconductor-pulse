import asyncio
import json
import os
import logging
import time
from aiohttp import web
from datetime import datetime, timezone

import asyncpg
from shared.audit import init_audit_logger, get_audit_logger
from shared.logging import configure_logging, log_event
from shared.metrics import (
    pulse_queue_depth,
    pulse_processing_duration_seconds,
    pulse_db_pool_size,
    pulse_db_pool_free,
)

PG_HOST = os.getenv("PG_HOST", "iot-postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "iotcloud")
PG_USER = os.getenv("PG_USER", "iot")
PG_PASS = os.environ["PG_PASS"]
DATABASE_URL = os.getenv("DATABASE_URL")
configure_logging("dispatcher")
logger = logging.getLogger("dispatcher")

DISPATCH_POLL_SECONDS = int(os.getenv("DISPATCH_POLL_SECONDS", "5"))
ALERT_LOOKBACK_MINUTES = int(os.getenv("ALERT_LOOKBACK_MINUTES", "30"))
ALERT_LIMIT = int(os.getenv("ALERT_LIMIT", "200"))
ROUTE_LIMIT = int(os.getenv("ROUTE_LIMIT", "500"))

SEVERITY_MAP = {
    "CRITICAL": 5,
    "WARNING": 3,
    "INFO": 1,
}

COUNTERS = {
    "alerts_processed": 0,
    "routes_matched": 0,
    "jobs_queued": 0,
    "last_dispatch_at": None,
}

_notify_event = asyncio.Event()

COUNTERS = {
    "alerts_processed": 0,
    "routes_matched": 0,
    "jobs_queued": 0,
    "last_dispatch_at": None,
}

async def health_handler(request):
    return web.json_response(
        {
            "status": "healthy",
            "service": "dispatcher",
            "counters": {
                "alerts_processed": COUNTERS["alerts_processed"],
                "routes_matched": COUNTERS["routes_matched"],
                "jobs_queued": COUNTERS["jobs_queued"],
            },
            "last_dispatch_at": COUNTERS["last_dispatch_at"],
        }
    )


async def start_health_server():
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

    async def metrics_handler(request):
        return web.Response(
            body=generate_latest(),
            content_type=CONTENT_TYPE_LATEST.split(";")[0],
        )

    app = web.Application()
    app.router.add_get("/health", health_handler)
    app.router.add_get("/metrics", metrics_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    log_event(logger, "health server started", service_port=8080)

def now_utc() -> datetime:
    return datetime.now(timezone.utc)


async def health_handler(request):
    return web.json_response(
        {
            "status": "healthy",
            "service": "dispatcher",
            "counters": {
                "alerts_processed": COUNTERS["alerts_processed"],
                "routes_matched": COUNTERS["routes_matched"],
                "jobs_queued": COUNTERS["jobs_queued"],
            },
            "last_dispatch_at": COUNTERS["last_dispatch_at"],
        }
    )


async def start_health_server():
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

    async def metrics_handler(request):
        return web.Response(
            body=generate_latest(),
            content_type=CONTENT_TYPE_LATEST.split(";")[0],
        )

    app = web.Application()
    app.router.add_get("/health", health_handler)
    app.router.add_get("/metrics", metrics_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    log_event(logger, "health server started", service_port=8080)


def route_matches(alert: dict, route: dict) -> bool:
    if route["deliver_on"] is None or "OPEN" not in route["deliver_on"]:
        return False

    min_sev = route.get("min_severity")
    if min_sev is not None and alert["severity"] < min_sev:
        return False

    alert_types = route["alert_types"] or []
    if alert_types and alert["alert_type"] not in alert_types:
        return False

    site_ids = route["site_ids"] or []
    if site_ids and alert["site_id"] not in site_ids:
        return False

    prefixes = route["device_prefixes"] or []
    if prefixes:
        if not any(alert["device_id"].startswith(p) for p in prefixes):
            return False

    return True


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


def on_fleet_alert_notify(conn, pid, channel, payload):
    _notify_event.set()


async def fetch_open_alerts(conn: asyncpg.Connection) -> list[asyncpg.Record]:
    return await conn.fetch(
        """
        SELECT id, tenant_id, site_id, device_id, alert_type, severity, confidence, summary, details, created_at
        FROM fleet_alert
        WHERE status='OPEN'
          AND created_at > (now() - ($1::int * interval '1 minute'))
        ORDER BY created_at DESC
        LIMIT $2
        """,
        ALERT_LOOKBACK_MINUTES,
        ALERT_LIMIT,
    )


async def fetch_routes(conn: asyncpg.Connection, tenant_id: str) -> list[asyncpg.Record]:
    return await conn.fetch(
        """
        SELECT ir.tenant_id, ir.route_id, ir.integration_id, ir.min_severity,
               ir.alert_types, ir.site_ids, ir.device_prefixes, ir.deliver_on
        FROM integration_routes ir
        JOIN integrations i ON ir.integration_id = i.integration_id AND ir.tenant_id = i.tenant_id
        WHERE ir.tenant_id=$1
          AND ir.enabled=true
          AND i.enabled=true
        ORDER BY ir.priority ASC, ir.created_at ASC
        LIMIT $2
        """,
        tenant_id,
        ROUTE_LIMIT,
    )


def build_payload(alert: dict) -> dict:
    return {
        "alert_id": alert["id"],
        "site_id": alert["site_id"],
        "device_id": alert["device_id"],
        "alert_type": alert["alert_type"],
        "severity": alert["severity"],
        "confidence": float(alert["confidence"]) if alert["confidence"] is not None else None,
        "summary": alert["summary"],
        "status": "OPEN",
        "created_at": alert["created_at"].isoformat(),
        "details": alert["details"] or {},
    }


async def dispatch_once(conn: asyncpg.Connection) -> int:
    alerts = await fetch_open_alerts(conn)
    pulse_queue_depth.labels(
        service="dispatcher",
        queue_name="pending_alerts",
    ).set(len(alerts))
    if not alerts:
        return 0

    COUNTERS["alerts_processed"] += len(alerts)

    alerts_by_tenant: dict[str, list[asyncpg.Record]] = {}
    for alert in alerts:
        alerts_by_tenant.setdefault(alert["tenant_id"], []).append(alert)

    created = 0
    created_webhook = 0
    created_snmp = 0
    for tenant_id, tenant_alerts in alerts_by_tenant.items():
        routes = await fetch_routes(conn, tenant_id)
        if not routes:
            continue

        integration_types = {}
        for route in routes:
            if route["integration_id"] not in integration_types:
                int_type = await conn.fetchval(
                    "SELECT type FROM integrations WHERE integration_id = $1",
                    route["integration_id"],
                )
                integration_types[route["integration_id"]] = int_type or "webhook"

        for alert in tenant_alerts:
            alert_dict = dict(alert)
            payload = build_payload(alert_dict)

            for route in routes:
                if not route_matches(alert_dict, route):
                    continue
                COUNTERS["routes_matched"] += 1

                row = await conn.fetchrow(
                    """
                    INSERT INTO delivery_jobs (
                      tenant_id, alert_id, integration_id, route_id,
                      deliver_on_event, status, attempts, next_run_at, payload_json
                    )
                    VALUES ($1,$2,$3,$4,'OPEN','PENDING',0, now(), $5::jsonb)
                    ON CONFLICT (tenant_id, alert_id, route_id, deliver_on_event) DO NOTHING
                    RETURNING job_id
                    """,
                    alert_dict["tenant_id"],
                    alert_dict["id"],
                    route["integration_id"],
                    route["route_id"],
                    json.dumps(payload),
                )
                if row is not None:
                    created += 1
                    COUNTERS["jobs_queued"] += 1
                    log_event(
                        logger,
                        "delivery job created",
                        tenant_id=alert_dict["tenant_id"],
                        alert_id=str(alert_dict["id"]),
                        route_id=str(route["route_id"]),
                        integration_id=str(route["integration_id"]),
                    )
                    int_type = integration_types.get(route["integration_id"], "webhook")
                    if int_type == "snmp":
                        created_snmp += 1
                    else:
                        created_webhook += 1
                    audit = get_audit_logger()
                    if audit:
                        audit.delivery_queued(
                            alert_dict["tenant_id"],
                            str(row["job_id"]),
                            str(alert_dict["id"]),
                            int_type,
                        )

    if created:
        log_event(
            logger,
            "delivery jobs created",
            created_jobs=created,
            webhook_jobs=created_webhook,
            snmp_jobs=created_snmp,
        )
    COUNTERS["last_dispatch_at"] = now_utc().isoformat()

    return created


async def dispatch_escalated_alerts(
    conn: asyncpg.Connection,
    tenant_id: str,
    lookback_minutes: int = 5,
) -> int:
    alerts = await conn.fetch(
        """
        SELECT id, tenant_id, site_id, device_id, alert_type, severity, confidence,
               summary, status, created_at, details, escalated_at, escalation_level
        FROM fleet_alert
        WHERE tenant_id = $1
          AND escalated_at > now() - ($2 || ' minutes')::interval
          AND escalation_level > 0
        """,
        tenant_id,
        str(lookback_minutes),
    )
    if not alerts:
        return 0

    routes = await fetch_routes(conn, tenant_id)
    if not routes:
        return 0

    created = 0
    for alert in alerts:
        alert_dict = dict(alert)
        payload = build_payload(alert_dict)
        payload["escalated"] = True
        payload["escalation_level"] = alert_dict.get("escalation_level", 1)
        payload["status"] = "ESCALATED"
        for route in routes:
            if not route_matches(alert_dict, route):
                continue
            already_notified = await conn.fetchval(
                """
                SELECT 1
                FROM delivery_jobs
                WHERE tenant_id = $1
                  AND alert_id = $2
                  AND route_id = $3
                  AND status = 'COMPLETED'
                  AND created_at > $4
                LIMIT 1
                """,
                tenant_id,
                alert_dict["id"],
                route["route_id"],
                alert_dict["escalated_at"],
            )
            if already_notified:
                continue

            row = await conn.fetchrow(
                """
                INSERT INTO delivery_jobs (
                  tenant_id, alert_id, integration_id, route_id,
                  deliver_on_event, status, attempts, next_run_at, payload_json
                )
                VALUES ($1,$2,$3,$4,'CLOSED','PENDING',0, now(), $5::jsonb)
                ON CONFLICT (tenant_id, alert_id, route_id, deliver_on_event) DO NOTHING
                RETURNING job_id
                """,
                alert_dict["tenant_id"],
                alert_dict["id"],
                route["integration_id"],
                route["route_id"],
                json.dumps(payload),
            )
            if row:
                created += 1
                COUNTERS["jobs_queued"] += 1
                log_event(
                    logger,
                    "escalation delivery job created",
                    tenant_id=alert_dict["tenant_id"],
                    alert_id=str(alert_dict["id"]),
                    route_id=str(route["route_id"]),
                    escalation_level=payload["escalation_level"],
                )
    return created


async def main() -> None:
    pool = await get_pool()
    await start_health_server()
    audit = init_audit_logger(pool, "dispatcher")
    await audit.start()

    fallback_poll_seconds = int(os.getenv("FALLBACK_POLL_SECONDS", "30"))
    debounce_seconds = float(os.getenv("DEBOUNCE_SECONDS", "0.5"))

    listener_conn = None
    try:
        listener_conn = await init_notify_listener("new_fleet_alert", on_fleet_alert_notify)
        log_event(logger, "listen channel active", channel="new_fleet_alert")
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
            try:
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

                dispatch_start = time.monotonic()
                async with pool.acquire() as conn:
                    await dispatch_once(conn)
                    tenant_rows = await conn.fetch(
                        "SELECT DISTINCT tenant_id FROM fleet_alert WHERE escalated_at IS NOT NULL"
                    )
                    for tenant_row in tenant_rows:
                        await dispatch_escalated_alerts(
                            conn,
                            tenant_row["tenant_id"],
                            lookback_minutes=5,
                        )

                dispatch_duration = time.monotonic() - dispatch_start
                pulse_processing_duration_seconds.labels(
                    service="dispatcher",
                    operation="dispatch_cycle",
                ).observe(dispatch_duration)

                pulse_db_pool_size.labels(service="dispatcher").set(pool.get_size())
                pulse_db_pool_free.labels(service="dispatcher").set(pool.get_idle_size())
            except Exception as exc:
                logger.error(
                    "dispatch loop failed",
                    extra={"error_type": type(exc).__name__, "error": str(exc)},
                    exc_info=True,
                )
                await asyncio.sleep(1)
    finally:
        if listener_conn is not None:
            try:
                await listener_conn.remove_listener("new_fleet_alert", on_fleet_alert_notify)
            except Exception:
                pass
            await listener_conn.close()


if __name__ == "__main__":
    asyncio.run(main())
