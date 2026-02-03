# Task 008: Documentation Update for Email

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Create/Modify".
> Verify your work against the acceptance criteria.
> Commit with the exact message in the "Commit" section when done.

---

## Context

With email delivery implemented, we need to update all documentation to reflect this new capability.

**Read first**:
- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/INTEGRATIONS_AND_DELIVERY.md`

**Depends on**: Tasks 001-007

---

## Task

### 8.1 Update README.md

Add email to the features list:

```markdown
## Features

- **Multi-tenant isolation** - Strict tenant separation via JWT claims and database RLS
- **Real-time device monitoring** - Heartbeat tracking, telemetry ingestion, stale device detection
- **Alert generation** - Automatic alerts for device health issues
- **Customer self-service** - Customers manage their own integrations and alert routing
- **Webhook delivery** - HTTP POST to customer endpoints with retry logic
- **SNMP trap delivery** - SNMPv2c and SNMPv3 trap support for network management systems
- **Email delivery** - SMTP email alerts with HTML/text templates
- **Operator dashboards** - Cross-tenant visibility with full audit trail
```

Add to Alert Delivery section:

```markdown
## Alert Delivery

Customers can configure three types of integrations to receive alerts:

### Webhooks
- HTTP POST with JSON payload
- Automatic retry with exponential backoff
- SSRF protection (blocks internal IPs)

### SNMP Traps
- SNMPv2c (community string) and SNMPv3 (auth/priv)
- Custom OID prefix support
- Address validation (blocks internal networks)

### Email
- SMTP delivery with TLS support
- HTML and plain text templates
- Multiple recipients (to, cc, bcc)
- Customizable subject and body templates
```

Add email endpoints to API section:

```markdown
| GET | /customer/integrations/email | List email integrations |
| POST | /customer/integrations/email | Create email integration |
| POST | /customer/integrations/email/{id}/test | Test email delivery |
```

### 8.2 Update ARCHITECTURE.md

Add email to the delivery worker description:

```markdown
### services/delivery_worker
Alert delivery via webhook, SNMP, and email. Processes delivery_jobs with retry logic and exponential backoff. Supports:
- **Webhooks**: HTTP POST with JSON payload
- **SNMP**: v2c and v3 trap delivery
- **Email**: SMTP with HTML/text templates
```

Update the alert delivery flow:

```markdown
### Alert Delivery Flow
```
fleet_alert → dispatcher → route match → delivery_job
                                              ↓
                                      delivery_worker
                                       ↓     ↓     ↓
                            webhook  SNMP   email
                                       ↓     ↓     ↓
                              delivery_attempts (logged)
```
```

### 8.3 Update INTEGRATIONS_AND_DELIVERY.md

Add email as implemented (not future):

```markdown
## Supported Delivery Types

### Webhook (Implemented)
HTTP POST with JSON payload to customer-specified URLs.
...

### SNMP Trap (Implemented)
SNMP trap delivery to network management systems.
...

### Email (Implemented)
SMTP email delivery to customer-specified addresses.

**Features**:
- TLS/STARTTLS support
- Authentication (username/password)
- Multiple recipients (to, cc, bcc)
- HTML and plain text formats
- Customizable subject and body templates
- Template variables: {severity}, {alert_type}, {device_id}, {message}, {timestamp}
```

Add email schema:

```markdown
### Email Configuration (email_config)
```json
{
  "smtp_host": "smtp.example.com",
  "smtp_port": 587,
  "smtp_user": "user@example.com",
  "smtp_password": "...",
  "smtp_tls": true,
  "from_address": "alerts@example.com",
  "from_name": "OpsConductor Alerts"
}
```

### Email Recipients (email_recipients)
```json
{
  "to": ["admin@example.com", "oncall@example.com"],
  "cc": ["manager@example.com"],
  "bcc": []
}
```

### Email Template (email_template)
```json
{
  "subject_template": "[{severity}] {alert_type}: {device_id}",
  "body_template": "Custom HTML or text...",
  "format": "html"
}
```
```

Add email API endpoints:

```markdown
### Email Integrations
- `GET /customer/integrations/email` - List email integrations
- `POST /customer/integrations/email` - Create email integration
- `GET /customer/integrations/email/{id}` - Get email integration
- `PATCH /customer/integrations/email/{id}` - Update email integration
- `DELETE /customer/integrations/email/{id}` - Delete email integration
- `POST /customer/integrations/email/{id}/test` - Send test email
```

Remove "Email (Future)" section and update future enhancements:

```markdown
## Future Enhancements

- **Custom protocol adapters**: Plugin system for new output types
- **External secret management**: HashiCorp Vault integration
- **Delivery analytics**: Dashboard for delivery metrics and trends
- **SMS delivery**: Text message alerts for critical issues
```

### 8.4 Update db/README.md

Add migration 013 to the list:

```markdown
| 013 | email_integrations.sql | Email support columns |
```

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| MODIFY | `README.md` |
| MODIFY | `docs/ARCHITECTURE.md` |
| MODIFY | `docs/INTEGRATIONS_AND_DELIVERY.md` |
| MODIFY | `db/README.md` |

---

## Acceptance Criteria

- [ ] README lists email as a feature
- [ ] README includes email API endpoints
- [ ] ARCHITECTURE.md shows email in delivery worker
- [ ] ARCHITECTURE.md flow diagram includes email
- [ ] INTEGRATIONS_AND_DELIVERY.md documents email as implemented
- [ ] INTEGRATIONS_AND_DELIVERY.md includes email schema
- [ ] INTEGRATIONS_AND_DELIVERY.md lists email API endpoints
- [ ] db/README.md lists migration 013

**Test**:
```bash
# Visual review of all docs
cat README.md
cat docs/ARCHITECTURE.md
cat docs/INTEGRATIONS_AND_DELIVERY.md
cat db/README.md
```

---

## Commit

```
Update documentation for email delivery

- Add email to README features and API
- Update ARCHITECTURE with email in delivery flow
- Document email configuration in INTEGRATIONS doc
- Add migration 013 to db README

Part of Phase 6: Email Delivery
```
