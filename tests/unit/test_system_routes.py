from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock

import httpx
import pytest

import app as app_module
from middleware import auth as auth_module
from middleware import permissions as permissions_module
from routes import system as system_routes

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class _Pool:
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


def _mock_auth(monkeypatch, role="operator"):
    roles = [role]
    monkeypatch.setattr(
        auth_module,
        "validate_token",
        AsyncMock(
            return_value={
                "sub": "user-1",
                "role": role,
                "realm_access": {"roles": roles},
                "organization": {},
            }
        ),
    )
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
        yield c


async def test_system_health_returns_all_components(client, monkeypatch):
    _mock_auth(monkeypatch, role="operator")
    monkeypatch.setattr(system_routes, "check_postgres", AsyncMock(return_value={"status": "healthy", "latency_ms": 1}))
    monkeypatch.setattr(system_routes, "check_mqtt", AsyncMock(return_value={"status": "healthy", "latency_ms": 1}))
    monkeypatch.setattr(system_routes, "check_keycloak", AsyncMock(return_value={"status": "healthy", "latency_ms": 1}))
    monkeypatch.setattr(system_routes, "check_service", AsyncMock(return_value={"status": "healthy", "latency_ms": 1}))

    resp = await client.get("/operator/system/health", headers=_auth_header())
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert set(data["components"].keys()) == {
        "postgres", "mqtt", "keycloak", "ingest", "evaluator", "dispatcher", "delivery"
    }


async def test_system_health_degraded_when_service_down(client, monkeypatch):
    _mock_auth(monkeypatch, role="operator")
    monkeypatch.setattr(system_routes, "check_postgres", AsyncMock(return_value={"status": "healthy"}))
    monkeypatch.setattr(system_routes, "check_mqtt", AsyncMock(return_value={"status": "healthy"}))
    monkeypatch.setattr(system_routes, "check_keycloak", AsyncMock(return_value={"status": "healthy"}))

    async def _svc(name, _url):
        if name == "ingest":
            return {"status": "down", "error": "connection refused"}
        return {"status": "healthy"}

    monkeypatch.setattr(system_routes, "check_service", AsyncMock(side_effect=_svc))
    resp = await client.get("/operator/system/health", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["status"] == "degraded"
    assert resp.json()["components"]["ingest"]["status"] == "down"


async def test_system_health_requires_operator_role(client, monkeypatch):
    _mock_auth(monkeypatch, role="customer")
    resp = await client.get("/operator/system/health", headers=_auth_header())
    assert resp.status_code == 403


async def test_system_metrics_returns_throughput(client, monkeypatch):
    _mock_auth(monkeypatch, role="operator")
    monkeypatch.setattr(system_routes, "get_pool", AsyncMock(return_value=_Pool(object())))
    monkeypatch.setattr(system_routes, "calculate_ingest_rate", AsyncMock(return_value=3.5))
    monkeypatch.setattr(system_routes, "fetch_service_counters", AsyncMock(return_value={"messages_received": 10}))

    resp = await client.get("/operator/system/metrics", headers=_auth_header())
    assert resp.status_code == 200
    data = resp.json()
    assert data["throughput"]["ingest_rate_per_sec"] == 3.5
    assert "messages_received_total" in data["throughput"]


async def test_system_metrics_history_returns_time_series(client, monkeypatch):
    _mock_auth(monkeypatch, role="operator")
    now = datetime.now(timezone.utc)
    conn = AsyncMock()
    conn.fetch.return_value = [
        {"time": now - timedelta(minutes=1), "value": 1},
        {"time": now, "value": 2},
    ]
    monkeypatch.setattr(system_routes, "get_pool", AsyncMock(return_value=_Pool(conn)))

    resp = await client.get("/operator/system/metrics/history?metric=test_metric&minutes=5", headers=_auth_header())
    assert resp.status_code == 200
    points = resp.json()["points"]
    assert len(points) == 2
    assert points[0]["value"] == 1


async def test_system_metrics_history_batch_returns_multiple(client, monkeypatch):
    _mock_auth(monkeypatch, role="operator")
    monkeypatch.setattr(
        system_routes,
        "get_metrics_history",
        AsyncMock(side_effect=[
            {"metric": "m1", "points": [{"time": "t1", "value": 1}]},
            {"metric": "m2", "points": [{"time": "t2", "value": 2}]},
        ]),
    )
    resp = await client.get("/operator/system/metrics/history/batch?metrics=m1,m2&minutes=5", headers=_auth_header())
    assert resp.status_code == 200
    data = resp.json()
    assert "m1" in data and "m2" in data


async def test_system_metrics_latest_returns_current_values(client, monkeypatch):
    _mock_auth(monkeypatch, role="operator")
    now = datetime.now(timezone.utc)
    conn = AsyncMock()
    conn.fetch.return_value = [
        {"metric_name": "queue_depth", "service": "ingest", "value": 4, "time": now},
        {"metric_name": "alerts_created", "service": "evaluator", "value": 6, "time": now},
    ]
    monkeypatch.setattr(system_routes, "get_pool", AsyncMock(return_value=_Pool(conn)))
    resp = await client.get("/operator/system/metrics/latest", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["ingest"]["queue_depth"] == 4


async def test_capacity_returns_db_size_and_connections(client, monkeypatch):
    _mock_auth(monkeypatch, role="operator")
    monkeypatch.setattr(system_routes, "get_postgres_capacity", AsyncMock(return_value={"db_size_bytes": 1234, "active_connections": 3}))
    monkeypatch.setattr(system_routes, "get_disk_capacity", lambda: {"used_bytes": 10, "total_bytes": 100})
    resp = await client.get("/operator/system/capacity", headers=_auth_header())
    assert resp.status_code == 200
    data = resp.json()
    assert data["postgres"]["db_size_bytes"] == 1234
    assert data["disk"]["total_bytes"] == 100


async def test_aggregates_returns_platform_counts(client, monkeypatch):
    _mock_auth(monkeypatch, role="operator")
    now = datetime.now(timezone.utc)
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(side_effect=[
        {
            "tenants_active": 1,
            "tenants_suspended": 0,
            "tenants_deleted": 0,
            "tenants_total": 1,
            "devices_registered": 2,
            "devices_active": 2,
            "devices_revoked": 0,
            "devices_online": 1,
            "devices_stale": 1,
            "devices_offline": 0,
            "alerts_open": 3,
            "alerts_closed": 1,
            "alerts_acknowledged": 0,
            "alerts_24h": 4,
            "alerts_1h": 2,
            "integrations_total": 3,
            "integrations_active": 2,
            "integrations_webhook": 1,
            "integrations_email": 1,
            "rules_total": 5,
            "rules_active": 3,
            "deliveries_pending": 1,
            "deliveries_succeeded": 10,
            "deliveries_failed": 2,
            "deliveries_24h": 12,
            "sites_total": 1,
        },
        {
            "last_alert": now,
            "last_device_activity": now,
            "last_delivery": now,
        },
    ])
    monkeypatch.setattr(system_routes, "get_pool", AsyncMock(return_value=_Pool(conn)))
    monkeypatch.setattr(system_routes, "operator_connection", _operator_connection(conn))
    resp = await client.get("/operator/system/aggregates", headers=_auth_header())
    assert resp.status_code == 200
    data = resp.json()
    assert data["tenants"]["total"] == 1
    assert data["alerts"]["open"] == 3
    assert data["integrations"]["total"] == 3


async def test_aggregates_requires_operator_role(client, monkeypatch):
    _mock_auth(monkeypatch, role="customer")
    resp = await client.get("/operator/system/aggregates", headers=_auth_header())
    assert resp.status_code == 403


async def test_errors_returns_recent_failures(client, monkeypatch):
    _mock_auth(monkeypatch, role="operator")
    now = datetime.now(timezone.utc)
    conn = AsyncMock()
    conn.fetchval = AsyncMock(side_effect=["quarantine_events", "rate_limit_events", "operator_audit_log", 2, 1, 1])
    conn.fetch = AsyncMock(side_effect=[
        [  # delivery failures
            {"source": "delivery", "error_type": "delivery_failed", "timestamp": now, "tenant_id": "tenant-a", "details": {"last_error": "x"}}
        ],
        [  # quarantine events
            {"source": "ingest", "error_type": "quarantined", "timestamp": now, "tenant_id": "tenant-a", "details": {"reason": "bad"}}
        ],
        [  # auth failures
            {"source": "auth", "error_type": "auth_failure", "timestamp": now, "tenant_id": "tenant-a", "details": {"action": "denied"}}
        ],
        [  # rate limit events
            {"source": "ingest", "error_type": "rate_limited", "timestamp": now, "tenant_id": "tenant-a", "details": {"count": 10}}
        ],
    ])
    monkeypatch.setattr(system_routes, "get_pool", AsyncMock(return_value=_Pool(conn)))
    monkeypatch.setattr(system_routes, "operator_connection", _operator_connection(conn))
    resp = await client.get("/operator/system/errors?hours=1&limit=50", headers=_auth_header())
    assert resp.status_code == 200
    data = resp.json()
    assert data["counts"]["delivery_failures"] == 2
    assert len(data["errors"]) >= 1


async def test_errors_empty_when_no_failures(client, monkeypatch):
    _mock_auth(monkeypatch, role="operator")
    conn = AsyncMock()
    conn.fetchval = AsyncMock(side_effect=[None, None, None, 0, 0])
    conn.fetch = AsyncMock(side_effect=[[], [], []])
    monkeypatch.setattr(system_routes, "get_pool", AsyncMock(return_value=_Pool(conn)))
    monkeypatch.setattr(system_routes, "operator_connection", _operator_connection(conn))
    resp = await client.get("/operator/system/errors", headers=_auth_header())
    assert resp.status_code == 200
    data = resp.json()
    assert data["counts"]["delivery_failures"] == 0
    assert data["errors"] == []
