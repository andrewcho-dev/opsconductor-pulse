import pytest

from db import queries

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.fixture(scope="session", autouse=True)
async def setup_delivery_tables():
    yield


class FakeConn:
    def __init__(self):
        self.last_query = None
        self.last_args = None
        self.fetchval_result = 0
        self.execute_calls = []

    async def fetch(self, query, *args):
        self.last_query = query
        self.last_args = args
        return []

    async def fetchrow(self, query, *args):
        self.last_query = query
        self.last_args = args
        return {"tenant_id": "tenant-a"}

    async def fetchval(self, query, *args):
        self.last_query = query
        self.last_args = args
        return self.fetchval_result

    async def execute(self, query, *args):
        self.last_query = query
        self.last_args = args
        self.execute_calls.append((query, args))
        return "UPDATE 1"


async def test_list_devices_query_includes_tenant():
    conn = FakeConn()
    await queries.fetch_devices(conn, "tenant-a", limit=10, offset=0)
    assert "WHERE tenant_id = $1" in conn.last_query


async def test_list_devices_query_with_status_filter():
    conn = FakeConn()
    await queries.fetch_alerts(conn, "tenant-a", status="OPEN", limit=5)
    assert "status = $2" in conn.last_query


async def test_list_devices_query_with_limit():
    conn = FakeConn()
    await queries.fetch_devices(conn, "tenant-a", limit=25, offset=5)
    assert "LIMIT $2 OFFSET $3" in conn.last_query


async def test_get_device_query_includes_both_keys():
    conn = FakeConn()
    await queries.fetch_device(conn, "tenant-a", "device-1")
    assert "tenant_id = $1 AND device_id = $2" in conn.last_query


async def test_list_alerts_query_ordering():
    conn = FakeConn()
    await queries.fetch_alerts(conn, "tenant-a", status="OPEN", limit=5)
    assert "ORDER BY created_at DESC" in conn.last_query


async def test_list_integrations_query_tenant_scoped():
    conn = FakeConn()
    await queries.fetch_integrations(conn, "tenant-a", limit=10)
    assert "WHERE tenant_id = $1" in conn.last_query


async def test_fetch_device_count_query():
    conn = FakeConn()
    await queries.fetch_device_count(conn, "tenant-a")
    assert "COUNT(*)" in conn.last_query


async def test_fetch_delivery_attempts_query_order():
    conn = FakeConn()
    await queries.fetch_delivery_attempts(conn, "tenant-a", limit=5)
    assert "ORDER BY finished_at DESC" in conn.last_query


async def test_fetch_device_events_query():
    conn = FakeConn()
    await queries.fetch_device_events(conn, "tenant-a", "device-1", limit=10)
    assert "FROM raw_events" in conn.last_query


async def test_fetch_device_telemetry_query():
    conn = FakeConn()
    await queries.fetch_device_telemetry(conn, "tenant-a", "device-1", limit=10)
    assert "msg_type = 'telemetry'" in conn.last_query


async def test_fetch_integration_query_scoped():
    conn = FakeConn()
    await queries.fetch_integration(conn, "tenant-a", "int-1")
    assert "WHERE tenant_id = $1 AND integration_id = $2" in conn.last_query


async def test_update_integration_no_fields():
    conn = FakeConn()
    result = await queries.update_integration(conn, "tenant-a", "int-1")
    assert result is None


async def test_update_integration_webhook_url():
    conn = FakeConn()
    await queries.update_integration(conn, "tenant-a", "int-1", webhook_url="https://example.com")
    assert "config_json" in conn.last_query


async def test_check_and_increment_rate_limit_blocks():
    conn = FakeConn()
    conn.fetchval_result = 5
    allowed, count = await queries.check_and_increment_rate_limit(conn, "tenant-a", "test", limit=3, window_seconds=60)
    assert allowed is False
    assert count == 5


async def test_check_and_increment_rate_limit_allows():
    conn = FakeConn()
    conn.fetchval_result = 0
    allowed, count = await queries.check_and_increment_rate_limit(conn, "tenant-a", "test", limit=3, window_seconds=60)
    assert allowed is True
    assert count == 1


async def test_fetch_all_devices_query():
    conn = FakeConn()
    await queries.fetch_all_devices(conn, limit=10, offset=0)
    assert "ORDER BY tenant_id" in conn.last_query


async def test_fetch_all_alerts_query():
    conn = FakeConn()
    await queries.fetch_all_alerts(conn, status="OPEN", limit=10)
    assert "ORDER BY created_at DESC" in conn.last_query


async def test_fetch_all_integrations_query():
    conn = FakeConn()
    await queries.fetch_all_integrations(conn, limit=10)
    assert "FROM integrations" in conn.last_query


async def test_fetch_all_delivery_attempts_query():
    conn = FakeConn()
    await queries.fetch_all_delivery_attempts(conn, limit=10)
    assert "ORDER BY finished_at DESC" in conn.last_query


async def test_fetch_quarantine_events_query():
    conn = FakeConn()
    await queries.fetch_quarantine_events(conn, minutes=60, limit=10)
    assert "FROM quarantine_events" in conn.last_query
