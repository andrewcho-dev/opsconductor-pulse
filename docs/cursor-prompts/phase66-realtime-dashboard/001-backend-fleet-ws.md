# Prompt 001 — Backend: Fleet Subscription in WebSocket Protocol

Read `services/ui_iot/routes/api_v2.py` — find the WebSocket handler and `_ws_push_loop`.
Read `services/ui_iot/ws_manager.py` — find `WSConnection` and `ConnectionManager`.

## Update WSConnection

Add `fleet_subscription: bool = False` to the `WSConnection` dataclass.

## Update ConnectionManager

Add methods:
```python
def subscribe_fleet(self, ws_id: str) -> None:
    if ws_id in self.connections:
        self.connections[ws_id].fleet_subscription = True

def unsubscribe_fleet(self, ws_id: str) -> None:
    if ws_id in self.connections:
        self.connections[ws_id].fleet_subscription = False

async def broadcast_fleet_summary(self, tenant_id: str, summary: dict) -> None:
    """Push fleet summary to all fleet-subscribed connections for this tenant."""
    for conn in self.connections.values():
        if conn.tenant_id == tenant_id and conn.fleet_subscription:
            try:
                await conn.websocket.send_json({
                    "type": "fleet_summary",
                    "data": summary,
                })
            except Exception:
                pass  # stale connection, will be cleaned up
```

## Update WebSocket Message Handler

In the WS route where client messages are parsed (find the `action` handler), add:
```python
elif action == "subscribe" and msg_type == "fleet":
    manager.subscribe_fleet(ws_id)
    await websocket.send_json({"type": "subscribed", "channel": "fleet"})

elif action == "unsubscribe" and msg_type == "fleet":
    manager.unsubscribe_fleet(ws_id)
```

## Update _ws_push_loop (LISTEN/NOTIFY callback)

When `new_fleet_alert` or `device_state_changed` fires, recompute fleet summary and broadcast:

```python
async def _on_new_alert_notify(conn, pid, channel, payload):
    # Parse tenant_id from payload (if available) or recompute for all
    # Fetch fleet summary for affected tenant
    summary = await fetch_fleet_summary_for_tenant(conn, tenant_id)
    await manager.broadcast_fleet_summary(tenant_id, summary)
```

Add a helper:
```python
async def fetch_fleet_summary_for_tenant(conn, tenant_id: str) -> dict:
    """Fetch device status counts and active alert count for a tenant."""
    device_rows = await conn.fetch(
        """
        SELECT status, COUNT(*) as cnt
        FROM device
        WHERE tenant_id = $1
        GROUP BY status
        """,
        tenant_id
    )
    alert_count = await conn.fetchval(
        "SELECT COUNT(*) FROM fleet_alert WHERE tenant_id=$1 AND status IN ('OPEN','ACKNOWLEDGED')",
        tenant_id
    )
    counts = {r["status"]: r["cnt"] for r in device_rows}
    return {
        "online": counts.get("ONLINE", 0),
        "stale": counts.get("STALE", 0),
        "offline": counts.get("OFFLINE", 0),
        "total": sum(counts.values()),
        "active_alerts": alert_count or 0,
    }
```

Note: Look at how the existing `_ws_push_loop` handles LISTEN/NOTIFY callbacks — follow that same pattern.

## Acceptance Criteria

- [ ] `fleet_subscription` field on WSConnection
- [ ] `subscribe_fleet()`, `unsubscribe_fleet()`, `broadcast_fleet_summary()` on ConnectionManager
- [ ] WS handler accepts `{"action": "subscribe", "type": "fleet"}`
- [ ] LISTEN/NOTIFY triggers fleet summary broadcast to subscribed clients
- [ ] `{"type": "fleet_summary", "data": {...}}` message shape
- [ ] `pytest -m unit -v` passes
