import os
import sys
import types

import pytest

for mod in ["asyncpg"]:
    if mod not in sys.modules:
        sys.modules[mod] = types.SimpleNamespace(Connection=type("Connection", (), {}))

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "ui_iot"))
from db.queries import fetch_devices_v2, fetch_fleet_summary

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class FakeConn:
    def __init__(self):
        self.fetch_result = []
        self.fetchval_result = 0
        self.fetch_calls = []
        self.fetchval_calls = []

    async def fetch(self, query, *args):
        self.fetch_calls.append((query, args))
        return self.fetch_result

    async def fetchval(self, query, *args):
        self.fetchval_calls.append((query, args))
        return self.fetchval_result


async def test_fetch_devices_v2_returns_total():
    conn = FakeConn()
    conn.fetchval_result = 5
    conn.fetch_result = [{"device_id": "d1"}, {"device_id": "d2"}]

    result = await fetch_devices_v2(conn, "tenant-a", limit=10, offset=0)
    assert "total" in result
    assert "devices" in result
    assert result["total"] == 5


async def test_fetch_devices_v2_status_filter_adds_where_clause():
    conn = FakeConn()
    await fetch_devices_v2(conn, "tenant-a", status="ONLINE")
    assert any("COALESCE(ds.status, 'OFFLINE')" in call[0] for call in conn.fetch_calls)
    assert any(call[1][1] == "ONLINE" for call in conn.fetch_calls)


async def test_fetch_devices_v2_no_filter_returns_all():
    conn = FakeConn()
    conn.fetchval_result = 3
    conn.fetch_result = [{"device_id": "d1"}, {"device_id": "d2"}, {"device_id": "d3"}]

    result = await fetch_devices_v2(conn, "tenant-a")
    assert result["total"] == 3
    assert len(result["devices"]) == 3


async def test_fetch_devices_v2_tag_filter():
    conn = FakeConn()
    await fetch_devices_v2(conn, "tenant-a", tags=["rack-a", "rack-b"])
    assert any("COUNT(DISTINCT dt.tag)" in call[0] for call in conn.fetch_calls)
    assert any(call[1][1] == ["rack-a", "rack-b"] for call in conn.fetch_calls)


async def test_fetch_fleet_summary_returns_correct_shape():
    conn = FakeConn()
    conn.fetch_result = [{"status": "ONLINE", "count": 10}, {"status": "STALE", "count": 3}]
    summary = await fetch_fleet_summary(conn, "tenant-a")
    assert summary["ONLINE"] == 10
    assert summary["STALE"] == 3
    assert summary["OFFLINE"] == 0
    assert summary["total"] == 13
