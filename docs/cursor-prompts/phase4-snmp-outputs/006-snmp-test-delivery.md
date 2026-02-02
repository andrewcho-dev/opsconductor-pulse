# Task 006: SNMP Test Delivery Endpoint

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Create/Modify".
> Verify your work against the acceptance criteria.
> Commit with the exact message in the "Commit" section when done.

---

## Context

Customers need to test their SNMP integrations before relying on them for production alerts. The test endpoint sends a real SNMP trap marked as a test.

**Read first**:
- `services/ui_iot/routes/customer.py` (existing routes)
- `services/ui_iot/services/alert_dispatcher.py` (from Task 005)

**Depends on**: Tasks 003, 005

---

## Task

### 6.1 Add test delivery endpoint

Add to `services/ui_iot/routes/customer.py`:

```python
from services.ui_iot.services.alert_dispatcher import dispatch_to_integration, AlertPayload


@router.post("/integrations/snmp/{integration_id}/test")
async def test_snmp_integration(
    integration_id: str,
    tenant_id: str = Depends(get_tenant_id),
    role: str = Depends(get_user_role),
    db = Depends(get_tenant_connection),
):
    """Send a test SNMP trap."""
    if role not in ("customer_admin",):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        uuid.UUID(integration_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Integration not found")

    query = """
        SELECT id, tenant_id, name, type, snmp_host, snmp_port,
               snmp_config, snmp_oid_prefix, enabled
        FROM integrations
        WHERE id = $1 AND tenant_id = $2 AND type = 'snmp'
    """
    row = await db.fetchrow(query, integration_id, tenant_id)
    if not row:
        raise HTTPException(status_code=404, detail="Integration not found")

    test_alert = AlertPayload(
        alert_id=f"test-{int(datetime.utcnow().timestamp())}",
        device_id="test-device",
        tenant_id=tenant_id,
        severity="info",
        message="Test trap from OpsConductor Pulse",
        timestamp=datetime.utcnow(),
    )

    integration = {
        "id": row["id"],
        "name": row["name"],
        "type": row["type"],
        "snmp_host": row["snmp_host"],
        "snmp_port": row["snmp_port"],
        "snmp_config": row["snmp_config"],
        "snmp_oid_prefix": row["snmp_oid_prefix"],
        "enabled": True,
    }

    result = await dispatch_to_integration(test_alert, integration)

    return {
        "success": result.success,
        "integration_id": integration_id,
        "integration_name": row["name"],
        "destination": f"{row['snmp_host']}:{row['snmp_port']}",
        "error": result.error,
        "duration_ms": result.duration_ms,
    }


@router.post("/integrations/{integration_id}/test")
async def test_integration(
    integration_id: str,
    tenant_id: str = Depends(get_tenant_id),
    role: str = Depends(get_user_role),
    db = Depends(get_tenant_connection),
):
    """Send a test delivery to any integration type."""
    if role not in ("customer_admin",):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        uuid.UUID(integration_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Integration not found")

    query = """
        SELECT id, tenant_id, name, type, webhook_url, webhook_secret,
               snmp_host, snmp_port, snmp_config, snmp_oid_prefix, enabled
        FROM integrations
        WHERE id = $1 AND tenant_id = $2
    """
    row = await db.fetchrow(query, integration_id, tenant_id)
    if not row:
        raise HTTPException(status_code=404, detail="Integration not found")

    test_alert = AlertPayload(
        alert_id=f"test-{int(datetime.utcnow().timestamp())}",
        device_id="test-device",
        tenant_id=tenant_id,
        severity="info",
        message="Test delivery from OpsConductor Pulse",
        timestamp=datetime.utcnow(),
    )

    integration = dict(row)
    integration["enabled"] = True

    result = await dispatch_to_integration(test_alert, integration)

    response = {
        "success": result.success,
        "integration_id": integration_id,
        "integration_name": row["name"],
        "integration_type": row["type"],
        "error": result.error,
        "duration_ms": result.duration_ms,
    }

    if row["type"] == "webhook":
        response["destination"] = row["webhook_url"]
    elif row["type"] == "snmp":
        response["destination"] = f"{row['snmp_host']}:{row['snmp_port']}"

    return response
```

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| MODIFY | `services/ui_iot/routes/customer.py` |

---

## Acceptance Criteria

- [ ] POST /customer/integrations/snmp/{id}/test sends test trap
- [ ] POST /customer/integrations/{id}/test works for any type
- [ ] Response includes success/error details
- [ ] customer_admin role required

**Test**:
```bash
TOKEN=$(curl -s -X POST "http://localhost:8180/realms/pulse/protocol/openid-connect/token" \
  -d "grant_type=password&client_id=pulse-ui&username=customer1&password=test123" | jq -r '.access_token')

# Create integration first, then test
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/customer/integrations/snmp/{id}/test
```

---

## Commit

```
Add SNMP test delivery endpoint

- POST /customer/integrations/snmp/{id}/test
- POST /customer/integrations/{id}/test (unified)
- customer_admin role required

Part of Phase 4: SNMP and Alternative Outputs
```
