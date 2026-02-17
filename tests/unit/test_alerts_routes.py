from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock

import httpx
import pytest

import app as app_module
import dependencies as dependencies_module
from middleware import auth as auth_module
from middleware import permissions as permissions_module
from middleware import tenant as tenant_module
from routes import alerts as alerts_routes

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.fixture(scope="session", autouse=True)
async def setup_delivery_tables():
    # Override the integration DB bootstrap fixture from tests/conftest.py
    # so this file remains pure unit tests.
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
        self.fetchval_result = 0
        self.fetchval_results: list[object] | None = None
        self.executed = []

    async def fetchrow(self, query, *args):
        if self.fetchrow_results is not None:
            if not self.fetchrow_results:
                return None
            return self.fetchrow_results.pop(0)
        return self.fetchrow_result

    async def fetch(self, query, *args):
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

    def transaction(self):
        return _Tx()


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


def _mock_customer_deps(monkeypatch, conn: FakeConn, tenant_id: str = "tenant-a", perms: set[str] | None = None):
    user_payload = {
        "sub": "user-1",
        "tenant_id": tenant_id,
        "organization": {tenant_id: {}},
        "realm_access": {"roles": ["customer", "tenant-admin"]},
        "email": "u@example.com",
    }
    tenant_module.set_tenant_context(tenant_id, user_payload)
    monkeypatch.setattr(auth_module, "validate_token", AsyncMock(return_value=user_payload))

    async def _override_get_db_pool(_request=None):
        return FakePool(conn)

    app_module.app.dependency_overrides[dependencies_module.get_db_pool] = _override_get_db_pool
    monkeypatch.setattr(alerts_routes, "tenant_connection", _tenant_connection(conn))

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


async def test_list_alerts_default(client, monkeypatch):
    conn = FakeConn()
    conn.fetch_result = [
        {
            "alert_id": 1,
            "tenant_id": "tenant-a",
            "device_id": "d1",
            "severity": 2,
            "status": "OPEN",
            "alert_type": "THRESHOLD",
            "summary": "High temp",
            "created_at": datetime.now(timezone.utc),
        }
    ]
    conn.fetchval_result = 1
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/alerts", headers=_auth_header())
    assert resp.status_code == 200
    assert len(resp.json()["alerts"]) == 1
    assert resp.json()["total"] == 1


async def test_list_alerts_filter_by_status_all(client, monkeypatch):
    conn = FakeConn()
    conn.fetch_result = []
    conn.fetchval_result = 0
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/alerts?status=ALL", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["status_filter"] == "ALL"


async def test_list_alerts_invalid_status_returns_400(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/alerts?status=nope", headers=_auth_header())
    assert resp.status_code == 400


async def test_get_alert_success(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"alert_id": 1, "tenant_id": "tenant-a", "status": "OPEN"}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/alerts/1", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["alert"]["tenant_id"] == "tenant-a"


async def test_get_alert_not_found(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = None
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/alerts/999", headers=_auth_header())
    assert resp.status_code == 404


async def test_acknowledge_alert_success(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"id": 1, "status": "ACKNOWLEDGED"}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.patch("/api/v1/customer/alerts/1/acknowledge", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["status"] == "ACKNOWLEDGED"


async def test_acknowledge_alert_invalid_id(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.patch("/api/v1/customer/alerts/not-a-number/acknowledge", headers=_auth_header())
    assert resp.status_code == 400


async def test_acknowledge_alert_not_found_or_not_open(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = None
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.patch("/api/v1/customer/alerts/1/acknowledge", headers=_auth_header())
    assert resp.status_code == 404


async def test_close_alert_success(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"id": 1, "status": "CLOSED"}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.patch("/api/v1/customer/alerts/1/close", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["status"] == "CLOSED"


async def test_close_alert_invalid_id_returns_400(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.patch("/api/v1/customer/alerts/bad/close", headers=_auth_header())
    assert resp.status_code == 400


async def test_close_alert_not_found_returns_404(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = None
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.patch("/api/v1/customer/alerts/1/close", headers=_auth_header())
    assert resp.status_code == 404


async def test_silence_alert_requires_permission(client, monkeypatch):
    conn = FakeConn()
    # No permissions at all
    _mock_customer_deps(monkeypatch, conn, perms=set())
    resp = await client.patch(
        "/api/v1/customer/alerts/1/silence",
        headers=_auth_header(),
        json={"minutes": 60},
    )
    assert resp.status_code == 403


async def test_silence_alert_success(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"id": 1, "silenced_until": datetime.now(timezone.utc) + timedelta(minutes=60)}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.patch(
        "/api/v1/customer/alerts/1/silence",
        headers=_auth_header(),
        json={"minutes": 60},
    )
    assert resp.status_code == 200
    assert "silenced_until" in resp.json()


async def test_get_digest_settings_default_when_missing(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = None
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/alert-digest-settings", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["frequency"] == "daily"


async def test_get_digest_settings_returns_row(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"frequency": "weekly", "email": "ops@example.com", "last_sent_at": None}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/alert-digest-settings", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["frequency"] == "weekly"


async def test_update_digest_settings(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.put(
        "/api/v1/customer/alert-digest-settings",
        headers=_auth_header(),
        json={"frequency": "weekly", "email": "ops@example.com"},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


async def test_get_alert_trend(client, monkeypatch):
    conn = FakeConn()
    now_hour = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    conn.fetch_result = [{"hour": now_hour, "opened": 2, "closed": 1}]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/alerts/trend?hours=1", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["trend"][0]["opened"] == 2


async def test_list_alert_rule_templates_and_filter(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/alert-rule-templates", headers=_auth_header())
    assert resp.status_code == 200
    templates = resp.json()["templates"]
    assert isinstance(templates, list)
    if templates:
        device_type = templates[0].get("device_type")
        resp2 = await client.get(
            f"/api/v1/customer/alert-rule-templates?device_type={device_type}", headers=_auth_header()
        )
        assert resp2.status_code == 200


async def test_apply_alert_rule_templates_requires_valid_template_ids(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post(
        "/api/v1/customer/alert-rule-templates/apply",
        headers=_auth_header(),
        json={"template_ids": ["does-not-exist"], "site_ids": ["s1"]},
    )
    assert resp.status_code == 400


async def test_apply_alert_rule_templates_create_and_skip(client, monkeypatch):
    tmpl = alerts_routes.ALERT_RULE_TEMPLATES[0]
    conn = FakeConn()
    # First template: not existing -> create; Second: existing -> skip.
    conn.fetchval_results = [None, 123]
    conn.fetchrow_results = [{"id": "new-rule", "name": tmpl["name"]}]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post(
        "/api/v1/customer/alert-rule-templates/apply",
        headers=_auth_header(),
        json={"template_ids": [tmpl["template_id"], tmpl["template_id"]], "site_ids": ["s1"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["created"]) == 1
    assert len(data["skipped"]) == 1


async def test_list_alert_rules(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(alerts_routes, "fetch_alert_rules", AsyncMock(return_value=[{"rule_id": "r1", "name": "Rule 1"}]))
    resp = await client.get("/api/v1/customer/alert-rules", headers=_auth_header())
    assert resp.status_code == 200
    assert len(resp.json()["rules"]) == 1


async def test_get_alert_rule_success(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    rule_id = "00000000-0000-0000-0000-000000000000"
    monkeypatch.setattr(
        alerts_routes, "fetch_alert_rule", AsyncMock(return_value={"rule_id": rule_id, "name": "Rule 1"})
    )
    resp = await client.get(f"/api/v1/customer/alert-rules/{rule_id}", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["rule_id"] == rule_id


async def test_get_alert_rule_not_found(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(alerts_routes, "fetch_alert_rule", AsyncMock(return_value=None))
    rule_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/v1/customer/alert-rules/{rule_id}", headers=_auth_header())
    assert resp.status_code == 404


async def test_create_alert_rule_success(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(
        alerts_routes,
        "check_alert_rule_limit",
        AsyncMock(return_value={"allowed": True, "current": 0, "limit": 999}),
    )
    monkeypatch.setattr(
        alerts_routes,
        "create_alert_rule",
        AsyncMock(return_value={"rule_id": "new-rule-id", "name": "High Temp", "conditions": []}),
    )
    resp = await client.post(
        "/api/v1/customer/alert-rules",
        headers=_auth_header(),
        json={
            "name": "High Temperature",
            "metric_name": "temp_c",
            "operator": "GT",
            "threshold": 35,
            "severity": 3,
        },
    )
    assert resp.status_code == 201


async def test_create_alert_rule_missing_name_returns_422(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post(
        "/api/v1/customer/alert-rules",
        headers=_auth_header(),
        json={"metric_name": "temp_c", "operator": "GT", "threshold": 35},
    )
    assert resp.status_code == 422


async def test_create_alert_rule_invalid_operator_returns_400(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post(
        "/api/v1/customer/alert-rules",
        headers=_auth_header(),
        json={"name": "Bad", "metric_name": "temp_c", "operator": "BAD", "threshold": 1},
    )
    assert resp.status_code == 400


async def test_create_alert_rule_anomaly_requires_anomaly_conditions(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post(
        "/api/v1/customer/alert-rules",
        headers=_auth_header(),
        json={"name": "Anom", "rule_type": "anomaly"},
    )
    assert resp.status_code == 422


async def test_create_alert_rule_anomaly_invalid_metric_name_returns_400(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post(
        "/api/v1/customer/alert-rules",
        headers=_auth_header(),
        json={
            "name": "Anom",
            "rule_type": "anomaly",
            "anomaly_conditions": {"metric_name": "temp-c", "window_minutes": 60, "z_threshold": 3.0, "min_samples": 10},
        },
    )
    assert resp.status_code == 400


async def test_create_alert_rule_window_requires_aggregation(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post(
        "/api/v1/customer/alert-rules",
        headers=_auth_header(),
        json={
            "name": "Win",
            "rule_type": "window",
            "metric_name": "temp_c",
            "operator": "GT",
            "threshold": 1,
            "window_seconds": 60,
        },
    )
    assert resp.status_code == 422


async def test_create_alert_rule_window_invalid_aggregation_returns_400(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post(
        "/api/v1/customer/alert-rules",
        headers=_auth_header(),
        json={
            "name": "Win",
            "rule_type": "window",
            "metric_name": "temp_c",
            "operator": "GT",
            "threshold": 1,
            "window_seconds": 60,
            "aggregation": "median",
        },
    )
    assert resp.status_code == 400


async def test_create_alert_rule_gap_requires_gap_conditions(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post(
        "/api/v1/customer/alert-rules",
        headers=_auth_header(),
        json={"name": "Gap", "rule_type": "telemetry_gap"},
    )
    assert resp.status_code == 422


async def test_create_alert_rule_gap_success(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(
        alerts_routes,
        "check_alert_rule_limit",
        AsyncMock(return_value={"allowed": True, "current": 0, "limit": 999}),
    )
    monkeypatch.setattr(
        alerts_routes,
        "create_alert_rule",
        AsyncMock(return_value={"rule_id": "gap-rule", "name": "Gap", "rule_type": "telemetry_gap", "conditions": {}}),
    )
    resp = await client.post(
        "/api/v1/customer/alert-rules",
        headers=_auth_header(),
        json={
            "name": "Gap",
            "rule_type": "telemetry_gap",
            "gap_conditions": {"metric_name": "temp_c", "gap_minutes": 10},
        },
    )
    assert resp.status_code == 201


async def test_create_alert_rule_anomaly_success(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(
        alerts_routes,
        "check_alert_rule_limit",
        AsyncMock(return_value={"allowed": True, "current": 0, "limit": 999}),
    )
    monkeypatch.setattr(
        alerts_routes,
        "create_alert_rule",
        AsyncMock(return_value={"rule_id": "anom-rule", "name": "Anom", "rule_type": "anomaly", "conditions": {}}),
    )
    resp = await client.post(
        "/api/v1/customer/alert-rules",
        headers=_auth_header(),
        json={
            "name": "Anom",
            "rule_type": "anomaly",
            "anomaly_conditions": {"metric_name": "temp_c", "window_minutes": 60, "z_threshold": 3.0, "min_samples": 10},
        },
    )
    assert resp.status_code == 201


async def test_create_alert_rule_window_success(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(
        alerts_routes,
        "check_alert_rule_limit",
        AsyncMock(return_value={"allowed": True, "current": 0, "limit": 999}),
    )
    monkeypatch.setattr(
        alerts_routes,
        "create_alert_rule",
        AsyncMock(return_value={"rule_id": "win-rule", "name": "Win", "rule_type": "window", "conditions": []}),
    )
    resp = await client.post(
        "/api/v1/customer/alert-rules",
        headers=_auth_header(),
        json={
            "name": "Win",
            "rule_type": "window",
            "metric_name": "temp_c",
            "operator": "GT",
            "threshold": 1,
            "window_seconds": 60,
            "aggregation": "avg",
        },
    )
    assert resp.status_code == 201


async def test_create_alert_rule_conditions_list_success(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(
        alerts_routes,
        "check_alert_rule_limit",
        AsyncMock(return_value={"allowed": True, "current": 0, "limit": 999}),
    )
    create_mock = AsyncMock(
        return_value={
            "rule_id": "multi-rule",
            "name": "Multi",
            "rule_type": "threshold",
            "conditions": [],
        }
    )
    monkeypatch.setattr(alerts_routes, "create_alert_rule", create_mock)
    resp = await client.post(
        "/api/v1/customer/alert-rules",
        headers=_auth_header(),
        json={
            "name": "Multi",
            "conditions": [{"metric_name": "temp_c", "operator": "GT", "threshold": 10}],
            "severity": 2,
        },
    )
    assert resp.status_code == 201


async def test_create_alert_rule_ruleconditions_or_sets_match_mode_any(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(
        alerts_routes,
        "check_alert_rule_limit",
        AsyncMock(return_value={"allowed": True, "current": 0, "limit": 999}),
    )
    create_mock = AsyncMock(
        return_value={
            "rule_id": "rc-rule",
            "name": "RC",
            "rule_type": "threshold",
            "conditions": [],
        }
    )
    monkeypatch.setattr(alerts_routes, "create_alert_rule", create_mock)
    resp = await client.post(
        "/api/v1/customer/alert-rules",
        headers=_auth_header(),
        json={
            "name": "RC",
            "conditions": {
                "combinator": "OR",
                "conditions": [{"metric_name": "temp_c", "operator": "GT", "threshold": 10}],
            },
            # match_mode default is "all" (so OR should flip it to "any")
        },
    )
    assert resp.status_code == 201
    assert create_mock.await_args.kwargs["match_mode"] == "any"


async def test_create_alert_rule_invalid_site_id_returns_400(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post(
        "/api/v1/customer/alert-rules",
        headers=_auth_header(),
        json={
            "name": "BadSite",
            "metric_name": "temp_c",
            "operator": "GT",
            "threshold": 1,
            "site_ids": [""],
        },
    )
    assert resp.status_code == 400


async def test_create_alert_rule_invalid_group_ids_returns_400(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post(
        "/api/v1/customer/alert-rules",
        headers=_auth_header(),
        json={
            "name": "BadGroup",
            "metric_name": "temp_c",
            "operator": "GT",
            "threshold": 1,
            "group_ids": [" ", ""],
        },
    )
    assert resp.status_code == 400


async def test_update_alert_rule_no_fields_returns_400(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    rule_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.patch(
        f"/api/v1/customer/alert-rules/{rule_id}",
        headers=_auth_header(),
        json={},
    )
    assert resp.status_code == 400


async def test_update_alert_rule_invalid_uuid_returns_400(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.patch(
        "/api/v1/customer/alert-rules/not-a-uuid",
        headers=_auth_header(),
        json={"name": "x"},
    )
    assert resp.status_code == 400


async def test_update_alert_rule_success(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    rule_id = "00000000-0000-0000-0000-000000000000"
    monkeypatch.setattr(
        alerts_routes,
        "update_alert_rule",
        AsyncMock(return_value={"rule_id": rule_id, "name": "Updated Rule", "conditions": []}),
    )
    resp = await client.patch(
        f"/api/v1/customer/alert-rules/{rule_id}",
        headers=_auth_header(),
        json={"name": "Updated Rule"},
    )
    assert resp.status_code == 200


async def test_update_alert_rule_conditions_ruleconditions_or_sets_match_mode_any(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    rule_id = "00000000-0000-0000-0000-000000000000"
    update_mock = AsyncMock(return_value={"rule_id": rule_id, "name": "Updated", "rule_type": "threshold", "conditions": []})
    monkeypatch.setattr(alerts_routes, "update_alert_rule", update_mock)
    resp = await client.patch(
        f"/api/v1/customer/alert-rules/{rule_id}",
        headers=_auth_header(),
        json={
            "conditions": {
                "combinator": "OR",
                "conditions": [{"metric_name": "temp_c", "operator": "GT", "threshold": 10}],
            }
        },
    )
    assert resp.status_code == 200
    assert update_mock.await_args.kwargs["match_mode"] == "any"


async def test_delete_alert_rule_success(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    rule_id = "00000000-0000-0000-0000-000000000000"
    monkeypatch.setattr(alerts_routes, "delete_alert_rule", AsyncMock(return_value=True))
    resp = await client.delete(f"/api/v1/customer/alert-rules/{rule_id}", headers=_auth_header())
    assert resp.status_code == 204


async def test_delete_alert_rule_invalid_uuid_returns_400(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.delete("/api/v1/customer/alert-rules/not-a-uuid", headers=_auth_header())
    assert resp.status_code == 400


async def test_delete_alert_rule_not_found(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    rule_id = "00000000-0000-0000-0000-000000000000"
    monkeypatch.setattr(alerts_routes, "delete_alert_rule", AsyncMock(return_value=False))
    resp = await client.delete(f"/api/v1/customer/alert-rules/{rule_id}", headers=_auth_header())
    assert resp.status_code == 404
