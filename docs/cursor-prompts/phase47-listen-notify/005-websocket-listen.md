# Prompt 005 — WebSocket: LISTEN for Real-Time Browser Push

## Context

The WebSocket handler in `services/ui_iot/app.py` currently polls the DB every 5 seconds and pushes data to connected browser clients. After this prompt it pushes immediately when `device_state_changed` or `new_fleet_alert` notifications arrive.

## Your Task

**Read `services/ui_iot/app.py` fully** — find the WebSocket handler and its current polling loop.

### Current pattern (approximate)
```python
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    while True:
        data = await query_device_state(...)
        await ws.send_json(data)
        await asyncio.sleep(5)
```

### New pattern

The WebSocket should push immediately when either:
- `device_state_changed` fires (device came online/offline, new telemetry)
- `new_fleet_alert` fires (new alert opened)

Replace the 5s sleep with a wait on an asyncio Event:

```python
# Module-level shared event — set by LISTEN callbacks
_ws_notify_event = asyncio.Event()

def on_ws_notify(conn, pid, channel, payload):
    """Called on any device_state_changed or new_fleet_alert notification."""
    _ws_notify_event.set()
```

In the WebSocket handler:

```python
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    while True:
        try:
            # Wait for a notification OR timeout (send keepalive/refresh)
            try:
                await asyncio.wait_for(
                    _ws_notify_event.wait(),
                    timeout=10.0  # max 10s between pushes even if no notify
                )
            except asyncio.TimeoutError:
                pass  # send a refresh anyway (keepalive)

            _ws_notify_event.clear()

            # Query and push
            data = await query_device_state(...)
            await ws.send_json(data)

        except WebSocketDisconnect:
            break
        except Exception as e:
            print(f"[ws] error: {e}")
            break
```

### Startup: register LISTEN on the shared connection

In the app startup (lifespan or `@app.on_event("startup")`), create one shared listener connection for the WebSocket channel:

```python
_ws_listener_conn = None  # module-level

async def setup_ws_listener():
    global _ws_listener_conn
    try:
        _ws_listener_conn = await asyncpg.connect(DATABASE_URL)
        await _ws_listener_conn.add_listener("device_state_changed", on_ws_notify)
        await _ws_listener_conn.add_listener("new_fleet_alert", on_ws_notify)
        print("[ws] LISTEN on device_state_changed + new_fleet_alert active")
    except Exception as e:
        print(f"[ws] WARNING: LISTEN setup failed, using poll-only mode: {e}")
```

Call `setup_ws_listener()` in the startup handler. Add it to `asyncio.gather()` if there are other startup tasks.

**Important:** The `_ws_notify_event` is shared across ALL connected WebSocket clients. When any device state changes, ALL connected clients get pushed. This is correct — all clients should see the update.

## Acceptance Criteria

- [ ] WebSocket pushes within ~1s of a `device_state_changed` notification
- [ ] WebSocket pushes within ~1s of a `new_fleet_alert` notification
- [ ] Fallback: still sends data every 10s even if no notifications (keepalive)
- [ ] Graceful degradation: if LISTEN setup fails, WebSocket still works (poll-only at 10s)
- [ ] `pytest -m unit -v` passes
