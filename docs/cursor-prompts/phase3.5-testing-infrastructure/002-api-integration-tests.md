# Task 002: API Integration Tests

> **CURSOR: EXECUTE THIS TASK**
>
> This is an implementation task. Read the instructions below and implement them.
> Modify the files listed in "Files to Create/Modify" section.
> Follow the acceptance criteria to verify your work.
> Commit with the message in the "Commit" section when done.

---

## Context

We need comprehensive API integration tests for all endpoints. These tests verify that routes work correctly with the database, authentication, and business logic.

**Read first**:
- `services/ui_iot/routes/customer.py` (customer endpoints)
- `services/ui_iot/routes/operator.py` (operator endpoints)
- `tests/conftest.py` (fixtures from Task 001)

**Depends on**: Task 001

## Task

### 2.1 Create customer routes tests

Create `tests/api/test_customer_routes.py`:

```python
import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestCustomerDevices:
    """Test /customer/devices endpoints."""

    async def test_list_devices_requires_auth(self, client: AsyncClient):
        """Unauthenticated request returns 401."""
        response = await client.get("/customer/devices")
        assert response.status_code == 401

    async def test_list_devices_with_token(
        self, client: AsyncClient, customer_a_token: str, test_tenants
    ):
        """Authenticated request returns tenant's devices only."""
        response = await client.get(
            "/customer/devices",
            headers={"Authorization": f"Bearer {customer_a_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "devices" in data
        assert "tenant_id" in data
        # All devices should belong to tenant-a
        for device in data["devices"]:
            assert device["tenant_id"] == test_tenants["tenant_a"]

    async def test_list_devices_with_cookie(
        self, client: AsyncClient, customer_a_token: str, test_tenants
    ):
        """Cookie authentication works."""
        response = await client.get(
            "/customer/devices",
            cookies={"pulse_session": customer_a_token}
        )
        assert response.status_code == 200

    async def test_get_device_detail(
        self, client: AsyncClient, customer_a_token: str, test_tenants
    ):
        """Get single device by ID."""
        response = await client.get(
            "/customer/devices/test-device-a1",
            headers={"Authorization": f"Bearer {customer_a_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["device"]["device_id"] == "test-device-a1"

    async def test_get_device_wrong_tenant_returns_404(
        self, client: AsyncClient, customer_a_token: str, test_tenants
    ):
        """Cannot access device from another tenant."""
        response = await client.get(
            "/customer/devices/test-device-b1",  # Belongs to tenant-b
            headers={"Authorization": f"Bearer {customer_a_token}"}
        )
        assert response.status_code == 404

    async def test_operator_cannot_access_customer_routes(
        self, client: AsyncClient, operator_token: str
    ):
        """Operator role cannot access customer routes."""
        response = await client.get(
            "/customer/devices",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 403


class TestCustomerAlerts:
    """Test /customer/alerts endpoints."""

    async def test_list_alerts(
        self, client: AsyncClient, customer_a_token: str, test_tenants
    ):
        """List alerts for tenant."""
        response = await client.get(
            "/customer/alerts",
            headers={"Authorization": f"Bearer {customer_a_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data
        for alert in data["alerts"]:
            assert alert["tenant_id"] == test_tenants["tenant_a"]


class TestCustomerIntegrations:
    """Test /customer/integrations CRUD endpoints."""

    async def test_list_integrations(
        self, client: AsyncClient, customer_a_token: str, test_integrations
    ):
        """List integrations for tenant."""
        response = await client.get(
            "/customer/integrations",
            headers={"Authorization": f"Bearer {customer_a_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "integrations" in data

    async def test_create_integration(
        self, client: AsyncClient, customer_a_token: str, clean_db
    ):
        """Create new integration."""
        response = await client.post(
            "/customer/integrations",
            headers={"Authorization": f"Bearer {customer_a_token}"},
            json={
                "name": "Test Integration",
                "webhook_url": "https://webhook.site/test-uuid",
                "enabled": True
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Integration"
        assert "integration_id" in data

    async def test_create_integration_ssrf_blocked(
        self, client: AsyncClient, customer_a_token: str
    ):
        """SSRF blocked for private IPs."""
        response = await client.post(
            "/customer/integrations",
            headers={"Authorization": f"Bearer {customer_a_token}"},
            json={
                "name": "Evil Integration",
                "webhook_url": "https://10.0.0.1/internal",
                "enabled": True
            }
        )
        assert response.status_code == 400
        assert "Private IP" in response.json()["detail"] or "blocked" in response.json()["detail"].lower()

    async def test_create_integration_localhost_blocked(
        self, client: AsyncClient, customer_a_token: str
    ):
        """SSRF blocked for localhost."""
        response = await client.post(
            "/customer/integrations",
            headers={"Authorization": f"Bearer {customer_a_token}"},
            json={
                "name": "Localhost Integration",
                "webhook_url": "https://localhost/hook",
                "enabled": True
            }
        )
        assert response.status_code == 400

    async def test_update_integration(
        self, client: AsyncClient, customer_a_token: str, test_integrations
    ):
        """Update existing integration."""
        response = await client.patch(
            f"/customer/integrations/{test_integrations['integration_a']}",
            headers={"Authorization": f"Bearer {customer_a_token}"},
            json={"enabled": False}
        )
        assert response.status_code == 200
        assert response.json()["enabled"] == False

    async def test_update_integration_empty_patch_rejected(
        self, client: AsyncClient, customer_a_token: str, test_integrations
    ):
        """Empty PATCH returns 400."""
        response = await client.patch(
            f"/customer/integrations/{test_integrations['integration_a']}",
            headers={"Authorization": f"Bearer {customer_a_token}"},
            json={}
        )
        assert response.status_code == 400

    async def test_delete_integration(
        self, client: AsyncClient, customer_a_token: str, test_integrations
    ):
        """Delete integration."""
        response = await client.delete(
            f"/customer/integrations/{test_integrations['integration_a']}",
            headers={"Authorization": f"Bearer {customer_a_token}"}
        )
        assert response.status_code == 204

    async def test_cannot_access_other_tenant_integration(
        self, client: AsyncClient, customer_a_token: str, test_integrations
    ):
        """Cannot access integration from another tenant."""
        response = await client.get(
            f"/customer/integrations/{test_integrations['integration_b']}",
            headers={"Authorization": f"Bearer {customer_a_token}"}
        )
        assert response.status_code == 404

    async def test_viewer_cannot_create(
        self, client: AsyncClient, customer_viewer_token: str
    ):
        """Customer viewer cannot create integrations."""
        response = await client.post(
            "/customer/integrations",
            headers={"Authorization": f"Bearer {customer_viewer_token}"},
            json={
                "name": "Viewer Integration",
                "webhook_url": "https://example.com/hook",
                "enabled": True
            }
        )
        assert response.status_code == 403


class TestTestDelivery:
    """Test /customer/integrations/{id}/test endpoint."""

    async def test_test_delivery(
        self, client: AsyncClient, customer_a_token: str, test_integrations
    ):
        """Test delivery returns result."""
        response = await client.post(
            f"/customer/integrations/{test_integrations['integration_a']}/test",
            headers={"Authorization": f"Bearer {customer_a_token}"}
        )
        # May succeed or fail depending on webhook URL, but should return proper format
        assert response.status_code in [200, 400]  # 400 if URL validation fails
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert "latency_ms" in data

    async def test_rate_limiting(
        self, client: AsyncClient, customer_a_token: str, test_integrations
    ):
        """Rate limiting kicks in after 5 requests."""
        integration_id = test_integrations['integration_a']

        # Make 6 requests
        for i in range(6):
            response = await client.post(
                f"/customer/integrations/{integration_id}/test",
                headers={"Authorization": f"Bearer {customer_a_token}"}
            )
            if i < 5:
                # First 5 should succeed (or fail for other reasons)
                assert response.status_code != 429
            else:
                # 6th should be rate limited
                assert response.status_code == 429
```

### 2.2 Create operator routes tests

Create `tests/api/test_operator_routes.py`:

```python
import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestOperatorDevices:
    """Test /operator/devices endpoints."""

    async def test_list_all_devices_requires_operator(
        self, client: AsyncClient, customer_a_token: str
    ):
        """Customer cannot access operator routes."""
        response = await client.get(
            "/operator/devices",
            headers={"Authorization": f"Bearer {customer_a_token}"}
        )
        assert response.status_code == 403

    async def test_list_all_devices(
        self, client: AsyncClient, operator_token: str, test_tenants
    ):
        """Operator sees all devices across tenants."""
        response = await client.get(
            "/operator/devices",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "devices" in data
        # Should see devices from both tenants
        tenant_ids = set(d["tenant_id"] for d in data["devices"])
        assert test_tenants["tenant_a"] in tenant_ids
        assert test_tenants["tenant_b"] in tenant_ids

    async def test_list_devices_with_tenant_filter(
        self, client: AsyncClient, operator_token: str, test_tenants
    ):
        """Operator can filter by tenant."""
        response = await client.get(
            f"/operator/devices?tenant_filter={test_tenants['tenant_a']}",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        for device in data["devices"]:
            assert device["tenant_id"] == test_tenants["tenant_a"]


class TestOperatorAudit:
    """Test operator audit logging."""

    async def test_operator_access_creates_audit_entry(
        self, client: AsyncClient, operator_token: str, db_pool
    ):
        """Operator access is logged."""
        # Make request
        await client.get(
            "/operator/devices",
            headers={"Authorization": f"Bearer {operator_token}"}
        )

        # Check audit log
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT user_id, action, rls_bypassed
                FROM operator_audit_log
                ORDER BY created_at DESC
                LIMIT 1
            """)
            assert len(rows) == 1
            assert rows[0]["action"] == "list_all_devices"
            assert rows[0]["rls_bypassed"] == True

    async def test_audit_log_endpoint_requires_admin(
        self, client: AsyncClient, operator_token: str
    ):
        """Regular operator cannot access audit log."""
        response = await client.get(
            "/operator/audit-log",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 403

    async def test_audit_log_endpoint(
        self, client: AsyncClient, operator_admin_token: str
    ):
        """Operator admin can access audit log."""
        response = await client.get(
            "/operator/audit-log",
            headers={"Authorization": f"Bearer {operator_admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestOperatorSettings:
    """Test /operator/settings endpoints."""

    async def test_settings_requires_admin(
        self, client: AsyncClient, operator_token: str
    ):
        """Regular operator cannot access settings."""
        response = await client.get(
            "/operator/settings",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 403

    async def test_settings_admin_access(
        self, client: AsyncClient, operator_admin_token: str
    ):
        """Operator admin can access settings."""
        response = await client.get(
            "/operator/settings",
            headers={"Authorization": f"Bearer {operator_admin_token}"}
        )
        assert response.status_code == 200
```

### 2.3 Create deprecated routes tests

Create `tests/api/test_deprecated_routes.py`:

```python
import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestDeprecatedRoutes:
    """Test deprecated routes return proper responses."""

    async def test_old_device_route_returns_410(self, client: AsyncClient):
        """Old /device/{id} route returns 410 Gone."""
        response = await client.get("/device/any-device-id")
        assert response.status_code == 410
        assert "deprecated" in response.text.lower() or "gone" in response.text.lower()
```

### 2.4 Add customer_viewer_token fixture

Update `tests/conftest.py` to add:

```python
@pytest.fixture
def customer_viewer_token():
    """Get valid JWT for customer viewer in tenant-a."""
    return "customer_viewer_token_placeholder"
```

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `tests/api/test_customer_routes.py` |
| CREATE | `tests/api/test_operator_routes.py` |
| CREATE | `tests/api/test_deprecated_routes.py` |
| MODIFY | `tests/conftest.py` |

## Acceptance Criteria

- [ ] All customer route tests defined
- [ ] All operator route tests defined
- [ ] Deprecated route test defined
- [ ] Tests cover authentication (401/403)
- [ ] Tests cover tenant isolation
- [ ] Tests cover SSRF blocking
- [ ] Tests cover rate limiting
- [ ] Tests cover audit logging

**Note**: Tests will fail until Task 003 provides real tokens. That's expected.

**Run tests** (expect failures without real tokens):
```bash
pytest tests/api/ -v --collect-only
```

## Commit

```
Add API integration tests

- Customer routes: devices, alerts, integrations, test delivery
- Operator routes: devices, audit log, settings
- Deprecated routes: 410 Gone check
- Tests for auth, tenant isolation, SSRF, rate limiting

Part of Phase 3.5: Testing Infrastructure
```
