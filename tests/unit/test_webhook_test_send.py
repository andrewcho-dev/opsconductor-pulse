from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import httpx
import pytest

import app as app_module
import dependencies as dependencies_module
from middleware import auth as auth_module
from middleware import tenant as tenant_module
from routes import customer as customer_routes

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class FakeConn:
    def __init__(self):
        self.integration_row = {
            "integration_id": "11111111-1111-1111-1111-111111111111",
            "type": "webhook",
            "config_json": {"url": "https://example.com/hook", "headers": {}},
            "enabled": True,
        }
        self.jobs_rows = []
        self.jobs_total = 0
        self.job_exists = {"job_id": 1}
        self.attempt_rows = []
        self.fetch_queries = []

    async def fetchrow(self, query, *args):
        if "FROM integrations" in query:
            return self.integration_row
        if "SELECT job_id FROM delivery_jobs" in query:
            return self.job_exists
        return None

    async def fetch(self, query, *args):
        self.fetch_queries.append(query)
        if "FROM delivery_jobs" in query:
            return self.jobs_rows
        if "FROM delivery_attempts" in query:
            return self.attempt_rows
        return []

    async def fetchval(self, query, *args):
        self.fetch_queries.append(query)
        if "COUNT(*) FROM delivery_jobs" in query:
            return self.jobs_total
        return None


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
    return {"Authorization": "Bearer test-token", "X-CSRF-Token": "csrf"}


def _mock_customer_deps(monkeypatch, conn, tenant_id="tenant-a"):
    user_payload = {
        "sub": "user-1",
        "tenant_id": tenant_id,
        "organization": {tenant_id: {}},
        "realm_access": {"roles": ["customer", "tenant-admin"]},
    }
    tenant_module.set_tenant_context(tenant_id, user_payload)
    monkeypatch.setattr(auth_module, "validate_token", AsyncMock(return_value=user_payload))
    monkeypatch.setattr(customer_routes, "validate_webhook_url", AsyncMock(return_value=(True, None)))

    async def _override_get_db_pool(_request=None):
        return FakePool(conn)

    app_module.app.dependency_overrides[dependencies_module.get_db_pool] = _override_get_db_pool
    monkeypatch.setattr(customer_routes, "get_db_pool", AsyncMock(return_value=FakePool(conn)))
    monkeypatch.setattr(customer_routes, "tenant_connection", _tenant_connection(conn))


@pytest.fixture
async def client():
    app_module.app.router.on_startup.clear()
    app_module.app.router.on_shutdown.clear()
    transport = httpx.ASGITransport(app=app_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set("csrf_token", "csrf")
        yield client
    app_module.app.dependency_overrides.clear()


class _MockResp:
    def __init__(self, status_code=200):
        self.status_code = status_code


class _MockAsyncClient:
    def __init__(self, status_code=200, raises: Exception | None = None, **_kwargs):
        self.status_code = status_code
        self.raises = raises

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *_args, **_kwargs):
        if self.raises:
            raise self.raises
        return _MockResp(self.status_code)


async def test_test_send_success(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    with patch("routes.customer.httpx.AsyncClient", return_value=_MockAsyncClient(status_code=200)):
        resp = await client.post(
            "/customer/integrations/11111111-1111-1111-1111-111111111111/test-send",
            headers=_auth_header(),
        )
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    assert resp.json()["http_status"] == 200


async def test_test_send_not_found(client, monkeypatch):
    conn = FakeConn()
    conn.integration_row = None
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post("/customer/integrations/missing/test-send", headers=_auth_header())
    assert resp.status_code == 404


async def test_test_send_not_webhook_type(client, monkeypatch):
    conn = FakeConn()
    conn.integration_row = {**conn.integration_row, "type": "email"}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post("/customer/integrations/11111111-1111-1111-1111-111111111111/test-send", headers=_auth_header())
    assert resp.status_code == 400


async def test_test_send_disabled(client, monkeypatch):
    conn = FakeConn()
    conn.integration_row = {**conn.integration_row, "enabled": False}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post("/customer/integrations/11111111-1111-1111-1111-111111111111/test-send", headers=_auth_header())
    assert resp.status_code == 400


async def test_test_send_no_url(client, monkeypatch):
    conn = FakeConn()
    conn.integration_row = {**conn.integration_row, "config_json": {}}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post("/customer/integrations/11111111-1111-1111-1111-111111111111/test-send", headers=_auth_header())
    assert resp.status_code == 400


async def test_test_send_connection_error(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    with patch("routes.customer.httpx.AsyncClient", return_value=_MockAsyncClient(raises=RuntimeError("boom"))):
        resp = await client.post(
            "/customer/integrations/11111111-1111-1111-1111-111111111111/test-send",
            headers=_auth_header(),
        )
    assert resp.status_code == 200
    assert resp.json()["success"] is False
    assert "boom" in resp.json()["error"]


async def test_list_delivery_jobs_default(client, monkeypatch):
    conn = FakeConn()
    conn.jobs_rows = [{"job_id": 1, "alert_id": 1, "integration_id": "i", "route_id": "r", "status": "FAILED", "attempts": 1, "last_error": "x", "deliver_on_event": "OPEN", "created_at": "2020-01-01T00:00:00Z", "updated_at": "2020-01-01T00:00:00Z"}]
    conn.jobs_total = 1
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/customer/delivery-jobs", headers=_auth_header())
    assert resp.status_code == 200
    assert len(resp.json()["jobs"]) == 1


async def test_list_delivery_jobs_filter_status(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/customer/delivery-jobs?status=FAILED", headers=_auth_header())
    assert resp.status_code == 200
    assert any("status =" in q for q in conn.fetch_queries)


async def test_list_delivery_jobs_invalid_status(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/customer/delivery-jobs?status=BOGUS", headers=_auth_header())
    assert resp.status_code == 400


async def test_get_job_attempts_success(client, monkeypatch):
    conn = FakeConn()
    conn.attempt_rows = [{"attempt_no": 1, "ok": True, "http_status": 200, "latency_ms": 10, "error": None, "started_at": "2020-01-01T00:00:00Z", "finished_at": "2020-01-01T00:00:01Z"}]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/customer/delivery-jobs/1/attempts", headers=_auth_header())
    assert resp.status_code == 200
    assert len(resp.json()["attempts"]) == 1


async def test_get_job_attempts_not_found(client, monkeypatch):
    conn = FakeConn()
    conn.job_exists = None
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/customer/delivery-jobs/1/attempts", headers=_auth_header())
    assert resp.status_code == 404
