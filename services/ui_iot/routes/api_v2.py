import os
import json
import logging
import asyncio

from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from starlette.websockets import WebSocket, WebSocketDisconnect

import asyncpg

from middleware.auth import validate_token
from ws_manager import manager as ws_manager
from db.pool import tenant_connection
from db.queries import fetch_alerts
from db.telemetry_queries import fetch_device_telemetry_latest

logger = logging.getLogger(__name__)

PG_HOST = os.getenv("PG_HOST", "iot-postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "iotcloud")
PG_USER = os.getenv("PG_USER", "iot")
PG_PASS = os.environ["PG_PASS"]

WS_KEEPALIVE_SECONDS = float(os.getenv("WS_KEEPALIVE_SECONDS", "10"))


pool: asyncpg.Pool | None = None
_ws_notify_event = asyncio.Event()
_ws_listener_conn: asyncpg.Connection | None = None


async def get_pool() -> asyncpg.Pool:
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(
            host=PG_HOST, port=PG_PORT, database=PG_DB,
            user=PG_USER, password=PG_PASS,
            min_size=1, max_size=5,
        )
    return pool


def on_ws_notify(conn, pid, channel, payload):
    """Called on device_state_changed/new_fleet_alert notifications."""
    _ws_notify_event.set()


async def fetch_fleet_summary_for_tenant(conn, tenant_id: str) -> dict:
    """Fetch fleet summary payload for websocket fleet subscribers."""
    device_rows = await conn.fetch(
        """
        SELECT status, COUNT(*) AS cnt
        FROM device_state
        WHERE tenant_id = $1
        GROUP BY status
        """,
        tenant_id,
    )
    alert_count = await conn.fetchval(
        """
        SELECT COUNT(*)
        FROM fleet_alert
        WHERE tenant_id = $1
          AND status IN ('OPEN', 'ACKNOWLEDGED')
        """,
        tenant_id,
    )
    counts = {row["status"]: row["cnt"] for row in device_rows}
    total = int(sum(counts.values()))
    return {
        "ONLINE": int(counts.get("ONLINE", 0)),
        "STALE": int(counts.get("STALE", 0)),
        "OFFLINE": int(counts.get("OFFLINE", 0)),
        "total": total,
        "active_alerts": int(alert_count or 0),
    }


async def setup_ws_listener() -> None:
    """Create shared LISTEN connection used to wake websocket push loops."""
    global _ws_listener_conn
    if _ws_listener_conn is not None:
        return
    try:
        _ws_listener_conn = await asyncpg.connect(
            host=PG_HOST,
            port=PG_PORT,
            database=PG_DB,
            user=PG_USER,
            password=PG_PASS,
        )
        await _ws_listener_conn.add_listener("device_state_changed", on_ws_notify)
        await _ws_listener_conn.add_listener("new_fleet_alert", on_ws_notify)
        logger.info("[ws] LISTEN on device_state_changed + new_fleet_alert active")
    except Exception as exc:
        logger.warning("[ws] WARNING: LISTEN setup failed, using poll-only mode: %s", exc)
        _ws_listener_conn = None


async def shutdown_ws_listener() -> None:
    global _ws_listener_conn
    if _ws_listener_conn is not None:
        await _ws_listener_conn.close()
        _ws_listener_conn = None


ws_router = APIRouter()


async def _ws_push_loop(conn):
    """Background task that polls DB and pushes data to a WebSocket connection.

    Runs until the connection closes or an error occurs.
    """
    while True:
        try:
            try:
                await asyncio.wait_for(_ws_notify_event.wait(), timeout=WS_KEEPALIVE_SECONDS)
            except asyncio.TimeoutError:
                pass
            _ws_notify_event.clear()

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

            # Push fleet summary
            if conn.fleet_subscription:
                try:
                    p = await get_pool()
                    async with tenant_connection(p, conn.tenant_id) as db_conn:
                        summary = await fetch_fleet_summary_for_tenant(db_conn, conn.tenant_id)
                    await conn.websocket.send_json({
                        "type": "fleet_summary",
                        "data": summary,
                    })
                except Exception:
                    logger.debug("[ws] fleet summary push failed")

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

    # Extract roles from realm_access.roles (standard Keycloak roles scope).
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
                elif sub_type == "fleet":
                    ws_manager.subscribe_fleet(conn)
                    await websocket.send_json({
                        "type": "subscribed",
                        "channel": "fleet",
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
                elif sub_type == "fleet":
                    ws_manager.unsubscribe_fleet(conn)
                    await websocket.send_json({
                        "type": "unsubscribed",
                        "channel": "fleet",
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
