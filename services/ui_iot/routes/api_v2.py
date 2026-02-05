import os
import time
import logging
import re
import asyncio
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from starlette.websockets import WebSocket, WebSocketDisconnect

import asyncpg
import httpx

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
from db.influx_queries import fetch_device_telemetry_dynamic

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
_influx_client: httpx.AsyncClient | None = None


def _get_influx_client() -> httpx.AsyncClient:
    global _influx_client
    if _influx_client is None:
        _influx_client = httpx.AsyncClient(timeout=10.0)
    return _influx_client


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


_ISO8601_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


def _validate_timestamp(value: str | None, param_name: str) -> str | None:
    """Validate and sanitize an ISO 8601 timestamp for use in InfluxDB SQL.

    Returns None if value is None. Raises 400 if format is invalid.
    """
    if value is None:
        return None
    if not _ISO8601_PATTERN.match(value):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {param_name}: expected ISO 8601 format (e.g., 2024-01-15T10:30:00Z)",
        )
    # Sanitize: only allow expected characters to prevent SQL injection
    clean = re.sub(r"[^0-9A-Za-z\-:T.Z+]", "", value)
    return clean


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
        devices = await fetch_devices_v2(conn, tenant_id, limit=limit, offset=offset)
    return JSONResponse(jsonable_encoder({
        "tenant_id": tenant_id,
        "devices": devices,
        "count": len(devices),
        "limit": limit,
        "offset": offset,
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
    start: str | None = Query(None, description="ISO 8601 start time"),
    end: str | None = Query(None, description="ISO 8601 end time"),
    limit: int = Query(120, ge=1, le=1000),
):
    """Fetch device telemetry with all dynamic metrics.

    Returns all metric columns (battery_pct, temp_c, pressure_psi, etc.)
    rather than a hardcoded set. Supports time-range filtering.
    """
    tenant_id = get_tenant_id()

    # Validate timestamp parameters
    clean_start = _validate_timestamp(start, "start")
    clean_end = _validate_timestamp(end, "end")

    # Verify device exists and belongs to tenant (prevents InfluxDB injection)
    p = await get_pool()
    async with tenant_connection(p, tenant_id) as conn:
        device = await fetch_device_v2(conn, tenant_id, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    ic = _get_influx_client()
    data = await fetch_device_telemetry_dynamic(
        ic, tenant_id, device_id,
        start=clean_start, end=clean_end, limit=limit,
    )
    return JSONResponse(jsonable_encoder({
        "device_id": device_id,
        "telemetry": data,
        "count": len(data),
    }))


@router.get("/devices/{device_id}/telemetry/latest")
async def get_device_telemetry_latest(
    device_id: str,
    count: int = Query(1, ge=1, le=10),
):
    """Fetch the most recent telemetry readings for a device.

    Defaults to 1 (the latest reading). Max 10.
    """
    tenant_id = get_tenant_id()

    # Verify device exists and belongs to tenant
    p = await get_pool()
    async with tenant_connection(p, tenant_id) as conn:
        device = await fetch_device_v2(conn, tenant_id, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    ic = _get_influx_client()
    data = await fetch_device_telemetry_dynamic(ic, tenant_id, device_id, limit=count)
    return JSONResponse(jsonable_encoder({
        "device_id": device_id,
        "telemetry": data,
        "count": len(data),
    }))


async def _ws_push_loop(conn):
    """Background task that polls DB and pushes data to a WebSocket connection.

    Runs until the connection closes or an error occurs.
    """
    from db.influx_queries import fetch_device_telemetry_dynamic

    while True:
        try:
            await asyncio.sleep(WS_POLL_SECONDS)

            # Push telemetry for subscribed devices
            if conn.device_subscriptions:
                ic = _get_influx_client()
                for device_id in list(conn.device_subscriptions):
                    try:
                        data = await fetch_device_telemetry_dynamic(
                            ic, conn.tenant_id, device_id, limit=1,
                        )
                        if data:
                            await conn.websocket.send_json({
                                "type": "telemetry",
                                "device_id": device_id,
                                "data": data[0],
                            })
                    except Exception:
                        logger.debug("[ws] telemetry push failed for %s", device_id)

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
        {"type": "telemetry", "device_id": "dev-0001", "data": {"timestamp": "...", "metrics": {...}}}
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

    tenant_id = payload.get("tenant_id")
    role = payload.get("role", "")
    if not tenant_id or role not in ("customer_admin", "customer_viewer"):
        await websocket.close(code=4003, reason="Unauthorized")
        return

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
