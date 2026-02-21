import sys
import types
import os
import time
import pytest
from unittest.mock import MagicMock
from dataclasses import dataclass, field

# Stub modules not available in test environment
for mod in ["asyncpg", "httpx"]:
    if mod not in sys.modules:
        sys.modules[mod] = types.SimpleNamespace(
            AsyncClient=lambda **kw: None,
            create_pool=lambda **kw: None,
            Connection=type("Connection", (), {}),
            Pool=type("Pool", (), {}),
        )
if "jose" not in sys.modules:
    sys.modules["jose"] = types.SimpleNamespace(
        jwk=types.SimpleNamespace(construct=lambda k: None),
        jwt=types.SimpleNamespace(
            decode=lambda *a, **kw: {},
            get_unverified_header=lambda t: {},
        ),
    )
    sys.modules["jose.exceptions"] = types.SimpleNamespace(
        ExpiredSignatureError=Exception,
        JWTClaimsError=Exception,
        JWTError=Exception,
    )

# Stub starlette WebSocket for ws_manager import
if "starlette" not in sys.modules:
    ws_mod = types.SimpleNamespace(WebSocket=type("WebSocket", (), {}))
    sys.modules["starlette"] = types.SimpleNamespace(websockets=ws_mod)
    sys.modules["starlette.websockets"] = ws_mod

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "ui_iot"))

from ws_manager import ConnectionManager, WSConnection

from routes.api_v2 import create_ws_ticket, consume_ws_ticket, _ws_tickets

from fastapi import HTTPException

pytestmark = [pytest.mark.unit]


class MockWebSocket:
    def __init__(self):
        self.accepted = False
        self.closed = False
        self.sent_messages = []

    async def accept(self):
        self.accepted = True

    async def send_json(self, data):
        self.sent_messages.append(data)

    async def close(self, code=1000, reason=""):
        self.closed = True


@pytest.mark.asyncio
async def test_connect_adds_connection():
    manager = ConnectionManager()
    ws = MockWebSocket()
    await manager.connect(ws, "tenant-1", {"email": "test@example.com"})
    assert manager.connection_count == 1


@pytest.mark.asyncio
async def test_disconnect_removes_connection():
    manager = ConnectionManager()
    ws = MockWebSocket()
    conn = await manager.connect(ws, "tenant-1", {"email": "test@example.com"})
    await manager.disconnect(conn)
    assert manager.connection_count == 0


@pytest.mark.asyncio
async def test_subscribe_device():
    manager = ConnectionManager()
    ws = MockWebSocket()
    conn = await manager.connect(ws, "tenant-1", {"email": "test@example.com"})
    manager.subscribe_device(conn, "dev-0001")
    assert "dev-0001" in conn.device_subscriptions


@pytest.mark.asyncio
async def test_unsubscribe_device():
    manager = ConnectionManager()
    ws = MockWebSocket()
    conn = await manager.connect(ws, "tenant-1", {"email": "test@example.com"})
    manager.subscribe_device(conn, "dev-0001")
    manager.unsubscribe_device(conn, "dev-0001")
    assert "dev-0001" not in conn.device_subscriptions


@pytest.mark.asyncio
async def test_unsubscribe_nonexistent_device():
    manager = ConnectionManager()
    ws = MockWebSocket()
    conn = await manager.connect(ws, "tenant-1", {"email": "test@example.com"})
    manager.unsubscribe_device(conn, "dev-0001")
    assert "dev-0001" not in conn.device_subscriptions


@pytest.mark.asyncio
async def test_subscribe_alerts():
    manager = ConnectionManager()
    ws = MockWebSocket()
    conn = await manager.connect(ws, "tenant-1", {"email": "test@example.com"})
    manager.subscribe_alerts(conn)
    assert conn.alert_subscription is True


@pytest.mark.asyncio
async def test_unsubscribe_alerts():
    manager = ConnectionManager()
    ws = MockWebSocket()
    conn = await manager.connect(ws, "tenant-1", {"email": "test@example.com"})
    manager.subscribe_alerts(conn)
    manager.unsubscribe_alerts(conn)
    assert conn.alert_subscription is False


@pytest.mark.asyncio
async def test_multiple_device_subscriptions():
    manager = ConnectionManager()
    ws = MockWebSocket()
    conn = await manager.connect(ws, "tenant-1", {"email": "test@example.com"})
    manager.subscribe_device(conn, "dev-0001")
    manager.subscribe_device(conn, "dev-0002")
    manager.subscribe_device(conn, "dev-0003")
    assert len(conn.device_subscriptions) == 3


@pytest.mark.asyncio
async def test_multiple_connections():
    manager = ConnectionManager()
    ws1 = MockWebSocket()
    ws2 = MockWebSocket()
    conn1 = await manager.connect(ws1, "tenant-1", {"email": "a@example.com"})
    await manager.connect(ws2, "tenant-1", {"email": "b@example.com"})
    assert manager.connection_count == 2
    await manager.disconnect(conn1)
    assert manager.connection_count == 1


def test_create_ws_ticket_returns_token():
    _ws_tickets.clear()
    ticket = create_ws_ticket({"sub": "user-1", "tenant_id": "tenant-a"})
    assert isinstance(ticket, str)
    assert ticket in _ws_tickets


def test_consume_ws_ticket_single_use():
    _ws_tickets.clear()
    ticket = create_ws_ticket({"sub": "user-1"})
    first = consume_ws_ticket(ticket)
    second = consume_ws_ticket(ticket)
    assert first is not None
    assert first.get("sub") == "user-1"
    assert second is None


def test_consume_ws_ticket_invalid_returns_none():
    _ws_tickets.clear()
    assert consume_ws_ticket("invalid-ticket") is None
