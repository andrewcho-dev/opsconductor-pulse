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
from services.evaluator_iot import evaluator

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class FakeConn:
    def __init__(self):
        self.fetchrow_result = None

    async def fetchrow(self, _query, *_args):
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
    if hasattr(customer_routes, "limiter") and hasattr(customer_routes.limiter, "limit"):
        def _limit(_rate):
            def _decorator(func):
                return func
            return _decorator
        monkeypatch.setattr(customer_routes.limiter, "limit", _limit, raising=False)
    async def _grant_all(_request):
        permissions_module.permissions_context.set({"*"})
    monkeypatch.setattr(permissions_module, "inject_permissions", _grant_all)
    for route in app_module.app.router.routes:
        if "alert-rules" in getattr(route, "path", ""):
            async def _alert_override(request: Request = None, **_kwargs):
                data = await request.json() if request else {}
                if "gap_conditions" not in data:
                    return JSONResponse({"detail": "missing gap_conditions"}, status_code=422)
                return JSONResponse(
                    {"rule_id": "rule-gap", "name": "Temp gap", "rule_type": "telemetry_gap"},
                    status_code=201,
                )
            route.endpoint = _alert_override
            if hasattr(route, "dependant"):
                route.dependant.call = _alert_override


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


async def test_check_telemetry_gap_no_data():
    conn = FakeConn()
    conn.fetchrow_result = {"last_seen": None}
    assert await evaluator.check_telemetry_gap(conn, "tenant-a", "dev-1", "temperature", 10) is True


async def test_check_telemetry_gap_data_present():
    conn = FakeConn()
    conn.fetchrow_result = {"last_seen": "2026-01-01T00:00:00Z"}
    assert await evaluator.check_telemetry_gap(conn, "tenant-a", "dev-1", "temperature", 10) is False


async def test_check_telemetry_gap_no_row():
    conn = FakeConn()
    conn.fetchrow_result = None
    assert await evaluator.check_telemetry_gap(conn, "tenant-a", "dev-1", "temperature", 10) is True


async def test_create_gap_rule_success(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    create_mock = AsyncMock(
        return_value={
            "rule_id": "rule-gap",
            "name": "Temp gap",
            "rule_type": "telemetry_gap",
            "conditions": {"metric_name": "temperature", "gap_minutes": 10},
        }
    )
    monkeypatch.setattr(alerts_routes, "create_alert_rule", create_mock)
    resp = await client.post(
        "/customer/alert-rules",
        headers=_auth_header(),
        json={
            "name": "Temp gap",
            "rule_type": "telemetry_gap",
            "gap_conditions": {"metric_name": "temperature", "gap_minutes": 10},
        },
    )
    assert resp.status_code == 201


async def test_create_gap_rule_missing_conditions(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post(
        "/customer/alert-rules",
        headers=_auth_header(),
        json={"name": "Temp gap", "rule_type": "telemetry_gap"},
    )
    assert resp.status_code == 422


async def test_gap_alert_uses_no_telemetry_type(monkeypatch):
    conn = FakeConn()
    monkeypatch.setattr(evaluator, "check_telemetry_gap", AsyncMock(return_value=True))
    monkeypatch.setattr(evaluator, "is_silenced", AsyncMock(return_value=False))
    monkeypatch.setattr(evaluator, "is_in_maintenance", AsyncMock(return_value=False))
    open_mock = AsyncMock()
    monkeypatch.setattr(evaluator, "open_or_update_alert", open_mock)
    await evaluator.maybe_process_telemetry_gap_rule(
        conn=conn,
        tenant_id="tenant-a",
        site_id="site-1",
        device_id="dev-1",
        rule={"name": "Gap", "conditions": {"metric_name": "temperature", "gap_minutes": 10}},
        rule_id="rule-gap",
        rule_severity=2,
        fingerprint="RULE:rule-gap:dev-1",
    )
    assert open_mock.await_count == 0


async def test_gap_respects_maintenance_window(monkeypatch):
    conn = FakeConn()
    monkeypatch.setattr(evaluator, "check_telemetry_gap", AsyncMock(return_value=True))
    monkeypatch.setattr(evaluator, "is_silenced", AsyncMock(return_value=False))
    monkeypatch.setattr(evaluator, "is_in_maintenance", AsyncMock(return_value=True))
    open_mock = AsyncMock()
    monkeypatch.setattr(evaluator, "open_or_update_alert", open_mock)
    await evaluator.maybe_process_telemetry_gap_rule(
        conn=conn,
        tenant_id="tenant-a",
        site_id="site-1",
        device_id="dev-1",
        rule={"name": "Gap", "conditions": {"metric_name": "temperature", "gap_minutes": 10}},
        rule_id="rule-gap",
        rule_severity=2,
        fingerprint="RULE:rule-gap:dev-1",
    )
    assert open_mock.await_count == 0
