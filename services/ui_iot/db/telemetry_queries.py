"""
Telemetry queries using TimescaleDB.
Replaces InfluxDB queries.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import asyncpg

logger = logging.getLogger(__name__)


def _coerce_metrics(value) -> dict:
    if isinstance(value, dict):
        return value
    if value is None:
        return {}
    if isinstance(value, str):
        if not value:
            return {}
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


async def fetch_device_telemetry(
    conn: asyncpg.Connection,
    tenant_id: str,
    device_id: str,
    hours: int | None = 6,
    limit: int = 500,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[dict]:
    """
    Fetch recent telemetry for a device.
    Returns list of {time, metrics} dicts.
    """
    now = datetime.now(timezone.utc)
    if start is None:
        if hours is None:
            hours = 6
        end = end or now
        start = end - timedelta(hours=hours)
    else:
        end = end or now

    rows = await conn.fetch(
        """
        SELECT time, metrics, seq, msg_type
        FROM telemetry
        WHERE tenant_id = $1
          AND device_id = $2
          AND time >= $3
          AND time <= $4
        ORDER BY time DESC
        LIMIT $5
        """,
        tenant_id,
        device_id,
        start,
        end,
        limit,
    )

    return [
        {
            "timestamp": row["time"].isoformat(),
            "metrics": _coerce_metrics(row["metrics"]),
            "seq": row["seq"],
            "msg_type": row["msg_type"],
        }
        for row in rows
    ]


async def fetch_device_telemetry_latest(
    conn: asyncpg.Connection,
    tenant_id: str,
    device_id: str,
) -> Optional[dict]:
    """Fetch the most recent telemetry for a device."""
    row = await conn.fetchrow(
        """
        SELECT time, metrics, seq
        FROM telemetry
        WHERE tenant_id = $1 AND device_id = $2
        ORDER BY time DESC
        LIMIT 1
        """,
        tenant_id,
        device_id,
    )

    if not row:
        return None

    return {
        "timestamp": row["time"].isoformat(),
        "metrics": _coerce_metrics(row["metrics"]),
        "seq": row["seq"],
    }


async def fetch_device_events(
    conn: asyncpg.Connection,
    tenant_id: str,
    device_id: str,
    hours: int = 24,
    limit: int = 100,
) -> list[dict]:
    """Fetch events (non-telemetry messages) for a device."""
    rows = await conn.fetch(
        """
        SELECT time, msg_type, metrics, seq
        FROM telemetry
        WHERE tenant_id = $1
          AND device_id = $2
          AND msg_type != 'telemetry'
          AND time > now() - make_interval(hours => $3)
        ORDER BY time DESC
        LIMIT $4
        """,
        tenant_id,
        device_id,
        hours,
        limit,
    )

    return [
        {
            "timestamp": row["time"].isoformat(),
            "msg_type": row["msg_type"],
            "metrics": _coerce_metrics(row["metrics"]),
            "seq": row["seq"],
        }
        for row in rows
    ]


async def fetch_tenant_telemetry_stats(
    conn: asyncpg.Connection,
    tenant_id: str,
    hours: int = 24,
) -> dict:
    """Get telemetry statistics for a tenant."""
    row = await conn.fetchrow(
        """
        SELECT
            COUNT(*) as message_count,
            COUNT(DISTINCT device_id) as device_count,
            MIN(time) as earliest,
            MAX(time) as latest
        FROM telemetry
        WHERE tenant_id = $1
          AND time > now() - make_interval(hours => $2)
        """,
        tenant_id,
        hours,
    )

    return {
        "message_count": row["message_count"] or 0,
        "device_count": row["device_count"] or 0,
        "earliest": row["earliest"].isoformat() if row["earliest"] else None,
        "latest": row["latest"].isoformat() if row["latest"] else None,
        "period_hours": hours,
    }


async def fetch_fleet_telemetry_summary(
    conn: asyncpg.Connection,
    tenant_id: str,
    metric_keys: list[str],
    hours: int = 1,
) -> dict:
    """
    Get aggregated telemetry for dashboard widgets.
    Returns avg/min/max for specified metric keys.
    """
    metric_aggs = []
    for key in metric_keys:
        metric_aggs.append(
            f"""
            AVG((metrics->>'{key}')::numeric) FILTER (WHERE metrics ? '{key}') as {key}_avg,
            MIN((metrics->>'{key}')::numeric) FILTER (WHERE metrics ? '{key}') as {key}_min,
            MAX((metrics->>'{key}')::numeric) FILTER (WHERE metrics ? '{key}') as {key}_max
            """
        )

    query = f"""
        SELECT
            COUNT(*) as sample_count,
            COUNT(DISTINCT device_id) as device_count,
            {', '.join(metric_aggs)}
        FROM telemetry
        WHERE tenant_id = $1
          AND time > now() - make_interval(hours => $2)
          AND msg_type = 'telemetry'
    """

    row = await conn.fetchrow(query, tenant_id, hours)

    result = {
        "sample_count": row["sample_count"] or 0,
        "device_count": row["device_count"] or 0,
        "metrics": {},
    }

    for key in metric_keys:
        result["metrics"][key] = {
            "avg": float(row[f"{key}_avg"]) if row.get(f"{key}_avg") else None,
            "min": float(row[f"{key}_min"]) if row.get(f"{key}_min") else None,
            "max": float(row[f"{key}_max"]) if row.get(f"{key}_max") else None,
        }

    return result


async def fetch_telemetry_time_series(
    conn: asyncpg.Connection,
    tenant_id: str,
    device_id: Optional[str],
    metric_key: str,
    hours: int = 6,
    bucket_minutes: int = 5,
) -> list[dict]:
    """
    Get time-bucketed telemetry for charting.
    Uses TimescaleDB time_bucket for efficient aggregation.
    """
    if device_id:
        rows = await conn.fetch(
            """
            SELECT
                time_bucket($1::interval, time) as bucket,
                AVG((metrics->>$2)::numeric) as avg_value,
                MIN((metrics->>$2)::numeric) as min_value,
                MAX((metrics->>$2)::numeric) as max_value,
                COUNT(*) as sample_count
            FROM telemetry
            WHERE tenant_id = $3
              AND device_id = $4
              AND time > now() - make_interval(hours => $5)
              AND metrics ? $2
            GROUP BY bucket
            ORDER BY bucket ASC
            """,
            timedelta(minutes=bucket_minutes),
            metric_key,
            tenant_id,
            device_id,
            hours,
        )
    else:
        rows = await conn.fetch(
            """
            SELECT
                time_bucket($1::interval, time) as bucket,
                AVG((metrics->>$2)::numeric) as avg_value,
                MIN((metrics->>$2)::numeric) as min_value,
                MAX((metrics->>$2)::numeric) as max_value,
                COUNT(*) as sample_count,
                COUNT(DISTINCT device_id) as device_count
            FROM telemetry
            WHERE tenant_id = $3
              AND time > now() - make_interval(hours => $4)
              AND metrics ? $2
            GROUP BY bucket
            ORDER BY bucket ASC
            """,
            timedelta(minutes=bucket_minutes),
            metric_key,
            tenant_id,
            hours,
        )

    return [
        {
            "time": row["bucket"].isoformat(),
            "avg": float(row["avg_value"]) if row["avg_value"] else None,
            "min": float(row["min_value"]) if row["min_value"] else None,
            "max": float(row["max_value"]) if row["max_value"] else None,
            "samples": row["sample_count"],
        }
        for row in rows
    ]
