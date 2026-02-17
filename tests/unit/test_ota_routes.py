from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import httpx
import pytest

import app as app_module
import dependencies as dependencies_module
from middleware import auth as auth_module
from middleware import permissions as permissions_module
from middleware import tenant as tenant_module
from routes import ota as ota_routes

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.fixture(scope="session", autouse=True)
async def setup_delivery_tables():
    # Keep this file pure unit tests (override integration DB bootstrap fixture).
    yield


class _Tx:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class FakeConn:
    def __init__(self):
        self.fetchrow_result = None
        self.fetchrow_results: list[object] | None = None
        self.fetch_result = []
        self.fetch_results: list[list[object]] | None = None
        self.fetchval_result = None
        self.fetchval_results: list[object] | None = None
        self.executed = []
        self.executemany_calls = []

    async def fetchrow(self, query, *args):
        if self.fetchrow_results is not None:
            if not self.fetchrow_results:
                return None
            return self.fetchrow_results.pop(0)
        return self.fetchrow_result

    async def fetch(self, query, *args):
        if self.fetch_results is not None:
            if not self.fetch_results:
                return []
            return self.fetch_results.pop(0)
        return self.fetch_result

    async def fetchval(self, query, *args):
        if self.fetchval_results is not None:
            if not self.fetchval_results:
                return None
            return self.fetchval_results.pop(0)
        return self.fetchval_result

    async def execute(self, query, *args):
        self.executed.append((query, args))
        return "OK"

    async def executemany(self, query, seq_of_args):
        self.executemany_calls.append((query, list(seq_of_args)))
        return "OK"

    def transaction(self):
        return _Tx()


class FakePool:
    def __init__(self, conn: FakeConn):
        self.conn = conn

    @asynccontextmanager
    async def acquire(self):
        yield self.conn


def _tenant_connection(conn: FakeConn):
    @asynccontextmanager
    async def _ctx(_pool, _tenant_id):
        yield conn

    return _ctx


def _auth_header():
    return {"Authorization": "Bearer test-token", "X-CSRF-Token": "csrf"}


def _mock_customer_deps(monkeypatch, conn: FakeConn, *, tenant_id: str = "tenant-a", perms: set[str] | None = None):
    user_payload = {
        "sub": "user-1",
        "organization": {tenant_id: {}},
        "realm_access": {"roles": ["customer", "tenant-admin"]},
        "email": "u@example.com",
        "preferred_username": "me",
    }
    tenant_module.set_tenant_context(tenant_id, user_payload)
    monkeypatch.setattr(auth_module, "validate_token", AsyncMock(return_value=user_payload))

    async def _override_get_db_pool(_request=None):
        return FakePool(conn)

    app_module.app.dependency_overrides[dependencies_module.get_db_pool] = _override_get_db_pool
    monkeypatch.setattr(ota_routes, "tenant_connection", _tenant_connection(conn))

    if perms is None:
        perms = {"*"}

    async def _inject(_request):
        permissions_module.permissions_context.set(set(perms))
        return None

    monkeypatch.setattr(permissions_module, "inject_permissions", AsyncMock(side_effect=_inject))


@pytest.fixture
async def client():
    app_module.app.router.on_startup.clear()
    app_module.app.router.on_shutdown.clear()
    transport = httpx.ASGITransport(app=app_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        c.cookies.set("csrf_token", "csrf")
        yield c
    app_module.app.dependency_overrides.clear()


async def test_list_firmware_versions(client, monkeypatch):
    conn = FakeConn()
    conn.fetch_result = [
        {"id": 1, "version": "1.0.0", "device_type": "sensor", "created_at": datetime.now(timezone.utc)}
    ]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/firmware", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


async def test_list_firmware_versions_with_device_type_filter(client, monkeypatch):
    conn = FakeConn()
    conn.fetch_result = []
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/firmware?device_type=sensor", headers=_auth_header())
    assert resp.status_code == 200


async def test_create_firmware_version_duplicate_returns_409(client, monkeypatch):
    conn = FakeConn()
    conn.fetchval_result = 1
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post(
        "/api/v1/customer/firmware",
        headers=_auth_header(),
        json={"version": "1.0.0", "file_url": "https://example/fw.bin", "device_type": "sensor"},
    )
    assert resp.status_code == 409


async def test_create_firmware_version_success(client, monkeypatch):
    conn = FakeConn()
    conn.fetchval_result = None
    conn.fetchrow_result = {"id": 1, "version": "1.0.1", "file_url": "https://example/fw.bin"}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post(
        "/api/v1/customer/firmware",
        headers=_auth_header(),
        json={"version": "1.0.1", "file_url": "https://example/fw.bin", "device_type": "sensor"},
    )
    assert resp.status_code == 201
    assert resp.json()["id"] == 1


async def test_list_campaigns_filter_by_status(client, monkeypatch):
    conn = FakeConn()
    conn.fetch_result = [{"id": 1, "name": "C", "status": "RUNNING"}]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/ota/campaigns?status=running", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


async def test_create_campaign_firmware_not_found(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = None  # firmware version lookup
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post(
        "/api/v1/customer/ota/campaigns",
        headers=_auth_header(),
        json={"name": "Update", "firmware_version_id": 1, "target_group_id": "all", "rollout_strategy": "linear"},
    )
    assert resp.status_code == 404


async def test_create_campaign_group_not_found(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_results = [{"id": 1, "version": "1.0.0", "file_url": "x", "checksum_sha256": None}]
    conn.fetchval_results = [None]  # group not found
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post(
        "/api/v1/customer/ota/campaigns",
        headers=_auth_header(),
        json={"name": "Update", "firmware_version_id": 1, "target_group_id": "missing", "rollout_strategy": "linear"},
    )
    assert resp.status_code == 404


async def test_create_campaign_group_has_no_members(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_results = [{"id": 1, "version": "1.0.0", "file_url": "x", "checksum_sha256": None}]
    conn.fetchval_results = [1]  # group exists
    conn.fetch_results = [[]]  # members empty
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post(
        "/api/v1/customer/ota/campaigns",
        headers=_auth_header(),
        json={"name": "Update", "firmware_version_id": 1, "target_group_id": "all", "rollout_strategy": "linear"},
    )
    assert resp.status_code == 400


async def test_create_campaign_success(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_results = [
        {"id": 1, "version": "1.0.0", "file_url": "x", "checksum_sha256": None},  # firmware
        {"id": 10, "name": "Update", "status": "CREATED", "total_devices": 2, "created_at": datetime.now(timezone.utc), "created_by": "user-1"},
    ]
    conn.fetchval_results = [1]  # group exists
    conn.fetch_results = [[{"device_id": "d1"}, {"device_id": "d2"}]]  # members
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post(
        "/api/v1/customer/ota/campaigns",
        headers=_auth_header(),
        json={"name": "Update v1.1", "firmware_version_id": 1, "target_group_id": "all", "rollout_strategy": "linear"},
    )
    assert resp.status_code == 201
    assert resp.json()["target_group_id"] == "all"
    assert conn.executemany_calls  # pre-populated device status rows


async def test_get_campaign_not_found(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = None
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/ota/campaigns/1", headers=_auth_header())
    assert resp.status_code == 404


async def test_get_campaign_success_includes_status_breakdown(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_results = [
        {"id": 1, "tenant_id": "tenant-a", "firmware_version_id": 1, "status": "RUNNING", "name": "C"},
    ]
    conn.fetch_results = [[{"status": "SUCCEEDED", "count": 2}, {"status": "FAILED", "count": 1}]]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/ota/campaigns/1", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["status_breakdown"]["SUCCEEDED"] == 2


async def test_start_campaign_invalid_status_returns_400(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"id": 1, "status": "RUNNING"}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post("/api/v1/customer/ota/campaigns/1/start", headers=_auth_header())
    assert resp.status_code == 400


async def test_pause_campaign_invalid_status_returns_400(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"id": 1, "status": "CREATED"}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post("/api/v1/customer/ota/campaigns/1/pause", headers=_auth_header())
    assert resp.status_code == 400


async def test_abort_campaign_terminal_status_returns_400(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"id": 1, "status": "COMPLETED"}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post("/api/v1/customer/ota/campaigns/1/abort", headers=_auth_header())
    assert resp.status_code == 400


async def test_abort_campaign_success(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"id": 1, "status": "RUNNING"}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post("/api/v1/customer/ota/campaigns/1/abort", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["status"] == "ABORTED"


async def test_list_campaign_devices_campaign_not_found(client, monkeypatch):
    conn = FakeConn()
    conn.fetchval_result = None  # exists
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/ota/campaigns/1/devices", headers=_auth_header())
    assert resp.status_code == 404


async def test_list_campaign_devices_success(client, monkeypatch):
    conn = FakeConn()
    conn.fetchval_results = [1, 2]  # campaign exists, total
    conn.fetch_result = [{"device_id": "d1", "status": "SUCCEEDED"}]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/ota/campaigns/1/devices?status=SUCCEEDED", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["total"] == 2

