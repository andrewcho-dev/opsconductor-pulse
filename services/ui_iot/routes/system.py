import os
import time
import logging
import shutil
import json
from datetime import datetime, timezone
from typing import Optional

import httpx
import asyncpg
from fastapi import APIRouter, Depends, Query, HTTPException
from starlette.requests import Request

from middleware.auth import JWTBearer
from middleware.tenant import inject_tenant_context, require_operator
from db.pool import operator_connection

logger = logging.getLogger(__name__)

POSTGRES_HOST = os.getenv("PG_HOST", "iot-postgres")
POSTGRES_PORT = int(os.getenv("PG_PORT", "5432"))
POSTGRES_DB = os.getenv("PG_DB", "iotcloud")
POSTGRES_USER = os.getenv("PG_USER", "iot")
POSTGRES_PASS = os.getenv("PG_PASS", "iot_dev")

KEYCLOAK_INTERNAL_URL = os.getenv("KEYCLOAK_INTERNAL_URL", "http://pulse-keycloak:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "pulse")

INGEST_URL = os.getenv("INGEST_HEALTH_URL", "http://iot-ingest:8080")
EVALUATOR_URL = os.getenv("EVALUATOR_HEALTH_URL", "http://iot-evaluator:8080")

router = APIRouter(
    prefix="/api/v1/operator/system",
    tags=["system"],
    dependencies=[
        Depends(JWTBearer()),
        Depends(inject_tenant_context),
        Depends(require_operator),
    ],
)

_pool: asyncpg.Pool | None = None


async def _init_db_connection(conn: asyncpg.Connection) -> None:
    # Avoid passing statement_timeout as a startup parameter (PgBouncer rejects it).
    await conn.execute("SET statement_timeout TO 30000")


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASS,
            min_size=1,
            max_size=5,
            command_timeout=30,
            init=_init_db_connection,
        )
    return _pool


async def check_postgres() -> dict:
    start = time.time()
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            connections = await conn.fetchval(
                "SELECT count(*) FROM pg_stat_activity WHERE datname = $1",
                POSTGRES_DB,
            )
            max_conn = await conn.fetchval("SHOW max_connections")
        latency = int((time.time() - start) * 1000)
        return {
            "status": "healthy",
            "latency_ms": latency,
            "connections": connections,
            "max_connections": int(max_conn),
        }
    except Exception as e:
        logger.error("Postgres health check failed: %s", e)
        return {"status": "down", "error": str(e)}


async def check_keycloak() -> dict:
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{KEYCLOAK_INTERNAL_URL}/realms/{KEYCLOAK_REALM}"
            )
            latency = int((time.time() - start) * 1000)
            if resp.status_code == 200:
                return {"status": "healthy", "latency_ms": latency}
            return {
                "status": "degraded",
                "latency_ms": latency,
                "http_status": resp.status_code,
            }
    except Exception as e:
        logger.error("Keycloak health check failed: %s", e)
        return {"status": "down", "error": str(e)}


async def check_service(name: str, url: str) -> dict:
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
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
    except Exception as e:
        logger.error("%s health check failed: %s", name, e)
        return {"status": "unknown", "error": str(e)}


async def check_mqtt() -> dict:
    import socket

    mqtt_host = os.getenv("MQTT_HOST", "iot-mqtt")
    mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
    start = time.time()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((mqtt_host, mqtt_port))
        sock.close()
        latency = int((time.time() - start) * 1000)
        if result == 0:
            return {"status": "healthy", "latency_ms": latency}
        return {"status": "down", "error": f"Connection failed: {result}"}
    except Exception as e:
        return {"status": "down", "error": str(e)}


async def fetch_service_counters(url: str) -> dict:
    """Fetch counters from a service health endpoint."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{url}/health")
            if resp.status_code == 200:
                data = resp.json()
                counters = data.get("counters", {})
                for key in [
                    "last_write_at",
                    "last_evaluation_at",
                    "last_dispatch_at",
                    "last_delivery_at",
                ]:
                    if key in data:
                        counters[key] = data[key]
                return counters
    except Exception as e:
        logger.warning("Failed to fetch counters from %s: %s", url, e)
    return {}


async def calculate_ingest_rate(pool: asyncpg.Pool) -> float:
    """Calculate messages per second from telemetry (last 60 seconds)."""
    try:
        async with operator_connection(pool) as conn:
            count = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM telemetry
                WHERE time >= now() - interval '60 seconds'
                  AND msg_type = 'telemetry'
                """
            )
        return round((count or 0) / 60.0, 2)
    except Exception as e:
        logger.warning("Failed to calculate ingest rate: %s", e)
    return 0.0


@router.get("/health")
async def get_system_health(request: Request):
    import asyncio

    results = await asyncio.gather(
        check_postgres(),
        check_mqtt(),
        check_keycloak(),
        check_service("ingest", INGEST_URL),
        check_service("evaluator", EVALUATOR_URL),
        return_exceptions=True,
    )

    component_names = [
        "postgres",
        "mqtt",
        "keycloak",
        "ingest",
        "evaluator",
    ]

    components = {}
    for name, result in zip(component_names, results):
        if isinstance(result, Exception):
            components[name] = {"status": "unknown", "error": str(result)}
        else:
            components[name] = result

    # Deprecated services removed in phase 138; keep keys for UI compatibility.
    components["dispatcher"] = {"status": "unknown", "error": "deprecated"}
    components["delivery"] = {"status": "unknown", "error": "deprecated"}

    core_statuses = [
        components[c].get("status", "unknown")
        for c in ("postgres", "mqtt", "keycloak", "ingest", "evaluator")
    ]
    if all(s == "healthy" for s in core_statuses):
        overall = "healthy"
    elif any(s == "down" for s in core_statuses):
        overall = "degraded"
    else:
        overall = "degraded"

    return {
        "status": overall,
        "components": components,
        "checked_at": datetime.now(timezone.utc).isoformat() + "Z",
    }


@router.get("/metrics")
async def get_system_metrics(request: Request):
    """
    Get system throughput and latency metrics.
    Aggregates data from service health endpoints and TimescaleDB.
    """
    import asyncio

    service_metrics = await asyncio.gather(
        fetch_service_counters(INGEST_URL),
        fetch_service_counters(EVALUATOR_URL),
        return_exceptions=True,
    )

    ingest_counters = service_metrics[0] if not isinstance(service_metrics[0], Exception) else {}
    evaluator_counters = service_metrics[1] if not isinstance(service_metrics[1], Exception) else {}
    dispatcher_counters = {}
    delivery_counters = {}

    pool = await get_pool()
    ingest_rate = await calculate_ingest_rate(pool)

    return {
        "throughput": {
            "ingest_rate_per_sec": ingest_rate,
            "messages_received_total": ingest_counters.get("messages_received", 0),
            "messages_written_total": ingest_counters.get("messages_written", 0),
            "messages_rejected_total": ingest_counters.get("messages_rejected", 0),
            "alerts_created_total": evaluator_counters.get("alerts_created", 0),
            "alerts_dispatched_total": dispatcher_counters.get("alerts_processed", 0),
            "deliveries_succeeded_total": delivery_counters.get("jobs_succeeded", 0),
            "deliveries_failed_total": delivery_counters.get("jobs_failed", 0),
        },
        "queues": {
            "ingest_queue_depth": ingest_counters.get("queue_depth", 0),
            "delivery_pending": delivery_counters.get("jobs_pending", 0),
        },
        "last_activity": {
            "last_ingest": ingest_counters.get("last_write_at"),
            "last_evaluation": evaluator_counters.get("last_evaluation_at"),
            "last_dispatch": dispatcher_counters.get("last_dispatch_at"),
            "last_delivery": delivery_counters.get("last_delivery_at"),
        },
        "period": "since_service_start",
    }


@router.get("/metrics/history")
async def get_metrics_history(
    request: Request,
    metric: str = Query(..., description="Metric name"),
    minutes: int = Query(15, ge=1, le=1440),
    service: Optional[str] = Query(None, description="Filter by service"),
    rate: bool = Query(False, description="Compute rate (derivative) for counter metrics"),
):
    """Get historical time-series for a metric.

    When rate=True, computes the derivative (change per second) between
    consecutive data points. Use this for cumulative counter metrics like
    messages_written to show actual throughput rates.
    """
    pool = await get_pool()

    async with pool.acquire() as conn:
        if service:
            rows = await conn.fetch(
                """
                SELECT time, value
                FROM system_metrics
                WHERE metric_name = $1
                  AND service = $2
                  AND time > now() - ($3::int * interval '1 minute')
                ORDER BY time ASC
                """,
                metric,
                service,
                minutes,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT time, value
                FROM system_metrics
                WHERE metric_name = $1
                  AND time > now() - ($2::int * interval '1 minute')
                ORDER BY time ASC
                """,
                metric,
                minutes,
            )

    if rate and len(rows) >= 2:
        # Compute rate (derivative) between consecutive points
        points = []
        for i in range(1, len(rows)):
            prev_row = rows[i - 1]
            curr_row = rows[i]

            time_delta = (curr_row["time"] - prev_row["time"]).total_seconds()
            if time_delta > 0:
                value_delta = curr_row["value"] - prev_row["value"]
                # Handle counter resets (value decreased means service restarted)
                if value_delta < 0:
                    value_delta = curr_row["value"]
                rate_per_sec = round(value_delta / time_delta, 2)
                points.append({
                    "time": curr_row["time"].isoformat(),
                    "value": rate_per_sec,
                })
    else:
        points = [
            {"time": row["time"].isoformat(), "value": row["value"]}
            for row in rows
        ]

    return {
        "metric": metric,
        "service": service,
        "points": points,
        "minutes": minutes,
        "rate": rate,
    }


@router.get("/metrics/history/batch")
async def get_metrics_history_batch(
    request: Request,
    metrics: str = Query(..., description="Comma-separated metric names"),
    minutes: int = Query(15, ge=1, le=1440),
):
    """
    Get historical data for multiple metrics in one request.
    More efficient for loading the dashboard.
    """
    import asyncio

    metric_list = [m.strip() for m in metrics.split(",")]
    results = await asyncio.gather(
        *[
            get_metrics_history(request, metric=m, minutes=minutes)
            for m in metric_list
        ],
        return_exceptions=True,
    )

    response = {}
    for metric, result in zip(metric_list, results):
        if isinstance(result, Exception):
            response[metric] = {"points": [], "error": str(result)}
        else:
            response[metric] = result

    return response


@router.get("/metrics/latest")
async def get_latest_metrics(request: Request):
    """Get most recent value for all metrics."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT DISTINCT ON (metric_name, service)
                metric_name,
                service,
                value,
                time
            FROM system_metrics
            ORDER BY metric_name, service, time DESC
            """
        )

    result = {}
    for row in rows:
        service = row["service"] or "system"
        if service not in result:
            result[service] = {}
        result[service][row["metric_name"]] = row["value"]

    return result


@router.get("/capacity")
async def get_system_capacity(request: Request):
    """
    Get system capacity and utilization metrics.
    Includes disk usage, database sizes, and connection counts.
    """
    import asyncio

    postgres_stats = await get_postgres_capacity()
    disk_stats = get_disk_capacity()

    if isinstance(postgres_stats, Exception):
        postgres_stats = {"error": str(postgres_stats)}
    if isinstance(disk_stats, Exception):
        disk_stats = {"error": str(disk_stats)}

    return {
        "postgres": postgres_stats,
        "disk": disk_stats,
    }


@router.get("/aggregates")
async def get_system_aggregates(request: Request):
    """
    Get platform-wide aggregate counts.
    Cross-tenant totals for operators to see system-wide state.
    """
    pool = await get_pool()

    async with operator_connection(pool) as conn:
        stats = await conn.fetchrow(
            """
            SELECT
                (SELECT COUNT(*) FROM tenants WHERE status = 'ACTIVE') AS tenants_active,
                (SELECT COUNT(*) FROM tenants WHERE status = 'SUSPENDED') AS tenants_suspended,
                (SELECT COUNT(*) FROM tenants WHERE status = 'DELETED') AS tenants_deleted,
                (SELECT COUNT(*) FROM tenants) AS tenants_total,
                (SELECT COUNT(*) FROM device_registry) AS devices_registered,
                (SELECT COUNT(*) FROM device_registry WHERE status = 'ACTIVE') AS devices_active,
                (SELECT COUNT(*) FROM device_registry WHERE status = 'REVOKED') AS devices_revoked,
                (SELECT COUNT(*) FROM device_state WHERE status = 'ONLINE') AS devices_online,
                (SELECT COUNT(*) FROM device_state WHERE status = 'STALE') AS devices_stale,
                (SELECT COUNT(*) FROM device_state WHERE status = 'OFFLINE') AS devices_offline,
                (SELECT COUNT(*) FROM fleet_alert WHERE status = 'OPEN') AS alerts_open,
                (SELECT COUNT(*) FROM fleet_alert WHERE status = 'CLOSED') AS alerts_closed,
                (SELECT COUNT(*) FROM fleet_alert WHERE status = 'ACKNOWLEDGED') AS alerts_acknowledged,
                (SELECT COUNT(*) FROM fleet_alert
                 WHERE created_at >= now() - interval '24 hours') AS alerts_24h,
                (SELECT COUNT(*) FROM fleet_alert
                 WHERE created_at >= now() - interval '1 hour') AS alerts_1h,
                (SELECT COUNT(*) FROM integrations) AS integrations_total,
                (SELECT COUNT(*) FROM integrations WHERE enabled = true) AS integrations_active,
                (SELECT COUNT(*) FROM integrations WHERE type = 'webhook') AS integrations_webhook,
                (SELECT COUNT(*) FROM integrations WHERE type = 'email') AS integrations_email,
                (SELECT COUNT(*) FROM alert_rules) AS rules_total,
                (SELECT COUNT(*) FROM alert_rules WHERE enabled = true) AS rules_active,
                (SELECT COUNT(*) FROM delivery_jobs WHERE status = 'PENDING') AS deliveries_pending,
                (SELECT COUNT(*) FROM delivery_jobs WHERE status = 'COMPLETED') AS deliveries_succeeded,
                (SELECT COUNT(*) FROM delivery_jobs WHERE status = 'FAILED') AS deliveries_failed,
                (SELECT COUNT(*) FROM delivery_jobs
                 WHERE created_at >= now() - interval '24 hours') AS deliveries_24h,
                (SELECT COUNT(DISTINCT site_id) FROM device_registry) AS sites_total
            """
        )

        activity = await conn.fetchrow(
            """
            SELECT
                (SELECT MAX(created_at) FROM fleet_alert) AS last_alert,
                (SELECT MAX(last_seen_at) FROM device_state) AS last_device_activity,
                (SELECT MAX(created_at) FROM delivery_jobs) AS last_delivery
            """
        )

    return {
        "tenants": {
            "active": stats["tenants_active"] or 0,
            "suspended": stats["tenants_suspended"] or 0,
            "deleted": stats["tenants_deleted"] or 0,
            "total": stats["tenants_total"] or 0,
        },
        "devices": {
            "registered": stats["devices_registered"] or 0,
            "active": stats["devices_active"] or 0,
            "revoked": stats["devices_revoked"] or 0,
            "online": stats["devices_online"] or 0,
            "stale": stats["devices_stale"] or 0,
            "offline": stats["devices_offline"] or 0,
        },
        "alerts": {
            "open": stats["alerts_open"] or 0,
            "acknowledged": stats["alerts_acknowledged"] or 0,
            "closed": stats["alerts_closed"] or 0,
            "triggered_1h": stats["alerts_1h"] or 0,
            "triggered_24h": stats["alerts_24h"] or 0,
        },
        "integrations": {
            "total": stats["integrations_total"] or 0,
            "active": stats["integrations_active"] or 0,
            "by_type": {
                "webhook": stats["integrations_webhook"] or 0,
                "email": stats["integrations_email"] or 0,
            },
        },
        "rules": {
            "total": stats["rules_total"] or 0,
            "active": stats["rules_active"] or 0,
        },
        "deliveries": {
            "pending": stats["deliveries_pending"] or 0,
            "succeeded": stats["deliveries_succeeded"] or 0,
            "failed": stats["deliveries_failed"] or 0,
            "total_24h": stats["deliveries_24h"] or 0,
        },
        "sites": {
            "total": stats["sites_total"] or 0,
        },
        "last_activity": {
            "alert": activity["last_alert"].isoformat() + "Z"
            if activity["last_alert"]
            else None,
            "device": activity["last_device_activity"].isoformat() + "Z"
            if activity["last_device_activity"]
            else None,
            "delivery": activity["last_delivery"].isoformat() + "Z"
            if activity["last_delivery"]
            else None,
        },
    }


@router.get("/errors")
async def get_system_errors(
    request: Request,
    hours: int = Query(1, ge=1, le=24, description="Hours to look back"),
    limit: int = Query(50, ge=1, le=200, description="Max errors to return"),
):
    """
    Get recent system errors and failures.
    Aggregates from various error sources across the platform.
    """
    pool = await get_pool()

    async with operator_connection(pool) as conn:
        quarantine_exists = await conn.fetchval(
            "SELECT to_regclass('public.quarantine_events')"
        )
        rate_limit_exists = await conn.fetchval(
            "SELECT to_regclass('public.rate_limit_events')"
        )
        audit_exists = await conn.fetchval(
            "SELECT to_regclass('public.operator_audit_log')"
        )

        delivery_failures = await conn.fetch(
            """
            SELECT
                'delivery' as source,
                'delivery_failed' as error_type,
                created_at as timestamp,
                tenant_id,
                jsonb_build_object(
                    'job_id', job_id,
                    'integration_id', integration_id,
                    'attempts', attempts,
                    'last_error', last_error
                ) as details
            FROM delivery_jobs
            WHERE status = 'FAILED'
              AND created_at >= now() - ($1::int * interval '1 hour')
            ORDER BY created_at DESC
            LIMIT $2
            """,
            hours,
            limit,
        )

        quarantine_events = []
        if quarantine_exists:
            quarantine_events = await conn.fetch(
                """
                SELECT
                    'ingest' as source,
                    'quarantined' as error_type,
                    ingested_at as timestamp,
                    tenant_id,
                    jsonb_build_object(
                        'device_id', device_id,
                        'reason', reason,
                        'topic', topic
                    ) as details
                FROM quarantine_events
                WHERE ingested_at >= now() - ($1::int * interval '1 hour')
                ORDER BY ingested_at DESC
                LIMIT $2
                """,
                hours,
                limit,
            )

        auth_failures = await conn.fetch(
            """
            SELECT
                'auth' as source,
                'auth_failure' as error_type,
                created_at as timestamp,
                tenant_filter as tenant_id,
                jsonb_build_object(
                    'user_id', user_id,
                    'action', action,
                    'ip_address', ip_address
                ) as details
            FROM operator_audit_log
            WHERE (action LIKE '%fail%' OR action LIKE '%denied%')
              AND created_at >= now() - ($1::int * interval '1 hour')
            ORDER BY created_at DESC
            LIMIT $2
            """,
            hours,
            limit,
        )

        rate_limit_events = []
        if rate_limit_exists:
            rate_limit_events = await conn.fetch(
                """
                SELECT
                    'ingest' as source,
                    'rate_limited' as error_type,
                    created_at as timestamp,
                    tenant_id,
                    jsonb_build_object(
                        'device_id', device_id,
                        'count', event_count
                    ) as details
                FROM rate_limit_events
                WHERE created_at >= now() - ($1::int * interval '1 hour')
                ORDER BY created_at DESC
                LIMIT $2
                """,
                hours,
                limit,
            )
        if not audit_exists:
            auth_failures = []

        delivery_failures_count = await conn.fetchval(
            """
            SELECT COUNT(*) FROM delivery_jobs
            WHERE status = 'FAILED'
              AND created_at >= now() - ($1::int * interval '1 hour')
            """,
            hours,
        )
        stuck_deliveries_count = await conn.fetchval(
            """
            SELECT COUNT(*) FROM delivery_jobs
            WHERE status = 'PENDING'
              AND created_at < now() - interval '5 minutes'
            """
        )
        quarantined_count = 0
        if quarantine_exists:
            quarantined_count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM quarantine_events
                WHERE ingested_at >= now() - ($1::int * interval '1 hour')
                """,
                hours,
            )

    all_errors = []

    def _coerce_details(value):
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return {}
        return {}

    for row in delivery_failures:
        all_errors.append(
            {
                "source": row["source"],
                "error_type": row["error_type"],
                "timestamp": row["timestamp"].isoformat() + "Z",
                "tenant_id": row["tenant_id"],
                "details": _coerce_details(row["details"]),
            }
        )

    for row in quarantine_events:
        all_errors.append(
            {
                "source": row["source"],
                "error_type": row["error_type"],
                "timestamp": row["timestamp"].isoformat() + "Z",
                "tenant_id": row["tenant_id"],
                "details": _coerce_details(row["details"]),
            }
        )

    for row in auth_failures:
        all_errors.append(
            {
                "source": row["source"],
                "error_type": row["error_type"],
                "timestamp": row["timestamp"].isoformat() + "Z",
                "tenant_id": row["tenant_id"],
                "details": _coerce_details(row["details"]),
            }
        )

    for row in rate_limit_events:
        all_errors.append(
            {
                "source": row["source"],
                "error_type": row["error_type"],
                "timestamp": row["timestamp"].isoformat() + "Z",
                "tenant_id": row["tenant_id"],
                "details": _coerce_details(row["details"]),
            }
        )

    all_errors.sort(key=lambda x: x["timestamp"], reverse=True)

    return {
        "errors": all_errors[:limit],
        "counts": {
            "delivery_failures": delivery_failures_count or 0,
            "quarantined": quarantined_count or 0,
            "stuck_deliveries": stuck_deliveries_count or 0,
        },
        "period_hours": hours,
    }


async def get_postgres_capacity() -> dict:
    """Get PostgreSQL capacity metrics."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            db_size = await conn.fetchval("SELECT pg_database_size($1)", POSTGRES_DB)
            connections = await conn.fetchval(
                "SELECT count(*) FROM pg_stat_activity WHERE datname = $1",
                POSTGRES_DB,
            )
            max_conn = await conn.fetchval("SHOW max_connections")
            table_sizes = await conn.fetch(
                """
                SELECT
                    schemaname || '.' || relname as table_name,
                    pg_total_relation_size(relid) as total_size,
                    pg_relation_size(relid) as data_size,
                    pg_indexes_size(relid) as index_size
                FROM pg_catalog.pg_statio_user_tables
                ORDER BY pg_total_relation_size(relid) DESC
                LIMIT 10
                """
            )

        return {
            "db_size_bytes": db_size,
            "db_size_mb": round(db_size / (1024 * 1024), 2),
            "connections_used": connections,
            "connections_max": int(max_conn),
            "connections_pct": round(connections / int(max_conn) * 100, 1),
            "top_tables": [
                {
                    "name": r["table_name"],
                    "total_mb": round(r["total_size"] / (1024 * 1024), 2),
                    "data_mb": round(r["data_size"] / (1024 * 1024), 2),
                    "index_mb": round(r["index_size"] / (1024 * 1024), 2),
                }
                for r in table_sizes
            ],
        }
    except Exception as e:
        logger.error("Failed to get Postgres capacity: %s", e)
        raise


def get_disk_capacity() -> dict:
    """Get disk capacity for data volumes."""
    try:
        paths_to_check = [
            ("/", "root"),
            ("/var/lib/postgresql/data", "postgres_data"),
        ]

        volumes = {}
        for path, name in paths_to_check:
            try:
                usage = shutil.disk_usage(path)
                volumes[name] = {
                    "path": path,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2),
                    "used_pct": round(usage.used / usage.total * 100, 1),
                }
            except (FileNotFoundError, PermissionError):
                pass

        if not volumes:
            usage = shutil.disk_usage("/")
            volumes["root"] = {
                "path": "/",
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "used_pct": round(usage.used / usage.total * 100, 1),
            }

        return {"volumes": volumes}
    except Exception as e:
        logger.error("Failed to get disk capacity: %s", e)
        return {"error": str(e)}
