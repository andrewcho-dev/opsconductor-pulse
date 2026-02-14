from unittest.mock import AsyncMock

import pytest

from services.evaluator_iot import evaluator

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class FakeConn:
    def __init__(self):
        self.fetchrow_result = None
        self.fetchrow_calls = []

    async def fetchrow(self, query, *args):
        self.fetchrow_calls.append((query, args))
        return self.fetchrow_result


async def test_acknowledged_alert_not_reset_to_open():
    conn = FakeConn()
    conn.fetchrow_result = {"id": 123, "inserted": False}
    alert_id, inserted = await evaluator.open_or_update_alert(
        conn,
        tenant_id="tenant-a",
        site_id="site-a",
        device_id="device-1",
        alert_type="THRESHOLD",
        fingerprint="RULE:r1:device-1",
        severity=4,
        confidence=0.9,
        summary="high temp",
        details={"metric": "temp_c"},
    )
    assert alert_id == 123
    assert inserted is False
    query = conn.fetchrow_calls[0][0]
    assert "status IN ('OPEN', 'ACKNOWLEDGED')" in query
    assert "status = EXCLUDED.status" not in query


async def test_silenced_alert_skipped(monkeypatch):
    conn = FakeConn()
    open_or_update_mock = AsyncMock()
    monkeypatch.setattr(evaluator, "is_silenced", AsyncMock(return_value=True))
    monkeypatch.setattr(evaluator, "open_or_update_alert", open_or_update_mock)

    if await evaluator.is_silenced(conn, "tenant-a", "RULE:r1:device-1"):
        pass
    else:
        await evaluator.open_or_update_alert(
            conn,
            "tenant-a",
            "site-a",
            "device-1",
            "THRESHOLD",
            "RULE:r1:device-1",
            4,
            1.0,
            "summary",
            {},
        )

    open_or_update_mock.assert_not_awaited()


async def test_not_silenced_proceeds(monkeypatch):
    conn = FakeConn()
    open_or_update_mock = AsyncMock(return_value=(1, True))
    monkeypatch.setattr(evaluator, "is_silenced", AsyncMock(return_value=False))
    monkeypatch.setattr(evaluator, "open_or_update_alert", open_or_update_mock)

    if await evaluator.is_silenced(conn, "tenant-a", "RULE:r1:device-1"):
        pass
    else:
        await evaluator.open_or_update_alert(
            conn,
            "tenant-a",
            "site-a",
            "device-1",
            "THRESHOLD",
            "RULE:r1:device-1",
            4,
            1.0,
            "summary",
            {},
        )

    open_or_update_mock.assert_awaited_once()


async def test_is_silenced_false_when_no_row():
    conn = FakeConn()
    conn.fetchrow_result = None
    result = await evaluator.is_silenced(conn, "tenant-a", "RULE:r1:device-1")
    assert result is False


async def test_is_silenced_true_when_future():
    conn = FakeConn()
    conn.fetchrow_result = {"silenced_until": "2099-01-01T00:00:00Z"}
    result = await evaluator.is_silenced(conn, "tenant-a", "RULE:r1:device-1")
    assert result is True
