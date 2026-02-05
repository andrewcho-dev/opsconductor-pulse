# Task 004: WebSocket Live Telemetry + Alerts

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

**THE PROBLEM**: The current UI refreshes data by reloading entire pages every 5 seconds. External dashboards and mobile apps need a real-time data feed. WebSocket enables push-based updates for device telemetry and alert state changes.

**Read first**:
- `services/ui_iot/routes/api_v2.py` — the router from Tasks 001-003, including `_get_influx_client()`, `get_pool()`, `ws_router`
- `services/ui_iot/middleware/auth.py` — `validate_token(token)` function (line 77) — used for WebSocket auth
- `services/ui_iot/db/influx_queries.py` — `fetch_device_telemetry_dynamic` (from Task 003) — used for telemetry push
- `services/ui_iot/db/queries.py` — `fetch_alerts` (lines 86-106) — used for alert push
- `services/ui_iot/db/pool.py` — `tenant_connection` context manager

**Design decisions**:
- **Auth via query param**: Browsers cannot set custom headers on WebSocket connections. The JWT is passed as `?token=JWT` query parameter.
- **Polling-bridge pattern**: Server polls InfluxDB and PostgreSQL at a configurable interval and pushes to subscribed clients. This is simple and matches the existing polling architecture.
- **Per-connection polling**: Each WebSocket connection has its own background polling task. Simple for the current scale (~100 concurrent connections).
- **Client protocol**: JSON messages for subscribe/unsubscribe. Server pushes JSON messages with telemetry data or alert lists.

---

## Task

### 4.1 Create WebSocket connection manager

**File**: `services/ui_iot/ws_manager.py` (NEW)

Create a simple connection manager that tracks active WebSocket connections and their subscriptions:

```python
import logging
from dataclasses import dataclass, field

from starlette.websockets import WebSocket

logger = logging.getLogger(__name__)


@dataclass
class WSConnection:
    """Represents a single WebSocket client connection with its subscriptions."""
    websocket: WebSocket
    tenant_id: str
    user: dict
    device_subscriptions: set = field(default_factory=set)
    alert_subscription: bool = False


class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self):
        self.connections: list[WSConnection] = []

    async def connect(self, websocket: WebSocket, tenant_id: str, user: dict) -> WSConnection:
        """Accept a WebSocket connection and track it."""
        await websocket.accept()
        conn = WSConnection(websocket=websocket, tenant_id=tenant_id, user=user)
        self.connections.append(conn)
        logger.info("[ws] connected: tenant=%s email=%s", tenant_id, user.get("email"))
        return conn

    async def disconnect(self, conn: WSConnection):
        """Remove a connection from tracking."""
        if conn in self.connections:
            self.connections.remove(conn)
        logger.info("[ws] disconnected: tenant=%s", conn.tenant_id)

    def subscribe_device(self, conn: WSConnection, device_id: str):
        """Add a device to the connection's telemetry subscriptions."""
        conn.device_subscriptions.add(device_id)

    def unsubscribe_device(self, conn: WSConnection, device_id: str):
        """Remove a device from the connection's telemetry subscriptions."""
        conn.device_subscriptions.discard(device_id)

    def subscribe_alerts(self, conn: WSConnection):
        """Enable alert push for this connection."""
        conn.alert_subscription = True

    def unsubscribe_alerts(self, conn: WSConnection):
        """Disable alert push for this connection."""
        conn.alert_subscription = False

    @property
    def connection_count(self) -> int:
        return len(self.connections)


manager = ConnectionManager()
```

This module has NO external dependencies beyond Starlette (which is always available). This makes it easy to test.

### 4.2 Add WebSocket endpoint and push loop to api_v2.py

**File**: `services/ui_iot/routes/api_v2.py`

Add these imports near the top with the existing imports:

```python
import asyncio
from starlette.websockets import WebSocket, WebSocketDisconnect
from middleware.auth import validate_token
from ws_manager import manager as ws_manager
from db.queries import fetch_alerts
```

Note: `validate_token` may already be indirectly imported through JWTBearer. Import it directly for use in the WebSocket handler.

Also add the `WS_POLL_SECONDS` env var near the other env vars:

```python
WS_POLL_SECONDS = int(os.getenv("WS_POLL_SECONDS", "5"))
```

Add the push loop function after the existing telemetry endpoints (but before any future endpoints):

```python
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
```

Add the WebSocket endpoint to `ws_router` (NOT `router` — the ws_router has no HTTP auth dependencies):

```python
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
```

**Important notes**:
- The WebSocket endpoint is on `ws_router` (NOT `router`), because HTTP auth dependencies like JWTBearer don't work with WebSocket connections. Auth is handled manually via `validate_token(token)`.
- The `ws_router` was already created in Task 001 and mounted in app.py. No changes to app.py needed.
- The push loop imports `fetch_device_telemetry_dynamic` inline to avoid circular imports.
- `jsonable_encoder` is used for alerts because they contain datetime objects.
- The push loop catches `asyncio.CancelledError` and re-raises (standard pattern for cleanup on cancellation).

---

## Files to Modify

| Action | Path | What changes |
|--------|------|--------------|
| CREATE | `services/ui_iot/ws_manager.py` | WSConnection dataclass + ConnectionManager class |
| MODIFY | `services/ui_iot/routes/api_v2.py` | Add WebSocket endpoint, push loop, WS imports |

---

## Test

### Step 1: Run existing unit tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

### Step 2: Verify WebSocket code

Read the files and confirm:
- [ ] `ws_manager.py` has `WSConnection` dataclass with `device_subscriptions: set` and `alert_subscription: bool`
- [ ] `ConnectionManager` has `connect`, `disconnect`, `subscribe_device`, `unsubscribe_device`, `subscribe_alerts`, `unsubscribe_alerts` methods
- [ ] Module-level `manager = ConnectionManager()` singleton
- [ ] WebSocket endpoint on `ws_router` at `/api/v2/ws`
- [ ] Token extracted from query param, validated with `validate_token`
- [ ] Role check: only `customer_admin` or `customer_viewer`
- [ ] Background push task created with `asyncio.create_task`
- [ ] Push loop polls every `WS_POLL_SECONDS` (default 5)
- [ ] Telemetry push: calls `fetch_device_telemetry_dynamic` with `limit=1` per subscribed device
- [ ] Alert push: calls `fetch_alerts` within `tenant_connection` for RLS
- [ ] `finally` block cancels push task and disconnects
- [ ] Client messages handled: subscribe/unsubscribe for device and alerts
- [ ] Server sends confirmation messages: `{"type": "subscribed", ...}`

### Step 3: Trace through a connection scenario

Verify the code handles this flow:
1. Client connects: `ws://host/api/v2/ws?token=VALID_JWT`
2. Server validates token, extracts tenant_id, accepts connection
3. Client sends: `{"action": "subscribe", "type": "device", "device_id": "dev-0001"}`
4. Server responds: `{"type": "subscribed", "channel": "device", "device_id": "dev-0001"}`
5. Every 5 seconds, server queries InfluxDB for dev-0001's latest telemetry
6. Server pushes: `{"type": "telemetry", "device_id": "dev-0001", "data": {"timestamp": "...", "metrics": {...}}}`
7. Client sends: `{"action": "subscribe", "type": "alerts"}`
8. Server also pushes: `{"type": "alerts", "alerts": [...]}`
9. Client disconnects → push task cancelled, connection removed from manager

---

## Acceptance Criteria

- [ ] `ws_manager.py` has WSConnection dataclass and ConnectionManager class
- [ ] WebSocket endpoint validates JWT from query param
- [ ] Client can subscribe/unsubscribe to device telemetry and alerts
- [ ] Server pushes telemetry data for subscribed devices at regular intervals
- [ ] Server pushes alert list for subscribed connections
- [ ] Push loop uses `fetch_device_telemetry_dynamic` (all metrics, not hardcoded)
- [ ] Push loop uses `tenant_connection` for alert queries (RLS enforced)
- [ ] Connection cleanup on disconnect (cancel push task, remove from manager)
- [ ] All existing tests pass

---

## Commit

```
Add WebSocket endpoint for live telemetry and alerts

Polling-bridge pattern: clients subscribe to devices and alerts
via JSON messages, server polls InfluxDB and PostgreSQL at
configurable intervals and pushes updates. JWT auth via query
parameter. Connection manager tracks subscriptions.

Phase 16 Task 4: WebSocket Live Data
```
