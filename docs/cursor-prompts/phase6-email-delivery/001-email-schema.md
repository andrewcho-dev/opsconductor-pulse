# Task 001: Email Integration Schema

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Create/Modify".
> Verify your work against the acceptance criteria.
> Commit with the exact message in the "Commit" section when done.

---

## Context

We need to extend the integrations table to support email delivery alongside webhooks and SNMP. Email integrations require SMTP configuration and recipient settings.

**Read first**:
- `db/migrations/001_webhook_delivery_v1.sql` (integrations table)
- `db/migrations/011_snmp_integrations.sql` (how SNMP was added)
- `services/ui_iot/routes/customer.py` (existing integration patterns)

**Depends on**: Phase 5 completion

---

## Task

### 1.1 Create email schema migration

Create `db/migrations/013_email_integrations.sql`:

```sql
-- Add email support to integrations table
-- Migration: 013_email_integrations.sql

-- Update type constraint to include 'email'
ALTER TABLE integrations DROP CONSTRAINT IF EXISTS integrations_type_check;
ALTER TABLE integrations ADD CONSTRAINT integrations_type_check
    CHECK (type IN ('webhook', 'snmp', 'email'));

-- Add email configuration columns
ALTER TABLE integrations ADD COLUMN IF NOT EXISTS email_config JSONB;
-- email_config structure:
-- {
--   "smtp_host": "smtp.example.com",
--   "smtp_port": 587,
--   "smtp_user": "user@example.com",
--   "smtp_password": "encrypted-or-placeholder",
--   "smtp_tls": true,
--   "from_address": "alerts@example.com",
--   "from_name": "OpsConductor Alerts"
-- }

ALTER TABLE integrations ADD COLUMN IF NOT EXISTS email_recipients JSONB;
-- email_recipients structure:
-- {
--   "to": ["admin@customer.com", "oncall@customer.com"],
--   "cc": [],
--   "bcc": []
-- }

ALTER TABLE integrations ADD COLUMN IF NOT EXISTS email_template JSONB;
-- email_template structure:
-- {
--   "subject_template": "[{severity}] Alert: {alert_type} on {device_id}",
--   "body_template": "html_or_text_template_string",
--   "format": "html"  -- or "text"
-- }

-- Add index for email integrations
CREATE INDEX IF NOT EXISTS idx_integrations_email
    ON integrations(tenant_id, type)
    WHERE type = 'email';

-- Comments for documentation
COMMENT ON COLUMN integrations.email_config IS 'SMTP server configuration for email integrations';
COMMENT ON COLUMN integrations.email_recipients IS 'Email recipient lists (to, cc, bcc)';
COMMENT ON COLUMN integrations.email_template IS 'Email subject and body templates';
```

### 1.2 Create Pydantic schemas for email

Create `services/ui_iot/schemas/email.py`:

```python
"""Pydantic schemas for email integrations."""

from typing import Optional
from pydantic import BaseModel, Field, EmailStr, field_validator


class SMTPConfig(BaseModel):
    """SMTP server configuration."""
    smtp_host: str = Field(..., min_length=1, max_length=255)
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_user: Optional[str] = Field(default=None, max_length=255)
    smtp_password: Optional[str] = Field(default=None, max_length=255)
    smtp_tls: bool = Field(default=True)
    from_address: EmailStr
    from_name: Optional[str] = Field(default="OpsConductor Alerts", max_length=100)


class EmailRecipients(BaseModel):
    """Email recipient configuration."""
    to: list[EmailStr] = Field(..., min_length=1, max_length=10)
    cc: list[EmailStr] = Field(default_factory=list, max_length=10)
    bcc: list[EmailStr] = Field(default_factory=list, max_length=10)

    @field_validator('to')
    @classmethod
    def validate_to_not_empty(cls, v):
        if not v:
            raise ValueError('At least one recipient required')
        return v


class EmailTemplate(BaseModel):
    """Email template configuration."""
    subject_template: str = Field(
        default="[{severity}] {alert_type}: {device_id}",
        max_length=200
    )
    body_template: Optional[str] = Field(default=None, max_length=10000)
    format: str = Field(default="html", pattern="^(html|text)$")


class EmailIntegrationCreate(BaseModel):
    """Request body for creating email integration."""
    name: str = Field(..., min_length=1, max_length=100)
    smtp_config: SMTPConfig
    recipients: EmailRecipients
    template: Optional[EmailTemplate] = None
    enabled: bool = True


class EmailIntegrationUpdate(BaseModel):
    """Request body for updating email integration."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    smtp_config: Optional[SMTPConfig] = None
    recipients: Optional[EmailRecipients] = None
    template: Optional[EmailTemplate] = None
    enabled: Optional[bool] = None


class EmailIntegrationResponse(BaseModel):
    """Response for email integration."""
    id: str
    tenant_id: str
    name: str
    smtp_host: str
    smtp_port: int
    smtp_tls: bool
    from_address: str
    recipient_count: int
    template_format: str
    enabled: bool
    created_at: str
    updated_at: str
```

### 1.3 Update schemas __init__.py

Add to `services/ui_iot/schemas/__init__.py`:

```python
from .email import (
    SMTPConfig,
    EmailRecipients,
    EmailTemplate,
    EmailIntegrationCreate,
    EmailIntegrationUpdate,
    EmailIntegrationResponse,
)
```

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `db/migrations/013_email_integrations.sql` |
| CREATE | `services/ui_iot/schemas/email.py` |
| MODIFY | `services/ui_iot/schemas/__init__.py` |

---

## Acceptance Criteria

- [ ] Migration adds email to type constraint
- [ ] Migration adds email_config, email_recipients, email_template columns
- [ ] Pydantic schemas validate SMTP configuration
- [ ] Pydantic schemas validate email addresses
- [ ] Pydantic schemas enforce at least one recipient
- [ ] Migration runs without error

**Test**:
```bash
# Run migration
PGPASSWORD=iot_dev psql -h localhost -U iot -d iotcloud -f db/migrations/013_email_integrations.sql

# Verify columns exist
PGPASSWORD=iot_dev psql -h localhost -U iot -d iotcloud -c "\d integrations"

# Verify type constraint
PGPASSWORD=iot_dev psql -h localhost -U iot -d iotcloud -c "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'integrations_type_check';"
```

---

## Commit

```
Add email integration schema

- Migration 013: email type, config columns
- Pydantic schemas for SMTP, recipients, templates
- Email validation with EmailStr

Part of Phase 6: Email Delivery
```
