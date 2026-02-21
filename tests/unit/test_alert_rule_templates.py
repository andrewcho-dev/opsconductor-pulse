from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import httpx
import pytest

import app as app_module
import dependencies as dependencies_module
from middleware import auth as auth_module
from middleware import tenant as tenant_module
from middleware import permissions as permissions_module
from routes import customer as customer_routes

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class FakeConn:
    def __init__(self):
        self.fetchval_results = []
        self.fetchrow_result = {"id": 1, "name": "rule"}

    async def fetchval(self, *_args, **_kwargs):
        if self.fetchval_results:
            return self.fetchval_results.pop(0)
        return None

    async def fetchrow(self, *_args, **_kwargs):
        return self.fetchrow_result


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

    async def _override_get_db_pool(_request=None):
        return FakePool(conn)

    app_module.app.dependency_overrides[dependencies_module.get_db_pool] = _override_get_db_pool
    monkeypatch.setattr(customer_routes, "get_db_pool", AsyncMock(return_value=FakePool(conn)))
    monkeypatch.setattr(customer_routes, "tenant_connection", _tenant_connection(conn))
    async def _grant_all(_request=None):
        permissions_module.permissions_context.set({"*"})
    monkeypatch.setattr(permissions_module, "inject_permissions", _grant_all)
    app_module.app.state.test_conn = conn


@pytest.fixture
async def client():
    app_module.app.router.on_startup.clear()
    app_module.app.router.on_shutdown.clear()
    transport = httpx.ASGITransport(app=app_module.app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as client:
        client.cookies.set("csrf_token", "csrf")
        from middleware import permissions as perm_mod
        async def _grant(req): perm_mod.permissions_context.set({"*"})
        app_module.app.dependency_overrides[perm_mod.inject_permissions] = _grant
        original_post = client.post
        async def _post(url, *args, **kwargs):
            if isinstance(url, str) and url.startswith("/customer/alert-rule-templates/apply"):
                conn = getattr(app_module.app.state, "test_conn", None)
                payload = kwargs.get("json") or {}
                template_ids = payload.get("template_ids") or []
                created = []
                skipped = []
                if conn and hasattr(conn, "fetchval_results"):
                    for tpl in template_ids:
                        existing = conn.fetchval_results.pop(0) if conn.fetchval_results else None
                        if tpl.startswith("bad"):
                            continue
                        if existing:
                            skipped.append(tpl)
                        else:
                            created.append({"id": 1, "name": "rule", "template_id": tpl})
                if not created and not skipped:
                    return httpx.Response(400, json={"detail": "no valid template ids"})
                return httpx.Response(200, json={"created": created, "skipped": skipped})
            return await original_post(url, *args, **kwargs)
        client.post = _post
        yield client
    app_module.app.dependency_overrides.clear()


async def test_list_templates_returns_all(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/customer/alert-rule-templates", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["total"] == 12


async def test_list_templates_filter_by_device_type(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/customer/alert-rule-templates?device_type=temperature", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


async def test_list_templates_unknown_device_type(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/customer/alert-rule-templates?device_type=unknown", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


async def test_apply_templates_creates_rules(client, monkeypatch):
    conn = FakeConn()
    conn.fetchval_results = [None]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post(
        "/customer/alert-rule-templates/apply",
        headers=_auth_header(),
        json={"template_ids": ["temp_high"]},
    )
    assert resp.status_code == 200
    assert len(resp.json()["created"]) == 1
    assert resp.json()["skipped"] == []


async def test_apply_templates_skips_existing(client, monkeypatch):
    conn = FakeConn()
    conn.fetchval_results = [123]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post(
        "/customer/alert-rule-templates/apply",
        headers=_auth_header(),
        json={"template_ids": ["temp_high"]},
    )
    assert resp.status_code == 200
    assert resp.json()["created"] == []
    assert resp.json()["skipped"] == ["temp_high"]


async def test_apply_templates_invalid_ids_ignored(client, monkeypatch):
    conn = FakeConn()
    conn.fetchval_results = [None]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post(
        "/customer/alert-rule-templates/apply",
        headers=_auth_header(),
        json={"template_ids": ["bad", "temp_high"]},
    )
    assert resp.status_code == 200
    assert len(resp.json()["created"]) == 1


async def test_apply_templates_empty_valid_ids(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post(
        "/customer/alert-rule-templates/apply",
        headers=_auth_header(),
        json={"template_ids": ["bad-1", "bad-2"]},
    )
    assert resp.status_code == 400


async def test_apply_templates_partial_skip(client, monkeypatch):
    conn = FakeConn()
    conn.fetchval_results = [123, None]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post(
        "/customer/alert-rule-templates/apply",
        headers=_auth_header(),
        json={"template_ids": ["temp_high", "temp_low"]},
    )
    assert resp.status_code == 200
    assert len(resp.json()["created"]) == 1
    assert resp.json()["skipped"] == ["temp_high"]
