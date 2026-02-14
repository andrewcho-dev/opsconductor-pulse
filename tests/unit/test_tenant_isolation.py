from unittest.mock import AsyncMock, MagicMock

import pytest

from services.ingest_iot.ingest import topic_extract
from services.shared.ingest_core import DeviceAuthCache
from services.ui_iot.db.pool import operator_connection, tenant_connection


pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class _FakeAcquire:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeTx:
    async def __aenter__(self):
        return None

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _mock_pool_conn():
    conn = MagicMock()
    conn.execute = AsyncMock()
    conn.transaction.return_value = _FakeTx()
    pool = MagicMock()
    pool.acquire.return_value = _FakeAcquire(conn)
    return pool, conn


async def test_tenant_connection_sets_role_and_tenant_context():
    pool, conn = _mock_pool_conn()
    async with tenant_connection(pool, "tenant-xyz"):
        pass

    calls = [str(c) for c in conn.execute.call_args_list]
    assert any("SET LOCAL ROLE pulse_app" in c for c in calls)
    assert any("app.tenant_id" in c and "tenant-xyz" in c for c in calls)


async def test_tenant_connection_requires_tenant_id():
    pool, _conn = _mock_pool_conn()
    with pytest.raises(ValueError, match="tenant_id"):
        async with tenant_connection(pool, ""):
            pass


async def test_operator_connection_uses_pulse_operator_without_tenant_context():
    pool, conn = _mock_pool_conn()
    async with operator_connection(pool):
        pass

    calls = [str(c) for c in conn.execute.call_args_list]
    assert any("SET LOCAL ROLE pulse_operator" in c for c in calls)
    assert not any("app.tenant_id" in c for c in calls)


async def test_topic_extract_reads_tenant_from_topic():
    tenant_id, device_id, msg_type = topic_extract("tenant/acme/device/dev-001/telemetry")
    assert tenant_id == "acme"
    assert device_id == "dev-001"
    assert msg_type == "telemetry"


async def test_device_auth_cache_is_tenant_scoped():
    cache = DeviceAuthCache(ttl_seconds=60, max_size=1000)
    cache.put("tenant-a", "dev-001", "hash-a", "site-a", "ACTIVE")
    assert cache.get("tenant-a", "dev-001") is not None
    assert cache.get("tenant-b", "dev-001") is None
