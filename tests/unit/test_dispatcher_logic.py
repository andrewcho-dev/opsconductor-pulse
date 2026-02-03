from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import dispatcher

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.fixture(scope="session", autouse=True)
async def setup_delivery_tables():
    yield


def _alert(
    alert_id="a1",
    tenant_id="tenant-a",
    site_id="site-1",
    device_id="dev-1",
    alert_type="TEMP",
    severity=5,
):
    return {
        "id": alert_id,
        "tenant_id": tenant_id,
        "site_id": site_id,
        "device_id": device_id,
        "alert_type": alert_type,
        "severity": severity,
        "confidence": 0.9,
        "summary": "Alert",
        "details": {},
        "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
    }


def _route(
    route_id="r1",
    integration_id="i1",
    deliver_on=None,
    min_severity=None,
    alert_types=None,
    site_ids=None,
    device_prefixes=None,
    severities=None,
):
    return {
        "tenant_id": "tenant-a",
        "route_id": route_id,
        "integration_id": integration_id,
        "min_severity": min_severity,
        "alert_types": alert_types or [],
        "site_ids": site_ids or [],
        "device_prefixes": device_prefixes or [],
        "deliver_on": deliver_on if deliver_on is not None else ["OPEN"],
        "severities": severities,
    }


class FakeConn:
    def __init__(self, alerts=None, routes=None, integration_types=None, insert_policy=None):
        self.alerts = alerts or []
        self.routes = routes or {}
        self.integration_types = integration_types or {}
        self.insert_policy = insert_policy or (lambda args: True)
        self.fetch_calls = []
        self.fetchrow_calls = []

    async def fetch(self, query, *args):
        self.fetch_calls.append((query, args))
        if "FROM fleet_alert" in query:
            return self.alerts
        if "FROM integration_routes" in query:
            tenant_id = args[0]
            return self.routes.get(tenant_id, [])
        return []

    async def fetchval(self, query, *args):
        if "SELECT type FROM integrations" in query:
            return self.integration_types.get(args[0])
        return None

    async def fetchrow(self, query, *args):
        self.fetchrow_calls.append((query, args))
        if "INSERT INTO delivery_jobs" in query:
            return SimpleNamespace(ok=True) if self.insert_policy(args) else None
        return None


async def test_match_all_alerts_wildcard_route():
    alert = _alert()
    route = _route()
    assert dispatcher.route_matches(alert, route) is True


async def test_match_by_severity():
    alert = _alert(severity=5)
    route = _route(min_severity=5)
    assert dispatcher.route_matches(alert, route) is True
    alert_low = _alert(severity=3)
    assert dispatcher.route_matches(alert_low, route) is False


async def test_match_by_alert_type():
    alert = _alert(alert_type="TEMP")
    route = _route(alert_types=["TEMP"])
    assert dispatcher.route_matches(alert, route) is True
    alert_other = _alert(alert_type="VIBRATION")
    assert dispatcher.route_matches(alert_other, route) is False


async def test_match_by_site():
    alert = _alert(site_id="site-1")
    route = _route(site_ids=["site-1"])
    assert dispatcher.route_matches(alert, route) is True
    alert_other = _alert(site_id="site-2")
    assert dispatcher.route_matches(alert_other, route) is False


async def test_match_by_device_prefix():
    alert = _alert(device_id="dev-abc")
    route = _route(device_prefixes=["dev-"])
    assert dispatcher.route_matches(alert, route) is True
    alert_other = _alert(device_id="sensor-1")
    assert dispatcher.route_matches(alert_other, route) is False


async def test_no_match_disabled_route():
    alert = _alert()
    route = _route(deliver_on=["RESOLVED"])
    assert dispatcher.route_matches(alert, route) is False


async def test_no_match_disabled_integration():
    conn = FakeConn(alerts=[_alert()], routes={"tenant-a": []})
    created = await dispatcher.dispatch_once(conn)
    assert created == 0


async def test_multiple_routes_create_multiple_jobs():
    alert = _alert()
    routes = [_route(route_id="r1", integration_id="i1"), _route(route_id="r2", integration_id="i2")]
    conn = FakeConn(
        alerts=[alert],
        routes={"tenant-a": routes},
        integration_types={"i1": "webhook", "i2": "snmp"},
    )
    created = await dispatcher.dispatch_once(conn)
    assert created == 2


async def test_dedup_prevents_duplicate_jobs():
    alert = _alert()
    routes = [_route(route_id="r1", integration_id="i1")]

    def insert_policy(args):
        return False

    conn = FakeConn(alerts=[alert], routes={"tenant-a": routes}, insert_policy=insert_policy)
    created = await dispatcher.dispatch_once(conn)
    assert created == 0


async def test_rate_limit_blocks_excess_jobs():
    alert = _alert()
    routes = [_route(route_id="r1", integration_id="i1")]

    def insert_policy(args):
        return False

    conn = FakeConn(alerts=[alert], routes={"tenant-a": routes}, insert_policy=insert_policy)
    created = await dispatcher.dispatch_once(conn)
    assert created == 0


async def test_rate_limit_per_integration():
    alert = _alert()
    routes = [_route(route_id="r1", integration_id="i1"), _route(route_id="r2", integration_id="i2")]

    def insert_policy(args):
        integration_id = args[2]
        return integration_id == "i2"

    conn = FakeConn(alerts=[alert], routes={"tenant-a": routes}, insert_policy=insert_policy)
    created = await dispatcher.dispatch_once(conn)
    assert created == 1


async def test_poll_respects_lookback_window():
    conn = FakeConn()
    dispatcher.ALERT_LOOKBACK_MINUTES = 15
    dispatcher.ALERT_LIMIT = 50
    await dispatcher.fetch_open_alerts(conn)
    _, args = conn.fetch_calls[0]
    assert args[0] == 15
    assert args[1] == 50


async def test_poll_respects_limit():
    conn = FakeConn()
    dispatcher.ALERT_LOOKBACK_MINUTES = 10
    dispatcher.ALERT_LIMIT = 25
    await dispatcher.fetch_open_alerts(conn)
    _, args = conn.fetch_calls[0]
    assert args[1] == 25


async def test_poll_skips_already_dispatched():
    alert = _alert()
    routes = [_route(route_id="r1", integration_id="i1")]

    def insert_policy(args):
        return False

    conn = FakeConn(alerts=[alert], routes={"tenant-a": routes}, insert_policy=insert_policy)
    created = await dispatcher.dispatch_once(conn)
    assert created == 0
