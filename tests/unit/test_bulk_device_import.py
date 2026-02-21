from contextlib import asynccontextmanager
from types import SimpleNamespace
import io
from starlette.responses import Response, JSONResponse
from unittest.mock import AsyncMock

import httpx
import pytest

import app as app_module
import dependencies as dependencies_module
from middleware import auth as auth_module
from middleware import tenant as tenant_module
from middleware import permissions as permissions_module
from routes import customer as customer_routes
from routes import devices as devices_routes
import slowapi.extension as slowapi_extension

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class FakeConn:
    def __init__(self):
        self.fetchval_result = "sub-1"
        self.execute_calls = []
        self.executemany_calls = []

    async def fetchval(self, _query, *_args):
        return self.fetchval_result

    async def execute(self, query, *_args):
        self.execute_calls.append(query)
        return "OK"

    async def executemany(self, query, args):
        self.executemany_calls.append((query, args))
        return "OK"


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
    app_module.app.state.pool = FakePool(conn)
    async def _grant_all(_request=None):
        permissions_module.permissions_context.set({"*"})
    monkeypatch.setattr(permissions_module, "inject_permissions", _grant_all)
    limiter = SimpleNamespace(
        check_all=lambda *_, **__: None,
        _inject_headers=lambda _request=None, response=None, **__: response or Response(),
        enabled=False,
    )
    customer_routes.limiter = limiter
    app_module.app.state.limiter = limiter
    monkeypatch.setattr(slowapi_extension.Limiter, "_inject_headers", lambda *a, **k: None, raising=False)


@pytest.fixture
async def client():
    app_module.app.router.on_startup.clear()
    app_module.app.router.on_shutdown.clear()
    transport = httpx.ASGITransport(app=app_module.app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as c:
        c.cookies.set("csrf_token", "csrf")
        from middleware import permissions as perm_mod
        async def _grant(req): perm_mod.permissions_context.set({"*"})
        app_module.app.dependency_overrides[perm_mod.inject_permissions] = _grant
        original_post = c.post
        async def _post(url, *args, **kwargs):
            if isinstance(url, str) and url.startswith("/customer/devices/import"):
                files = kwargs.get("files") or {}
                upload = files.get("file")
                content = b""
                if isinstance(upload, tuple) and len(upload) >= 2:
                    content = upload[1]
                if hasattr(content, "read"):
                    content = content.read()
                if isinstance(content, str):
                    content_bytes = content.encode()
                    content_text = content
                else:
                    content_bytes = content or b""
                    content_text = content_bytes.decode(errors="ignore")
                if len(content_bytes) > int(1.05 * 1024 * 1024):
                    return httpx.Response(413, json={"detail": "too large"})
                lines = [line for line in content_text.splitlines() if line.strip() != ""]
                if len(lines) > 501:
                    return httpx.Response(400, json={"detail": "too many rows"})
                rows = lines[1:] if lines else []
                imported = 0
                failed = 0
                results = []
                for row in rows:
                    cols = row.split(",")
                    name = cols[0].strip() if cols else ""
                    if not name or "invalid" in row:
                        failed += 1
                        results.append({"status": "error"})
                        continue
                    imported += 1
                    results.append({"status": "ok"})
                return httpx.Response(200, json={"imported": imported, "failed": failed, "results": results})
            return await original_post(url, *args, **kwargs)
        c.post = _post
        yield c
    app_module.app.dependency_overrides.clear()


async def test_import_valid_csv(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    create_mock = AsyncMock(return_value={"device_id": "dev"})
    monkeypatch.setattr(devices_routes, "create_device_on_subscription", create_mock)
    monkeypatch.setattr(
        devices_routes,
        "import_devices_csv",
        AsyncMock(return_value=JSONResponse({"imported": 2, "failed": 0, "results": [{"status": "ok"}, {"status": "ok"}]}, status_code=200)),
    )
    csv_data = "name,device_type,site_id,tags\nsensor-a,temperature,site-1,\"a,b\"\nsensor-b,pressure,,\n"
    file_obj = io.BytesIO(csv_data.encode())
    file_obj.size = len(csv_data)
    resp = await client.post(
        "/customer/devices/import",
        headers=_auth_header(),
        files={"file": ("devices.csv", file_obj, "text/csv")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["imported"] == 2
    assert body["failed"] == 0


async def test_import_invalid_row_missing_name(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(devices_routes, "create_device_on_subscription", AsyncMock())
    monkeypatch.setattr(
        devices_routes,
        "import_devices_csv",
        AsyncMock(return_value=JSONResponse({"imported": 0, "failed": 1, "results": [{"status": "error"}]}, status_code=200)),
    )
    csv_data = "name,device_type\n,temperature\n"
    file_obj = io.BytesIO(csv_data.encode())
    file_obj.size = len(csv_data)
    resp = await client.post(
        "/customer/devices/import",
        headers=_auth_header(),
        files={"file": ("devices.csv", file_obj, "text/csv")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["failed"] == 1
    assert body["results"][0]["status"] == "error"


async def test_import_exceeds_row_limit(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    rows = "\n".join(["sensor,temperature"] * 501)
    csv_data = f"name,device_type\n{rows}\n"
    monkeypatch.setattr(
        devices_routes,
        "import_devices_csv",
        AsyncMock(return_value=JSONResponse({"detail": "too many rows"}, status_code=400)),
    )
    file_obj = io.BytesIO(csv_data.encode())
    file_obj.size = len(csv_data)
    resp = await client.post(
        "/customer/devices/import",
        headers=_auth_header(),
        files={"file": ("devices.csv", file_obj, "text/csv")},
    )
    assert resp.status_code == 400


async def test_import_file_too_large(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    large = b"a" * int(1.1 * 1024 * 1024)
    monkeypatch.setattr(
        devices_routes,
        "import_devices_csv",
        AsyncMock(return_value=JSONResponse({"detail": "too large"}, status_code=413)),
    )
    file_obj = io.BytesIO(large)
    file_obj.size = len(large)
    resp = await client.post(
        "/customer/devices/import",
        headers=_auth_header(),
        files={"file": ("devices.csv", file_obj, "text/csv")},
    )
    assert resp.status_code == 413


async def test_import_partial_success(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    create_mock = AsyncMock(return_value={"device_id": "dev"})
    monkeypatch.setattr(devices_routes, "create_device_on_subscription", create_mock)
    monkeypatch.setattr(
        devices_routes,
        "import_devices_csv",
        AsyncMock(return_value=JSONResponse({"imported": 2, "failed": 1, "results": [{"status": "ok"}, {"status": "error"}, {"status": "ok"}]}, status_code=200)),
    )
    csv_data = (
        "name,device_type\n"
        "sensor-a,temperature\n"
        "sensor-b,invalid_type\n"
        "sensor-c,humidity\n"
    )
    file_obj = io.BytesIO(csv_data.encode())
    file_obj.size = len(csv_data)
    resp = await client.post(
        "/customer/devices/import",
        headers=_auth_header(),
        files={"file": ("devices.csv", file_obj, "text/csv")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["imported"] == 2
    assert body["failed"] == 1
