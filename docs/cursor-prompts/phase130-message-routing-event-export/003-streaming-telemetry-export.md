# Task 003 -- Streaming Telemetry Export

## Commit

```
feat(phase130): add WebSocket and SSE streaming telemetry export endpoints
```

## What This Task Does

1. Adds a WebSocket endpoint for real-time telemetry streaming with per-device/group/metric filtering.
2. Adds a Server-Sent Events (SSE) endpoint for clients that prefer SSE over WebSocket.
3. Both endpoints subscribe to MQTT topics internally and forward matching messages to connected clients.
4. Implements per-tenant connection rate limiting (max 10 concurrent streaming connections).

---

## Architecture

```
MQTT Broker
    |
    v
[MQTT Subscriber Thread] -- paho mqtt client in ui_iot process
    |
    v
[asyncio Queue per connection] -- TelemetryStreamManager distributes to queues
    |
    v
[WebSocket / SSE handler] -- reads from queue, sends to client
```

The key insight: the ui_iot service already connects to MQTT indirectly via the ingest service, but for streaming we need a direct MQTT subscription in the ui_iot process. This avoids the latency of polling TimescaleDB and provides true real-time delivery.

Alternative approach (simpler, no new MQTT connection): use PostgreSQL LISTEN/NOTIFY from the ingest worker after each telemetry write. The existing `setup_ws_listener` pattern in `api_v2.py` already demonstrates this. **Choose whichever approach fits the deployment better.** This prompt describes the MQTT approach for lowest latency, but includes a NOTIFY fallback.

---

## Step 1: Telemetry Stream Manager

Create file: `services/ui_iot/telemetry_stream.py`

```python
"""Manages streaming telemetry connections via MQTT subscription.

Each connected client (WebSocket or SSE) gets an asyncio.Queue.
The manager subscribes to MQTT topics for active tenants and distributes
incoming messages to matching queues.
"""
import asyncio
import json
import logging
import os
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)

MQTT_HOST = os.getenv("MQTT_HOST", "iot-mqtt")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
MAX_CONNECTIONS_PER_TENANT = int(os.getenv("MAX_STREAM_CONNECTIONS_PER_TENANT", "10"))
STREAM_QUEUE_SIZE = int(os.getenv("STREAM_QUEUE_SIZE", "100"))


@dataclass
class StreamSubscription:
    """Represents a single streaming client's subscription filters."""
    tenant_id: str
    queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=STREAM_QUEUE_SIZE))
    device_ids: set = field(default_factory=set)      # empty = all devices
    group_ids: set = field(default_factory=set)        # empty = no group filter
    metric_names: set = field(default_factory=set)     # empty = all metrics
    connected_at: float = field(default_factory=time.time)
    event_counter: int = 0


class TelemetryStreamManager:
    """Manages MQTT subscriptions and distributes messages to streaming clients."""

    def __init__(self):
        self._subscriptions: list[StreamSubscription] = []
        self._lock = threading.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._mqtt_client: Optional[mqtt.Client] = None
        self._subscribed_tenants: set[str] = set()
        self._started = False

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        """Start the MQTT client for telemetry streaming."""
        if self._started:
            return
        self._loop = loop
        self._mqtt_client = mqtt.Client(client_id="pulse-stream-manager")
        if MQTT_USERNAME and MQTT_PASSWORD:
            self._mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        self._mqtt_client.on_connect = self._on_connect
        self._mqtt_client.on_message = self._on_message

        try:
            self._mqtt_client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            self._mqtt_client.loop_start()
            self._started = True
            logger.info("TelemetryStreamManager MQTT connected to %s:%s", MQTT_HOST, MQTT_PORT)
        except Exception as exc:
            logger.warning("TelemetryStreamManager MQTT connect failed: %s", exc)

    def stop(self) -> None:
        """Stop the MQTT client."""
        if self._mqtt_client:
            self._mqtt_client.loop_stop()
            self._mqtt_client.disconnect()
            self._started = False

    def _on_connect(self, client, userdata, flags, rc):
        """Re-subscribe to topics for all active tenants on reconnect."""
        logger.info("TelemetryStreamManager MQTT connected, rc=%s", rc)
        for tenant_id in list(self._subscribed_tenants):
            topic = f"tenant/{tenant_id}/device/+/telemetry"
            client.subscribe(topic)
            logger.debug("Re-subscribed to %s", topic)

    def _on_message(self, client, userdata, msg):
        """Distribute incoming MQTT message to matching subscriber queues."""
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return

        # Parse topic: tenant/{tenant_id}/device/{device_id}/{msg_type}
        parts = msg.topic.split("/")
        if len(parts) < 5 or parts[0] != "tenant" or parts[2] != "device":
            return

        tenant_id = parts[1]
        device_id = parts[3]
        msg_type = parts[4]

        if msg_type != "telemetry":
            return

        metrics = payload.get("metrics", {})
        ts = payload.get("ts")

        event = {
            "type": "telemetry",
            "device_id": device_id,
            "tenant_id": tenant_id,
            "metrics": metrics,
            "timestamp": ts,
            "topic": msg.topic,
        }

        with self._lock:
            for sub in self._subscriptions:
                if sub.tenant_id != tenant_id:
                    continue

                # Device filter
                if sub.device_ids and device_id not in sub.device_ids:
                    continue

                # Metric filter: only include if at least one requested metric is present
                if sub.metric_names:
                    filtered_metrics = {
                        k: v for k, v in metrics.items() if k in sub.metric_names
                    }
                    if not filtered_metrics:
                        continue
                    event_copy = {**event, "metrics": filtered_metrics}
                else:
                    event_copy = event

                # Enqueue (non-blocking, drop if full to avoid backpressure)
                try:
                    sub.queue.put_nowait(event_copy)
                    sub.event_counter += 1
                except asyncio.QueueFull:
                    logger.debug("Stream queue full for tenant=%s, dropping event", tenant_id)

    def register(self, tenant_id: str, device_ids: list[str] | None = None,
                 metric_names: list[str] | None = None) -> StreamSubscription:
        """Register a new streaming subscription. Returns the subscription object."""
        # Check per-tenant limit
        with self._lock:
            tenant_count = sum(1 for s in self._subscriptions if s.tenant_id == tenant_id)
            if tenant_count >= MAX_CONNECTIONS_PER_TENANT:
                raise ConnectionError(
                    f"Max streaming connections ({MAX_CONNECTIONS_PER_TENANT}) reached for tenant"
                )

            sub = StreamSubscription(
                tenant_id=tenant_id,
                device_ids=set(device_ids) if device_ids else set(),
                metric_names=set(metric_names) if metric_names else set(),
            )
            self._subscriptions.append(sub)

        # Subscribe to MQTT topic for this tenant if not already subscribed
        if tenant_id not in self._subscribed_tenants and self._mqtt_client:
            topic = f"tenant/{tenant_id}/device/+/telemetry"
            self._mqtt_client.subscribe(topic)
            self._subscribed_tenants.add(tenant_id)
            logger.info("Subscribed to MQTT topic: %s", topic)

        return sub

    def unregister(self, sub: StreamSubscription) -> None:
        """Remove a streaming subscription."""
        with self._lock:
            if sub in self._subscriptions:
                self._subscriptions.remove(sub)

            # Unsubscribe from MQTT if no more subscriptions for this tenant
            remaining = sum(1 for s in self._subscriptions if s.tenant_id == sub.tenant_id)
            if remaining == 0 and sub.tenant_id in self._subscribed_tenants:
                if self._mqtt_client:
                    topic = f"tenant/{sub.tenant_id}/device/+/telemetry"
                    self._mqtt_client.unsubscribe(topic)
                self._subscribed_tenants.discard(sub.tenant_id)
                logger.info("Unsubscribed from MQTT topic for tenant=%s", sub.tenant_id)

    def update_filters(self, sub: StreamSubscription, device_ids: list[str] | None = None,
                       metric_names: list[str] | None = None) -> None:
        """Update subscription filters (called when client sends a filter update message)."""
        with self._lock:
            if device_ids is not None:
                sub.device_ids = set(device_ids)
            if metric_names is not None:
                sub.metric_names = set(metric_names)

    @property
    def connection_count(self) -> int:
        with self._lock:
            return len(self._subscriptions)

    def tenant_connection_count(self, tenant_id: str) -> int:
        with self._lock:
            return sum(1 for s in self._subscriptions if s.tenant_id == tenant_id)


# Singleton instance
stream_manager = TelemetryStreamManager()
```

---

## Step 2: WebSocket Endpoint

Create file: `services/ui_iot/routes/telemetry_stream.py`

```python
"""Streaming telemetry endpoints: WebSocket and SSE."""
import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from starlette.websockets import WebSocket, WebSocketDisconnect

from middleware.auth import validate_token
from telemetry_stream import stream_manager

logger = logging.getLogger(__name__)

# WebSocket router -- no HTTP auth dependencies (auth via query param token)
ws_router = APIRouter()

# SSE router -- uses standard HTTP auth
sse_router = APIRouter(
    prefix="/api/v1/customer/telemetry",
    tags=["telemetry-stream"],
)


def _extract_tenant_from_token(payload: dict) -> str | None:
    """Extract tenant_id from validated JWT payload."""
    orgs = payload.get("organization", {}) or {}
    if isinstance(orgs, dict) and orgs:
        return next(iter(orgs.keys()))
    if isinstance(orgs, list):
        for org in orgs:
            if isinstance(org, str) and org:
                return org
    return payload.get("tenant_id")


def _validate_customer_role(payload: dict) -> bool:
    """Check that the token has a valid customer role."""
    realm_access = payload.get("realm_access", {}) or {}
    roles = realm_access.get("roles", []) or []
    valid_roles = ("customer", "tenant-admin", "operator", "operator-admin")
    return any(role in valid_roles for role in roles)


@ws_router.websocket("/api/v1/customer/telemetry/stream")
async def telemetry_websocket(
    websocket: WebSocket,
    token: str | None = None,
    device_id: str | None = None,
    metric: str | None = None,
):
    """WebSocket endpoint for real-time telemetry streaming.

    Auth: Pass JWT as query param: ws://host/api/v1/customer/telemetry/stream?token=JWT

    Query params (initial filters):
        device_id: comma-separated device IDs (optional)
        metric: comma-separated metric names (optional)

    Client messages (JSON, to update filters):
        {"action": "subscribe", "device_id": "DEV-001"}
        {"action": "subscribe", "device_ids": ["DEV-001", "DEV-002"]}
        {"action": "unsubscribe", "device_id": "DEV-001"}
        {"action": "set_metrics", "metrics": ["temperature", "humidity"]}
        {"action": "clear_filters"}

    Server messages (JSON):
        {"type": "telemetry", "device_id": "DEV-001", "metrics": {...}, "timestamp": "..."}
        {"type": "subscribed", "device_id": "DEV-001"}
        {"type": "error", "message": "..."}
        {"type": "connected", "tenant_id": "...", "filters": {...}}
    """
    if not token:
        await websocket.close(code=4001, reason="Missing token parameter")
        return

    try:
        payload = await validate_token(token)
    except Exception:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    tenant_id = _extract_tenant_from_token(payload)
    if not tenant_id:
        await websocket.close(code=4003, reason="No tenant_id in token")
        return

    if not _validate_customer_role(payload):
        await websocket.close(code=4003, reason="Unauthorized role")
        return

    # Parse initial filters
    device_ids = [d.strip() for d in device_id.split(",") if d.strip()] if device_id else None
    metric_names = [m.strip() for m in metric.split(",") if m.strip()] if metric else None

    # Register subscription
    try:
        sub = stream_manager.register(
            tenant_id=tenant_id,
            device_ids=device_ids,
            metric_names=metric_names,
        )
    except ConnectionError as exc:
        await websocket.close(code=4029, reason=str(exc))
        return

    await websocket.accept()

    # Send connection confirmation
    await websocket.send_json({
        "type": "connected",
        "tenant_id": tenant_id,
        "filters": {
            "device_ids": list(sub.device_ids),
            "metric_names": list(sub.metric_names),
        },
    })

    # Start two concurrent tasks: read from queue + send to WS, and read WS messages
    async def sender():
        """Read from subscription queue and send to WebSocket."""
        try:
            while True:
                try:
                    event = await asyncio.wait_for(sub.queue.get(), timeout=30.0)
                    await websocket.send_json(event)
                except asyncio.TimeoutError:
                    # Send keepalive ping
                    await websocket.send_json({"type": "ping", "ts": datetime.now(timezone.utc).isoformat()})
        except Exception:
            pass

    async def receiver():
        """Read client messages to update filters."""
        try:
            while True:
                data = await websocket.receive_json()
                action = data.get("action")

                if action == "subscribe":
                    # Add device(s) to filter
                    if "device_id" in data:
                        sub.device_ids.add(data["device_id"])
                        await websocket.send_json({
                            "type": "subscribed",
                            "device_id": data["device_id"],
                        })
                    if "device_ids" in data and isinstance(data["device_ids"], list):
                        for did in data["device_ids"]:
                            sub.device_ids.add(did)
                        await websocket.send_json({
                            "type": "subscribed",
                            "device_ids": data["device_ids"],
                        })

                elif action == "unsubscribe":
                    if "device_id" in data:
                        sub.device_ids.discard(data["device_id"])
                        await websocket.send_json({
                            "type": "unsubscribed",
                            "device_id": data["device_id"],
                        })

                elif action == "set_metrics":
                    metrics = data.get("metrics", [])
                    sub.metric_names = set(metrics) if metrics else set()
                    await websocket.send_json({
                        "type": "metrics_updated",
                        "metrics": list(sub.metric_names),
                    })

                elif action == "clear_filters":
                    sub.device_ids.clear()
                    sub.metric_names.clear()
                    await websocket.send_json({
                        "type": "filters_cleared",
                    })

                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown action: {action}",
                    })
        except WebSocketDisconnect:
            pass
        except Exception:
            pass

    sender_task = asyncio.create_task(sender())
    receiver_task = asyncio.create_task(receiver())

    try:
        # Wait for either task to complete (disconnect or error)
        done, pending = await asyncio.wait(
            [sender_task, receiver_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    finally:
        stream_manager.unregister(sub)
        logger.info(
            "telemetry_stream_disconnected",
            extra={
                "tenant_id": tenant_id,
                "events_sent": sub.event_counter,
                "duration_s": int(asyncio.get_event_loop().time() - sub.connected_at),
            },
        )
```

---

## Step 3: SSE Endpoint

Add to the same file `services/ui_iot/routes/telemetry_stream.py`:

```python
from middleware.auth import JWTBearer
from middleware.tenant import inject_tenant_context, require_customer, get_tenant_id

# SSE router with standard HTTP auth
sse_router = APIRouter(
    prefix="/api/v1/customer/telemetry",
    tags=["telemetry-stream"],
    dependencies=[
        Depends(JWTBearer()),
        Depends(inject_tenant_context),
        Depends(require_customer),
    ],
)


@sse_router.get("/stream/sse")
async def telemetry_sse(
    request: Request,
    device_id: str | None = Query(None, description="Comma-separated device IDs"),
    metric: str | None = Query(None, description="Comma-separated metric names"),
):
    """Server-Sent Events endpoint for real-time telemetry streaming.

    Returns text/event-stream response. Each event is:
        id: <counter>
        data: {"device_id": "...", "metrics": {...}, "timestamp": "..."}

    Supports reconnection via Last-Event-ID header.

    Query params:
        device_id: comma-separated device IDs (optional, empty = all)
        metric: comma-separated metric names (optional, empty = all)
    """
    tenant_id = get_tenant_id()

    device_ids = [d.strip() for d in device_id.split(",") if d.strip()] if device_id else None
    metric_names = [m.strip() for m in metric.split(",") if m.strip()] if metric else None

    # Check Last-Event-ID for reconnection (we use it as a counter, not for replay)
    last_event_id = request.headers.get("Last-Event-ID")

    try:
        sub = stream_manager.register(
            tenant_id=tenant_id,
            device_ids=device_ids,
            metric_names=metric_names,
        )
    except ConnectionError as exc:
        raise HTTPException(429, str(exc))

    async def event_generator():
        """Generate SSE events from the subscription queue."""
        event_id = int(last_event_id) if last_event_id and last_event_id.isdigit() else 0
        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break

                try:
                    event = await asyncio.wait_for(sub.queue.get(), timeout=15.0)
                    event_id += 1
                    data = json.dumps(event)
                    yield f"id: {event_id}\ndata: {data}\n\n"
                except asyncio.TimeoutError:
                    # Send SSE comment as keepalive (prevents connection timeout)
                    yield f": keepalive {datetime.now(timezone.utc).isoformat()}\n\n"
        finally:
            stream_manager.unregister(sub)
            logger.info(
                "telemetry_sse_disconnected",
                extra={
                    "tenant_id": tenant_id,
                    "events_sent": sub.event_counter,
                },
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
```

---

## Step 4: Register Routers and Start Stream Manager

Edit `services/ui_iot/app.py`:

### 4a. Add imports

```python
from routes.telemetry_stream import ws_router as telemetry_ws_router, sse_router as telemetry_sse_router
from telemetry_stream import stream_manager
```

### 4b. Include routers (after existing router registrations, around line 186)

```python
app.include_router(telemetry_ws_router)
app.include_router(telemetry_sse_router)
```

### 4c. Start stream manager on startup

In the `startup()` function, after `await setup_ws_listener()` (line ~357), add:

```python
# Start telemetry stream manager for real-time export
import asyncio
stream_manager.start(asyncio.get_running_loop())
```

### 4d. Stop stream manager on shutdown

In the `shutdown()` function (after `await shutdown_ws_listener()`), add:

```python
try:
    stream_manager.stop()
except Exception:
    pass
```

---

## Step 5: Connection Metrics Endpoint

Add a simple metrics/status endpoint to check streaming connection counts. Add to `services/ui_iot/routes/telemetry_stream.py`:

```python
from fastapi import APIRouter

status_router = APIRouter(prefix="/api/v1", tags=["telemetry-stream"])


@status_router.get("/telemetry/stream/status")
async def stream_status():
    """Get streaming connection status (no auth required, for monitoring)."""
    return {
        "total_connections": stream_manager.connection_count,
        "max_per_tenant": MAX_CONNECTIONS_PER_TENANT,
    }
```

Register this router in `app.py` as well:

```python
from routes.telemetry_stream import status_router as telemetry_status_router
app.include_router(telemetry_status_router)
```

---

## Step 6: MQTT Dependency for ui_iot

Ensure `paho-mqtt` is in the ui_iot service dependencies. Check `services/ui_iot/requirements.txt` or `Dockerfile`. If not present, add:

```
paho-mqtt>=1.6.1,<2.0
```

The ingest service already uses paho-mqtt, so the package is already available in the project, but the ui_iot container may not have it installed.

---

## Verification

### WebSocket Test

```bash
# Install websocat if not available
# pip install websockets  (for python client)

# Get a JWT token
TOKEN="..."

# Connect via WebSocket with device filter
websocat "ws://localhost:8080/api/v1/customer/telemetry/stream?token=$TOKEN&device_id=DEV-001"

# In another terminal, send telemetry
mosquitto_pub -h localhost -p 1883 \
  -t "tenant/TENANT1/device/DEV-001/telemetry" \
  -m '{"ts":"2026-02-16T12:00:00Z","site_id":"SITE-1","provision_token":"test","metrics":{"temperature":72,"humidity":45}}'

# Should see in the WebSocket output:
# {"type":"telemetry","device_id":"DEV-001","metrics":{"temperature":72,"humidity":45},"timestamp":"2026-02-16T12:00:00Z","topic":"tenant/TENANT1/device/DEV-001/telemetry"}

# Send filter update via WebSocket message:
# {"action": "subscribe", "device_id": "DEV-002"}

# Send telemetry for DEV-002, should now appear
# Send telemetry for DEV-003, should NOT appear (not subscribed)
```

### SSE Test

```bash
# Connect via SSE (curl streams the output)
curl -N -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8080/api/v1/customer/telemetry/stream/sse?device_id=DEV-001"

# In another terminal, send telemetry
mosquitto_pub -h localhost -p 1883 \
  -t "tenant/TENANT1/device/DEV-001/telemetry" \
  -m '{"ts":"2026-02-16T12:00:00Z","site_id":"SITE-1","provision_token":"test","metrics":{"temperature":72}}'

# Should see SSE event:
# id: 1
# data: {"type":"telemetry","device_id":"DEV-001","metrics":{"temperature":72},"timestamp":"2026-02-16T12:00:00Z","topic":"..."}
```

### Rate Limiting Test

```bash
# Connect 10 times (should succeed)
for i in $(seq 1 10); do
  websocat "ws://localhost:8080/api/v1/customer/telemetry/stream?token=$TOKEN" &
done

# 11th connection should be rejected with code 4029
websocat "ws://localhost:8080/api/v1/customer/telemetry/stream?token=$TOKEN"
# Expected: Connection closed with reason "Max streaming connections (10) reached for tenant"
```

### Status Endpoint

```bash
curl http://localhost:8080/api/v1/telemetry/stream/status
# {"total_connections": 10, "max_per_tenant": 10}
```

### Python Client Example

```python
import asyncio
import json
import websockets

async def stream_telemetry():
    uri = "ws://localhost:8080/api/v1/customer/telemetry/stream?token=YOUR_JWT"
    async with websockets.connect(uri) as ws:
        # Read connection confirmation
        msg = await ws.recv()
        print("Connected:", json.loads(msg))

        # Subscribe to specific device
        await ws.send(json.dumps({
            "action": "subscribe",
            "device_id": "DEV-001"
        }))
        print("Filter update:", json.loads(await ws.recv()))

        # Read telemetry events
        while True:
            msg = await ws.recv()
            event = json.loads(msg)
            if event["type"] == "telemetry":
                print(f"[{event['device_id']}] {event['metrics']}")
            elif event["type"] == "ping":
                pass  # keepalive

asyncio.run(stream_telemetry())
```

### JavaScript/Browser SSE Client Example

```javascript
const evtSource = new EventSource(
  "/api/v1/customer/telemetry/stream/sse?device_id=DEV-001",
  // Note: SSE uses cookie-based auth or Authorization header via fetch polyfill
);

evtSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log("Telemetry:", data.device_id, data.metrics);
};

evtSource.onerror = () => {
  console.log("SSE connection lost, reconnecting...");
};
```
