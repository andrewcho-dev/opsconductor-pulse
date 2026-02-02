import os

import asyncpg
import pytest

from db.pool import tenant_connection, operator_connection


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://iot:iot_dev@localhost:5432/iotcloud")


@pytest.fixture
async def db_pool():
    pool = await asyncpg.create_pool(DATABASE_URL)
    yield pool
    await pool.close()


@pytest.fixture
async def test_data(db_pool):
    """Create test data in two tenants."""
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO device_state (tenant_id, device_id, site_id, status)
            VALUES
                ('test-tenant-a', 'device-a1', 'site-a', 'ONLINE'),
                ('test-tenant-a', 'device-a2', 'site-a', 'ONLINE'),
                ('test-tenant-b', 'device-b1', 'site-b', 'ONLINE')
            ON CONFLICT DO NOTHING
            """
        )
    yield
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            DELETE FROM device_state WHERE tenant_id IN ('test-tenant-a', 'test-tenant-b')
            """
        )


@pytest.mark.asyncio
async def test_no_tenant_context_returns_zero_rows(db_pool, test_data):
    """Without app.tenant_id set, RLS should return zero rows."""
    async with db_pool.acquire() as conn:
        await conn.execute("SET LOCAL ROLE pulse_app")
        rows = await conn.fetch(
            "SELECT * FROM device_state WHERE tenant_id IN ('test-tenant-a', 'test-tenant-b')"
        )
        assert len(rows) == 0, "Expected zero rows when tenant context not set"


@pytest.mark.asyncio
async def test_wrong_tenant_returns_zero_rows(db_pool, test_data):
    """With wrong app.tenant_id, RLS should return zero rows."""
    async with db_pool.acquire() as conn:
        await conn.execute("SET LOCAL ROLE pulse_app")
        await conn.execute("SET LOCAL app.tenant_id = 'wrong-tenant'")
        rows = await conn.fetch(
            "SELECT * FROM device_state WHERE tenant_id = 'test-tenant-a'"
        )
        assert len(rows) == 0, "Expected zero rows for wrong tenant"


@pytest.mark.asyncio
async def test_correct_tenant_returns_matching_rows(db_pool, test_data):
    """With correct app.tenant_id, RLS returns only that tenant's rows."""
    async with db_pool.acquire() as conn:
        await conn.execute("SET LOCAL ROLE pulse_app")
        await conn.execute("SET LOCAL app.tenant_id = 'test-tenant-a'")
        rows = await conn.fetch("SELECT * FROM device_state")
        assert len(rows) == 2, "Expected 2 rows for test-tenant-a"
        for row in rows:
            assert row["tenant_id"] == "test-tenant-a"


@pytest.mark.asyncio
async def test_operator_bypasses_rls(db_pool, test_data):
    """Operator role should see all rows regardless of tenant context."""
    async with db_pool.acquire() as conn:
        await conn.execute("SET LOCAL ROLE pulse_operator")
        rows = await conn.fetch(
            "SELECT * FROM device_state WHERE tenant_id IN ('test-tenant-a', 'test-tenant-b')"
        )
        assert len(rows) == 3, "Operator should see all 3 test rows"


@pytest.mark.asyncio
async def test_cross_tenant_query_blocked(db_pool, test_data):
    """App role cannot see other tenant's data even with explicit query."""
    async with db_pool.acquire() as conn:
        await conn.execute("SET LOCAL ROLE pulse_app")
        await conn.execute("SET LOCAL app.tenant_id = 'test-tenant-a'")
        rows = await conn.fetch(
            "SELECT * FROM device_state WHERE tenant_id = 'test-tenant-b'"
        )
        assert len(rows) == 0, "Cross-tenant query should return zero rows"


@pytest.mark.asyncio
async def test_insert_wrong_tenant_blocked(db_pool):
    """Cannot insert data for a different tenant."""
    async with db_pool.acquire() as conn:
        await conn.execute("SET LOCAL ROLE pulse_app")
        await conn.execute("SET LOCAL app.tenant_id = 'test-tenant-a'")
        with pytest.raises(asyncpg.exceptions.InsufficientPrivilegeError):
            await conn.execute(
                """
                INSERT INTO device_state (tenant_id, device_id, site_id, status)
                VALUES ('test-tenant-b', 'hacked-device', 'site', 'ONLINE')
                """
            )


@pytest.mark.asyncio
async def test_tenant_connection_wrapper(db_pool, test_data):
    """tenant_connection should set correct context."""
    async with tenant_connection(db_pool, "test-tenant-a") as conn:
        rows = await conn.fetch("SELECT * FROM device_state")
        assert len(rows) == 2
        for row in rows:
            assert row["tenant_id"] == "test-tenant-a"


@pytest.mark.asyncio
async def test_operator_connection_wrapper(db_pool, test_data):
    """operator_connection should bypass RLS."""
    async with operator_connection(db_pool) as conn:
        rows = await conn.fetch(
            "SELECT * FROM device_state WHERE tenant_id IN ('test-tenant-a', 'test-tenant-b')"
        )
        assert len(rows) == 3
