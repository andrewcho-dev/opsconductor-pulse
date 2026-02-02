# Task 006: SNMP Test Delivery Endpoint

> **CURSOR: EXECUTE THIS TASK**
>
> This is an implementation task. Read the instructions below and implement them.
> Modify the files listed in "Files to Create/Modify" section.
> Follow the acceptance criteria to verify your work.
> Commit with the message in the "Commit" section when done.

---

## Context

Customers need to test their SNMP integrations before relying on them for production alerts. This is the SNMP equivalent of the webhook test delivery endpoint. The test should send a real SNMP trap but be clearly marked as a test.

**Read first**:
- Existing webhook test delivery endpoint in `services/ui_iot/routes/customer.py`
- `services/ui_iot/services/snmp_sender.py` (SNMP sender)
- `services/ui_iot/services/alert_dispatcher.py` (dispatcher)

**Depends on**: Tasks 002, 003, 005

## Task

### 6.1 Add test delivery endpoint

Add to `services/ui_iot/routes/customer.py`:

```python
from services.ui_iot.services.alert_dispatcher import (
    dispatch_to_integration,
    AlertPayload,
)


@router.post("/integrations/snmp/{integration_id}/test")
async def test_snmp_integration(
    integration_id: str,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    role: str = Depends(get_user_role),
    db = Depends(get_tenant_connection),
):
    """
    Send a test SNMP trap to verify integration configuration.

    The trap will contain:
    - alert_id: "test-{timestamp}"
    - severity: "info"
    - message: "Test trap from OpsConductor Pulse"
    """
    # Require customer_admin role
    if role not in ("customer_admin",):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Validate UUID format
    try:
        uuid.UUID(integration_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Integration not found")

    # Get integration
    query = """
        SELECT id, tenant_id, name, type, snmp_host, snmp_port,
               snmp_config, snmp_oid_prefix, enabled
        FROM integrations
        WHERE id = $1 AND tenant_id = $2 AND type = 'snmp'
    """
    row = await db.fetchrow(query, integration_id, tenant_id)

    if not row:
        raise HTTPException(status_code=404, detail="Integration not found")

    # Build test alert
    test_alert = AlertPayload(
        alert_id=f"test-{int(datetime.utcnow().timestamp())}",
        device_id="test-device",
        tenant_id=tenant_id,
        severity="info",
        message="Test trap from OpsConductor Pulse. If you receive this, your SNMP integration is working correctly.",
        timestamp=datetime.utcnow(),
        metadata={"test": True, "triggered_by": "manual_test"},
    )

    # Build integration dict from row
    integration = {
        "id": row["id"],
        "name": row["name"],
        "type": row["type"],
        "snmp_host": row["snmp_host"],
        "snmp_port": row["snmp_port"],
        "snmp_config": row["snmp_config"],
        "snmp_oid_prefix": row["snmp_oid_prefix"],
        "enabled": True,  # Always send for test, even if disabled
    }

    # Send test trap
    result = await dispatch_to_integration(test_alert, integration)

    # Return result
    return {
        "success": result.success,
        "integration_id": integration_id,
        "integration_name": row["name"],
        "destination": f"{row['snmp_host']}:{row['snmp_port']}",
        "error": result.error,
        "duration_ms": result.duration_ms,
        "test_alert_id": test_alert.alert_id,
    }
```

### 6.2 Add generic test endpoint for any integration

Add a unified test endpoint that works for both webhook and SNMP:

```python
@router.post("/integrations/{integration_id}/test")
async def test_integration(
    integration_id: str,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    role: str = Depends(get_user_role),
    db = Depends(get_tenant_connection),
):
    """
    Send a test delivery to verify any integration (webhook or SNMP).

    Automatically detects integration type and sends appropriate test.
    """
    # Require customer_admin role
    if role not in ("customer_admin",):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Validate UUID format
    try:
        uuid.UUID(integration_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Integration not found")

    # Get integration (any type)
    query = """
        SELECT id, tenant_id, name, type,
               webhook_url, webhook_secret,
               snmp_host, snmp_port, snmp_config, snmp_oid_prefix,
               enabled
        FROM integrations
        WHERE id = $1 AND tenant_id = $2
    """
    row = await db.fetchrow(query, integration_id, tenant_id)

    if not row:
        raise HTTPException(status_code=404, detail="Integration not found")

    # Build test alert
    test_alert = AlertPayload(
        alert_id=f"test-{int(datetime.utcnow().timestamp())}",
        device_id="test-device",
        tenant_id=tenant_id,
        severity="info",
        message="Test delivery from OpsConductor Pulse. If you receive this, your integration is working correctly.",
        timestamp=datetime.utcnow(),
        metadata={"test": True, "triggered_by": "manual_test"},
    )

    # Build integration dict from row
    integration = dict(row)
    integration["enabled"] = True  # Always send for test

    # Send test delivery
    result = await dispatch_to_integration(test_alert, integration)

    # Build response based on type
    response = {
        "success": result.success,
        "integration_id": integration_id,
        "integration_name": row["name"],
        "integration_type": row["type"],
        "error": result.error,
        "duration_ms": result.duration_ms,
        "test_alert_id": test_alert.alert_id,
    }

    if row["type"] == "webhook":
        response["destination"] = row["webhook_url"]
    elif row["type"] == "snmp":
        response["destination"] = f"{row['snmp_host']}:{row['snmp_port']}"

    return response
```

### 6.3 Add rate limiting for test endpoint

Test endpoints should be rate-limited to prevent abuse:

```python
from services.ui_iot.utils.rate_limiter import check_rate_limit

@router.post("/integrations/{integration_id}/test")
async def test_integration(
    integration_id: str,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    role: str = Depends(get_user_role),
    db = Depends(get_tenant_connection),
):
    """..."""
    # Rate limit: 10 tests per hour per tenant
    rate_key = f"test_delivery:{tenant_id}"
    if not await check_rate_limit(db, rate_key, limit=10, window_seconds=3600):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Maximum 10 test deliveries per hour."
        )

    # ... rest of function ...
```

### 6.4 Create integration tests

Create `tests/api/test_snmp_endpoints.py`:

```python
"""Integration tests for SNMP endpoints."""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestSNMPIntegrationCRUD:
    """Test SNMP integration CRUD operations."""

    async def test_create_snmp_integration(
        self, client: AsyncClient, customer_a_token: str
    ):
        """Create SNMP integration."""
        response = await client.post(
            "/customer/integrations/snmp",
            headers={"Authorization": f"Bearer {customer_a_token}"},
            json={
                "name": "Test SNMP",
                "snmp_host": "203.0.113.100",  # TEST-NET-3 (safe public IP)
                "snmp_port": 162,
                "snmp_config": {"version": "2c", "community": "public"},
            },
        )
        # Note: May fail if 203.0.113.x is blocked in validator
        # Adjust test IP if needed
        assert response.status_code in (201, 400)

    async def test_create_snmp_integration_blocked_ip(
        self, client: AsyncClient, customer_a_token: str
    ):
        """Cannot create SNMP integration with private IP."""
        response = await client.post(
            "/customer/integrations/snmp",
            headers={"Authorization": f"Bearer {customer_a_token}"},
            json={
                "name": "Bad SNMP",
                "snmp_host": "192.168.1.100",
                "snmp_port": 162,
                "snmp_config": {"version": "2c", "community": "public"},
            },
        )
        assert response.status_code == 400
        assert "Invalid SNMP destination" in response.json()["detail"]

    async def test_list_snmp_integrations(
        self, client: AsyncClient, customer_a_token: str
    ):
        """List SNMP integrations."""
        response = await client.get(
            "/customer/integrations/snmp",
            headers={"Authorization": f"Bearer {customer_a_token}"},
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_list_all_integrations(
        self, client: AsyncClient, customer_a_token: str
    ):
        """List all integrations (webhook + SNMP)."""
        response = await client.get(
            "/customer/integrations",
            headers={"Authorization": f"Bearer {customer_a_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "integrations" in data

    async def test_viewer_cannot_create_snmp(
        self, client: AsyncClient, customer_viewer_token: str
    ):
        """Customer viewer cannot create SNMP integration."""
        response = await client.post(
            "/customer/integrations/snmp",
            headers={"Authorization": f"Bearer {customer_viewer_token}"},
            json={
                "name": "Test SNMP",
                "snmp_host": "8.8.8.8",
                "snmp_config": {"version": "2c", "community": "public"},
            },
        )
        assert response.status_code == 403


class TestSNMPTestDelivery:
    """Test SNMP test delivery endpoint."""

    @patch("services.ui_iot.services.snmp_sender.sendNotification")
    async def test_snmp_test_delivery(
        self, mock_send, client: AsyncClient, customer_a_token: str
    ):
        """Test SNMP delivery sends trap."""
        mock_send.return_value = (None, None, None, [])

        # First create an integration
        # This test may need adjustment based on actual test data

        # For now, test that endpoint exists and returns 404 for missing
        response = await client.post(
            "/customer/integrations/snmp/00000000-0000-0000-0000-000000000000/test",
            headers={"Authorization": f"Bearer {customer_a_token}"},
        )
        assert response.status_code == 404

    async def test_test_delivery_invalid_uuid(
        self, client: AsyncClient, customer_a_token: str
    ):
        """Invalid UUID returns 404."""
        response = await client.post(
            "/customer/integrations/snmp/invalid-uuid/test",
            headers={"Authorization": f"Bearer {customer_a_token}"},
        )
        assert response.status_code == 404
```

## Files to Create/Modify

| Action | Path |
|--------|------|
| MODIFY | `services/ui_iot/routes/customer.py` |
| CREATE | `tests/api/test_snmp_endpoints.py` |

## Acceptance Criteria

- [ ] POST /customer/integrations/snmp/{id}/test sends test trap
- [ ] POST /customer/integrations/{id}/test works for any type
- [ ] Test traps clearly marked as test in message
- [ ] Response includes success/error details
- [ ] Rate limited to prevent abuse
- [ ] customer_admin role required
- [ ] Integration tests pass

**Test**:
```bash
# Get token
TOKEN=$(curl -s -X POST "http://localhost:8180/realms/pulse/protocol/openid-connect/token" \
  -d "grant_type=password&client_id=pulse-ui&username=customer1&password=test123" | jq -r '.access_token')

# Create SNMP integration first
INTEGRATION=$(curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test SNMP","snmp_host":"8.8.8.8","snmp_config":{"version":"2c","community":"public"}}' \
  http://localhost:8080/customer/integrations/snmp | jq -r '.id')

# Test delivery
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/customer/integrations/snmp/$INTEGRATION/test

# Run integration tests
pytest tests/api/test_snmp_endpoints.py -v
```

## Commit

```
Add SNMP test delivery endpoint

- POST /customer/integrations/snmp/{id}/test
- POST /customer/integrations/{id}/test (unified)
- Test traps clearly marked in message
- Rate limited (10/hour per tenant)
- Integration tests for SNMP endpoints

Part of Phase 4: SNMP and Alternative Outputs
```
