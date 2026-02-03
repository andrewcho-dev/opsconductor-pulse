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
                INSERT INTO integration_routes (tenant_id, integration_id, name, alert_types, deliver_on, enabled)
                VALUES ($1, $2, 'Test Route', ARRAY['NO_HEARTBEAT'], ARRAY['OPEN'], true)
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

            route_id = await conn.fetchval(
                """
                INSERT INTO integration_routes (tenant_id, integration_id, name, alert_types, deliver_on, enabled)
                VALUES ($1, $2, 'Webhook Route', ARRAY['NO_HEARTBEAT'], ARRAY['OPEN'], true)
                RETURNING route_id
                """,
                test_tenant,
                integration_id,
            )

            job_id = await conn.fetchval(
                """
                INSERT INTO delivery_jobs (tenant_id, alert_id, integration_id, route_id, deliver_on_event, status, payload_json)
                VALUES ($1, 1, $2, $3, 'OPEN', 'PENDING', '{"alert_id": 1, "message": "test"}')
                RETURNING job_id
                """,
                test_tenant,
                integration_id,
                route_id,
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
                INSERT INTO integration_routes (tenant_id, integration_id, name, alert_types, deliver_on, enabled)
                VALUES ($1, $2, 'SNMP Route', ARRAY['NO_HEARTBEAT'], ARRAY['OPEN'], true)
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

            route_id = await conn.fetchval(
                """
                INSERT INTO integration_routes (tenant_id, integration_id, name, alert_types, deliver_on, enabled)
                VALUES ($1, $2, 'SNMP Job Route', ARRAY['NO_HEARTBEAT'], ARRAY['OPEN'], true)
                RETURNING route_id
                """,
                test_tenant,
                integration_id,
            )

            job_id = await conn.fetchval(
                """
                INSERT INTO delivery_jobs (tenant_id, alert_id, integration_id, route_id, deliver_on_event, status, payload_json)
                VALUES ($1, 2, $2, $3, 'OPEN', 'PENDING', '{"alert_id": 2, "severity": 4, "summary": "test", "device_id": "dev-1"}')
                RETURNING job_id
                """,
                test_tenant,
                integration_id,
                route_id,
            )

            # Mock SNMP sender
            with patch("services.delivery_worker.worker.send_alert_trap") as mock_snmp, patch(
                "services.delivery_worker.worker.PYSNMP_AVAILABLE", True
            ):
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

            route_id = await conn.fetchval(
                """
                INSERT INTO integration_routes (tenant_id, integration_id, name, alert_types, deliver_on, enabled)
                VALUES ($1, $2, 'Retry Route', ARRAY['NO_HEARTBEAT'], ARRAY['OPEN'], true)
                RETURNING route_id
                """,
                test_tenant,
                integration_id,
            )

            job_id = await conn.fetchval(
                """
                INSERT INTO delivery_jobs (tenant_id, alert_id, integration_id, route_id, deliver_on_event, status, attempts, payload_json)
                VALUES ($1, 3, $2, $3, 'OPEN', 'PENDING', 0, '{"alert_id": 3}')
                RETURNING job_id
                """,
                test_tenant,
                integration_id,
                route_id,
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
            route_id = await conn.fetchval(
                """
                INSERT INTO integration_routes (tenant_id, integration_id, name, alert_types, deliver_on, enabled)
                VALUES ($1, $2, 'Max Attempts Route', ARRAY['NO_HEARTBEAT'], ARRAY['OPEN'], true)
                RETURNING route_id
                """,
                test_tenant,
                integration_id,
            )

            job_id = await conn.fetchval(
                """
                INSERT INTO delivery_jobs (tenant_id, alert_id, integration_id, route_id, deliver_on_event, status, attempts, payload_json)
                VALUES ($1, 4, $2, $3, 'OPEN', 'PENDING', 4, '{"alert_id": 4}')
                RETURNING job_id
                """,
                test_tenant,
                integration_id,
                route_id,
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
                INSERT INTO integration_routes (tenant_id, integration_id, name, alert_types, deliver_on, enabled)
                VALUES ($1, $2, 'Filter Route', ARRAY['LOW_BATTERY'], ARRAY['OPEN'], true)
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


class TestEmailDeliveryE2E:
    """Test email delivery end-to-end."""

    async def test_email_integration_creates_job(self, db_pool, test_tenant):
        """Verify email integration creates delivery job."""
        async with db_pool.acquire() as conn:
            # Create email integration
            integration_id = await conn.fetchval(
                """
                INSERT INTO integrations (
                    tenant_id, name, type, email_config, email_recipients, enabled
                )
                VALUES ($1, 'Test Email', 'email',
                    '{"smtp_host": "smtp.example.com", "smtp_port": 587, "from_address": "a@b.com"}',
                    '{"to": ["admin@example.com"]}',
                    true)
                RETURNING integration_id
                """,
                test_tenant,
            )

            # Create route
            await conn.execute(
                """
                INSERT INTO integration_routes (tenant_id, integration_id, name, alert_types, deliver_on, enabled)
                VALUES ($1, $2, 'Email Route', ARRAY['NO_HEARTBEAT'], ARRAY['OPEN'], true)
                """,
                test_tenant,
                integration_id,
            )

            # Create alert
            alert_id = await conn.fetchval(
                """
                INSERT INTO fleet_alert (tenant_id, site_id, device_id, alert_type, fingerprint, severity, confidence, summary, status)
                VALUES ($1, 'site-1', 'device-email', 'NO_HEARTBEAT', 'fp-email-1', 4, 0.9, 'Email test alert', 'OPEN')
                RETURNING id
                """,
                test_tenant,
            )

            # Run dispatcher
            from services.dispatcher.dispatcher import dispatch_once
            await dispatch_once(conn)

            # Verify job created
            job = await conn.fetchrow(
                "SELECT * FROM delivery_jobs WHERE tenant_id = $1 AND alert_id = $2",
                test_tenant,
                alert_id,
            )

            assert job is not None
            assert job["integration_id"] == integration_id

    async def test_email_delivery_calls_sender(self, db_pool, test_tenant):
        """Verify email delivery calls email sender."""
        async with db_pool.acquire() as conn:
            integration_id = await conn.fetchval(
                """
                INSERT INTO integrations (
                    tenant_id, name, type, email_config, email_recipients, email_template, enabled
                )
                VALUES ($1, 'Test Email', 'email',
                    '{"smtp_host": "smtp.example.com", "smtp_port": 587, "smtp_tls": true, "from_address": "alerts@example.com", "from_name": "Alerts"}',
                    '{"to": ["admin@example.com"]}',
                    '{"subject_template": "[{severity}] {alert_type}", "format": "html"}',
                    true)
                RETURNING integration_id
                """,
                test_tenant,
            )

            route_id = await conn.fetchval(
                """
                INSERT INTO integration_routes (tenant_id, integration_id, name, alert_types, deliver_on, enabled)
                VALUES ($1, $2, 'Email Delivery Route', ARRAY['NO_HEARTBEAT'], ARRAY['OPEN'], true)
                RETURNING route_id
                """,
                test_tenant,
                integration_id,
            )

            job_id = await conn.fetchval(
                """
                INSERT INTO delivery_jobs (tenant_id, alert_id, integration_id, route_id, deliver_on_event, status, payload_json)
                VALUES ($1, 100, $2, $3, 'OPEN', 'PENDING',
                    '{"alert_id": 100, "severity": "critical", "alert_type": "NO_HEARTBEAT", "device_id": "dev-1", "summary": "Test"}')
                RETURNING job_id
                """,
                test_tenant,
                integration_id,
                route_id,
            )

            # Mock email sender
            with patch("services.delivery_worker.worker.send_alert_email", new=AsyncMock()) as mock_email, patch(
                "services.delivery_worker.worker.AIOSMTPLIB_AVAILABLE", True
            ):
                mock_email.return_value = MagicMock(
                    success=True,
                    error=None,
                    recipients_count=1,
                )

                from services.delivery_worker.worker import process_job

                job = await conn.fetchrow("SELECT * FROM delivery_jobs WHERE job_id = $1", job_id)
                await process_job(conn, job)

                # Verify email sender was called
                mock_email.assert_called_once()
                call_kwargs = mock_email.call_args.kwargs
                assert call_kwargs["smtp_host"] == "smtp.example.com"
                assert "admin@example.com" in call_kwargs["recipients"]["to"]

            # Verify job completed
            job = await conn.fetchrow("SELECT * FROM delivery_jobs WHERE job_id = $1", job_id)
            assert job["status"] == "COMPLETED"


class TestMultiTypeDelivery:
    """Test delivery to multiple integration types."""

    async def test_alert_dispatches_to_all_types(self, db_pool, test_tenant):
        """Verify alert creates jobs for webhook, SNMP, and email."""
        async with db_pool.acquire() as conn:
            # Create one of each type
            webhook_id = await conn.fetchval(
                """
                INSERT INTO integrations (tenant_id, name, type, config_json, enabled)
                VALUES ($1, 'Webhook', 'webhook', '{"url": "https://example.com"}', true)
                RETURNING integration_id
                """,
                test_tenant,
            )

            snmp_id = await conn.fetchval(
                """
                INSERT INTO integrations (tenant_id, name, type, snmp_host, snmp_port, snmp_config, enabled)
                VALUES ($1, 'SNMP', 'snmp', '192.0.2.100', 162, '{"version": "2c", "community": "public"}', true)
                RETURNING integration_id
                """,
                test_tenant,
            )

            email_id = await conn.fetchval(
                """
                INSERT INTO integrations (tenant_id, name, type, email_config, email_recipients, enabled)
                VALUES ($1, 'Email', 'email', '{"smtp_host": "smtp.example.com", "from_address": "a@b.com"}', '{"to": ["x@y.com"]}', true)
                RETURNING integration_id
                """,
                test_tenant,
            )

            # Create routes for each
            for int_id in [webhook_id, snmp_id, email_id]:
                await conn.execute(
                    """
                    INSERT INTO integration_routes (tenant_id, integration_id, name, alert_types, deliver_on, enabled)
                    VALUES ($1, $2, 'Multi Route', ARRAY['NO_HEARTBEAT'], ARRAY['OPEN'], true)
                    """,
                    test_tenant,
                    int_id,
                )

            # Create alert
            alert_id = await conn.fetchval(
                """
                INSERT INTO fleet_alert (tenant_id, site_id, device_id, alert_type, fingerprint, severity, confidence, summary, status)
                VALUES ($1, 'site-1', 'multi-device', 'NO_HEARTBEAT', 'fp-multi-1', 4, 0.9, 'Multi-type test', 'OPEN')
                RETURNING id
                """,
                test_tenant,
            )

            # Run dispatcher
            from services.dispatcher.dispatcher import dispatch_once
            created = await dispatch_once(conn)

            # Verify 3 jobs created
            jobs = await conn.fetch(
                "SELECT * FROM delivery_jobs WHERE tenant_id = $1 AND alert_id = $2",
                test_tenant,
                alert_id,
            )

            assert len(jobs) == 3
            integration_ids = {j["integration_id"] for j in jobs}
            assert webhook_id in integration_ids
            assert snmp_id in integration_ids
            assert email_id in integration_ids


@pytest.fixture(scope="session")
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
