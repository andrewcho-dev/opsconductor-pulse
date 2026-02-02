import asyncio
import os
import sys
from typing import AsyncGenerator

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services", "ui_iot"))
from app import app

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://iot:iot_dev@localhost:5432/iotcloud_test",
)

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8180")


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def db_pool() -> AsyncGenerator[asyncpg.Pool, None]:
    """Create database pool for tests."""
    pool = await asyncpg.create_pool(TEST_DATABASE_URL, min_size=2, max_size=10)
    yield pool
    await pool.close()


@pytest.fixture
async def db_connection(db_pool) -> AsyncGenerator[asyncpg.Connection, None]:
    """Get a single connection with transaction rollback."""
    async with db_pool.acquire() as conn:
        transaction = conn.transaction()
        await transaction.start()
        yield conn
        await transaction.rollback()


@pytest.fixture
async def clean_db(db_pool):
    """Clean test data before and after test."""
    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM device_state WHERE tenant_id LIKE 'test-%'")
        await conn.execute("DELETE FROM fleet_alert WHERE tenant_id LIKE 'test-%'")
        await conn.execute("DELETE FROM integrations WHERE tenant_id LIKE 'test-%'")
        await conn.execute("DELETE FROM integration_routes WHERE tenant_id LIKE 'test-%'")
        await conn.execute("DELETE FROM rate_limits WHERE tenant_id LIKE 'test-%'")
    yield
    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM device_state WHERE tenant_id LIKE 'test-%'")
        await conn.execute("DELETE FROM fleet_alert WHERE tenant_id LIKE 'test-%'")
        await conn.execute("DELETE FROM integrations WHERE tenant_id LIKE 'test-%'")
        await conn.execute("DELETE FROM integration_routes WHERE tenant_id LIKE 'test-%'")
        await conn.execute("DELETE FROM rate_limits WHERE tenant_id LIKE 'test-%'")


@pytest.fixture
async def test_tenants(db_pool, clean_db):
    """Create test tenants with sample data."""
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO device_state (tenant_id, device_id, site_id, status, last_seen_at)
            VALUES
                ('test-tenant-a', 'test-device-a1', 'test-site-a', 'ONLINE', now()),
                ('test-tenant-a', 'test-device-a2', 'test-site-a', 'STALE', now() - interval '1 hour')
            ON CONFLICT (tenant_id, device_id) DO NOTHING
            """
        )
        await conn.execute(
            """
            INSERT INTO device_state (tenant_id, device_id, site_id, status, last_seen_at)
            VALUES
                ('test-tenant-b', 'test-device-b1', 'test-site-b', 'ONLINE', now())
            ON CONFLICT (tenant_id, device_id) DO NOTHING
            """
        )
    yield {
        "tenant_a": "test-tenant-a",
        "tenant_b": "test-tenant-b",
    }


@pytest.fixture
async def test_integrations(db_pool, test_tenants):
    """Create test integrations."""
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO integrations (tenant_id, integration_id, name, enabled, config_json)
            VALUES
                ('test-tenant-a', 'int-a1', 'Test Webhook A', true, '{"url": "https://example.com/hook-a"}'),
                ('test-tenant-b', 'int-b1', 'Test Webhook B', true, '{"url": "https://example.com/hook-b"}')
            ON CONFLICT DO NOTHING
            """
        )
    yield {
        "integration_a": "int-a1",
        "integration_b": "int-b1",
    }


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for API tests."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def customer_a_token():
    """Get valid JWT for customer in tenant-a."""
    return "customer_a_token_placeholder"


@pytest.fixture
def customer_b_token():
    """Get valid JWT for customer in tenant-b."""
    return "customer_b_token_placeholder"


@pytest.fixture
def operator_token():
    """Get valid JWT for operator."""
    return "operator_token_placeholder"


@pytest.fixture
def operator_admin_token():
    """Get valid JWT for operator admin."""
    return "operator_admin_token_placeholder"


@pytest.fixture
def customer_viewer_token():
    """Get valid JWT for customer viewer in tenant-a."""
    return "customer_viewer_token_placeholder"
