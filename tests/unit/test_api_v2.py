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

# Configure rate limit for tests before importing api_v2
os.environ.setdefault("API_RATE_LIMIT", "5")
os.environ.setdefault("API_RATE_WINDOW_SECONDS", "60")

try:
    from routes.api_v2 import _check_rate_limit, _rate_buckets, _validate_timestamp, API_RATE_LIMIT
    _api_v2_imported = True
except Exception:
    _api_v2_imported = False

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


def test_rate_limit_allows_under_limit():
    if not _api_v2_imported:
        pytest.skip("api_v2 import unavailable in test environment")
    _rate_buckets.clear()
    for _ in range(API_RATE_LIMIT):
        assert _check_rate_limit("tenant-test") is True


def test_rate_limit_blocks_over_limit():
    if not _api_v2_imported:
        pytest.skip("api_v2 import unavailable in test environment")
    _rate_buckets.clear()
    for _ in range(API_RATE_LIMIT):
        assert _check_rate_limit("tenant-test") is True
    assert _check_rate_limit("tenant-test") is False


def test_rate_limit_per_tenant_isolation():
    if not _api_v2_imported:
        pytest.skip("api_v2 import unavailable in test environment")
    _rate_buckets.clear()
    for _ in range(API_RATE_LIMIT):
        assert _check_rate_limit("tenant-a") is True
    assert _check_rate_limit("tenant-a") is False
    assert _check_rate_limit("tenant-b") is True


def test_validate_timestamp_valid():
    if not _api_v2_imported:
        pytest.skip("api_v2 import unavailable in test environment")
    assert _validate_timestamp("2024-01-15T10:30:00Z", "start") == "2024-01-15T10:30:00Z"


def test_validate_timestamp_none():
    if not _api_v2_imported:
        pytest.skip("api_v2 import unavailable in test environment")
    assert _validate_timestamp(None, "start") is None


def test_validate_timestamp_invalid():
    if not _api_v2_imported:
        pytest.skip("api_v2 import unavailable in test environment")
    with pytest.raises(HTTPException) as excinfo:
        _validate_timestamp("not-a-date", "start")
    assert excinfo.value.status_code == 400


def test_validate_timestamp_sanitizes():
    if not _api_v2_imported:
        pytest.skip("api_v2 import unavailable in test environment")
    value = "2024-01-15T10:30:00Z; DROP TABLE"
    assert _validate_timestamp(value, "start") == "2024-01-15T10:30:00ZDROPTABLE"
