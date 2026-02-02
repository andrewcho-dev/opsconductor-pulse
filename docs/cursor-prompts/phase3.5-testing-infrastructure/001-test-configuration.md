# Task 001: Test Configuration

> **CURSOR: EXECUTE THIS TASK**
>
> This is an implementation task. Read the instructions below and implement them.
> Modify the files listed in "Files to Create/Modify" section.
> Follow the acceptance criteria to verify your work.
> Commit with the message in the "Commit" section when done.

---

## Context

We need a solid testing foundation before adding more tests. This includes pytest configuration, shared fixtures, test database management, and a clean project structure.

**Read first**:
- `tests/test_rls_enforcement.py` (existing tests)
- `tests/conftest.py` (existing fixtures)
- `services/ui_iot/requirements.txt` (current dependencies)

**Depends on**: Phase 3 complete

## Task

### 1.1 Create pytest configuration

Create `pytest.ini` in project root:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
addopts = -v --tb=short --strict-markers
markers =
    unit: Unit tests (fast, no external dependencies)
    integration: Integration tests (require database)
    e2e: End-to-end tests (require running services)
    slow: Slow tests (skip with -m "not slow")
filterwarnings =
    ignore::DeprecationWarning
```

### 1.2 Enhance conftest.py

Update `tests/conftest.py` with comprehensive fixtures:

```python
import pytest
import asyncio
import asyncpg
import os
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport

# Import the FastAPI app
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'ui_iot'))
from app import app

# ============================================
# Configuration
# ============================================

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://iot:iot_dev@localhost:5432/iotcloud_test"
)

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8180")

# ============================================
# Event Loop
# ============================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# ============================================
# Database Fixtures
# ============================================

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
        await transaction.rollback()  # Rollback after each test

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

# ============================================
# Test Data Fixtures
# ============================================

@pytest.fixture
async def test_tenants(db_pool, clean_db):
    """Create test tenants with sample data."""
    async with db_pool.acquire() as conn:
        # Tenant A devices
        await conn.execute("""
            INSERT INTO device_state (tenant_id, device_id, site_id, status, last_seen_at)
            VALUES
                ('test-tenant-a', 'test-device-a1', 'test-site-a', 'ONLINE', now()),
                ('test-tenant-a', 'test-device-a2', 'test-site-a', 'STALE', now() - interval '1 hour')
            ON CONFLICT (tenant_id, device_id) DO NOTHING
        """)
        # Tenant B devices
        await conn.execute("""
            INSERT INTO device_state (tenant_id, device_id, site_id, status, last_seen_at)
            VALUES
                ('test-tenant-b', 'test-device-b1', 'test-site-b', 'ONLINE', now())
            ON CONFLICT (tenant_id, device_id) DO NOTHING
        """)
    yield {
        "tenant_a": "test-tenant-a",
        "tenant_b": "test-tenant-b",
    }

@pytest.fixture
async def test_integrations(db_pool, test_tenants):
    """Create test integrations."""
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO integrations (tenant_id, integration_id, name, enabled, config_json)
            VALUES
                ('test-tenant-a', 'int-a1', 'Test Webhook A', true, '{"url": "https://example.com/hook-a"}'),
                ('test-tenant-b', 'int-b1', 'Test Webhook B', true, '{"url": "https://example.com/hook-b"}')
            ON CONFLICT DO NOTHING
        """)
    yield {
        "integration_a": "int-a1",
        "integration_b": "int-b1",
    }

# ============================================
# HTTP Client Fixtures
# ============================================

@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for API tests."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

# ============================================
# Auth Fixtures
# ============================================

@pytest.fixture
def customer_a_token():
    """Get valid JWT for customer in tenant-a."""
    # This should be a real token from Keycloak or a mock
    # For now, return placeholder - will be implemented in Task 003
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
```

### 1.3 Create test database

Add script `scripts/setup_test_db.sh`:

```bash
#!/bin/bash
set -e

# Create test database
docker exec -i iot-postgres psql -U iot -d postgres -c "
    SELECT pg_terminate_backend(pid)
    FROM pg_stat_activity
    WHERE datname = 'iotcloud_test' AND pid <> pg_backend_pid();
"
docker exec -i iot-postgres psql -U iot -d postgres -c "DROP DATABASE IF EXISTS iotcloud_test;"
docker exec -i iot-postgres psql -U iot -d postgres -c "CREATE DATABASE iotcloud_test TEMPLATE iotcloud;"

echo "Test database created: iotcloud_test"
```

### 1.4 Create test runner script

Add script `scripts/run_tests.sh`:

```bash
#!/bin/bash
set -e

# Setup test database
./scripts/setup_test_db.sh

# Run tests
export TEST_DATABASE_URL="postgresql://iot:iot_dev@localhost:5432/iotcloud_test"

if [ "$1" == "unit" ]; then
    pytest -m unit "$@"
elif [ "$1" == "integration" ]; then
    pytest -m integration "$@"
elif [ "$1" == "e2e" ]; then
    pytest -m e2e "$@"
elif [ "$1" == "all" ]; then
    pytest "$@"
else
    pytest "$@"
fi
```

### 1.5 Update requirements

Add to `services/ui_iot/requirements.txt` (or create `requirements-test.txt`):

```
# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
httpx>=0.24.0
respx>=0.20.0
```

### 1.6 Create directory structure

```bash
mkdir -p tests/api
mkdir -p tests/e2e
mkdir -p tests/fixtures
touch tests/api/__init__.py
touch tests/e2e/__init__.py
touch tests/fixtures/__init__.py
```

### 1.7 Create test data fixtures file

Create `tests/fixtures/test_data.sql`:

```sql
-- Test data for integration tests
-- Run with: psql -U iot -d iotcloud_test -f tests/fixtures/test_data.sql

-- Clear existing test data
DELETE FROM device_state WHERE tenant_id LIKE 'test-%';
DELETE FROM fleet_alert WHERE tenant_id LIKE 'test-%';
DELETE FROM integrations WHERE tenant_id LIKE 'test-%';

-- Tenant A data
INSERT INTO device_state (tenant_id, device_id, site_id, status, last_seen_at, state)
VALUES
    ('test-tenant-a', 'test-device-a1', 'test-site-a', 'ONLINE', now(), '{"battery_pct": 85, "temp_c": 22.5}'),
    ('test-tenant-a', 'test-device-a2', 'test-site-a', 'STALE', now() - interval '2 hours', '{"battery_pct": 20, "temp_c": 25.0}');

-- Tenant B data
INSERT INTO device_state (tenant_id, device_id, site_id, status, last_seen_at, state)
VALUES
    ('test-tenant-b', 'test-device-b1', 'test-site-b', 'ONLINE', now(), '{"battery_pct": 90, "temp_c": 21.0}');

-- Test alerts
INSERT INTO fleet_alert (tenant_id, device_id, site_id, alert_type, severity, summary, status, created_at)
VALUES
    ('test-tenant-a', 'test-device-a2', 'test-site-a', 'LOW_BATTERY', 'WARNING', 'Battery below 25%', 'OPEN', now());
```

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `pytest.ini` |
| MODIFY | `tests/conftest.py` |
| CREATE | `scripts/setup_test_db.sh` |
| CREATE | `scripts/run_tests.sh` |
| MODIFY | `services/ui_iot/requirements.txt` |
| CREATE | `tests/api/__init__.py` |
| CREATE | `tests/e2e/__init__.py` |
| CREATE | `tests/fixtures/__init__.py` |
| CREATE | `tests/fixtures/test_data.sql` |

## Acceptance Criteria

- [ ] `pytest.ini` exists with proper configuration
- [ ] `tests/conftest.py` has database and client fixtures
- [ ] Test database can be created with `scripts/setup_test_db.sh`
- [ ] Directory structure exists: `tests/api/`, `tests/e2e/`, `tests/fixtures/`
- [ ] Existing RLS tests still pass
- [ ] `pytest --collect-only` shows proper test discovery

**Test**:
```bash
chmod +x scripts/*.sh
./scripts/setup_test_db.sh
pytest tests/test_rls_enforcement.py -v
```

## Commit

```
Add test configuration and infrastructure

- pytest.ini with markers and async mode
- Enhanced conftest.py with database and client fixtures
- Test database setup script
- Directory structure for api/e2e/fixtures tests
- Test data SQL fixtures

Part of Phase 3.5: Testing Infrastructure
```
