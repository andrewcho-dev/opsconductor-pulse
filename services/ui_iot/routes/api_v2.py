import os
import json
import time
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from starlette.websockets import WebSocket, WebSocketDisconnect

import asyncpg

from middleware.auth import JWTBearer
from middleware.auth import validate_token
from middleware.tenant import inject_tenant_context, require_customer, get_tenant_id, get_user
from ws_manager import manager as ws_manager
from db.pool import tenant_connection
from db.queries import (
    fetch_devices_v2,
    fetch_device_v2,
    fetch_alerts_v2,
    fetch_alert_v2,
    fetch_alert_rules,
    fetch_alert_rule,
    fetch_alerts,
)
from db.telemetry_queries import (
    fetch_device_telemetry,
    fetch_device_telemetry_latest,
    fetch_fleet_telemetry_summary,
    fetch_telemetry_time_series,
)

logger = logging.getLogger(__name__)

PG_HOST = os.getenv("PG_HOST", "iot-postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "iotcloud")
PG_USER = os.getenv("PG_USER", "iot")
PG_PASS = os.getenv("PG_PASS", "iot_dev")

API_RATE_LIMIT = int(os.getenv("API_RATE_LIMIT", "100"))
API_RATE_WINDOW = int(os.getenv("API_RATE_WINDOW_SECONDS", "60"))
WS_POLL_SECONDS = int(os.getenv("WS_POLL_SECONDS", "5"))


pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(
            host=PG_HOST, port=PG_PORT, database=PG_DB,
            user=PG_USER, password=PG_PASS,
            min_size=1, max_size=5,
        )
    return pool


# --- In-memory rate limiter ---
_rate_buckets: dict[str, deque] = defaultdict(deque)


def _check_rate_limit(tenant_id: str) -> bool:
    """Return True if request is allowed, False if rate limit exceeded."""
    now = time.time()
    bucket = _rate_buckets[tenant_id]
    cutoff = now - API_RATE_WINDOW
    while bucket and bucket[0] < cutoff:
        bucket.popleft()
    if len(bucket) >= API_RATE_LIMIT:
        return False
    bucket.append(now)
    return True


async def enforce_rate_limit():
    """FastAPI dependency that enforces per-tenant API rate limiting."""
    tenant_id = get_tenant_id()
    if not _check_rate_limit(tenant_id):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded ({API_RATE_LIMIT} requests per {API_RATE_WINDOW}s)",
        )


router = APIRouter(
    prefix="/api/v2",
    tags=["api-v2"],
    dependencies=[
        Depends(JWTBearer()),
        Depends(inject_tenant_context),
        Depends(require_customer),
        Depends(enforce_rate_limit),
    ],
)

# Separate router for WebSocket — no HTTP auth dependencies
# (WebSocket auth is handled inside the endpoint via query param token)
ws_router = APIRouter()


@router.get("/devices")
async def list_devices(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List all devices for the authenticated tenant with full metric state."""
    tenant_id = get_tenant_id()
    p = await get_pool()
    async with tenant_connection(p, tenant_id) as conn:
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM device_state WHERE tenant_id = $1",
            tenant_id,
        )
        devices = await fetch_devices_v2(conn, tenant_id, limit=limit, offset=offset)
    for device in devices:
        state = device.get("state")
        if isinstance(state, dict):
            device["state"] = state
        elif state is None:
            device["state"] = {}
        elif isinstance(state, str):
            try:
                device["state"] = json.loads(state)
            except json.JSONDecodeError:
                device["state"] = {}
        else:
            device["state"] = state
    return JSONResponse(jsonable_encoder({
        "tenant_id": tenant_id,
        "devices": devices,
        "count": len(devices),
        "total": total or 0,
        "limit": limit,
        "offset": offset,
    }))


@router.get("/fleet/summary")
async def get_fleet_summary():
    """Fleet health summary for dashboard widget."""
    tenant_id = get_tenant_id()
    p = await get_pool()

    low_battery_threshold = 20

    async with tenant_connection(p, tenant_id) as conn:
        device_counts = await conn.fetchrow(
            """
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE status = 'ONLINE') AS online,
                COUNT(*) FILTER (WHERE status = 'STALE') AS stale,
                COUNT(*) FILTER (WHERE status = 'OFFLINE') AS offline
            FROM device_state
            WHERE tenant_id = $1
            """,
            tenant_id,
        )

        alert_counts = await conn.fetchrow(
            """
            SELECT
                COUNT(*) AS open_alerts,
                COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour') AS new_1h
            FROM fleet_alert
            WHERE tenant_id = $1 AND status = 'OPEN'
            """,
            tenant_id,
        )

        low_battery_count = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM device_state
            WHERE tenant_id = $1
              AND (state->>'battery_pct') ~ '^[0-9]+(\\.[0-9]+)?$'
              AND (state->>'battery_pct')::float < $2
            """,
            tenant_id,
            low_battery_threshold,
        )

        low_battery_devices = await conn.fetch(
            """
            SELECT device_id
            FROM device_state
            WHERE tenant_id = $1
              AND (state->>'battery_pct') ~ '^[0-9]+(\\.[0-9]+)?$'
              AND (state->>'battery_pct')::float < $2
            ORDER BY device_id
            LIMIT 10
            """,
            tenant_id,
            low_battery_threshold,
        )

    return JSONResponse(jsonable_encoder({
        "total_devices": device_counts["total"] or 0,
        "online": device_counts["online"] or 0,
        "stale": device_counts["stale"] or 0,
        "offline": device_counts["offline"] or 0,
        "alerts_open": alert_counts["open_alerts"] or 0,
        "alerts_new_1h": alert_counts["new_1h"] or 0,
        "low_battery_count": low_battery_count or 0,
        "low_battery_threshold": low_battery_threshold,
        "low_battery_devices": [row["device_id"] for row in low_battery_devices],
    }))


@router.get("/devices/{device_id}")
async def get_device(device_id: str):
    """Get device detail with full state JSONB and timestamps."""
    tenant_id = get_tenant_id()
    p = await get_pool()
    async with tenant_connection(p, tenant_id) as conn:
        device = await fetch_device_v2(conn, tenant_id, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    state = device.get("state")
    if isinstance(state, dict):
        device["state"] = state
    elif state is None:
        device["state"] = {}
    elif isinstance(state, str):
        try:
            device["state"] = json.loads(state)
        except json.JSONDecodeError:
            device["state"] = {}
    else:
        device["state"] = state
    return JSONResponse(jsonable_encoder({
        "tenant_id": tenant_id,
        "device": device,
    }))


@router.get("/alerts")
async def list_alerts(
    status: str = Query("OPEN"),
    alert_type: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List alerts with optional status and alert_type filters."""
    tenant_id = get_tenant_id()
    p = await get_pool()
    async with tenant_connection(p, tenant_id) as conn:
        alerts = await fetch_alerts_v2(
            conn, tenant_id, status=status, alert_type=alert_type,
            limit=limit, offset=offset,
        )
    return JSONResponse(jsonable_encoder({
        "tenant_id": tenant_id,
        "alerts": alerts,
        "count": len(alerts),
        "status": status,
        "alert_type": alert_type,
        "limit": limit,
        "offset": offset,
    }))


@router.get("/alerts/trend")
async def get_alert_trend(
    request: Request,
    hours: int = Query(24, ge=1, le=168),
):
    """
    Get hourly alert counts for the last N hours.
    Returns [{hour: ISO timestamp, opened: count, closed: count}, ...]
    """
    pool = await get_pool()
    tenant_id = get_tenant_id()

    async with pool.acquire() as conn:
        # Set tenant context for RLS
        await conn.execute("SELECT set_config('app.tenant_id', $1, true)", tenant_id)

        rows = await conn.fetch("""
            WITH hours AS (
                SELECT generate_series(
                    date_trunc('hour', now() - interval '1 hour' * $1),
                    date_trunc('hour', now()),
                    interval '1 hour'
                ) AS hour
            ),
            opened AS (
                SELECT date_trunc('hour', created_at) AS hour, COUNT(*) AS cnt
                FROM fleet_alert
                WHERE created_at >= now() - interval '1 hour' * $1
                GROUP BY 1
            ),
            closed AS (
                SELECT date_trunc('hour', closed_at) AS hour, COUNT(*) AS cnt
                FROM fleet_alert
                WHERE closed_at >= now() - interval '1 hour' * $1
                GROUP BY 1
            )
            SELECT
                h.hour,
                COALESCE(o.cnt, 0) AS opened,
                COALESCE(c.cnt, 0) AS closed
            FROM hours h
            LEFT JOIN opened o ON o.hour = h.hour
            LEFT JOIN closed c ON c.hour = h.hour
            ORDER BY h.hour
        """, hours)

    return {
        "trend": [
            {"hour": row["hour"].isoformat(), "opened": row["opened"], "closed": row["closed"]}
            for row in rows
        ]
    }


@router.get("/alerts/{alert_id}")
async def get_alert(alert_id: int):
    """Get alert detail with full details JSONB."""
    tenant_id = get_tenant_id()
    p = await get_pool()
    async with tenant_connection(p, tenant_id) as conn:
        alert = await fetch_alert_v2(conn, tenant_id, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return JSONResponse(jsonable_encoder({
        "tenant_id": tenant_id,
        "alert": alert,
    }))


@router.get("/alert-rules")
async def list_alert_rules(
    limit: int = Query(100, ge=1, le=500),
):
    """List all alert rules for the authenticated tenant."""
    tenant_id = get_tenant_id()
    p = await get_pool()
    async with tenant_connection(p, tenant_id) as conn:
        rules = await fetch_alert_rules(conn, tenant_id, limit=limit)
    return JSONResponse(jsonable_encoder({
        "tenant_id": tenant_id,
        "rules": rules,
        "count": len(rules),
    }))


@router.get("/alert-rules/{rule_id}")
async def get_alert_rule(rule_id: str):
    """Get a single alert rule by ID."""
    tenant_id = get_tenant_id()
    p = await get_pool()
    async with tenant_connection(p, tenant_id) as conn:
        rule = await fetch_alert_rule(conn, tenant_id, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return JSONResponse(jsonable_encoder({
        "tenant_id": tenant_id,
        "rule": rule,
    }))


@router.get("/devices/{device_id}/telemetry")
async def get_device_telemetry(
    device_id: str,
    hours: int | None = Query(None, ge=1, le=168),
    limit: int = Query(500, ge=1, le=2000),
    start: str | None = Query(None),
    end: str | None = Query(None),
):
    """Get telemetry for a device."""
    tenant_id = get_tenant_id()

    start_dt: datetime | None = None
    end_dt: datetime | None = None
    if start:
        try:
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            end_dt = (
                datetime.fromisoformat(end.replace("Z", "+00:00"))
                if end
                else datetime.now(timezone.utc)
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid start/end timestamp") from exc
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=timezone.utc)
        if start_dt > end_dt:
            raise HTTPException(status_code=400, detail="Start must be before end")
    else:
        if hours is None:
            hours = 24
        end_dt = datetime.now(timezone.utc)
        start_dt = end_dt - timedelta(hours=hours)

    p = await get_pool()
    async with tenant_connection(p, tenant_id) as conn:
        device = await fetch_device_v2(conn, tenant_id, device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        data = await fetch_device_telemetry(
            conn,
            tenant_id,
            device_id,
            hours=None,
            limit=limit,
            start=start_dt,
            end=end_dt,
        )

    response = {
        "tenant_id": tenant_id,
        "device_id": device_id,
        "telemetry": data,
        "hours": hours,
        "start": start_dt.isoformat() if start_dt else None,
        "end": end_dt.isoformat() if end_dt else None,
    }
    return JSONResponse(jsonable_encoder(response))


@router.get("/devices/{device_id}/telemetry/latest")
async def get_device_telemetry_latest(
    device_id: str,
    count: int = Query(1, ge=1, le=10),
):
    """Fetch the most recent telemetry readings for a device.

    Defaults to 1 (the latest reading). Max 10.
    """
    tenant_id = get_tenant_id()

    p = await get_pool()
    async with tenant_connection(p, tenant_id) as conn:
        device = await fetch_device_v2(conn, tenant_id, device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        if count == 1:
            latest = await fetch_device_telemetry_latest(conn, tenant_id, device_id)
            data = [latest] if latest else []
        else:
            data = await fetch_device_telemetry(conn, tenant_id, device_id, hours=168, limit=count)
    return JSONResponse(jsonable_encoder({
        "device_id": device_id,
        "telemetry": data,
        "count": len(data),
    }))


@router.get("/telemetry/summary")
async def get_fleet_telemetry_summary(
    request: Request,
    hours: int = Query(1, ge=1, le=24),
):
    """Get fleet-wide telemetry summary for dashboard."""
    tenant_id = get_tenant_id()
    p = await get_pool()

    async with tenant_connection(p, tenant_id) as conn:
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
    device_id: str | None = Query(None),
    hours: int = Query(6, ge=1, le=168),
    bucket_minutes: int = Query(5, ge=1, le=60),
):
    """Get time-series data for charting."""
    tenant_id = get_tenant_id()
    p = await get_pool()

    async with tenant_connection(p, tenant_id) as conn:
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


@router.get("/metrics/reference")
async def get_metrics_reference():
    """Return discovered raw metrics, mappings, and normalized metrics."""
    tenant_id = get_tenant_id()
    p = await get_pool()

    async with tenant_connection(p, tenant_id) as conn:
        raw_rows = await conn.fetch(
            """
            SELECT DISTINCT key AS metric_name
            FROM telemetry
            CROSS JOIN LATERAL jsonb_object_keys(metrics) AS key
            WHERE tenant_id = $1
              AND time > NOW() - INTERVAL '7 days'
              AND metrics IS NOT NULL
              AND jsonb_typeof(metrics) = 'object'
            ORDER BY metric_name
            LIMIT 200
            """,
            tenant_id,
        )
        mapping_rows = await conn.fetch(
            """
            SELECT raw_metric, normalized_name
            FROM metric_mappings
            WHERE tenant_id = $1
            """,
            tenant_id,
        )
        normalized_rows = await conn.fetch(
            """
            SELECT normalized_name, display_unit, description, expected_min, expected_max
            FROM normalized_metrics
            WHERE tenant_id = $1
            ORDER BY normalized_name
            """,
            tenant_id,
        )

    raw_metrics = [r["metric_name"] for r in raw_rows]
    mapping_by_raw = {r["raw_metric"]: r["normalized_name"] for r in mapping_rows}
    mapped_from: dict[str, list[str]] = {}
    for row in mapping_rows:
        mapped_from.setdefault(row["normalized_name"], []).append(row["raw_metric"])

    normalized_metrics = [
        {
            "name": row["normalized_name"],
            "display_unit": row["display_unit"],
            "description": row["description"],
            "expected_min": row["expected_min"],
            "expected_max": row["expected_max"],
            "mapped_from": sorted(mapped_from.get(row["normalized_name"], [])),
        }
        for row in normalized_rows
    ]

    raw_metrics_response = [
        {"name": name, "mapped_to": mapping_by_raw.get(name)}
        for name in raw_metrics
    ]
    unmapped = [name for name in raw_metrics if name not in mapping_by_raw]

    return {
        "raw_metrics": raw_metrics_response,
        "normalized_metrics": normalized_metrics,
        "unmapped": unmapped,
    }


async def _ws_push_loop(conn):
    """Background task that polls DB and pushes data to a WebSocket connection.

    Runs until the connection closes or an error occurs.
    """
    while True:
        try:
            await asyncio.sleep(WS_POLL_SECONDS)

            # Push telemetry for subscribed devices
            if conn.device_subscriptions:
                try:
                    p = await get_pool()
                    async with tenant_connection(p, conn.tenant_id) as db_conn:
                        for device_id in list(conn.device_subscriptions):
                            try:
                                latest = await fetch_device_telemetry_latest(
                                    db_conn, conn.tenant_id, device_id
                                )
                                if latest:
                                    await conn.websocket.send_json({
                                        "type": "telemetry",
                                        "device_id": device_id,
                                        "data": latest,
                                    })
                            except Exception:
                                logger.debug("[ws] telemetry push failed for %s", device_id)
                except Exception:
                    logger.debug("[ws] telemetry push failed")

            # Push alerts
            if conn.alert_subscription:
                try:
                    p = await get_pool()
                    async with tenant_connection(p, conn.tenant_id) as db_conn:
                        alerts = await fetch_alerts(db_conn, conn.tenant_id, status="OPEN", limit=100)
                    await conn.websocket.send_json({
                        "type": "alerts",
                        "alerts": jsonable_encoder(alerts),
                    })
                except Exception:
                    logger.debug("[ws] alert push failed")

        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("[ws] push loop error, closing")
            break


@ws_router.websocket("/api/v2/ws")
async def websocket_endpoint(websocket: WebSocket, token: str | None = None):
    """WebSocket endpoint for live telemetry and alert streaming.

    Auth: Pass JWT as query param: ws://host/api/v2/ws?token=JWT_TOKEN

    Client messages (JSON):
        {"action": "subscribe", "type": "device", "device_id": "dev-0001"}
        {"action": "subscribe", "type": "alerts"}
        {"action": "unsubscribe", "type": "device", "device_id": "dev-0001"}
        {"action": "unsubscribe", "type": "alerts"}

    Server messages (JSON):
        {"type": "telemetry", "device_id": "dev-0001", "data": {"time": "...", "metrics": {...}}}
        {"type": "alerts", "alerts": [...]}
        {"type": "subscribed", "channel": "device", "device_id": "dev-0001"}
        {"type": "subscribed", "channel": "alerts"}
        {"type": "error", "message": "..."}
    """
    if not token:
        await websocket.close(code=4001, reason="Missing token parameter")
        return

    try:
        payload = await validate_token(token)
    except Exception:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    # Extract tenant ID from organization claim (new format), with legacy fallback.
    tenant_id = None
    orgs = payload.get("organization", {}) or {}
    if isinstance(orgs, dict) and orgs:
        tenant_id = next(iter(orgs.keys()))
    elif isinstance(orgs, list):
        for org in orgs:
            if isinstance(org, str) and org:
                tenant_id = org
                break
    if not tenant_id:
        tenant_id = payload.get("tenant_id")

    # Extract roles from realm_access.roles (new format).
    realm_access = payload.get("realm_access", {}) or {}
    roles = realm_access.get("roles", []) or []
    if not isinstance(roles, list):
        roles = []

    valid_roles = ("customer", "tenant-admin", "operator", "operator-admin")
    if not any(role in valid_roles for role in roles):
        await websocket.close(code=4003, reason="Unauthorized")
        return
    # Operators have no tenant_id — use a placeholder for the WS connection
    if not tenant_id:
        tenant_id = "__operator__"

    conn = await ws_manager.connect(websocket, tenant_id, payload)
    push_task = asyncio.create_task(_ws_push_loop(conn))

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            sub_type = data.get("type")

            if action == "subscribe":
                if sub_type == "device":
                    device_id = data.get("device_id")
                    if device_id:
                        ws_manager.subscribe_device(conn, device_id)
                        await websocket.send_json({
                            "type": "subscribed",
                            "channel": "device",
                            "device_id": device_id,
                        })
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "message": "device_id required for device subscription",
                        })
                elif sub_type == "alerts":
                    ws_manager.subscribe_alerts(conn)
                    await websocket.send_json({
                        "type": "subscribed",
                        "channel": "alerts",
                    })

            elif action == "unsubscribe":
                if sub_type == "device":
                    device_id = data.get("device_id")
                    if device_id:
                        ws_manager.unsubscribe_device(conn, device_id)
                        await websocket.send_json({
                            "type": "unsubscribed",
                            "channel": "device",
                            "device_id": device_id,
                        })
                elif sub_type == "alerts":
                    ws_manager.unsubscribe_alerts(conn)
                    await websocket.send_json({
                        "type": "unsubscribed",
                        "channel": "alerts",
                    })

    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("[ws] error in WebSocket handler")
    finally:
        push_task.cancel()
        try:
            await push_task
        except asyncio.CancelledError:
            pass
        await ws_manager.disconnect(conn)
