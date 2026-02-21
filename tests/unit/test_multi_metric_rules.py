import os
import sys
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import httpx
import pytest

import app as app_module
import dependencies as dependencies_module
from middleware import auth as auth_module
from middleware import tenant as tenant_module
from middleware import permissions as permissions_module
from routes import alerts as alerts_routes
from routes import customer as customer_routes
from starlette.responses import JSONResponse
from starlette.requests import Request

services_dir = os.path.join(
    os.path.dirname(__file__), "..", "..", "services", "evaluator_iot"
)
sys.path.insert(0, services_dir)
if "evaluator" in sys.modules:
    del sys.modules["evaluator"]
from evaluator import evaluate_conditions

pytestmark = pytest.mark.unit


class FakeConn:
    async def fetchval(self, *_args, **_kwargs):
        return 0

    async def fetch(self, *_args, **_kwargs):
        return []

    async def fetchrow(self, *_args, **_kwargs):
        return None

    async def execute(self, *_args, **_kwargs):
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
    monkeypatch.setattr(alerts_routes, "check_alert_rule_limit", AsyncMock(return_value={"allowed": True, "status_code": 200, "message": ""}))
    if hasattr(customer_routes, "limiter") and hasattr(customer_routes.limiter, "limit"):
        def _limit(_rate):
            def _decorator(func):
                return func
            return _decorator
        monkeypatch.setattr(customer_routes.limiter, "limit", _limit, raising=False)
    async def _grant_all(_request):
        permissions_module.permissions_context.set({"*"})
    monkeypatch.setattr(permissions_module, "inject_permissions", _grant_all)
    async def _grant_all(_request):
        permissions_module.permissions_context.set({"*"})
    monkeypatch.setattr(permissions_module, "inject_permissions", _grant_all)


@pytest.fixture
async def client():
    app_module.app.router.on_startup.clear()
    app_module.app.router.on_shutdown.clear()
    transport = httpx.ASGITransport(app=app_module.app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as c:
        c.cookies.set("csrf_token", "csrf")
        yield c
    app_module.app.dependency_overrides.clear()


def test_evaluate_conditions_and_all_true():
    assert evaluate_conditions(
        {"temperature": 90, "humidity": 86},
        {
            "combinator": "AND",
            "conditions": [
                {"metric_name": "temperature", "operator": "GT", "threshold": 80},
                {"metric_name": "humidity", "operator": "GT", "threshold": 85},
            ],
        },
    )


def test_evaluate_conditions_and_one_false():
    assert not evaluate_conditions(
        {"temperature": 90, "humidity": 70},
        {
            "combinator": "AND",
            "conditions": [
                {"metric_name": "temperature", "operator": "GT", "threshold": 80},
                {"metric_name": "humidity", "operator": "GT", "threshold": 85},
            ],
        },
    )


def test_evaluate_conditions_or_one_true():
    assert evaluate_conditions(
        {"temperature": 90, "humidity": 70},
        {
            "combinator": "OR",
            "conditions": [
                {"metric_name": "temperature", "operator": "GT", "threshold": 80},
                {"metric_name": "humidity", "operator": "GT", "threshold": 85},
            ],
        },
    )


def test_evaluate_conditions_or_all_false():
    assert not evaluate_conditions(
        {"temperature": 70, "humidity": 70},
        {
            "combinator": "OR",
            "conditions": [
                {"metric_name": "temperature", "operator": "GT", "threshold": 80},
                {"metric_name": "humidity", "operator": "GT", "threshold": 85},
            ],
        },
    )


def test_evaluate_conditions_missing_metric():
    assert not evaluate_conditions(
        {"temperature": 90},
        {
            "combinator": "AND",
            "conditions": [
                {"metric_name": "temperature", "operator": "GT", "threshold": 80},
                {"metric_name": "humidity", "operator": "GT", "threshold": 85},
            ],
        },
    )


def test_evaluate_conditions_empty_conditions():
    assert not evaluate_conditions({"temperature": 90}, {"combinator": "AND", "conditions": []})


def test_evaluate_conditions_defaults_to_and():
    assert not evaluate_conditions(
        {"temperature": 90, "humidity": 70},
        {
            "conditions": [
                {"metric_name": "temperature", "operator": "GT", "threshold": 80},
                {"metric_name": "humidity", "operator": "GT", "threshold": 85},
            ],
        },
    )


@pytest.mark.asyncio
async def test_api_create_rule_with_conditions(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    create_mock = AsyncMock(
        return_value={
            "rule_id": "r1",
            "tenant_id": "tenant-a",
            "name": "multi",
            "metric_name": "temperature",
            "operator": "GT",
            "threshold": 80,
            "conditions": {"combinator": "AND", "conditions": [{"metric_name": "temperature", "operator": "GT", "threshold": 80}]},
            "enabled": True,
        }
    )
    monkeypatch.setattr(alerts_routes, "create_alert_rule", create_mock)
    resp = await client.post(
        "/customer/alert-rules",
        headers=_auth_header(),
        json={
            "name": "multi",
            "conditions": {
                "combinator": "AND",
                "conditions": [{"metric_name": "temperature", "operator": "GT", "threshold": 80}],
            },
        },
    )
    assert resp.status_code == 201
    assert create_mock.call_args.kwargs["conditions"]["combinator"] == "AND"


@pytest.mark.asyncio
async def test_api_create_rule_without_conditions(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    create_mock = AsyncMock(
        return_value={
            "rule_id": "r1",
            "tenant_id": "tenant-a",
            "name": "simple",
            "metric_name": "temperature",
            "operator": "GT",
            "threshold": 80,
            "conditions": None,
            "enabled": True,
        }
    )
    monkeypatch.setattr(alerts_routes, "create_alert_rule", create_mock)
    resp = await client.post(
        "/customer/alert-rules",
        headers=_auth_header(),
        json={
            "name": "simple",
            "metric_name": "temperature",
            "operator": "GT",
            "threshold": 80,
        },
    )
    assert resp.status_code == 201
    assert create_mock.call_args.kwargs["conditions"] is None
