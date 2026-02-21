from datetime import datetime, timezone
from unittest.mock import AsyncMock

import httpx
import pytest

import app as app_module
from routes import system as system_routes
from tests.unit.test_system_routes import _Pool, _auth_header, _mock_auth

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.fixture
async def client():
    app_module.app.router.on_startup.clear()
    app_module.app.router.on_shutdown.clear()
    transport = httpx.ASGITransport(app=app_module.app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as c:
        yield c


async def test_system_metrics_latest_returns_snapshot(client, monkeypatch):
    _mock_auth(monkeypatch, role="operator")
    now = datetime.now(timezone.utc)
    conn = AsyncMock()
    conn.fetch.return_value = [
        {"metric_name": "queue_depth", "service": "ingest", "value": 4, "time": now},
        {"metric_name": "jobs_failed", "service": "delivery", "value": 2, "time": now},
    ]
    monkeypatch.setattr(system_routes, "get_pool", AsyncMock(return_value=_Pool(conn)))
    resp = await client.get("/operator/system/metrics/latest", headers=_auth_header())
    assert resp.status_code == 200
    body = resp.json()
    assert body["ingest"]["queue_depth"] == 4
    assert body["delivery"]["jobs_failed"] == 2


async def test_system_metrics_history_returns_points(client, monkeypatch):
    _mock_auth(monkeypatch, role="operator")
    conn = AsyncMock()
    now = datetime.now(timezone.utc)
    conn.fetch.return_value = [{"time": now, "value": 12.5}]
    monkeypatch.setattr(system_routes, "get_pool", AsyncMock(return_value=_Pool(conn)))
    resp = await client.get(
        "/operator/system/metrics/history?metric=messages_written&minutes=60",
        headers=_auth_header(),
    )
    assert resp.status_code == 200
    assert len(resp.json()["points"]) == 1


async def test_system_metrics_requires_operator(client, monkeypatch):
    _mock_auth(monkeypatch, role="customer")
    resp = await client.get("/operator/system/metrics/latest", headers=_auth_header())
    assert resp.status_code in {401, 403}
