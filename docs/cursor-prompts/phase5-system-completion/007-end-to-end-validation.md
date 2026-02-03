# Task 007: End-to-End Validation Tests

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Create/Modify".
> Verify your work against the acceptance criteria.
> Commit with the exact message in the "Commit" section when done.

---

## Context

With all features implemented, we need integration tests that verify the complete alert-to-delivery flow for both webhook and SNMP integrations.

**Read first**:
- `tests/integration/` (existing test patterns)
- `services/dispatcher/dispatcher.py` (dispatcher logic)
- `services/delivery_worker/worker.py` (worker logic)

**Depends on**: Tasks 001-006

---

## Task

### 7.1 Create end-to-end delivery test

Create `tests/integration/test_delivery_e2e.py`:

```python
"""End-to-end tests for alert delivery pipeline.

These tests verify the complete flow from alert creation to delivery.
"""

import asyncio
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock, MagicMock

import asyncpg

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestWebhookDeliveryE2E:
    """Test webhook delivery end-to-end."""

    async def test_alert_creates_delivery_job(self, db_pool, test_tenant):
        """Verify alert + route creates delivery job."""
        async with db_pool.acquire() as conn:
            # Create integration
            integration_id = await conn.fetchval(
                """
                INSERT INTO integrations (tenant_id, name, type, config_json, enabled)
                VALUES ($1, 'Test Webhook', 'webhook', '{"url": "https://example.com/webhook"}', true)
                RETURNING integration_id
                """,
                test_tenant,
            )

            # Create route
            route_id = await conn.fetchval(
                """
                INSERT INTO integration_routes (tenant_id, integration_id, alert_types, deliver_on, enabled)
                VALUES ($1, $2, ARRAY['NO_HEARTBEAT'], ARRAY['OPEN'], true)
                RETURNING route_id
                """,
                test_tenant,
                integration_id,
            )

            # Create alert
            alert_id = await conn.fetchval(
                """
                INSERT INTO fleet_alert (tenant_id, site_id, device_id, alert_type, fingerprint, severity, confidence, summary, status)
                VALUES ($1, 'site-1', 'device-1', 'NO_HEARTBEAT', 'fp-test-1', 4, 0.9, 'Test alert', 'OPEN')
                RETURNING id
                """,
                test_tenant,
            )

            # Import and run dispatcher once
            from services.dispatcher.dispatcher import dispatch_once

            created = await dispatch_once(conn)

            # Verify job was created
            job = await conn.fetchrow(
                """
                SELECT * FROM delivery_jobs
                WHERE tenant_id = $1 AND alert_id = $2
                """,
                test_tenant,
                alert_id,
            )

            assert job is not None
            assert job["integration_id"] == integration_id
            assert job["route_id"] == route_id
            assert job["status"] == "PENDING"

    async def test_webhook_delivery_success(self, db_pool, test_tenant):
        """Verify webhook delivery sends HTTP POST."""
        async with db_pool.acquire() as conn:
            # Setup integration and job
            integration_id = await conn.fetchval(
                """
                INSERT INTO integrations (tenant_id, name, type, config_json, enabled)
                VALUES ($1, 'Test Webhook', 'webhook', '{"url": "https://httpbin.org/post"}', true)
                RETURNING integration_id
                """,
                test_tenant,
            )

            job_id = await conn.fetchval(
                """
                INSERT INTO delivery_jobs (tenant_id, alert_id, integration_id, route_id, deliver_on_event, status, payload_json)
                VALUES ($1, 1, $2, gen_random_uuid(), 'OPEN', 'PENDING', '{"alert_id": 1, "message": "test"}')
                RETURNING job_id
                """,
                test_tenant,
                integration_id,
            )

            # Mock httpx to avoid real HTTP call
            with patch("services.delivery_worker.worker.httpx.AsyncClient") as mock_client:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

                from services.delivery_worker.worker import process_job

                job = await conn.fetchrow("SELECT * FROM delivery_jobs WHERE job_id = $1", job_id)
                await process_job(conn, job)

            # Verify job completed
            job = await conn.fetchrow("SELECT * FROM delivery_jobs WHERE job_id = $1", job_id)
            assert job["status"] == "COMPLETED"

            # Verify attempt recorded
            attempt = await conn.fetchrow(
                "SELECT * FROM delivery_attempts WHERE job_id = $1",
                job_id,
            )
            assert attempt is not None
            assert attempt["ok"] is True


class TestSNMPDeliveryE2E:
    """Test SNMP delivery end-to-end."""

    async def test_snmp_integration_creates_job(self, db_pool, test_tenant):
        """Verify SNMP integration creates delivery job."""
        async with db_pool.acquire() as conn:
            # Create SNMP integration
            integration_id = await conn.fetchval(
                """
                INSERT INTO integrations (
                    tenant_id, name, type, snmp_host, snmp_port, snmp_config, enabled
                )
                VALUES ($1, 'Test SNMP', 'snmp', '192.0.2.100', 162, '{"version": "2c", "community": "public"}', true)
                RETURNING integration_id
                """,
                test_tenant,
            )

            # Create route
            route_id = await conn.fetchval(
                """
                INSERT INTO integration_routes (tenant_id, integration_id, alert_types, deliver_on, enabled)
                VALUES ($1, $2, ARRAY['NO_HEARTBEAT'], ARRAY['OPEN'], true)
                RETURNING route_id
                """,
                test_tenant,
                integration_id,
            )

            # Create alert
            alert_id = await conn.fetchval(
                """
                INSERT INTO fleet_alert (tenant_id, site_id, device_id, alert_type, fingerprint, severity, confidence, summary, status)
                VALUES ($1, 'site-1', 'device-snmp', 'NO_HEARTBEAT', 'fp-snmp-1', 4, 0.9, 'SNMP test alert', 'OPEN')
                RETURNING id
                """,
                test_tenant,
            )

            # Run dispatcher
            from services.dispatcher.dispatcher import dispatch_once

            await dispatch_once(conn)

            # Verify job created
            job = await conn.fetchrow(
                """
                SELECT * FROM delivery_jobs
                WHERE tenant_id = $1 AND alert_id = $2
                """,
                test_tenant,
                alert_id,
            )

            assert job is not None
            assert job["integration_id"] == integration_id

    async def test_snmp_delivery_calls_sender(self, db_pool, test_tenant):
        """Verify SNMP delivery calls snmp_sender."""
        async with db_pool.acquire() as conn:
            # Setup SNMP integration and job
            integration_id = await conn.fetchval(
                """
                INSERT INTO integrations (
                    tenant_id, name, type, snmp_host, snmp_port, snmp_config, snmp_oid_prefix, enabled
                )
                VALUES ($1, 'Test SNMP', 'snmp', '192.0.2.100', 162, '{"version": "2c", "community": "public"}', '1.3.6.1.4.1.99999', true)
                RETURNING integration_id
                """,
                test_tenant,
            )

            job_id = await conn.fetchval(
                """
                INSERT INTO delivery_jobs (tenant_id, alert_id, integration_id, route_id, deliver_on_event, status, payload_json)
                VALUES ($1, 2, $2, gen_random_uuid(), 'OPEN', 'PENDING', '{"alert_id": 2, "severity": 4, "summary": "test", "device_id": "dev-1"}')
                RETURNING job_id
                """,
                test_tenant,
                integration_id,
            )

            # Mock SNMP sender
            with patch("services.delivery_worker.worker.send_alert_trap") as mock_snmp:
                mock_result = MagicMock()
                mock_result.success = True
                mock_result.error = None
                mock_snmp.return_value = mock_result

                from services.delivery_worker.worker import process_job

                job = await conn.fetchrow("SELECT * FROM delivery_jobs WHERE job_id = $1", job_id)
                await process_job(conn, job)

                # Verify SNMP sender was called
                mock_snmp.assert_called_once()
                call_kwargs = mock_snmp.call_args.kwargs
                assert call_kwargs["host"] == "192.0.2.100"
                assert call_kwargs["port"] == 162

            # Verify job completed
            job = await conn.fetchrow("SELECT * FROM delivery_jobs WHERE job_id = $1", job_id)
            assert job["status"] == "COMPLETED"


class TestDeliveryRetry:
    """Test delivery retry logic."""

    async def test_failed_delivery_retries(self, db_pool, test_tenant):
        """Verify failed delivery schedules retry."""
        async with db_pool.acquire() as conn:
            integration_id = await conn.fetchval(
                """
                INSERT INTO integrations (tenant_id, name, type, config_json, enabled)
                VALUES ($1, 'Failing Webhook', 'webhook', '{"url": "https://example.com/fail"}', true)
                RETURNING integration_id
                """,
                test_tenant,
            )

            job_id = await conn.fetchval(
                """
                INSERT INTO delivery_jobs (tenant_id, alert_id, integration_id, route_id, deliver_on_event, status, attempts, payload_json)
                VALUES ($1, 3, $2, gen_random_uuid(), 'OPEN', 'PENDING', 0, '{"alert_id": 3}')
                RETURNING job_id
                """,
                test_tenant,
                integration_id,
            )

            # Mock HTTP failure
            with patch("services.delivery_worker.worker.httpx.AsyncClient") as mock_client:
                mock_response = MagicMock()
                mock_response.status_code = 500
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

                from services.delivery_worker.worker import process_job

                job = await conn.fetchrow("SELECT * FROM delivery_jobs WHERE job_id = $1", job_id)
                await process_job(conn, job)

            # Verify job is pending retry (not failed, since attempts < max)
            job = await conn.fetchrow("SELECT * FROM delivery_jobs WHERE job_id = $1", job_id)
            assert job["status"] == "PENDING"
            assert job["attempts"] == 1
            assert job["last_error"] == "http_500"
            assert job["next_run_at"] > datetime.now(timezone.utc)

    async def test_max_attempts_fails_job(self, db_pool, test_tenant):
        """Verify job fails after max attempts."""
        async with db_pool.acquire() as conn:
            integration_id = await conn.fetchval(
                """
                INSERT INTO integrations (tenant_id, name, type, config_json, enabled)
                VALUES ($1, 'Failing Webhook', 'webhook', '{"url": "https://example.com/fail"}', true)
                RETURNING integration_id
                """,
                test_tenant,
            )

            # Job already at attempt 4 (max is 5)
            job_id = await conn.fetchval(
                """
                INSERT INTO delivery_jobs (tenant_id, alert_id, integration_id, route_id, deliver_on_event, status, attempts, payload_json)
                VALUES ($1, 4, $2, gen_random_uuid(), 'OPEN', 'PENDING', 4, '{"alert_id": 4}')
                RETURNING job_id
                """,
                test_tenant,
                integration_id,
            )

            with patch("services.delivery_worker.worker.httpx.AsyncClient") as mock_client:
                mock_response = MagicMock()
                mock_response.status_code = 500
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

                from services.delivery_worker.worker import process_job

                job = await conn.fetchrow("SELECT * FROM delivery_jobs WHERE job_id = $1", job_id)
                await process_job(conn, job)

            # Verify job is FAILED
            job = await conn.fetchrow("SELECT * FROM delivery_jobs WHERE job_id = $1", job_id)
            assert job["status"] == "FAILED"
            assert job["attempts"] == 5


class TestRouteMatching:
    """Test alert-to-route matching."""

    async def test_route_filters_by_alert_type(self, db_pool, test_tenant):
        """Verify route only matches specified alert types."""
        async with db_pool.acquire() as conn:
            integration_id = await conn.fetchval(
                """
                INSERT INTO integrations (tenant_id, name, type, config_json, enabled)
                VALUES ($1, 'Filtered Webhook', 'webhook', '{"url": "https://example.com"}', true)
                RETURNING integration_id
                """,
                test_tenant,
            )

            # Route only matches LOW_BATTERY
            await conn.execute(
                """
                INSERT INTO integration_routes (tenant_id, integration_id, alert_types, deliver_on, enabled)
                VALUES ($1, $2, ARRAY['LOW_BATTERY'], ARRAY['OPEN'], true)
                """,
                test_tenant,
                integration_id,
            )

            # Create NO_HEARTBEAT alert (should NOT match)
            alert_id = await conn.fetchval(
                """
                INSERT INTO fleet_alert (tenant_id, site_id, device_id, alert_type, fingerprint, severity, confidence, summary, status)
                VALUES ($1, 'site-1', 'device-1', 'NO_HEARTBEAT', 'fp-filter-1', 4, 0.9, 'Wrong type', 'OPEN')
                RETURNING id
                """,
                test_tenant,
            )

            from services.dispatcher.dispatcher import dispatch_once

            await dispatch_once(conn)

            # Verify no job created
            job = await conn.fetchrow(
                "SELECT * FROM delivery_jobs WHERE tenant_id = $1 AND alert_id = $2",
                test_tenant,
                alert_id,
            )
            assert job is None


@pytest.fixture
async def db_pool():
    """Create database connection pool for tests."""
    import os

    pool = await asyncpg.create_pool(
        host=os.getenv("PG_HOST", "localhost"),
        port=int(os.getenv("PG_PORT", "5432")),
        database=os.getenv("PG_DB", "iotcloud_test"),
        user=os.getenv("PG_USER", "iot"),
        password=os.getenv("PG_PASS", "iot_dev"),
        min_size=1,
        max_size=5,
    )
    yield pool
    await pool.close()


@pytest.fixture
def test_tenant():
    """Unique tenant ID for test isolation."""
    import uuid

    return f"test-tenant-{uuid.uuid4().hex[:8]}"
```

### 7.2 Add test configuration for delivery tests

Update `pytest.ini` or `conftest.py` to include delivery worker paths:

Add to `conftest.py`:

```python
import sys
from pathlib import Path

# Add service paths for imports
services_path = Path(__file__).parent.parent / "services"
sys.path.insert(0, str(services_path / "dispatcher"))
sys.path.insert(0, str(services_path / "delivery_worker"))
```

### 7.3 Create test database setup for delivery tables

Add to test setup in `tests/conftest.py`:

```python
@pytest.fixture(scope="session", autouse=True)
async def setup_delivery_tables(db_pool):
    """Ensure delivery tables exist in test database."""
    async with db_pool.acquire() as conn:
        # Run key migrations
        migrations = [
            "db/migrations/001_webhook_delivery_v1.sql",
            "db/migrations/011_snmp_integrations.sql",
            "db/migrations/012_delivery_log.sql",
        ]
        for migration in migrations:
            try:
                with open(migration) as f:
                    await conn.execute(f.read())
            except Exception as e:
                print(f"Migration {migration}: {e}")
```

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `tests/integration/test_delivery_e2e.py` |
| MODIFY | `tests/conftest.py` |

---

## Acceptance Criteria

- [ ] Test verifies alert creates delivery job via dispatcher
- [ ] Test verifies webhook delivery sends HTTP POST
- [ ] Test verifies SNMP delivery calls snmp_sender
- [ ] Test verifies retry logic on failure
- [ ] Test verifies max attempts marks job FAILED
- [ ] Test verifies route filtering works
- [ ] All tests pass with mocked external calls

**Test**:
```bash
# Run delivery e2e tests
pytest tests/integration/test_delivery_e2e.py -v

# Run all tests
pytest -v
```

---

## Commit

```
Add end-to-end delivery integration tests

- Test alert-to-job creation via dispatcher
- Test webhook delivery with mocked HTTP
- Test SNMP delivery with mocked sender
- Test retry logic and max attempts
- Test route filtering by alert type

Part of Phase 5: System Completion
```
