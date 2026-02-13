from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock

import pytest

from services.ui_iot.services import subscription

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class FakeConn:
    def __init__(self):
        self.fetchval_result = None
        self.fetchrow_side_effect = []
        self.fetch_result = []
        self.execute_calls = []

    async def fetchval(self, *_args, **_kwargs):
        return self.fetchval_result

    async def fetchrow(self, *_args, **_kwargs):
        if self.fetchrow_side_effect:
            return self.fetchrow_side_effect.pop(0)
        return None

    async def fetch(self, *_args, **_kwargs):
        return self.fetch_result

    async def execute(self, query, *args):
        self.execute_calls.append((query, args))
        return "OK"


async def test_create_main_subscription():
    conn = FakeConn()
    conn.fetchval_result = "sub-main-1"
    now = datetime.now(timezone.utc)
    conn.fetchrow_side_effect = [
        {
            "subscription_id": "sub-main-1",
            "tenant_id": "tenant-a",
            "subscription_type": "MAIN",
            "device_limit": 100,
            "term_start": now,
            "term_end": now + timedelta(days=365),
            "status": "ACTIVE",
        }
    ]
    row = await subscription.create_subscription(
        conn,
        tenant_id="tenant-a",
        subscription_type="MAIN",
        device_limit=100,
        term_start=now,
        term_end=now + timedelta(days=365),
    )
    assert row["subscription_id"] == "sub-main-1"


async def test_create_addon_requires_parent():
    conn = FakeConn()
    conn.fetchval_result = "sub-addon-1"
    with pytest.raises(ValueError, match="requires parent_subscription_id"):
        await subscription.create_subscription(
            conn,
            tenant_id="tenant-a",
            subscription_type="ADDON",
            device_limit=10,
            term_start=datetime.now(timezone.utc),
            term_end=datetime.now(timezone.utc) + timedelta(days=30),
        )


async def test_assign_device_validates_subscription_exists():
    conn = FakeConn()
    conn.fetchrow_side_effect = [
        {"subscription_id": "old-sub"},
        None,
    ]
    with pytest.raises(ValueError, match="not found for tenant"):
        await subscription.assign_device_to_subscription(conn, "tenant-a", "device-1", "missing-sub")


async def test_assign_device_blocks_full_subscription():
    conn = FakeConn()
    conn.fetchrow_side_effect = [
        {"subscription_id": "old-sub"},
        {"subscription_id": "new-sub", "tenant_id": "tenant-a", "status": "ACTIVE", "active_device_count": 5, "device_limit": 5},
    ]
    with pytest.raises(ValueError, match="at device limit"):
        await subscription.assign_device_to_subscription(conn, "tenant-a", "device-1", "new-sub")


async def test_assign_device_updates_counts_and_registry(monkeypatch):
    conn = FakeConn()
    conn.fetchrow_side_effect = [
        {"subscription_id": "old-sub"},
        {"subscription_id": "new-sub", "tenant_id": "tenant-a", "status": "ACTIVE", "active_device_count": 1, "device_limit": 10},
    ]
    monkeypatch.setattr(subscription, "log_subscription_event", AsyncMock())
    result = await subscription.assign_device_to_subscription(conn, "tenant-a", "device-1", "new-sub")
    assert result["subscription_id"] == "new-sub"
    assert len(conn.execute_calls) == 3


async def test_check_subscription_limit_returns_false_for_suspended():
    conn = FakeConn()
    conn.fetchrow_side_effect = [{"active_device_count": 1, "device_limit": 5, "status": "SUSPENDED"}]
    can_add, current, limit = await subscription.check_subscription_limit(conn, "sub-1")
    assert can_add is False
    assert current == 1 and limit == 5


async def test_check_device_access_returns_subscription_expired():
    conn = FakeConn()
    conn.fetchrow_side_effect = [{"status": "EXPIRED", "subscription_id": "sub-1"}]
    ok, reason = await subscription.check_device_access(conn, "tenant-a", "device-1")
    assert ok is False
    assert reason == "SUBSCRIPTION_EXPIRED"


async def test_get_tenant_subscriptions_filters_expired():
    conn = FakeConn()
    conn.fetch_result = [{"subscription_id": "sub-1", "status": "ACTIVE"}]
    rows = await subscription.get_tenant_subscriptions(conn, "tenant-a", include_expired=False)
    assert rows[0]["status"] == "ACTIVE"


async def test_create_device_on_subscription_rejects_limit(monkeypatch):
    conn = FakeConn()
    monkeypatch.setattr(subscription, "check_subscription_limit", AsyncMock(return_value=(False, 5, 5)))
    with pytest.raises(ValueError, match="at limit"):
        await subscription.create_device_on_subscription(conn, "tenant-a", "device-1", "site-1", "sub-1")


async def test_create_device_on_subscription_happy_path(monkeypatch):
    conn = FakeConn()
    monkeypatch.setattr(subscription, "check_subscription_limit", AsyncMock(return_value=(True, 1, 5)))
    conn.fetchrow_side_effect = [{"tenant_id": "tenant-a", "status": "ACTIVE"}]
    monkeypatch.setattr(subscription, "log_subscription_event", AsyncMock())
    result = await subscription.create_device_on_subscription(
        conn, "tenant-a", "device-1", "site-1", "sub-1"
    )
    assert result["device_id"] == "device-1"
    assert len(conn.execute_calls) == 2
