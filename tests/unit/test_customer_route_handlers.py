from contextlib import asynccontextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import HTTPException

import app as app_module
from middleware import auth as auth_module
from routes import customer as customer_routes

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.fixture(scope="session", autouse=True)
async def setup_delivery_tables():
    yield


class FakeConn:
    def __init__(self):
        self.fetchrow_result = None
        self.fetch_result = []
        self.execute_result = "DELETE 1"

    async def fetchrow(self, *args, **kwargs):
        return self.fetchrow_result

    async def fetch(self, *args, **kwargs):
        return self.fetch_result

    async def execute(self, *args, **kwargs):
        return self.execute_result

    async def fetchval(self, *args, **kwargs):
        return 0


class FakePool:
    def __init__(self, conn):
        self.conn = conn

    @asynccontextmanager
    async def acquire(self):
        yield self.conn


def _tenant_connection(conn):
    @asynccontextmanager
    async def _ctx(_pool, _tenant_id):
        yield conn

    return _ctx


def _auth_header():
    return {"Authorization": "Bearer test-token"}


def _mock_customer_deps(monkeypatch, conn, role="customer_admin", tenant_id="tenant-a"):
    monkeypatch.setattr(
        auth_module,
        "validate_token",
        AsyncMock(return_value={"sub": "user-1", "role": role, "tenant_id": tenant_id}),
    )
    monkeypatch.setattr(customer_routes, "get_pool", AsyncMock(return_value=FakePool(conn)))
    monkeypatch.setattr(customer_routes, "tenant_connection", _tenant_connection(conn))


def _mock_async_client(response=None, exc=None):
    context = AsyncMock()
    client = AsyncMock()
    if exc is not None:
        client.post.side_effect = exc
        client.get.side_effect = exc
    else:
        client.post.return_value = response
        client.get.return_value = response
    context.__aenter__.return_value = client
    return context


@pytest.fixture
async def client():
    app_module.app.router.on_startup.clear()
    app_module.app.router.on_shutdown.clear()
    transport = httpx.ASGITransport(app=app_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def test_dashboard_returns_html(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(customer_routes, "fetch_device_count", AsyncMock(return_value={"total": 0, "online": 0, "stale": 0}))
    monkeypatch.setattr(customer_routes, "fetch_devices", AsyncMock(return_value=[]))
    monkeypatch.setattr(customer_routes, "fetch_alerts", AsyncMock(return_value=[]))
    monkeypatch.setattr(customer_routes, "fetch_delivery_attempts", AsyncMock(return_value=[]))

    resp = await client.get("/customer/dashboard", headers=_auth_header())
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


async def test_devices_page_returns_html(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(customer_routes, "fetch_devices", AsyncMock(return_value=[]))

    resp = await client.get("/customer/devices", headers=_auth_header())
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


async def test_devices_json_format(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(customer_routes, "fetch_devices", AsyncMock(return_value=[]))

    resp = await client.get("/customer/devices?format=json", headers=_auth_header())
    assert resp.status_code == 200
    assert "application/json" in resp.headers["content-type"]


async def test_alerts_page_returns_html(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(customer_routes, "fetch_alerts", AsyncMock(return_value=[]))

    resp = await client.get("/customer/alerts", headers=_auth_header())
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


async def test_alerts_json_format(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(customer_routes, "fetch_alerts", AsyncMock(return_value=[]))

    resp = await client.get("/customer/alerts?format=json", headers=_auth_header())
    assert resp.status_code == 200
    assert "application/json" in resp.headers["content-type"]


async def test_webhooks_page_returns_html(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/customer/webhooks", headers=_auth_header())
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


async def test_snmp_page_returns_html(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/customer/snmp-integrations", headers=_auth_header())
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


async def test_email_page_returns_html(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/customer/email-integrations", headers=_auth_header())
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


async def test_create_integration_valid(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(customer_routes, "validate_webhook_url", AsyncMock(return_value=(True, None)))
    monkeypatch.setattr(
        customer_routes,
        "create_integration",
        AsyncMock(return_value={"integration_id": "i1", "url": "https://example.com/path"}),
    )

    resp = await client.post(
        "/customer/integrations",
        headers=_auth_header(),
        json={"name": "Test", "webhook_url": "https://example.com/path", "enabled": True},
    )
    assert resp.status_code == 200


async def test_create_integration_missing_url(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)

    resp = await client.post(
        "/customer/integrations",
        headers=_auth_header(),
        json={"name": "Test", "enabled": True},
    )
    assert resp.status_code in (400, 422)


async def test_create_integration_ssrf_url(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(
        customer_routes, "validate_webhook_url", AsyncMock(return_value=(False, "Private IP addresses are not allowed"))
    )

    resp = await client.post(
        "/customer/integrations",
        headers=_auth_header(),
        json={"name": "Test", "webhook_url": "https://10.0.0.1/hook", "enabled": True},
    )
    assert resp.status_code == 400


async def test_list_integrations_empty(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(customer_routes, "fetch_integrations", AsyncMock(return_value=[]))

    resp = await client.get("/customer/integrations", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["integrations"] == []


async def test_delete_integration_not_found(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(customer_routes, "delete_integration", AsyncMock(return_value=False))

    resp = await client.delete("/customer/integrations/unknown", headers=_auth_header())
    assert resp.status_code == 404


async def test_delete_integration_wrong_tenant(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(customer_routes, "delete_integration", AsyncMock(return_value=False))

    resp = await client.delete("/customer/integrations/other", headers=_auth_header())
    assert resp.status_code == 404


async def test_create_snmp_v2c(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(customer_routes, "validate_snmp_host", lambda host, port: SimpleNamespace(valid=True))
    conn.fetchrow_result = {
        "integration_id": "snmp-1",
        "tenant_id": "tenant-a",
        "name": "SNMP v2c",
        "snmp_host": "198.51.100.10",
        "snmp_port": 162,
        "snmp_config": {"version": "2c"},
        "snmp_oid_prefix": "1.3.6.1.4.1.99999",
        "enabled": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    resp = await client.post(
        "/customer/integrations/snmp",
        headers=_auth_header(),
        json={
            "name": "SNMP v2c",
            "snmp_host": "198.51.100.10",
            "snmp_port": 162,
            "snmp_config": {"version": "2c", "community": "public"},
            "snmp_oid_prefix": "1.3.6.1.4.1.99999",
            "enabled": True,
        },
    )
    assert resp.status_code == 201


async def test_create_snmp_v3(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(customer_routes, "validate_snmp_host", lambda host, port: SimpleNamespace(valid=True))
    conn.fetchrow_result = {
        "integration_id": "snmp-2",
        "tenant_id": "tenant-a",
        "name": "SNMP v3",
        "snmp_host": "198.51.100.11",
        "snmp_port": 162,
        "snmp_config": {"version": "3"},
        "snmp_oid_prefix": "1.3.6.1.4.1.99999",
        "enabled": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    resp = await client.post(
        "/customer/integrations/snmp",
        headers=_auth_header(),
        json={
            "name": "SNMP v3",
            "snmp_host": "198.51.100.11",
            "snmp_port": 162,
            "snmp_config": {
                "version": "3",
                "username": "user",
                "auth_protocol": "SHA",
                "auth_password": "authpass123",
                "priv_protocol": "AES",
                "priv_password": "privpass123",
            },
            "snmp_oid_prefix": "1.3.6.1.4.1.99999",
            "enabled": True,
        },
    )
    assert resp.status_code == 201


async def test_create_snmp_invalid_host(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(
        customer_routes,
        "validate_snmp_host",
        lambda host, port: SimpleNamespace(valid=False, error="blocked"),
    )

    resp = await client.post(
        "/customer/integrations/snmp",
        headers=_auth_header(),
        json={
            "name": "Bad SNMP",
            "snmp_host": "10.0.0.1",
            "snmp_port": 162,
            "snmp_config": {"version": "2c", "community": "public"},
            "snmp_oid_prefix": "1.3.6.1.4.1.99999",
            "enabled": True,
        },
    )
    assert resp.status_code == 400


async def test_create_snmp_invalid_port(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)

    resp = await client.post(
        "/customer/integrations/snmp",
        headers=_auth_header(),
        json={
            "name": "Bad SNMP",
            "snmp_host": "198.51.100.10",
            "snmp_port": 70000,
            "snmp_config": {"version": "2c", "community": "public"},
            "snmp_oid_prefix": "1.3.6.1.4.1.99999",
            "enabled": True,
        },
    )
    assert resp.status_code in (400, 422)


async def test_create_email_valid(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(customer_routes, "validate_email_integration", lambda **_: SimpleNamespace(valid=True))
    conn.fetchrow_result = {
        "integration_id": "email-1",
        "tenant_id": "tenant-a",
        "name": "Email",
        "email_config": {},
        "email_recipients": {},
        "email_template": {},
        "enabled": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    resp = await client.post(
        "/customer/integrations/email",
        headers=_auth_header(),
        json={
            "name": "Email",
            "smtp_config": {
                "smtp_host": "smtp.example.com",
                "smtp_port": 587,
                "smtp_user": "user",
                "smtp_password": "pass",
                "smtp_tls": True,
                "from_address": "alerts@example.com",
                "from_name": "OpsConductor Alerts",
            },
            "recipients": {"to": ["ops@example.com"], "cc": [], "bcc": []},
            "enabled": True,
        },
    )
    assert resp.status_code == 201


async def test_create_email_no_recipients(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)

    resp = await client.post(
        "/customer/integrations/email",
        headers=_auth_header(),
        json={
            "name": "Email",
            "smtp_config": {
                "smtp_host": "smtp.example.com",
                "smtp_port": 587,
                "smtp_user": "user",
                "smtp_password": "pass",
                "smtp_tls": True,
                "from_address": "alerts@example.com",
                "from_name": "OpsConductor Alerts",
            },
            "recipients": {"to": [], "cc": [], "bcc": []},
            "enabled": True,
        },
    )
    assert resp.status_code in (400, 422)


async def test_create_email_invalid_smtp_host(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(
        customer_routes,
        "validate_email_integration",
        lambda **_: SimpleNamespace(valid=False, error="blocked"),
    )

    resp = await client.post(
        "/customer/integrations/email",
        headers=_auth_header(),
        json={
            "name": "Email",
            "smtp_config": {
                "smtp_host": "10.0.0.1",
                "smtp_port": 587,
                "smtp_user": "user",
                "smtp_password": "pass",
                "smtp_tls": True,
                "from_address": "alerts@example.com",
                "from_name": "OpsConductor Alerts",
            },
            "recipients": {"to": ["ops@example.com"], "cc": [], "bcc": []},
            "enabled": True,
        },
    )
    assert resp.status_code == 400


async def test_create_email_invalid_email_address(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)

    resp = await client.post(
        "/customer/integrations/email",
        headers=_auth_header(),
        json={
            "name": "Email",
            "smtp_config": {
                "smtp_host": "smtp.example.com",
                "smtp_port": 587,
                "smtp_user": "user",
                "smtp_password": "pass",
                "smtp_tls": True,
                "from_address": "not-an-email",
                "from_name": "OpsConductor Alerts",
            },
            "recipients": {"to": ["ops@example.com"], "cc": [], "bcc": []},
            "enabled": True,
        },
    )
    assert resp.status_code in (400, 422)


async def test_test_webhook_delivery(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(customer_routes, "check_and_increment_rate_limit", AsyncMock(return_value=(True, 1)))
    integration_id = "00000000-0000-0000-0000-000000000001"
    conn.fetchrow_result = {
        "integration_id": integration_id,
        "tenant_id": "tenant-a",
        "name": "Webhook",
        "type": "webhook",
        "webhook_url": "https://example.com/hook",
        "enabled": True,
        "snmp_host": None,
        "snmp_port": None,
        "snmp_config": None,
        "snmp_oid_prefix": None,
        "email_config": None,
        "email_recipients": None,
        "email_template": None,
    }
    monkeypatch.setattr(
        customer_routes,
        "dispatch_to_integration",
        AsyncMock(return_value=SimpleNamespace(success=True, error=None, duration_ms=5)),
    )

    resp = await client.post(f"/customer/integrations/{integration_id}/test", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["success"] is True


async def test_test_snmp_delivery(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(customer_routes, "check_and_increment_rate_limit", AsyncMock(return_value=(True, 1)))
    conn.fetchrow_result = {
        "integration_id": "snmp-1",
        "tenant_id": "tenant-a",
        "name": "SNMP",
        "type": "snmp",
        "snmp_host": "198.51.100.10",
        "snmp_port": 162,
        "snmp_config": {"version": "2c"},
        "snmp_oid_prefix": "1.3.6.1.4.1.99999",
        "enabled": True,
    }
    monkeypatch.setattr(
        customer_routes,
        "dispatch_to_integration",
        AsyncMock(return_value=SimpleNamespace(success=True, error=None, duration_ms=5)),
    )

    resp = await client.post("/customer/integrations/snmp/snmp-1/test", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["success"] is True


async def test_test_email_delivery(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(customer_routes, "check_and_increment_rate_limit", AsyncMock(return_value=(True, 1)))
    integration_id = "00000000-0000-0000-0000-000000000002"
    conn.fetchrow_result = {
        "integration_id": integration_id,
        "tenant_id": "tenant-a",
        "name": "Email",
        "type": "email",
        "email_config": {"smtp_host": "smtp.example.com"},
        "email_recipients": {"to": ["ops@example.com"]},
        "email_template": {},
        "enabled": True,
    }
    monkeypatch.setattr(
        customer_routes,
        "send_alert_email",
        AsyncMock(
            return_value=SimpleNamespace(success=True, error=None, duration_ms=5, recipients_count=1)
        ),
    )

    resp = await client.post(f"/customer/integrations/email/{integration_id}/test", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["success"] is True


async def test_test_delivery_rate_limited(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(customer_routes, "check_and_increment_rate_limit", AsyncMock(return_value=(False, 5)))
    integration_id = "00000000-0000-0000-0000-000000000003"
    conn.fetchrow_result = {
        "integration_id": integration_id,
        "tenant_id": "tenant-a",
        "type": "webhook",
        "webhook_url": "x",
        "name": "Webhook",
        "snmp_host": None,
        "snmp_port": None,
        "snmp_config": None,
        "snmp_oid_prefix": None,
        "email_config": None,
        "email_recipients": None,
        "email_template": None,
        "enabled": True,
    }

    resp = await client.post(f"/customer/integrations/{integration_id}/test", headers=_auth_header())
    assert resp.status_code == 429


async def test_viewer_cannot_create_integration(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn, role="customer_viewer")

    resp = await client.post(
        "/customer/integrations",
        headers=_auth_header(),
        json={"name": "Test", "webhook_url": "https://example.com/path", "enabled": True},
    )
    assert resp.status_code == 403


async def test_viewer_cannot_delete_integration(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn, role="customer_viewer")

    resp = await client.delete("/customer/integrations/abc", headers=_auth_header())
    assert resp.status_code == 403


async def test_viewer_can_list_integrations(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn, role="customer_viewer")
    monkeypatch.setattr(customer_routes, "fetch_integrations", AsyncMock(return_value=[]))

    resp = await client.get("/customer/integrations", headers=_auth_header())
    assert resp.status_code == 200


async def test_unauthenticated_rejected(client):
    resp = await client.get("/customer/devices")
    assert resp.status_code == 401


async def test_helpers_and_normalizers():
    assert customer_routes.to_float(None) is None
    assert customer_routes.to_float("2.5") == 2.5
    assert customer_routes.to_float("bad") is None
    assert customer_routes.to_int("3") == 3
    assert customer_routes.to_int("bad") is None

    assert customer_routes.sparkline_points([1]) == ""
    assert customer_routes.sparkline_points([1, 2, 3]) != ""

    assert customer_routes.redact_url("https://example.com:8080/path") == "https://example.com:8080"
    assert customer_routes.redact_url("not-a-url") == ""

    assert customer_routes._validate_name(" Valid ") == "Valid"
    with pytest.raises(HTTPException):
        customer_routes._validate_name(" ")
    with pytest.raises(HTTPException):
        customer_routes._validate_name("Bad@Name")

    normalized = customer_routes._normalize_list([" CRITICAL ", "CRITICAL"], customer_routes.SEVERITIES, "severities")
    assert normalized == ["CRITICAL"]
    with pytest.raises(HTTPException):
        customer_routes._normalize_list(["BAD"], customer_routes.SEVERITIES, "severities")

    assert customer_routes._normalize_json({"a": 1}) == {"a": 1}
    assert customer_routes._normalize_json(b'{"a":1}') == {"a": 1}
    assert customer_routes._normalize_json("not json") == {}

    payload = customer_routes.generate_test_payload("tenant-a", "Webhook")
    assert payload["_test"] is True
    assert payload["integration_name"] == "Webhook"


async def test_get_alert_success(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    conn.fetchrow_result = {
        "alert_id": "a1",
        "tenant_id": "tenant-a",
        "device_id": "d1",
        "site_id": "s1",
        "alert_type": "NO_HEARTBEAT",
        "severity": "WARNING",
        "confidence": 0.9,
        "summary": "Alert",
        "status": "OPEN",
        "created_at": datetime.now(timezone.utc),
    }

    resp = await client.get("/customer/alerts/a1", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["alert"]["alert_id"] == "a1"


async def test_get_alert_not_found(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    conn.fetchrow_result = None

    resp = await client.get("/customer/alerts/a1", headers=_auth_header())
    assert resp.status_code == 404


async def test_get_device_detail_json(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(customer_routes, "fetch_device", AsyncMock(return_value={"device_id": "d1"}))
    monkeypatch.setattr(customer_routes, "fetch_device_events_influx", AsyncMock(return_value=[]))
    monkeypatch.setattr(customer_routes, "fetch_device_telemetry_influx", AsyncMock(return_value=[]))

    resp = await client.get("/customer/devices/d1?format=json", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["device"]["device_id"] == "d1"


async def test_list_integration_routes(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(customer_routes, "fetch_integration_routes", AsyncMock(return_value=[]))

    resp = await client.get("/customer/integration-routes", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["routes"] == []


async def test_get_integration_route_invalid_uuid(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)

    resp = await client.get("/customer/integration-routes/not-a-uuid", headers=_auth_header())
    assert resp.status_code == 400


async def test_get_integration_route_not_found(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(customer_routes, "fetch_integration_route", AsyncMock(return_value=None))

    resp = await client.get(
        "/customer/integration-routes/00000000-0000-0000-0000-000000000010", headers=_auth_header()
    )
    assert resp.status_code == 404


async def test_create_integration_route_success(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(
        customer_routes,
        "fetch_integration",
        AsyncMock(return_value={"integration_id": "i1", "name": "Webhook"}),
    )
    monkeypatch.setattr(
        customer_routes,
        "create_integration_route",
        AsyncMock(return_value={"route_id": "r1", "integration_id": "i1"}),
    )

    resp = await client.post(
        "/customer/integration-routes",
        headers=_auth_header(),
        json={
            "integration_id": "00000000-0000-0000-0000-000000000011",
            "alert_types": ["NO_HEARTBEAT"],
            "severities": ["CRITICAL"],
            "enabled": True,
        },
    )
    assert resp.status_code == 200


async def test_create_integration_route_missing_integration(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(customer_routes, "fetch_integration", AsyncMock(return_value=None))

    resp = await client.post(
        "/customer/integration-routes",
        headers=_auth_header(),
        json={
            "integration_id": "00000000-0000-0000-0000-000000000012",
            "alert_types": ["NO_HEARTBEAT"],
            "severities": ["CRITICAL"],
            "enabled": True,
        },
    )
    assert resp.status_code == 400


async def test_patch_integration_route_no_fields(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)

    resp = await client.patch(
        "/customer/integration-routes/00000000-0000-0000-0000-000000000013",
        headers=_auth_header(),
        json={},
    )
    assert resp.status_code == 400


async def test_patch_integration_route_success(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(
        customer_routes,
        "update_integration_route",
        AsyncMock(return_value={"route_id": "r1", "integration_id": "i1"}),
    )

    resp = await client.patch(
        "/customer/integration-routes/00000000-0000-0000-0000-000000000014",
        headers=_auth_header(),
        json={"alert_types": ["NO_HEARTBEAT"], "severities": ["INFO"], "enabled": True},
    )
    assert resp.status_code == 200


async def test_delete_integration_route_not_found(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(customer_routes, "delete_integration_route", AsyncMock(return_value=False))

    resp = await client.delete(
        "/customer/integration-routes/00000000-0000-0000-0000-000000000015", headers=_auth_header()
    )
    assert resp.status_code == 404


async def test_delivery_status(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(customer_routes, "fetch_delivery_attempts", AsyncMock(return_value=[]))

    resp = await client.get("/customer/delivery-status", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["attempts"] == []


async def test_integration_delivery_email_type(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    integration_id = "00000000-0000-0000-0000-000000000016"
    monkeypatch.setattr(customer_routes, "check_and_increment_rate_limit", AsyncMock(return_value=(True, 1)))
    conn.fetchrow_result = {
        "integration_id": integration_id,
        "tenant_id": "tenant-a",
        "name": "Email",
        "type": "email",
        "email_config": {"smtp_host": "smtp.example.com"},
        "email_recipients": {"to": ["ops@example.com"]},
        "email_template": {},
        "enabled": True,
    }
    monkeypatch.setattr(
        customer_routes,
        "send_alert_email",
        AsyncMock(
            return_value=SimpleNamespace(success=True, error=None, duration_ms=5, recipients_count=1)
        ),
    )

    resp = await client.post(f"/customer/integrations/{integration_id}/test", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["integration_type"] == "email"


async def test_integration_delivery_snmp_type(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    integration_id = "00000000-0000-0000-0000-000000000017"
    monkeypatch.setattr(customer_routes, "check_and_increment_rate_limit", AsyncMock(return_value=(True, 1)))
    conn.fetchrow_result = {
        "integration_id": integration_id,
        "tenant_id": "tenant-a",
        "name": "SNMP",
        "type": "snmp",
        "snmp_host": "198.51.100.10",
        "snmp_port": 162,
        "snmp_config": {"version": "2c"},
        "snmp_oid_prefix": "1.3.6.1.4.1.99999",
        "enabled": True,
    }
    monkeypatch.setattr(
        customer_routes,
        "dispatch_to_integration",
        AsyncMock(return_value=SimpleNamespace(success=True, error=None, duration_ms=5)),
    )

    resp = await client.post(f"/customer/integrations/{integration_id}/test", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["integration_type"] == "snmp"


async def test_list_snmp_integrations(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    conn.fetch_result = [
        {
            "integration_id": "snmp-1",
            "tenant_id": "tenant-a",
            "name": "SNMP",
            "snmp_host": "198.51.100.10",
            "snmp_port": 162,
            "snmp_config": {"version": "2c"},
            "snmp_oid_prefix": "1.3.6.1.4.1.99999",
            "enabled": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
    ]

    resp = await client.get("/customer/integrations/snmp", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()[0]["snmp_host"] == "198.51.100.10"


async def test_get_snmp_integration_not_found(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    conn.fetchrow_result = None

    resp = await client.get("/customer/integrations/snmp/00000000-0000-0000-0000-000000000020", headers=_auth_header())
    assert resp.status_code == 404


async def test_update_snmp_integration_no_fields(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)

    resp = await client.patch(
        "/customer/integrations/snmp/00000000-0000-0000-0000-000000000021",
        headers=_auth_header(),
        json={},
    )
    assert resp.status_code == 400


async def test_update_snmp_integration_success(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(customer_routes, "validate_snmp_host", lambda host, port: SimpleNamespace(valid=True))
    conn.fetchrow_result = {
        "integration_id": "snmp-1",
        "tenant_id": "tenant-a",
        "name": "SNMP",
        "snmp_host": "198.51.100.10",
        "snmp_port": 162,
        "snmp_config": {"version": "2c"},
        "snmp_oid_prefix": "1.3.6.1.4.1.99999",
        "enabled": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    resp = await client.patch(
        "/customer/integrations/snmp/00000000-0000-0000-0000-000000000022",
        headers=_auth_header(),
        json={"name": "SNMP", "snmp_host": "198.51.100.10"},
    )
    assert resp.status_code == 200


async def test_delete_snmp_integration_success(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    conn.execute_result = "DELETE 1"

    resp = await client.delete(
        "/customer/integrations/snmp/00000000-0000-0000-0000-000000000023", headers=_auth_header()
    )
    assert resp.status_code == 204


async def test_list_email_integrations(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    conn.fetch_result = [
        {
            "integration_id": "email-1",
            "tenant_id": "tenant-a",
            "name": "Email",
            "email_config": {"smtp_host": "smtp.example.com", "smtp_port": 587, "smtp_tls": True, "from_address": "alerts@example.com"},
            "email_recipients": {"to": ["ops@example.com"]},
            "email_template": {"format": "html"},
            "enabled": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
    ]

    resp = await client.get("/customer/integrations/email", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()[0]["smtp_host"] == "smtp.example.com"


async def test_get_email_integration_not_found(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    conn.fetchrow_result = None

    resp = await client.get("/customer/integrations/email/00000000-0000-0000-0000-000000000024", headers=_auth_header())
    assert resp.status_code == 404


async def test_update_email_integration_no_fields(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)

    resp = await client.patch(
        "/customer/integrations/email/00000000-0000-0000-0000-000000000025",
        headers=_auth_header(),
        json={},
    )
    assert resp.status_code == 400


async def test_delete_email_integration_success(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    conn.execute_result = "DELETE 1"

    resp = await client.delete(
        "/customer/integrations/email/00000000-0000-0000-0000-000000000026", headers=_auth_header()
    )
    assert resp.status_code == 204


async def test_patch_integration_webhook_update(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(customer_routes, "validate_webhook_url", AsyncMock(return_value=(True, None)))
    monkeypatch.setattr(
        customer_routes,
        "update_integration",
        AsyncMock(return_value={"integration_id": "i1", "url": "https://example.com"}),
    )

    resp = await client.patch(
        "/customer/integrations/00000000-0000-0000-0000-000000000027",
        headers=_auth_header(),
        json={"webhook_url": "https://example.com", "enabled": False},
    )
    assert resp.status_code == 200


async def test_get_integration_not_found(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(customer_routes, "fetch_integration", AsyncMock(return_value=None))

    resp = await client.get("/customer/integrations/00000000-0000-0000-0000-000000000028", headers=_auth_header())
    assert resp.status_code == 404


async def test_device_detail_deprecated(client):
    resp = await client.get("/device/test-device")
    assert resp.status_code == 410


async def test_admin_create_device_success(client, monkeypatch):
    response = SimpleNamespace(status_code=200, text="ok")
    monkeypatch.setattr(app_module.httpx, "AsyncClient", lambda *a, **k: _mock_async_client(response))

    class AdminConn(FakeConn):
        async def execute(self, *args, **kwargs):
            return "OK"

    monkeypatch.setattr(app_module, "get_pool", AsyncMock(return_value=FakePool(AdminConn())))

    resp = await client.post(
        "/admin/create-device",
        data={"tenant_id": "tenant-a", "device_id": "d1", "site_id": "s1", "fw_version": "1.0"},
    )
    assert resp.status_code == 303


async def test_admin_activate_device_failure(client, monkeypatch):
    response = SimpleNamespace(status_code=400, text="bad")
    monkeypatch.setattr(app_module.httpx, "AsyncClient", lambda *a, **k: _mock_async_client(response))
    monkeypatch.setattr(app_module, "get_pool", AsyncMock(return_value=FakePool(FakeConn())))

    resp = await client.post(
        "/admin/activate-device",
        data={"tenant_id": "tenant-a", "device_id": "d1", "activation_code": "code"},
    )
    assert resp.status_code == 303


async def test_app_helpers(monkeypatch):
    monkeypatch.setenv("SECURE_COOKIES", "true")
    assert app_module._secure_cookies_enabled() is True
    monkeypatch.setenv("UI_BASE_URL", "http://localhost:8080/")
    assert app_module.get_ui_base_url() == "http://localhost:8080"
    verifier, challenge = app_module.generate_pkce_pair()
    assert verifier and challenge
    assert app_module.generate_state()
    assert app_module.redact_url("https://example.com/path") == "https://example.com"


async def test_login_redirects_to_keycloak(client, monkeypatch):
    monkeypatch.setenv("KEYCLOAK_PUBLIC_URL", "http://kc.example")
    monkeypatch.setattr(app_module, "generate_pkce_pair", lambda: ("verifier", "challenge"))
    monkeypatch.setattr(app_module, "generate_state", lambda: "state123")

    resp = await client.get("/login")
    assert resp.status_code == 302
    assert "kc.example" in resp.headers["location"]
    assert "code_challenge=challenge" in resp.headers["location"]


async def test_callback_missing_code(client):
    resp = await client.get("/callback")
    assert resp.status_code == 302
    assert resp.headers["location"] == "/?error=missing_code"


async def test_callback_state_mismatch(client, monkeypatch):
    monkeypatch.setattr(app_module, "validate_token", AsyncMock(return_value={"role": "customer_admin"}))
    cookies = {"oauth_state": "state123", "oauth_verifier": "verifier"}
    resp = await client.get("/callback?code=abc&state=other", cookies=cookies)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/?error=state_mismatch"


async def test_callback_token_exchange_failure(client, monkeypatch):
    response = SimpleNamespace(status_code=400, text="bad", json=lambda: {})
    cookies = {"oauth_state": "state123", "oauth_verifier": "verifier"}
    monkeypatch.setattr(app_module.httpx, "AsyncClient", lambda *a, **k: _mock_async_client(response))

    resp = await client.get("/callback?code=abc&state=state123", cookies=cookies)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/?error=invalid_code"


async def test_callback_success_customer(client, monkeypatch):
    response = SimpleNamespace(
        status_code=200,
        text="ok",
        json=lambda: {"access_token": "token", "refresh_token": "refresh", "expires_in": 300},
    )
    cookies = {"oauth_state": "state123", "oauth_verifier": "verifier"}
    monkeypatch.setattr(app_module.httpx, "AsyncClient", lambda *a, **k: _mock_async_client(response))
    monkeypatch.setattr(app_module, "validate_token", AsyncMock(return_value={"role": "customer_admin"}))

    resp = await client.get("/callback?code=abc&state=state123", cookies=cookies)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/customer/dashboard"


async def test_logout_redirects_to_keycloak(client, monkeypatch):
    monkeypatch.setenv("KEYCLOAK_PUBLIC_URL", "http://public.example")
    resp = await client.get("/logout")
    assert resp.status_code == 302
    assert "public.example" in resp.headers["location"]


async def test_auth_status_no_cookie(client):
    resp = await client.get("/api/auth/status")
    assert resp.json() == {"authenticated": False}


async def test_auth_status_valid_token(client, monkeypatch):
    monkeypatch.setattr(app_module, "validate_token", AsyncMock(return_value={"exp": 2000, "email": "a@b.com"}))
    monkeypatch.setattr(app_module.time, "time", lambda: 1700)
    resp = await client.get("/api/auth/status", cookies={"pulse_session": "token"})
    assert resp.json()["authenticated"] is True


async def test_auth_refresh_no_cookie(client):
    resp = await client.post("/api/auth/refresh")
    assert resp.status_code == 401


async def test_auth_refresh_success(client, monkeypatch):
    response = SimpleNamespace(
        status_code=200,
        json=lambda: {"access_token": "token", "refresh_token": "refresh", "expires_in": 120, "refresh_expires_in": 300},
    )
    monkeypatch.setattr(app_module.httpx, "AsyncClient", lambda *a, **k: _mock_async_client(response))
    resp = await client.post("/api/auth/refresh", cookies={"pulse_refresh": "refresh"})
    assert resp.status_code == 200


async def test_debug_auth_prod_mode(client, monkeypatch):
    monkeypatch.setenv("MODE", "PROD")
    resp = await client.get("/debug/auth")
    assert resp.status_code == 404


async def test_root_no_session(client):
    resp = await client.get("/")
    assert resp.status_code == 302
    assert resp.headers["location"] == "/login"


async def test_root_operator_session(client, monkeypatch):
    monkeypatch.setattr(app_module, "validate_token", AsyncMock(return_value={"role": "operator"}))
    resp = await client.get("/", cookies={"pulse_session": "token"})
    assert resp.status_code == 302
    assert resp.headers["location"] == "/operator/dashboard"
