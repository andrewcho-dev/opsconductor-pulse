# Task 003: Email Customer Routes

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Create/Modify".
> Verify your work against the acceptance criteria.
> Commit with the exact message in the "Commit" section when done.

---

## Context

Customers need CRUD routes to manage their email integrations, following the same patterns as webhook and SNMP integrations.

**Read first**:
- `services/ui_iot/routes/customer.py` (SNMP routes as pattern)
- `services/ui_iot/schemas/email.py` (from Task 001)

**Depends on**: Tasks 001, 002

---

## Task

### 3.1 Add email routes to customer.py

Add the following imports at the top of `services/ui_iot/routes/customer.py`:

```python
from schemas.email import (
    EmailIntegrationCreate,
    EmailIntegrationUpdate,
    EmailIntegrationResponse,
)
```

Add email integration routes after the SNMP routes:

```python
# ============================================================================
# EMAIL INTEGRATION ROUTES
# ============================================================================

@router.get("/integrations/email", response_model=list[EmailIntegrationResponse])
async def list_email_integrations():
    """List all email integrations for this tenant."""
    tenant_id = get_tenant_id()
    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            rows = await conn.fetch(
                """
                SELECT integration_id, tenant_id, name, email_config, email_recipients,
                       email_template, enabled, created_at, updated_at
                FROM integrations
                WHERE tenant_id = $1 AND type = 'email'
                ORDER BY created_at DESC
                """,
                tenant_id,
            )
    except Exception:
        logger.exception("Failed to fetch email integrations")
        raise HTTPException(status_code=500, detail="Internal server error")

    return [
        EmailIntegrationResponse(
            id=str(row["integration_id"]),
            tenant_id=row["tenant_id"],
            name=row["name"],
            smtp_host=(row["email_config"] or {}).get("smtp_host", ""),
            smtp_port=(row["email_config"] or {}).get("smtp_port", 587),
            smtp_tls=(row["email_config"] or {}).get("smtp_tls", True),
            from_address=(row["email_config"] or {}).get("from_address", ""),
            recipient_count=len((row["email_recipients"] or {}).get("to", [])),
            template_format=(row["email_template"] or {}).get("format", "html"),
            enabled=row["enabled"],
            created_at=row["created_at"].isoformat(),
            updated_at=row["updated_at"].isoformat(),
        )
        for row in rows
    ]


@router.get("/integrations/email/{integration_id}", response_model=EmailIntegrationResponse)
async def get_email_integration(integration_id: str):
    """Get a specific email integration."""
    tenant_id = get_tenant_id()
    try:
        UUID(integration_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Integration not found")

    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                SELECT integration_id, tenant_id, name, email_config, email_recipients,
                       email_template, enabled, created_at, updated_at
                FROM integrations
                WHERE integration_id = $1 AND tenant_id = $2 AND type = 'email'
                """,
                integration_id,
                tenant_id,
            )
    except Exception:
        logger.exception("Failed to fetch email integration")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not row:
        raise HTTPException(status_code=404, detail="Integration not found")

    return EmailIntegrationResponse(
        id=str(row["integration_id"]),
        tenant_id=row["tenant_id"],
        name=row["name"],
        smtp_host=(row["email_config"] or {}).get("smtp_host", ""),
        smtp_port=(row["email_config"] or {}).get("smtp_port", 587),
        smtp_tls=(row["email_config"] or {}).get("smtp_tls", True),
        from_address=(row["email_config"] or {}).get("from_address", ""),
        recipient_count=len((row["email_recipients"] or {}).get("to", [])),
        template_format=(row["email_template"] or {}).get("format", "html"),
        enabled=row["enabled"],
        created_at=row["created_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
    )


@router.post(
    "/integrations/email",
    response_model=EmailIntegrationResponse,
    status_code=201,
    dependencies=[Depends(require_customer_admin)],
)
async def create_email_integration(data: EmailIntegrationCreate):
    """Create a new email integration."""
    tenant_id = get_tenant_id()
    name = _validate_name(data.name)

    integration_id = str(uuid.uuid4())
    now = datetime.datetime.utcnow()

    email_config = data.smtp_config.model_dump()
    email_recipients = data.recipients.model_dump()
    email_template = data.template.model_dump() if data.template else {
        "subject_template": "[{severity}] {alert_type}: {device_id}",
        "format": "html"
    }

    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO integrations (
                    integration_id, tenant_id, name, type, email_config,
                    email_recipients, email_template, enabled, created_at, updated_at
                )
                VALUES ($1, $2, $3, 'email', $4, $5, $6, $7, $8, $9)
                RETURNING integration_id, tenant_id, name, email_config, email_recipients,
                          email_template, enabled, created_at, updated_at
                """,
                integration_id,
                tenant_id,
                name,
                json.dumps(email_config),
                json.dumps(email_recipients),
                json.dumps(email_template),
                data.enabled,
                now,
                now,
            )
    except Exception:
        logger.exception("Failed to create email integration")
        raise HTTPException(status_code=500, detail="Internal server error")

    return EmailIntegrationResponse(
        id=str(row["integration_id"]),
        tenant_id=row["tenant_id"],
        name=row["name"],
        smtp_host=email_config.get("smtp_host", ""),
        smtp_port=email_config.get("smtp_port", 587),
        smtp_tls=email_config.get("smtp_tls", True),
        from_address=email_config.get("from_address", ""),
        recipient_count=len(email_recipients.get("to", [])),
        template_format=email_template.get("format", "html"),
        enabled=row["enabled"],
        created_at=row["created_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
    )


@router.patch(
    "/integrations/email/{integration_id}",
    response_model=EmailIntegrationResponse,
    dependencies=[Depends(require_customer_admin)],
)
async def update_email_integration(integration_id: str, data: EmailIntegrationUpdate):
    """Update an email integration."""
    tenant_id = get_tenant_id()
    try:
        UUID(integration_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Integration not found")

    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates = []
    values = []
    param_idx = 1

    if "name" in update_data and update_data["name"] is not None:
        update_data["name"] = _validate_name(update_data["name"])
        updates.append(f"name = ${param_idx}")
        values.append(update_data["name"])
        param_idx += 1

    if "smtp_config" in update_data and update_data["smtp_config"] is not None:
        updates.append(f"email_config = ${param_idx}")
        values.append(json.dumps(data.smtp_config.model_dump()))
        param_idx += 1

    if "recipients" in update_data and update_data["recipients"] is not None:
        updates.append(f"email_recipients = ${param_idx}")
        values.append(json.dumps(data.recipients.model_dump()))
        param_idx += 1

    if "template" in update_data and update_data["template"] is not None:
        updates.append(f"email_template = ${param_idx}")
        values.append(json.dumps(data.template.model_dump()))
        param_idx += 1

    if "enabled" in update_data and update_data["enabled"] is not None:
        updates.append(f"enabled = ${param_idx}")
        values.append(update_data["enabled"])
        param_idx += 1

    updates.append(f"updated_at = ${param_idx}")
    values.append(datetime.datetime.utcnow())
    param_idx += 1

    values.extend([integration_id, tenant_id])

    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            row = await conn.fetchrow(
                f"""
                UPDATE integrations
                SET {", ".join(updates)}
                WHERE integration_id = ${param_idx} AND tenant_id = ${param_idx + 1} AND type = 'email'
                RETURNING integration_id, tenant_id, name, email_config, email_recipients,
                          email_template, enabled, created_at, updated_at
                """,
                *values,
            )
    except Exception:
        logger.exception("Failed to update email integration")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not row:
        raise HTTPException(status_code=404, detail="Integration not found")

    email_config = row["email_config"] or {}
    email_recipients = row["email_recipients"] or {}
    email_template = row["email_template"] or {}

    return EmailIntegrationResponse(
        id=str(row["integration_id"]),
        tenant_id=row["tenant_id"],
        name=row["name"],
        smtp_host=email_config.get("smtp_host", ""),
        smtp_port=email_config.get("smtp_port", 587),
        smtp_tls=email_config.get("smtp_tls", True),
        from_address=email_config.get("from_address", ""),
        recipient_count=len(email_recipients.get("to", [])),
        template_format=email_template.get("format", "html"),
        enabled=row["enabled"],
        created_at=row["created_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
    )


@router.delete(
    "/integrations/email/{integration_id}",
    status_code=204,
    dependencies=[Depends(require_customer_admin)],
)
async def delete_email_integration(integration_id: str):
    """Delete an email integration."""
    tenant_id = get_tenant_id()
    try:
        UUID(integration_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Integration not found")

    try:
        p = await get_pool()
        async with tenant_connection(p, tenant_id) as conn:
            result = await conn.execute(
                """
                DELETE FROM integrations
                WHERE integration_id = $1 AND tenant_id = $2 AND type = 'email'
                """,
                integration_id,
                tenant_id,
            )
    except Exception:
        logger.exception("Failed to delete email integration")
        raise HTTPException(status_code=500, detail="Internal server error")

    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Integration not found")

    return Response(status_code=204)
```

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| MODIFY | `services/ui_iot/routes/customer.py` |

---

## Acceptance Criteria

- [ ] GET /customer/integrations/email lists email integrations
- [ ] GET /customer/integrations/email/{id} returns single integration
- [ ] POST /customer/integrations/email creates integration
- [ ] PATCH /customer/integrations/email/{id} updates integration
- [ ] DELETE /customer/integrations/email/{id} deletes integration
- [ ] All routes require customer_admin for write operations
- [ ] Tenant isolation enforced

**Test**:
```bash
# Get token
TOKEN=$(curl -s -X POST "http://localhost:8180/realms/pulse/protocol/openid-connect/token" \
  -d "grant_type=password&client_id=pulse-ui&username=customer1&password=test123" | jq -r '.access_token')

# List (should be empty)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/customer/integrations/email

# Create
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "name": "Alert Emails",
    "smtp_config": {
      "smtp_host": "smtp.example.com",
      "smtp_port": 587,
      "smtp_tls": true,
      "from_address": "alerts@example.com"
    },
    "recipients": {
      "to": ["admin@example.com"]
    }
  }' \
  http://localhost:8080/customer/integrations/email
```

---

## Commit

```
Add email integration customer routes

- GET/POST/PATCH/DELETE for email integrations
- Tenant isolation via JWT
- customer_admin required for writes
- Follows SNMP route patterns

Part of Phase 6: Email Delivery
```
