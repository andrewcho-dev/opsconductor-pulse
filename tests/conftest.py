import asyncio
import os
import sys
from contextlib import asynccontextmanager
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

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8180")
os.environ.setdefault("KEYCLOAK_URL", KEYCLOAK_URL)
os.environ.setdefault("KEYCLOAK_PUBLIC_URL", KEYCLOAK_URL)
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
sys.path.insert(0, str(services_path))

from routes import customer as customer_routes
from routes import operator as operator_routes
_orig_cwd = os.getcwd()
os.chdir(ui_root)
try:
    from app import app
finally:
    os.chdir(_orig_cwd)
from tests.helpers.auth import (
    get_customer1_token,
    get_customer2_token,
    get_operator_token,
    get_operator_admin_token,
)


@asynccontextmanager
async def _safe_tenant_connection(pool, tenant_id):
    async with pool.acquire() as conn:
        tx_factory = getattr(conn, "transaction", None)
        if callable(tx_factory):
            async with tx_factory():
                yield conn
        else:
            yield conn


@asynccontextmanager
async def _safe_operator_connection(pool):
    async with pool.acquire() as conn:
        tx_factory = getattr(conn, "transaction", None)
        if callable(tx_factory):
            async with tx_factory():
                yield conn
        else:
            yield conn


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
        # Clean up potentially broken constraints from previous runs
        await conn.execute(
            "ALTER TABLE IF EXISTS integrations DROP CONSTRAINT IF EXISTS integration_type_config_check"
        )
        await conn.execute(
            "ALTER TABLE IF EXISTS integrations DROP CONSTRAINT IF EXISTS integrations_type_check"
        )
        try:
            with open("tests/fixtures/schema_minimal.sql") as f:
                await conn.execute(f.read())
        except Exception as e:
            print(f"Migration tests/fixtures/schema_minimal.sql: {e}")
        migrations = [
            "db/migrations/002_operator_audit_log.sql",
            "db/migrations/005_audit_rls_bypass.sql",
            "db/migrations/001_webhook_delivery_v1.sql",
            "db/migrations/003_rate_limits.sql",
            "db/migrations/004_enable_rls.sql",
            "db/migrations/011_snmp_integrations.sql",
            "db/migrations/012_delivery_log.sql",
            "db/migrations/013_email_integrations.sql",
            "db/migrations/014_mqtt_integrations.sql",
        ]
        for migration in migrations:
            try:
                with open(migration) as f:
                    await conn.execute(f.read())
            except Exception as e:
                print(f"Migration {migration}: {e}")

        try:
            await conn.execute("ALTER TABLE integrations ADD COLUMN IF NOT EXISTS mqtt_topic VARCHAR(512)")
            await conn.execute("ALTER TABLE integrations ADD COLUMN IF NOT EXISTS mqtt_qos INTEGER DEFAULT 1")
            await conn.execute("ALTER TABLE integrations ADD COLUMN IF NOT EXISTS mqtt_retain BOOLEAN DEFAULT false")
            await conn.execute("ALTER TABLE integrations ADD COLUMN IF NOT EXISTS mqtt_config JSONB")
        except Exception as e:
            print(f"Migration integrations.mqtt_columns: {e}")

        try:
            await conn.execute(
                """
                DO $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'integration_type') THEN
                        IF NOT EXISTS (
                            SELECT 1
                            FROM pg_enum
                            WHERE enumlabel = 'mqtt'
                              AND enumtypid = 'integration_type'::regtype
                        ) THEN
                            ALTER TYPE integration_type ADD VALUE 'mqtt';
                        END IF;
                    END IF;
                END$$;
                """
            )
            await conn.execute("ALTER TABLE integrations DROP CONSTRAINT IF EXISTS integrations_type_check")
            await conn.execute(
                """
                ALTER TABLE integrations ADD CONSTRAINT integrations_type_check
                CHECK (type::text IN ('webhook', 'snmp', 'email', 'mqtt'))
                """
            )
            await conn.execute(
                """
                ALTER TABLE integrations DROP CONSTRAINT IF EXISTS integration_type_config_check
                """
            )
            await conn.execute(
                """
                ALTER TABLE integrations ADD CONSTRAINT integration_type_config_check CHECK (
                    (type::text = 'webhook' AND (config_json->>'url') IS NOT NULL) OR
                    (type::text = 'snmp' AND snmp_host IS NOT NULL AND snmp_config IS NOT NULL) OR
                    (type::text = 'email' AND email_config IS NOT NULL AND email_recipients IS NOT NULL) OR
                    (type::text = 'mqtt' AND mqtt_topic IS NOT NULL)
                )
                """
            )
        except Exception as e:
            print(f"Migration integrations.mqtt_type: {e}")

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
async def test_integrations(db_pool, test_tenants, clean_db):
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


@pytest.fixture(autouse=True)
def patch_route_connection_contexts():
    from routes import alerts as alerts_routes
    from routes import devices as devices_routes
    from routes import exports as exports_routes
    from routes import metrics as metrics_routes

    modules = (
        customer_routes,
        operator_routes,
        alerts_routes,
        devices_routes,
        exports_routes,
        metrics_routes,
    )
    for mod in modules:
        if hasattr(mod, "tenant_connection"):
            setattr(mod, "tenant_connection", _safe_tenant_connection)
        if hasattr(mod, "operator_connection"):
            setattr(mod, "operator_connection", _safe_operator_connection)


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
