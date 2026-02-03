import asyncio
import os
import sys
from pathlib import Path
from typing import AsyncGenerator

import asyncpg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://iot:iot_dev@localhost:5432/iotcloud_test",
)

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://192.168.10.53:8180")
os.environ.setdefault("KEYCLOAK_URL", KEYCLOAK_URL)
os.environ.setdefault("KEYCLOAK_REALM", "pulse")
os.environ.setdefault("PG_HOST", "localhost")
os.environ.setdefault("PG_PORT", "5432")
os.environ.setdefault("PG_DB", "iotcloud_test")
os.environ.setdefault("PG_USER", "iot")
os.environ.setdefault("PG_PASS", "iot_dev")

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ui_root = os.path.join(repo_root, "services", "ui_iot")
sys.path.insert(0, repo_root)
sys.path.insert(0, ui_root)
services_path = Path(repo_root) / "services"
sys.path.insert(0, str(services_path / "dispatcher"))
sys.path.insert(0, str(services_path / "delivery_worker"))

from routes import customer as customer_routes
from routes import operator as operator_routes
_orig_cwd = os.getcwd()
os.chdir(ui_root)
try:
    from app import app
finally:
    os.chdir(_orig_cwd)
templates_path = os.path.join(ui_root, "templates")
customer_routes.templates.env.loader.searchpath = [templates_path]
operator_routes.templates.env.loader.searchpath = [templates_path]
from tests.helpers.auth import (
    get_customer1_token,
    get_customer2_token,
    get_operator_token,
    get_operator_admin_token,
)


@pytest.fixture(scope="session")
async def db_pool() -> AsyncGenerator[asyncpg.Pool, None]:
    """Create database pool for tests."""
    pool = await asyncpg.create_pool(TEST_DATABASE_URL, min_size=2, max_size=10)
    yield pool
    await pool.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_delivery_tables(db_pool):
    """Ensure delivery tables exist in test database."""
    async with db_pool.acquire() as conn:
        migrations = [
            "db/migrations/001_webhook_delivery_v1.sql",
            "db/migrations/011_snmp_integrations.sql",
            "db/migrations/012_delivery_log.sql",
            "db/migrations/013_email_integrations.sql",
        ]
        for migration in migrations:
            try:
                with open(migration) as f:
                    await conn.execute(f.read())
            except Exception as e:
                print(f"Migration {migration}: {e}")

        try:
            await conn.execute(
                "ALTER TABLE integration_routes ADD COLUMN IF NOT EXISTS severities TEXT[]"
            )
        except Exception as e:
            print(f"Migration integration_routes.severities: {e}")

        try:
            await conn.execute("ALTER TABLE integrations DROP CONSTRAINT IF EXISTS integrations_type_check")
        except Exception as e:
            print(f"Migration integrations.type_check: {e}")


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
        await conn.execute("DELETE FROM device_state WHERE tenant_id IN ('tenant-a', 'tenant-b')")
        await conn.execute("DELETE FROM fleet_alert WHERE tenant_id IN ('tenant-a', 'tenant-b')")
        await conn.execute("DELETE FROM integrations WHERE tenant_id IN ('tenant-a', 'tenant-b')")
        await conn.execute("DELETE FROM integration_routes WHERE tenant_id IN ('tenant-a', 'tenant-b')")
        await conn.execute("DELETE FROM rate_limits WHERE tenant_id IN ('tenant-a', 'tenant-b')")
    yield
    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM device_state WHERE tenant_id IN ('tenant-a', 'tenant-b')")
        await conn.execute("DELETE FROM fleet_alert WHERE tenant_id IN ('tenant-a', 'tenant-b')")
        await conn.execute("DELETE FROM integrations WHERE tenant_id IN ('tenant-a', 'tenant-b')")
        await conn.execute("DELETE FROM integration_routes WHERE tenant_id IN ('tenant-a', 'tenant-b')")
        await conn.execute("DELETE FROM rate_limits WHERE tenant_id IN ('tenant-a', 'tenant-b')")


@pytest.fixture
async def test_tenants(db_pool, clean_db):
    """Create test tenants with sample data."""
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO device_state (tenant_id, device_id, site_id, status, last_seen_at)
            VALUES
                ('tenant-a', 'test-device-a1', 'test-site-a', 'ONLINE', now()),
                ('tenant-a', 'test-device-a2', 'test-site-a', 'STALE', now() - interval '1 hour')
            ON CONFLICT (tenant_id, device_id) DO NOTHING
            """
        )
        await conn.execute(
            """
            INSERT INTO device_state (tenant_id, device_id, site_id, status, last_seen_at)
            VALUES
                ('tenant-b', 'test-device-b1', 'test-site-b', 'ONLINE', now())
            ON CONFLICT (tenant_id, device_id) DO NOTHING
            """
        )
    yield {
        "tenant_a": "tenant-a",
        "tenant_b": "tenant-b",
    }


@pytest.fixture
async def test_integrations(db_pool, test_tenants):
    """Create test integrations."""
    integration_a = "00000000-0000-0000-0000-0000000000a1"
    integration_b = "00000000-0000-0000-0000-0000000000b1"
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO integrations (tenant_id, integration_id, name, enabled, config_json)
            VALUES
                ('tenant-a', $1::uuid, 'Test Webhook A', true, '{"url": "https://example.com/hook-a"}'),
                ('tenant-b', $2::uuid, 'Test Webhook B', true, '{"url": "https://example.com/hook-b"}')
            ON CONFLICT DO NOTHING
            """,
            integration_a,
            integration_b,
        )
    yield {
        "integration_a": integration_a,
        "integration_b": integration_b,
    }


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for API tests."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture(scope="session")
async def customer_a_token() -> str:
    """Get valid JWT for customer1 (tenant-a, customer_admin)."""
    return await get_customer1_token()


@pytest_asyncio.fixture(scope="session")
async def customer_b_token() -> str:
    """Get valid JWT for customer2 (tenant-b, customer_viewer)."""
    return await get_customer2_token()


@pytest_asyncio.fixture(scope="session")
async def customer_viewer_token() -> str:
    """Alias for customer2 (customer_viewer role)."""
    return await get_customer2_token()


@pytest_asyncio.fixture(scope="session")
async def operator_token() -> str:
    """Get valid JWT for operator1."""
    return await get_operator_token()


@pytest_asyncio.fixture(scope="session")
async def operator_admin_token() -> str:
    """Get valid JWT for operator_admin."""
    return await get_operator_admin_token()


@pytest_asyncio.fixture
async def auth_headers():
    """Mock auth headers for customer admin."""
    token = await get_customer1_token()
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def other_tenant_headers():
    """Auth headers for a different tenant (for isolation tests)."""
    token = await get_customer2_token()
    return {"Authorization": f"Bearer {token}"}
