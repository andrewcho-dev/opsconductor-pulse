# Phase 30.5: Update Query Endpoints

## Task

Update all API endpoints that query telemetry to use PostgreSQL/TimescaleDB instead of InfluxDB.

---

## Update Influx Queries Module

**File:** `services/ui_iot/db/influx_queries.py`

Replace with PostgreSQL queries (or rename to `telemetry_queries.py`):

```python
"""
Telemetry queries using TimescaleDB.
Replaces InfluxDB queries.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import asyncpg

logger = logging.getLogger(__name__)


async def fetch_device_telemetry(
    conn: asyncpg.Connection,
    tenant_id: str,
    device_id: str,
    hours: int = 6,
    limit: int = 500,
) -> list[dict]:
    """
    Fetch recent telemetry for a device.
    Returns list of {time, metrics} dicts.
    """
    rows = await conn.fetch(
        """
        SELECT time, metrics, seq, msg_type
        FROM telemetry
        WHERE tenant_id = $1
          AND device_id = $2
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
            "time": row["time"].isoformat(),
            "metrics": dict(row["metrics"]) if row["metrics"] else {},
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
        "time": row["time"].isoformat(),
        "metrics": dict(row["metrics"]) if row["metrics"] else {},
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
            "time": row["time"].isoformat(),
            "msg_type": row["msg_type"],
            "metrics": dict(row["metrics"]) if row["metrics"] else {},
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
    # Build dynamic query for JSONB metric extraction
    metric_aggs = []
    for key in metric_keys:
        metric_aggs.append(f"""
            AVG((metrics->>'{key}')::numeric) FILTER (WHERE metrics ? '{key}') as {key}_avg,
            MIN((metrics->>'{key}')::numeric) FILTER (WHERE metrics ? '{key}') as {key}_min,
            MAX((metrics->>'{key}')::numeric) FILTER (WHERE metrics ? '{key}') as {key}_max
        """)

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
        # Fleet-wide aggregation
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
```

---

## Update API Routes

**File:** `services/ui_iot/routes/api_v2.py`

Update telemetry endpoints to use new queries:

```python
from db.telemetry_queries import (
    fetch_device_telemetry,
    fetch_device_telemetry_latest,
    fetch_device_events,
    fetch_tenant_telemetry_stats,
    fetch_fleet_telemetry_summary,
    fetch_telemetry_time_series,
)

# Remove InfluxDB client usage
# from db.influx_queries import fetch_device_telemetry_influx

@router.get("/devices/{device_id}/telemetry")
async def get_device_telemetry(
    request: Request,
    device_id: str,
    hours: int = Query(6, ge=1, le=168),
    limit: int = Query(500, ge=1, le=2000),
):
    """Get telemetry for a device."""
    tenant_id = get_tenant_id()
    pool = await get_pool()

    async with pool.acquire() as conn:
        # Set tenant context for RLS
        await conn.execute(f"SET app.tenant_id = '{tenant_id}'")

        telemetry = await fetch_device_telemetry(
            conn, tenant_id, device_id, hours=hours, limit=limit
        )

    return {
        "device_id": device_id,
        "tenant_id": tenant_id,
        "telemetry": telemetry,
        "hours": hours,
    }


@router.get("/telemetry/summary")
async def get_fleet_telemetry_summary(
    request: Request,
    hours: int = Query(1, ge=1, le=24),
):
    """Get fleet-wide telemetry summary for dashboard."""
    tenant_id = get_tenant_id()
    pool = await get_pool()

    async with pool.acquire() as conn:
        await conn.execute(f"SET app.tenant_id = '{tenant_id}'")

        summary = await fetch_fleet_telemetry_summary(
            conn,
            tenant_id,
            metric_keys=["battery_pct", "temp_c", "signal_dbm"],
            hours=hours,
        )

    return summary


@router.get("/telemetry/chart")
async def get_telemetry_chart(
    request: Request,
    metric: str = Query(..., description="Metric key to chart"),
    device_id: Optional[str] = Query(None),
    hours: int = Query(6, ge=1, le=168),
    bucket_minutes: int = Query(5, ge=1, le=60),
):
    """Get time-series data for charting."""
    tenant_id = get_tenant_id()
    pool = await get_pool()

    async with pool.acquire() as conn:
        await conn.execute(f"SET app.tenant_id = '{tenant_id}'")

        series = await fetch_telemetry_time_series(
            conn,
            tenant_id,
            device_id=device_id,
            metric_key=metric,
            hours=hours,
            bucket_minutes=bucket_minutes,
        )

    return {
        "metric": metric,
        "device_id": device_id,
        "series": series,
        "hours": hours,
    }
```

---

## Update Operator Routes

**File:** `services/ui_iot/routes/operator.py`

Remove InfluxDB usage in operator device views:

```python
# Remove InfluxDB imports
# from db.influx_queries import fetch_device_telemetry_influx, fetch_device_events_influx

from db.telemetry_queries import fetch_device_telemetry, fetch_device_events

@router.get("/tenants/{tenant_id}/devices/{device_id}")
async def view_device(request: Request, tenant_id: str, device_id: str):
    """View device details with telemetry."""
    # ... existing code ...

    async with operator_connection(pool) as conn:
        device = await fetch_device(conn, tenant_id, device_id)
        if not device:
            raise HTTPException(404, "Device not found")

        # Use PostgreSQL queries instead of InfluxDB
        events = await fetch_device_events(conn, tenant_id, device_id, hours=24, limit=50)
        telemetry = await fetch_device_telemetry(conn, tenant_id, device_id, hours=6, limit=120)

    return {
        "tenant_id": tenant_id,
        "device": device,
        "events": events,
        "telemetry": telemetry,
    }
```

---

## Verification

```bash
# Rebuild UI service
cd /home/opsconductor/simcloud/compose
docker compose build ui
docker compose up -d ui

# Test API endpoints
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8080/api/v2/devices/test-001/telemetry?hours=1"

curl -H "Authorization: Bearer <token>" \
  "http://localhost:8080/api/v2/telemetry/summary"
```

---

## Files

| Action | File |
|--------|------|
| CREATE | `services/ui_iot/db/telemetry_queries.py` (or rename influx_queries.py) |
| MODIFY | `services/ui_iot/routes/api_v2.py` |
| MODIFY | `services/ui_iot/routes/operator.py` |
