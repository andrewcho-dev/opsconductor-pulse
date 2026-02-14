import importlib

import httpx
import pytest
from starlette.requests import Request

import app as app_module
from routes import customer as customer_routes

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


def _request(path="/customer/devices", client_ip="127.0.0.1"):
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "path": path,
        "headers": [],
        "query_string": b"",
        "client": (client_ip, 12345),
        "scheme": "http",
        "server": ("test", 80),
    }
    return Request(scope)


async def test_rate_limit_key_uses_tenant_id():
    req = _request()
    req.state.tenant_id = "tenant-a"
    assert customer_routes.get_rate_limit_key(req) == "tenant-a"


async def test_rate_limit_key_falls_back_to_ip():
    req = _request(client_ip="10.0.0.5")
    assert customer_routes.get_rate_limit_key(req) == "10.0.0.5"


async def test_429_response_is_json():
    req = _request()

    class _Exc:
        retry_after = 60

    resp = await app_module.rate_limit_handler(req, _Exc())
    assert resp.status_code == 429
    assert b"Rate limit exceeded" in resp.body


async def test_429_has_retry_after_header():
    req = _request()

    class _Exc:
        retry_after = 42

    resp = await app_module.rate_limit_handler(req, _Exc())
    assert resp.headers.get("Retry-After") == "42"


async def test_health_endpoint_not_rate_limited():
    app_module.app.router.on_startup.clear()
    app_module.app.router.on_shutdown.clear()
    transport = httpx.ASGITransport(app=app_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/healthz")
    assert resp.status_code == 200


async def test_rate_limit_env_var_default(monkeypatch):
    monkeypatch.delenv("RATE_LIMIT_CUSTOMER", raising=False)
    reloaded = importlib.reload(customer_routes)
    assert reloaded.CUSTOMER_RATE_LIMIT == "100/minute"
