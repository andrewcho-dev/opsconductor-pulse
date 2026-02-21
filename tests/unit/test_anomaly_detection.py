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
from services.evaluator_iot import evaluator

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class FakeConn:
    def __init__(self):
        self.fetchrow_result = None

    async def fetchval(self, *_args, **_kwargs):
        return 0

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
    async def _grant_all(_request=None):
        permissions_module.permissions_context.set({"*"})
    monkeypatch.setattr(permissions_module, "inject_permissions", _grant_all)
    monkeypatch.setattr(
        alerts_routes,
        "check_alert_rule_limit",
        AsyncMock(return_value={"allowed": True, "status_code": 200, "message": ""}),
    )


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
        yield c
    app_module.app.dependency_overrides.clear()


async def test_compute_z_score_above_threshold():
    assert evaluator.compute_z_score(10, 5, 1) == 5.0


async def test_compute_z_score_below_threshold():
    assert evaluator.compute_z_score(5.5, 5, 1) == 0.5


async def test_compute_z_score_zero_stddev():
    assert evaluator.compute_z_score(5, 5, 0) is None


async def test_compute_z_score_negative_deviation():
    assert evaluator.compute_z_score(2, 5, 1) == 3.0


async def test_compute_rolling_stats_returns_stats():
    conn = FakeConn()
    conn.fetchrow_result = {
        "mean_val": 42.0,
        "stddev_val": 2.0,
        "sample_count": 15,
        "latest_val": 50.0,
    }
    stats = await evaluator.compute_rolling_stats(conn, "tenant-a", "dev-1", "temperature", 60)
    assert stats == {"mean": 42.0, "stddev": 2.0, "count": 15, "latest": 50.0}


async def test_compute_rolling_stats_insufficient_data():
    conn = FakeConn()
    conn.fetchrow_result = {
        "mean_val": 42.0,
        "stddev_val": 2.0,
        "sample_count": 1,
        "latest_val": 50.0,
    }
    stats = await evaluator.compute_rolling_stats(conn, "tenant-a", "dev-1", "temperature", 60)
    assert stats is None


async def test_compute_rolling_stats_null_result():
    conn = FakeConn()
    conn.fetchrow_result = None
    stats = await evaluator.compute_rolling_stats(conn, "tenant-a", "dev-1", "temperature", 60)
    assert stats is None


async def test_create_anomaly_rule_api(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    create_mock = AsyncMock(
        return_value={
            "rule_id": "rule-1",
            "name": "Temp anomaly",
            "rule_type": "anomaly",
            "conditions": {
                "metric_name": "temperature",
                "window_minutes": 60,
                "z_threshold": 3.0,
                "min_samples": 10,
            },
        }
    )
    monkeypatch.setattr(alerts_routes, "create_alert_rule", create_mock)
    resp = await client.post(
        "/customer/alert-rules",
        headers=_auth_header(),
        json={
            "name": "Temp anomaly",
            "rule_type": "anomaly",
            "anomaly_conditions": {
                "metric_name": "temperature",
                "window_minutes": 60,
                "z_threshold": 3.0,
                "min_samples": 10,
            },
        },
    )
    assert resp.status_code == 201
    called_kwargs = create_mock.await_args.kwargs
    assert called_kwargs["rule_type"] == "anomaly"
    assert called_kwargs["conditions"]["metric_name"] == "temperature"


async def test_create_anomaly_rule_missing_conditions(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post(
        "/customer/alert-rules",
        headers=_auth_header(),
        json={"name": "Temp anomaly", "rule_type": "anomaly"},
    )
    assert resp.status_code == 422
