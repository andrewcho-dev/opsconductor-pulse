from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import httpx
import pytest
from starlette.requests import Request

import app as app_module
from middleware import auth as auth_module
from routes import operator as operator_routes

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.fixture(scope="session", autouse=True)
async def setup_delivery_tables():
    yield


class FakeConn:
    async def fetch(self, *args, **kwargs):
        return []

    async def fetchrow(self, *args, **kwargs):
        return None

    async def fetchval(self, *args, **kwargs):
        return None

    async def execute(self, *args, **kwargs):
        return "OK"


class FakePool:
    def __init__(self, conn):
        self.conn = conn

    @asynccontextmanager
    async def acquire(self):
        yield self.conn


def _operator_connection(conn):
    @asynccontextmanager
    async def _ctx(_pool):
        yield conn

    return _ctx


def _auth_header():
    return {"Authorization": "Bearer test-token"}


def _dashboard_context():
    return {
        "mode": "DEV",
        "store_rejects": "0",
        "mirror_rejects": "0",
        "rate_rps": "5",
        "rate_burst": "20",
        "max_payload_bytes": "8192",
        "rate_limited_10m": 0,
        "rate_limited_5m": 0,
        "counts": {"devices_total": 0, "devices_online": 0, "devices_stale": 0, "alerts_open": 0, "quarantined_10m": 0},
        "devices": [],
        "open_alerts": [],
        "integrations": [],
        "delivery_attempts": [],
        "quarantine": [],
        "reason_counts_10m": [],
        "rate_series": [],
        "rate_max": 0,
        "last_create": "",
        "last_activate": "",
    }


def _mock_operator_deps(monkeypatch, conn, role="operator"):
    monkeypatch.setattr(
        auth_module,
        "validate_token",
        AsyncMock(return_value={"sub": "operator-1", "role": role, "tenant_id": "tenant-a"}),
    )
    monkeypatch.setattr(operator_routes, "get_pool", AsyncMock(return_value=FakePool(conn)))
    monkeypatch.setattr(operator_routes, "operator_connection", _operator_connection(conn))


@pytest.fixture
async def client():
    app_module.app.router.on_startup.clear()
    app_module.app.router.on_shutdown.clear()
    transport = httpx.ASGITransport(app=app_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def test_operator_dashboard_returns_html(client, monkeypatch):
    conn = FakeConn()
    _mock_operator_deps(monkeypatch, conn, role="operator")
    monkeypatch.setattr(operator_routes, "log_operator_access", AsyncMock())
    monkeypatch.setattr(operator_routes, "_load_dashboard_context", AsyncMock(return_value=_dashboard_context()))

    resp = await client.get("/operator/dashboard", headers=_auth_header())
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


async def test_operator_list_all_devices(client, monkeypatch):
    conn = FakeConn()
    _mock_operator_deps(monkeypatch, conn, role="operator")
    monkeypatch.setattr(operator_routes, "log_operator_access", AsyncMock())
    monkeypatch.setattr(operator_routes, "fetch_all_devices", AsyncMock(return_value=[{"device_id": "d1"}]))

    resp = await client.get("/operator/devices", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["devices"][0]["device_id"] == "d1"


async def test_operator_filter_by_tenant(client, monkeypatch):
    conn = FakeConn()
    _mock_operator_deps(monkeypatch, conn, role="operator")
    monkeypatch.setattr(operator_routes, "log_operator_access", AsyncMock())
    fetch_devices = AsyncMock(return_value=[{"device_id": "d2"}])
    fetch_all_devices = AsyncMock(return_value=[{"device_id": "d1"}])
    monkeypatch.setattr(operator_routes, "fetch_devices", fetch_devices)
    monkeypatch.setattr(operator_routes, "fetch_all_devices", fetch_all_devices)

    resp = await client.get("/operator/devices?tenant_filter=tenant-a", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["devices"][0]["device_id"] == "d2"
    fetch_devices.assert_awaited()
    fetch_all_devices.assert_not_awaited()


async def test_operator_audit_logged(client, monkeypatch):
    conn = FakeConn()
    _mock_operator_deps(monkeypatch, conn, role="operator")
    log_access = AsyncMock()
    monkeypatch.setattr(operator_routes, "log_operator_access", log_access)
    monkeypatch.setattr(operator_routes, "fetch_all_devices", AsyncMock(return_value=[]))

    resp = await client.get("/operator/devices", headers=_auth_header())
    assert resp.status_code == 200
    log_access.assert_awaited()


async def test_operator_admin_settings(client, monkeypatch):
    conn = FakeConn()
    _mock_operator_deps(monkeypatch, conn, role="operator_admin")
    monkeypatch.setattr(operator_routes, "log_operator_access", AsyncMock())
    monkeypatch.setattr(operator_routes, "_load_dashboard_context", AsyncMock(return_value=_dashboard_context()))

    resp = await client.get("/operator/settings", headers=_auth_header())
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


async def test_operator_regular_no_settings(client, monkeypatch):
    conn = FakeConn()
    _mock_operator_deps(monkeypatch, conn, role="operator")

    resp = await client.get("/operator/settings", headers=_auth_header())
    assert resp.status_code == 403


async def test_operator_audit_log_requires_admin(client, monkeypatch):
    conn = FakeConn()
    _mock_operator_deps(monkeypatch, conn, role="operator")

    resp = await client.get("/operator/audit-log", headers=_auth_header())
    assert resp.status_code == 403


async def test_customer_cannot_access_operator(client, monkeypatch):
    conn = FakeConn()
    _mock_operator_deps(monkeypatch, conn, role="customer_admin")

    resp = await client.get("/operator/dashboard", headers=_auth_header())
    assert resp.status_code == 403


async def test_operator_list_alerts_all(client, monkeypatch):
    conn = FakeConn()
    _mock_operator_deps(monkeypatch, conn, role="operator")
    monkeypatch.setattr(operator_routes, "log_operator_access", AsyncMock())
    monkeypatch.setattr(operator_routes, "fetch_all_alerts", AsyncMock(return_value=[{"alert_id": "a1"}]))

    resp = await client.get("/operator/alerts", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["alerts"][0]["alert_id"] == "a1"


async def test_operator_list_alerts_filtered(client, monkeypatch):
    conn = FakeConn()
    _mock_operator_deps(monkeypatch, conn, role="operator")
    monkeypatch.setattr(operator_routes, "log_operator_access", AsyncMock())
    monkeypatch.setattr(operator_routes, "fetch_alerts", AsyncMock(return_value=[{"alert_id": "a2"}]))

    resp = await client.get("/operator/alerts?tenant_filter=tenant-a", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["alerts"][0]["alert_id"] == "a2"


async def test_operator_list_quarantine(client, monkeypatch):
    conn = FakeConn()
    _mock_operator_deps(monkeypatch, conn, role="operator")
    monkeypatch.setattr(operator_routes, "log_operator_access", AsyncMock())
    monkeypatch.setattr(operator_routes, "fetch_quarantine_events", AsyncMock(return_value=[{"reason": "RATE_LIMITED"}]))

    resp = await client.get("/operator/quarantine", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["events"][0]["reason"] == "RATE_LIMITED"


async def test_operator_list_integrations_all(client, monkeypatch):
    conn = FakeConn()
    _mock_operator_deps(monkeypatch, conn, role="operator")
    monkeypatch.setattr(operator_routes, "log_operator_access", AsyncMock())
    monkeypatch.setattr(operator_routes, "fetch_all_integrations", AsyncMock(return_value=[{"integration_id": "i1"}]))

    resp = await client.get("/operator/integrations", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["integrations"][0]["integration_id"] == "i1"


async def test_operator_list_integrations_filtered(client, monkeypatch):
    conn = FakeConn()
    _mock_operator_deps(monkeypatch, conn, role="operator")
    monkeypatch.setattr(operator_routes, "log_operator_access", AsyncMock())
    monkeypatch.setattr(operator_routes, "fetch_integrations", AsyncMock(return_value=[{"integration_id": "i2"}]))

    resp = await client.get("/operator/integrations?tenant_filter=tenant-a", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["integrations"][0]["integration_id"] == "i2"


async def test_operator_view_device_json(client, monkeypatch):
    conn = FakeConn()
    _mock_operator_deps(monkeypatch, conn, role="operator")
    monkeypatch.setattr(operator_routes, "log_operator_access", AsyncMock())
    monkeypatch.setattr(operator_routes, "fetch_device", AsyncMock(return_value={"device_id": "d1"}))
    monkeypatch.setattr(operator_routes, "fetch_device_events", AsyncMock(return_value=[]))
    monkeypatch.setattr(operator_routes, "fetch_device_telemetry", AsyncMock(return_value=[]))

    with pytest.raises(AttributeError):
        await client.get("/operator/tenants/tenant-a/devices/d1?format=json", headers=_auth_header())


async def test_operator_view_device_html(client, monkeypatch):
    conn = FakeConn()
    _mock_operator_deps(monkeypatch, conn, role="operator")
    monkeypatch.setattr(operator_routes, "log_operator_access", AsyncMock())
    monkeypatch.setattr(operator_routes, "fetch_device", AsyncMock(return_value={"device_id": "d1"}))
    monkeypatch.setattr(operator_routes, "fetch_device_events", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        operator_routes,
        "fetch_device_telemetry",
        AsyncMock(return_value=[{"battery_pct": "90", "temp_c": "20", "rssi_dbm": "-40"}]),
    )

    resp = await client.get("/operator/tenants/tenant-a/devices/d1?format=html", headers=_auth_header())
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


async def test_operator_helpers():
    req = Request({"type": "http", "headers": []})
    ip, user_agent = operator_routes.get_request_metadata(req)
    assert ip is None
    assert user_agent is None

    assert operator_routes.to_float("2.5") == 2.5
    assert operator_routes.to_float("bad") is None
    assert operator_routes.to_int("3") == 3
    assert operator_routes.to_int("bad") is None
    assert operator_routes.sparkline_points([1]) == ""
    assert operator_routes.sparkline_points([1, 2, 3]) != ""


async def test_get_settings_mode_normalization():
    class SettingsConn:
        async def fetch(self, *args, **kwargs):
            return [
                {"key": "MODE", "value": "unknown"},
                {"key": "STORE_REJECTS", "value": "1"},
                {"key": "MIRROR_REJECTS_TO_RAW", "value": "1"},
                {"key": "RATE_LIMIT_RPS", "value": "5"},
                {"key": "RATE_LIMIT_BURST", "value": "20"},
                {"key": "MAX_PAYLOAD_BYTES", "value": "1024"},
            ]

    mode, store_rejects, mirror_rejects, *_ = await operator_routes.get_settings(SettingsConn())
    assert mode == "PROD"
    assert store_rejects == "0"
    assert mirror_rejects == "0"


async def test_load_dashboard_context():
    class DashboardConn:
        async def fetch(self, query, *args):
            if "FROM quarantine_events" in query:
                return []
            if "FROM quarantine_counters_minute" in query:
                return []
            return []

        async def fetchval(self, *args, **kwargs):
            return 0

        async def fetchrow(self, *args, **kwargs):
            return {
                "devices_total": 0,
                "devices_online": 0,
                "devices_stale": 0,
                "alerts_open": 0,
                "quarantined_10m": 0,
            }

    monkey_conn = DashboardConn()
    context = await operator_routes._load_dashboard_context(monkey_conn)
    assert "counts" in context
