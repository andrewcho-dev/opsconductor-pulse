# Task 009: Email Integration and E2E Tests

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Create/Modify".
> Verify your work against the acceptance criteria.
> Commit with the exact message in the "Commit" section when done.

---

## Context

Email delivery needs comprehensive test coverage including API integration tests and end-to-end delivery pipeline tests.

**Read first**:
- `tests/integration/test_customer_routes.py` (existing patterns)
- `tests/integration/test_delivery_e2e.py` (delivery test patterns from Phase 5)
- `services/ui_iot/routes/customer.py` (email routes)

**Depends on**: Tasks 001-008

---

## Task

### 9.1 Create API integration tests for email routes

Create `tests/integration/test_email_routes.py`:

```python
"""Integration tests for email integration routes."""

import pytest
from unittest.mock import patch, AsyncMock

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestEmailIntegrationRoutes:
    """Test email integration CRUD routes."""

    async def test_list_email_integrations_empty(self, client, auth_headers):
        """Test listing email integrations when none exist."""
        response = await client.get(
            "/customer/integrations/email",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_create_email_integration(self, client, auth_headers):
        """Test creating an email integration."""
        payload = {
            "name": "Test Email",
            "smtp_config": {
                "smtp_host": "smtp.example.com",
                "smtp_port": 587,
                "smtp_tls": True,
                "from_address": "alerts@example.com",
                "from_name": "Test Alerts",
            },
            "recipients": {
                "to": ["admin@example.com"],
                "cc": [],
                "bcc": [],
            },
            "enabled": True,
        }
        response = await client.post(
            "/customer/integrations/email",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Email"
        assert data["smtp_host"] == "smtp.example.com"
        assert data["recipient_count"] == 1

    async def test_create_email_integration_invalid_smtp_host(self, client, auth_headers):
        """Test that private SMTP hosts are rejected."""
        payload = {
            "name": "Bad SMTP",
            "smtp_config": {
                "smtp_host": "192.168.1.1",
                "smtp_port": 587,
                "smtp_tls": True,
                "from_address": "alerts@example.com",
            },
            "recipients": {
                "to": ["admin@example.com"],
            },
        }
        response = await client.post(
            "/customer/integrations/email",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "private" in response.json()["detail"].lower() or "blocked" in response.json()["detail"].lower()

    async def test_create_email_integration_no_recipients(self, client, auth_headers):
        """Test that at least one recipient is required."""
        payload = {
            "name": "No Recipients",
            "smtp_config": {
                "smtp_host": "smtp.example.com",
                "smtp_port": 587,
                "smtp_tls": True,
                "from_address": "alerts@example.com",
            },
            "recipients": {
                "to": [],
            },
        }
        response = await client.post(
            "/customer/integrations/email",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code in [400, 422]

    async def test_create_email_integration_invalid_email(self, client, auth_headers):
        """Test that invalid email addresses are rejected."""
        payload = {
            "name": "Invalid Email",
            "smtp_config": {
                "smtp_host": "smtp.example.com",
                "smtp_port": 587,
                "smtp_tls": True,
                "from_address": "not-an-email",
            },
            "recipients": {
                "to": ["admin@example.com"],
            },
        }
        response = await client.post(
            "/customer/integrations/email",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code in [400, 422]

    async def test_get_email_integration(self, client, auth_headers, created_email_integration):
        """Test getting a specific email integration."""
        integration_id = created_email_integration["id"]
        response = await client.get(
            f"/customer/integrations/email/{integration_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == integration_id

    async def test_get_email_integration_not_found(self, client, auth_headers):
        """Test getting non-existent integration returns 404."""
        response = await client.get(
            "/customer/integrations/email/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_update_email_integration(self, client, auth_headers, created_email_integration):
        """Test updating an email integration."""
        integration_id = created_email_integration["id"]
        response = await client.patch(
            f"/customer/integrations/email/{integration_id}",
            json={"name": "Updated Email", "enabled": False},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Email"
        assert data["enabled"] is False

    async def test_delete_email_integration(self, client, auth_headers, created_email_integration):
        """Test deleting an email integration."""
        integration_id = created_email_integration["id"]
        response = await client.delete(
            f"/customer/integrations/email/{integration_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

        # Verify it's gone
        response = await client.get(
            f"/customer/integrations/email/{integration_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_test_email_integration(self, client, auth_headers, created_email_integration):
        """Test sending a test email."""
        integration_id = created_email_integration["id"]

        with patch("services.ui_iot.services.email_sender.aiosmtplib") as mock_smtp:
            mock_smtp.SMTP.return_value.__aenter__ = AsyncMock()
            mock_smtp.SMTP.return_value.__aexit__ = AsyncMock()
            mock_smtp.SMTP.return_value.send_message = AsyncMock()

            response = await client.post(
                f"/customer/integrations/email/{integration_id}/test",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data

    async def test_tenant_isolation(self, client, auth_headers, other_tenant_headers, created_email_integration):
        """Test that one tenant cannot access another tenant's integrations."""
        integration_id = created_email_integration["id"]

        # Try to access with different tenant
        response = await client.get(
            f"/customer/integrations/email/{integration_id}",
            headers=other_tenant_headers,
        )
        assert response.status_code == 404


@pytest.fixture
async def created_email_integration(client, auth_headers):
    """Create an email integration for testing."""
    payload = {
        "name": "Test Email Fixture",
        "smtp_config": {
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "smtp_tls": True,
            "from_address": "alerts@example.com",
        },
        "recipients": {
            "to": ["admin@example.com"],
        },
    }
    response = await client.post(
        "/customer/integrations/email",
        json=payload,
        headers=auth_headers,
    )
    return response.json()
```

### 9.2 Add email delivery E2E tests

Add to `tests/integration/test_delivery_e2e.py`:

```python
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
                INSERT INTO integration_routes (tenant_id, integration_id, alert_types, deliver_on, enabled)
                VALUES ($1, $2, ARRAY['NO_HEARTBEAT'], ARRAY['OPEN'], true)
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

            job_id = await conn.fetchval(
                """
                INSERT INTO delivery_jobs (tenant_id, alert_id, integration_id, route_id, deliver_on_event, status, payload_json)
                VALUES ($1, 100, $2, gen_random_uuid(), 'OPEN', 'PENDING',
                    '{"alert_id": 100, "severity": "critical", "alert_type": "NO_HEARTBEAT", "device_id": "dev-1", "summary": "Test"}')
                RETURNING job_id
                """,
                test_tenant,
                integration_id,
            )

            # Mock email sender
            with patch("services.delivery_worker.worker.send_alert_email") as mock_email:
                mock_result = AsyncMock()
                mock_result.success = True
                mock_result.error = None
                mock_result.recipients_count = 1
                mock_email.return_value = mock_result

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
                    INSERT INTO integration_routes (tenant_id, integration_id, alert_types, deliver_on, enabled)
                    VALUES ($1, $2, ARRAY['NO_HEARTBEAT'], ARRAY['OPEN'], true)
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
```

### 9.3 Update conftest.py with email fixtures

Add to `tests/conftest.py`:

```python
@pytest.fixture
def auth_headers(test_tenant):
    """Mock auth headers for customer admin."""
    # This should match your existing auth mocking pattern
    return {"Authorization": f"Bearer mock-token-{test_tenant}"}


@pytest.fixture
def other_tenant_headers():
    """Auth headers for a different tenant (for isolation tests)."""
    return {"Authorization": "Bearer mock-token-other-tenant"}
```

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `tests/integration/test_email_routes.py` |
| MODIFY | `tests/integration/test_delivery_e2e.py` |
| MODIFY | `tests/conftest.py` |

---

## Acceptance Criteria

- [ ] Email CRUD routes have integration tests
- [ ] Email validation tested (invalid SMTP host, invalid email, no recipients)
- [ ] Tenant isolation tested
- [ ] Email delivery E2E test verifies job creation
- [ ] Email delivery E2E test verifies sender is called
- [ ] Multi-type delivery test verifies all 3 types get jobs
- [ ] All tests pass

**Test**:
```bash
# Run email route tests
pytest tests/integration/test_email_routes.py -v

# Run delivery E2E tests
pytest tests/integration/test_delivery_e2e.py -v

# Run all tests
pytest -v
```

---

## Commit

```
Add email integration and E2E tests

- API integration tests for email CRUD
- Validation tests (SMTP host, email format, recipients)
- Tenant isolation tests
- E2E tests for email delivery pipeline
- Multi-type delivery test (webhook + SNMP + email)

Part of Phase 6: Email Delivery
```
