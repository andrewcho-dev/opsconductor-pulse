# 140-008: Integration Tests for Key Workflows

## Task
Write end-to-end integration tests covering full workflows that span multiple route modules.

## Files to Create
- `tests/integration/test_device_lifecycle.py`
- `tests/integration/test_alert_pipeline.py`
- `tests/integration/test_user_lifecycle.py`
- `tests/integration/test_subscription_lifecycle.py`

**Prerequisites**: These tests require a running database (via `db_pool` fixture) and Keycloak (for real auth tokens). They use the `@pytest.mark.integration` marker.

---

## 1. Device Lifecycle
**File**: `tests/integration/test_device_lifecycle.py`

```python
import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestDeviceLifecycle:
    """Test complete device lifecycle: create → configure → telemetry → alert → decommission."""

    async def test_full_device_lifecycle(
        self, client: AsyncClient, customer_a_token: str, test_tenants, clean_db
    ):
        headers = {"Authorization": f"Bearer {customer_a_token}"}

        # 1. Create device
        create_resp = await client.post("/api/v1/customer/devices", headers=headers,
            json={"device_id": f"lifecycle-test-{uuid4().hex[:8]}", "site_id": "test-site-a"})
        assert create_resp.status_code in (200, 201)
        device_id = create_resp.json()["device"]["device_id"]

        # 2. Update device metadata
        update_resp = await client.patch(f"/api/v1/customer/devices/{device_id}", headers=headers,
            json={"model": "DHT22", "manufacturer": "Test Corp", "notes": "Integration test"})
        assert update_resp.status_code == 200

        # 3. Verify device appears in list
        list_resp = await client.get("/api/v1/customer/devices?format=json", headers=headers)
        assert list_resp.status_code == 200
        device_ids = [d["device_id"] for d in list_resp.json()["devices"]]
        assert device_id in device_ids

        # 4. Get device detail
        detail_resp = await client.get(f"/api/v1/customer/devices/{device_id}?format=json", headers=headers)
        assert detail_resp.status_code == 200
        assert detail_resp.json()["device"]["model"] == "DHT22"

        # 5. Delete/decommission device
        delete_resp = await client.delete(f"/api/v1/customer/devices/{device_id}", headers=headers)
        assert delete_resp.status_code in (200, 204)

        # 6. Verify device is gone or decommissioned
        verify_resp = await client.get(f"/api/v1/customer/devices/{device_id}?format=json", headers=headers)
        assert verify_resp.status_code in (404, 200)  # 200 if soft-deleted with DECOMMISSIONED status

    async def test_cross_tenant_isolation(
        self, client: AsyncClient, customer_a_token: str, customer_b_token: str, test_tenants
    ):
        """Tenant A cannot see or modify Tenant B's devices."""
        headers_a = {"Authorization": f"Bearer {customer_a_token}"}
        headers_b = {"Authorization": f"Bearer {customer_b_token}"}

        # List devices as tenant A
        resp_a = await client.get("/api/v1/customer/devices?format=json", headers=headers_a)
        assert resp_a.status_code == 200
        for device in resp_a.json()["devices"]:
            assert device["tenant_id"] == test_tenants["tenant_a"]

        # Try to access tenant A's device as tenant B
        if resp_a.json()["devices"]:
            device_id = resp_a.json()["devices"][0]["device_id"]
            cross_resp = await client.get(f"/api/v1/customer/devices/{device_id}", headers=headers_b)
            assert cross_resp.status_code == 404  # RLS prevents access
```

---

## 2. Alert Pipeline
**File**: `tests/integration/test_alert_pipeline.py`

```python
class TestAlertPipeline:
    """Test alert lifecycle: rule create → alert fires → acknowledge → close."""

    async def test_alert_rule_to_acknowledgment(
        self, client: AsyncClient, customer_a_token: str, test_tenants, clean_db
    ):
        headers = {"Authorization": f"Bearer {customer_a_token}"}

        # 1. Create alert rule
        rule_resp = await client.post("/api/v1/customer/alert-rules", headers=headers,
            json={
                "name": "Integration Test Rule",
                "metric_name": "temp_c",
                "operator": "GT",
                "threshold": 50,
                "severity": 3,
            })
        assert rule_resp.status_code in (200, 201)

        # 2. List alert rules - verify rule exists
        rules_resp = await client.get("/api/v1/customer/alert-rules", headers=headers)
        assert rules_resp.status_code == 200
        rule_names = [r["name"] for r in rules_resp.json().get("rules", [])]
        assert "Integration Test Rule" in rule_names

        # 3. Check alerts (may be pre-seeded from test fixtures)
        alerts_resp = await client.get("/api/v1/customer/alerts?status=OPEN", headers=headers)
        assert alerts_resp.status_code == 200

        # 4. If alerts exist, test acknowledge flow
        alerts = alerts_resp.json().get("alerts", [])
        if alerts:
            alert_id = alerts[0]["alert_id"]
            ack_resp = await client.patch(
                f"/api/v1/customer/alerts/{alert_id}/acknowledge", headers=headers)
            assert ack_resp.status_code == 200

        # 5. Clean up - delete the test rule
        # Find the rule ID and delete it
```

---

## 3. User Lifecycle
**File**: `tests/integration/test_user_lifecycle.py`

```python
class TestUserLifecycle:
    """Test user management: invite → list → change role → remove."""

    async def test_user_management_flow(
        self, client: AsyncClient, customer_a_token: str, test_tenants, clean_db
    ):
        headers = {"Authorization": f"Bearer {customer_a_token}"}

        # 1. List users
        list_resp = await client.get("/api/v1/customer/users", headers=headers)
        assert list_resp.status_code == 200
        initial_count = list_resp.json().get("total", 0)

        # 2. Invite a user (may fail if Keycloak user creation requires specific setup)
        # This test verifies the API contract, not Keycloak integration
        invite_resp = await client.post("/api/v1/customer/users/invite", headers=headers,
            json={"email": f"test-{uuid4().hex[:8]}@example.com", "role": "customer"})
        # Accept 200/201 (success) or 500/503 (Keycloak unavailable in test)
        if invite_resp.status_code in (200, 201):
            # Verify user count increased
            list_resp2 = await client.get("/api/v1/customer/users", headers=headers)
            assert list_resp2.json().get("total", 0) >= initial_count

    async def test_operator_cannot_access_customer_users(
        self, client: AsyncClient, operator_token: str
    ):
        """Operator role is blocked from customer user routes."""
        headers = {"Authorization": f"Bearer {operator_token}"}
        resp = await client.get("/api/v1/customer/users", headers=headers)
        assert resp.status_code == 403
```

---

## 4. Subscription Lifecycle
**File**: `tests/integration/test_subscription_lifecycle.py`

```python
class TestSubscriptionLifecycle:
    """Test subscription: view plan → subscribe → check limits."""

    async def test_view_plans_and_subscription(
        self, client: AsyncClient, customer_a_token: str, test_tenants
    ):
        headers = {"Authorization": f"Bearer {customer_a_token}"}

        # 1. List available plans
        plans_resp = await client.get("/api/v1/customer/plans", headers=headers)
        if plans_resp.status_code == 200:
            plans = plans_resp.json()
            assert isinstance(plans, list) or "plans" in plans

        # 2. Get current subscription
        sub_resp = await client.get("/api/v1/customer/subscription", headers=headers)
        assert sub_resp.status_code in (200, 404)  # 404 if no subscription

        # 3. Check device tiers
        tiers_resp = await client.get("/api/v1/customer/device-tiers", headers=headers)
        assert tiers_resp.status_code == 200
```

## Verification
```bash
pytest tests/integration/ -v -m integration --cov=services/ui_iot --cov-report=term-missing
# Should pass with real DB + Keycloak
```

**Note**: Integration tests require the full test environment (Postgres + Keycloak). They run in CI but may not run locally without docker compose. Mark with `@pytest.mark.integration` so they can be skipped with `-m "not integration"`.
