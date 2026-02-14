from types import SimpleNamespace

import pytest

from routes.api_v2 import fetch_fleet_summary_for_tenant
from ws_manager import ConnectionManager

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class FakeWebSocket:
    def __init__(self, fail=False):
        self.fail = fail
        self.messages = []

    async def send_json(self, payload):
        if self.fail:
            raise RuntimeError("stale")
        self.messages.append(payload)


class FakeConn:
    def __init__(self, device_rows, alert_count):
        self.device_rows = device_rows
        self.alert_count = alert_count

    async def fetch(self, query, tenant_id):
        assert "FROM device_state" in query
        assert tenant_id == "tenant-a"
        return self.device_rows

    async def fetchval(self, query, tenant_id):
        assert "FROM fleet_alert" in query
        assert tenant_id == "tenant-a"
        return self.alert_count


async def test_subscribe_fleet_sets_flag():
    manager = ConnectionManager()
    conn = SimpleNamespace(websocket=FakeWebSocket(), tenant_id="tenant-a", user={}, device_subscriptions=set(), alert_subscription=False, fleet_subscription=False)
    manager.connections.append(conn)
    manager.subscribe_fleet(conn)
    assert conn.fleet_subscription is True


async def test_unsubscribe_fleet_clears_flag():
    manager = ConnectionManager()
    conn = SimpleNamespace(websocket=FakeWebSocket(), tenant_id="tenant-a", user={}, device_subscriptions=set(), alert_subscription=False, fleet_subscription=False)
    manager.connections.append(conn)
    manager.subscribe_fleet(conn)
    manager.unsubscribe_fleet(conn)
    assert conn.fleet_subscription is False


async def test_broadcast_fleet_summary_sends_to_subscribed():
    manager = ConnectionManager()
    ws_a = FakeWebSocket()
    ws_b = FakeWebSocket()
    a = SimpleNamespace(websocket=ws_a, tenant_id="tenant-a", user={}, device_subscriptions=set(), alert_subscription=False, fleet_subscription=True)
    b = SimpleNamespace(websocket=ws_b, tenant_id="tenant-a", user={}, device_subscriptions=set(), alert_subscription=False, fleet_subscription=False)
    manager.connections.extend([a, b])
    await manager.broadcast_fleet_summary("tenant-a", {"ONLINE": 1, "STALE": 0, "OFFLINE": 0, "total": 1, "active_alerts": 0})
    assert len(ws_a.messages) == 1
    assert len(ws_b.messages) == 0


async def test_broadcast_fleet_summary_tenant_isolation():
    manager = ConnectionManager()
    ws_a = FakeWebSocket()
    ws_b = FakeWebSocket()
    a = SimpleNamespace(websocket=ws_a, tenant_id="tenant-a", user={}, device_subscriptions=set(), alert_subscription=False, fleet_subscription=True)
    b = SimpleNamespace(websocket=ws_b, tenant_id="tenant-b", user={}, device_subscriptions=set(), alert_subscription=False, fleet_subscription=True)
    manager.connections.extend([a, b])
    await manager.broadcast_fleet_summary("tenant-a", {"ONLINE": 1, "STALE": 0, "OFFLINE": 0, "total": 1, "active_alerts": 0})
    assert len(ws_a.messages) == 1
    assert len(ws_b.messages) == 0


async def test_fetch_fleet_summary_for_tenant():
    conn = FakeConn(
        device_rows=[
            {"status": "ONLINE", "cnt": 4},
            {"status": "STALE", "cnt": 2},
            {"status": "OFFLINE", "cnt": 1},
        ],
        alert_count=3,
    )
    summary = await fetch_fleet_summary_for_tenant(conn, "tenant-a")
    assert summary == {"ONLINE": 4, "STALE": 2, "OFFLINE": 1, "total": 7, "active_alerts": 3}


async def test_broadcast_ignores_stale_connection():
    manager = ConnectionManager()
    stale = SimpleNamespace(websocket=FakeWebSocket(fail=True), tenant_id="tenant-a", user={}, device_subscriptions=set(), alert_subscription=False, fleet_subscription=True)
    good_ws = FakeWebSocket()
    good = SimpleNamespace(websocket=good_ws, tenant_id="tenant-a", user={}, device_subscriptions=set(), alert_subscription=False, fleet_subscription=True)
    manager.connections.extend([stale, good])
    await manager.broadcast_fleet_summary("tenant-a", {"ONLINE": 1, "STALE": 0, "OFFLINE": 0, "total": 1, "active_alerts": 0})
    assert len(good_ws.messages) == 1
