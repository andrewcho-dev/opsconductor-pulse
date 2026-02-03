# Task 006: Email Test Delivery Endpoint

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Create/Modify".
> Verify your work against the acceptance criteria.
> Commit with the exact message in the "Commit" section when done.

---

## Context

Customers need to test their email integrations before relying on them for production alerts. The test endpoint sends a real email marked as a test.

**Read first**:
- `services/ui_iot/routes/customer.py` (SNMP test endpoint as pattern)
- `services/ui_iot/services/email_sender.py` (from Task 002)

**Depends on**: Tasks 002, 003

---

## Task

### 6.1 Add test delivery endpoint

Add to `services/ui_iot/routes/customer.py`:

```python
from services.email_sender import send_alert_email

@router.post(
    "/integrations/email/{integration_id}/test",
    dependencies=[Depends(require_customer_admin)],
)
async def test_email_integration(integration_id: str):
    """Send a test email."""
    tenant_id = get_tenant_id()

    try:
        UUID(integration_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Integration not found")

    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            # Rate limit
            allowed, _ = await check_and_increment_rate_limit(
                conn,
                tenant_id=tenant_id,
                action="test_delivery",
                limit=5,
                window_seconds=60,
            )
            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded. Maximum 5 test deliveries per minute.",
                )

            row = await conn.fetchrow(
                """
                SELECT integration_id, tenant_id, name, type, email_config,
                       email_recipients, email_template, enabled
                FROM integrations
                WHERE integration_id = $1 AND tenant_id = $2 AND type = 'email'
                """,
                integration_id,
                tenant_id,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch email integration for test")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not row:
        raise HTTPException(status_code=404, detail="Integration not found")

    email_config = row["email_config"] or {}
    email_recipients = row["email_recipients"] or {}
    email_template = row["email_template"] or {}

    # Send test email
    result = await send_alert_email(
        smtp_host=email_config.get("smtp_host", ""),
        smtp_port=email_config.get("smtp_port", 587),
        smtp_user=email_config.get("smtp_user"),
        smtp_password=email_config.get("smtp_password"),
        smtp_tls=email_config.get("smtp_tls", True),
        from_address=email_config.get("from_address", ""),
        from_name=email_config.get("from_name", "OpsConductor Alerts"),
        recipients=email_recipients,
        alert_id=f"test-{int(datetime.datetime.utcnow().timestamp())}",
        device_id="test-device",
        tenant_id=tenant_id,
        severity="info",
        message="This is a test email from OpsConductor Pulse. If you received this, your email integration is working correctly.",
        alert_type="TEST_ALERT",
        timestamp=datetime.datetime.utcnow(),
        subject_template=email_template.get("subject_template"),
        body_template=email_template.get("body_template"),
        body_format=email_template.get("format", "html"),
    )

    return {
        "success": result.success,
        "integration_id": integration_id,
        "integration_name": row["name"],
        "recipients_count": result.recipients_count,
        "error": result.error,
        "duration_ms": result.duration_ms,
    }
```

### 6.2 Update unified test endpoint

Update the existing `/integrations/{integration_id}/test` endpoint to handle email:

```python
@router.post("/integrations/{integration_id}/test", dependencies=[Depends(require_customer_admin)])
async def test_integration_delivery(integration_id: str):
    """Send a test delivery to any integration type."""
    tenant_id = get_tenant_id()

    try:
        UUID(integration_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Integration not found")

    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            allowed, _ = await check_and_increment_rate_limit(
                conn,
                tenant_id=tenant_id,
                action="test_delivery",
                limit=5,
                window_seconds=60,
            )
            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded. Maximum 5 test deliveries per minute.",
                )

            row = await conn.fetchrow(
                """
                SELECT integration_id, tenant_id, name, type,
                       config_json->>'url' AS webhook_url,
                       snmp_host, snmp_port, snmp_config, snmp_oid_prefix,
                       email_config, email_recipients, email_template,
                       enabled
                FROM integrations
                WHERE integration_id = $1 AND tenant_id = $2
                """,
                integration_id,
                tenant_id,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch integration for test")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not row:
        raise HTTPException(status_code=404, detail="Integration not found")

    integration_type = row["type"]
    now = datetime.datetime.utcnow()

    if integration_type == "email":
        # Email delivery
        email_config = row["email_config"] or {}
        email_recipients = row["email_recipients"] or {}
        email_template = row["email_template"] or {}

        result = await send_alert_email(
            smtp_host=email_config.get("smtp_host", ""),
            smtp_port=email_config.get("smtp_port", 587),
            smtp_user=email_config.get("smtp_user"),
            smtp_password=email_config.get("smtp_password"),
            smtp_tls=email_config.get("smtp_tls", True),
            from_address=email_config.get("from_address", ""),
            from_name=email_config.get("from_name", "OpsConductor Alerts"),
            recipients=email_recipients,
            alert_id=f"test-{int(now.timestamp())}",
            device_id="test-device",
            tenant_id=tenant_id,
            severity="info",
            message="Test delivery from OpsConductor Pulse",
            alert_type="TEST_ALERT",
            timestamp=now,
            subject_template=email_template.get("subject_template"),
            body_template=email_template.get("body_template"),
            body_format=email_template.get("format", "html"),
        )

        return {
            "success": result.success,
            "integration_id": integration_id,
            "integration_name": row["name"],
            "integration_type": "email",
            "destination": f"{len((email_recipients.get('to', [])))} recipients",
            "error": result.error,
            "duration_ms": result.duration_ms,
        }

    elif integration_type == "snmp":
        # SNMP delivery (existing code)
        test_alert = AlertPayload(
            alert_id=f"test-{int(now.timestamp())}",
            device_id="test-device",
            tenant_id=tenant_id,
            severity="info",
            message="Test delivery from OpsConductor Pulse",
            timestamp=now,
        )

        integration_dict = dict(row)
        integration_dict["enabled"] = True

        result = await dispatch_to_integration(test_alert, integration_dict)

        return {
            "success": result.success,
            "integration_id": integration_id,
            "integration_name": row["name"],
            "integration_type": "snmp",
            "destination": f"{row['snmp_host']}:{row['snmp_port']}",
            "error": result.error,
            "duration_ms": result.duration_ms,
        }

    else:
        # Webhook delivery (existing code)
        test_alert = AlertPayload(
            alert_id=f"test-{int(now.timestamp())}",
            device_id="test-device",
            tenant_id=tenant_id,
            severity="info",
            message="Test delivery from OpsConductor Pulse",
            timestamp=now,
        )

        integration_dict = dict(row)
        integration_dict["enabled"] = True
        integration_dict["webhook_url"] = row["webhook_url"]

        result = await dispatch_to_integration(test_alert, integration_dict)

        return {
            "success": result.success,
            "integration_id": integration_id,
            "integration_name": row["name"],
            "integration_type": "webhook",
            "destination": row["webhook_url"],
            "error": result.error,
            "duration_ms": result.duration_ms,
        }
```

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| MODIFY | `services/ui_iot/routes/customer.py` |

---

## Acceptance Criteria

- [ ] POST /customer/integrations/email/{id}/test sends test email
- [ ] POST /customer/integrations/{id}/test works for email type
- [ ] Response includes success/error and recipient count
- [ ] Rate limited to 5 per minute
- [ ] customer_admin role required

**Test**:
```bash
TOKEN=$(curl -s -X POST "http://localhost:8180/realms/pulse/protocol/openid-connect/token" \
  -d "grant_type=password&client_id=pulse-ui&username=customer1&password=test123" | jq -r '.access_token')

# Create email integration first, then test
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/customer/integrations/email/{id}/test
```

---

## Commit

```
Add email test delivery endpoint

- POST /customer/integrations/email/{id}/test
- Update unified test endpoint for email
- Rate limited to 5 per minute
- customer_admin required

Part of Phase 6: Email Delivery
```
