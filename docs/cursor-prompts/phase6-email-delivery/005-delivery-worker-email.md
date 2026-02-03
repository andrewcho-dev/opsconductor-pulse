# Task 005: Delivery Worker Email Support

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Create/Modify".
> Verify your work against the acceptance criteria.
> Commit with the exact message in the "Commit" section when done.

---

## Context

The delivery worker needs to support email delivery alongside webhooks and SNMP. This follows the same pattern used for adding SNMP support in Phase 5.

**Read first**:
- `services/delivery_worker/worker.py` (current worker with webhook + SNMP)
- `services/delivery_worker/snmp_sender.py` (pattern for adding new sender)
- `services/ui_iot/services/email_sender.py` (email sender from Task 002)

**Depends on**: Tasks 002, 003, 004

---

## Task

### 5.1 Copy email sender to delivery_worker service

Create `services/delivery_worker/email_sender.py`:

```python
"""Email sender for alert delivery.

Copied from services/ui_iot/services/email_sender.py for use in delivery_worker.
"""

import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

try:
    import aiosmtplib
    AIOSMTPLIB_AVAILABLE = True
except ImportError:
    AIOSMTPLIB_AVAILABLE = False
    logger.warning("aiosmtplib not available - email delivery disabled")


@dataclass
class EmailResult:
    """Result of email send attempt."""
    success: bool
    error: Optional[str] = None
    duration_ms: Optional[float] = None
    recipients_count: int = 0


DEFAULT_SUBJECT_TEMPLATE = "[{severity}] {alert_type}: {device_id}"

DEFAULT_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
        .alert-box {{ border: 1px solid #ddd; border-radius: 8px; padding: 20px; max-width: 600px; }}
        .alert-header {{ border-bottom: 1px solid #ddd; padding-bottom: 10px; margin-bottom: 15px; }}
        .severity-critical {{ color: #dc3545; }}
        .severity-warning {{ color: #ffc107; }}
        .severity-info {{ color: #17a2b8; }}
        .field {{ margin: 10px 0; }}
        .field-label {{ font-weight: bold; color: #666; }}
        .field-value {{ margin-top: 3px; }}
        .footer {{ margin-top: 20px; font-size: 12px; color: #999; }}
    </style>
</head>
<body>
    <div class="alert-box">
        <div class="alert-header">
            <h2 class="severity-{severity_lower}">{alert_type}</h2>
        </div>
        <div class="field">
            <div class="field-label">Device</div>
            <div class="field-value">{device_id}</div>
        </div>
        <div class="field">
            <div class="field-label">Severity</div>
            <div class="field-value">{severity}</div>
        </div>
        <div class="field">
            <div class="field-label">Message</div>
            <div class="field-value">{message}</div>
        </div>
        <div class="field">
            <div class="field-label">Timestamp</div>
            <div class="field-value">{timestamp}</div>
        </div>
        <div class="footer">
            This alert was sent by OpsConductor Pulse.
        </div>
    </div>
</body>
</html>
"""

DEFAULT_TEXT_TEMPLATE = """
ALERT: {alert_type}
====================

Device: {device_id}
Severity: {severity}
Message: {message}
Timestamp: {timestamp}

--
This alert was sent by OpsConductor Pulse.
"""


def render_template(template: str, **kwargs) -> str:
    """Render a template with the given variables."""
    try:
        kwargs['severity_lower'] = kwargs.get('severity', 'info').lower()
        return template.format(**kwargs)
    except KeyError as e:
        logger.warning(f"Template variable not found: {e}")
        return template


async def send_alert_email(
    smtp_host: str,
    smtp_port: int,
    smtp_user: Optional[str],
    smtp_password: Optional[str],
    smtp_tls: bool,
    from_address: str,
    from_name: str,
    recipients: dict,
    alert_id: str,
    device_id: str,
    tenant_id: str,
    severity: str,
    message: str,
    alert_type: str,
    timestamp: datetime,
    subject_template: Optional[str] = None,
    body_template: Optional[str] = None,
    body_format: str = "html",
) -> EmailResult:
    """Send an email alert."""
    if not AIOSMTPLIB_AVAILABLE:
        return EmailResult(success=False, error="aiosmtplib not available")

    start_time = asyncio.get_event_loop().time()

    try:
        template_vars = {
            "alert_id": alert_id,
            "device_id": device_id,
            "tenant_id": tenant_id,
            "severity": severity,
            "message": message,
            "alert_type": alert_type,
            "timestamp": timestamp.isoformat() if isinstance(timestamp, datetime) else str(timestamp),
        }

        subject = render_template(subject_template or DEFAULT_SUBJECT_TEMPLATE, **template_vars)

        if body_template:
            body = render_template(body_template, **template_vars)
        elif body_format == "html":
            body = render_template(DEFAULT_HTML_TEMPLATE, **template_vars)
        else:
            body = render_template(DEFAULT_TEXT_TEMPLATE, **template_vars)

        if body_format == "html":
            msg = MIMEMultipart("alternative")
            text_body = render_template(DEFAULT_TEXT_TEMPLATE, **template_vars)
            msg.attach(MIMEText(text_body, "plain"))
            msg.attach(MIMEText(body, "html"))
        else:
            msg = MIMEText(body, "plain")

        msg["Subject"] = subject
        msg["From"] = f"{from_name} <{from_address}>" if from_name else from_address

        to_addrs = recipients.get("to", [])
        cc_addrs = recipients.get("cc", [])
        bcc_addrs = recipients.get("bcc", [])

        if to_addrs:
            msg["To"] = ", ".join(to_addrs)
        if cc_addrs:
            msg["Cc"] = ", ".join(cc_addrs)

        all_recipients = to_addrs + cc_addrs + bcc_addrs

        if not all_recipients:
            return EmailResult(success=False, error="No recipients specified")

        if smtp_tls:
            smtp = aiosmtplib.SMTP(hostname=smtp_host, port=smtp_port, start_tls=True, timeout=30)
        else:
            smtp = aiosmtplib.SMTP(hostname=smtp_host, port=smtp_port, timeout=30)

        async with smtp:
            if smtp_user and smtp_password:
                await smtp.login(smtp_user, smtp_password)
            await smtp.send_message(msg, recipients=all_recipients)

        duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
        return EmailResult(success=True, duration_ms=duration_ms, recipients_count=len(all_recipients))

    except Exception as e:
        duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
        logger.exception("Email send failed")
        return EmailResult(success=False, error=str(e), duration_ms=duration_ms)
```

### 5.2 Update delivery worker to handle email

Add import at top of `services/delivery_worker/worker.py`:

```python
from email_sender import send_alert_email, EmailResult, AIOSMTPLIB_AVAILABLE
```

Add helper to normalize email_config:

```python
def normalize_email_config(value) -> dict:
    """Normalize email_config from various storage formats."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, (bytes, bytearray)):
        try:
            value = value.decode("utf-8")
        except Exception:
            return {}
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except Exception:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}
```

Update `fetch_integration` to return email fields:

```python
async def fetch_integration(conn: asyncpg.Connection, tenant_id: str, integration_id) -> dict | None:
    row = await conn.fetchrow(
        """
        SELECT type, enabled, config_json,
               snmp_host, snmp_port, snmp_config, snmp_oid_prefix,
               email_config, email_recipients, email_template
        FROM integrations
        WHERE tenant_id=$1 AND integration_id=$2
        """,
        tenant_id,
        integration_id,
    )
    if row is None:
        return None
    return dict(row)
```

Add `deliver_email` function:

```python
async def deliver_email(integration: dict, job: asyncpg.Record) -> tuple[bool, str | None]:
    """Deliver via email. Returns (ok, error)."""
    if not AIOSMTPLIB_AVAILABLE:
        return False, "email_not_available"

    email_config = normalize_email_config(integration.get("email_config"))
    email_recipients = normalize_email_config(integration.get("email_recipients"))
    email_template = normalize_email_config(integration.get("email_template"))

    smtp_host = email_config.get("smtp_host")
    if not smtp_host:
        return False, "missing_smtp_host"

    if not email_recipients.get("to"):
        return False, "missing_recipients"

    payload = job["payload_json"]
    if isinstance(payload, str):
        payload = json.loads(payload)

    alert_id = str(payload.get("alert_id", "unknown"))
    device_id = payload.get("device_id", "unknown")
    tenant_id = job["tenant_id"]
    severity = str(payload.get("severity", "info"))
    message = payload.get("summary") or payload.get("message") or "Alert"
    alert_type = payload.get("alert_type", "ALERT")

    ts_str = payload.get("created_at")
    if ts_str:
        try:
            timestamp = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except Exception:
            timestamp = now_utc()
    else:
        timestamp = now_utc()

    result = await send_alert_email(
        smtp_host=smtp_host,
        smtp_port=email_config.get("smtp_port", 587),
        smtp_user=email_config.get("smtp_user"),
        smtp_password=email_config.get("smtp_password"),
        smtp_tls=email_config.get("smtp_tls", True),
        from_address=email_config.get("from_address", "alerts@example.com"),
        from_name=email_config.get("from_name", "OpsConductor Alerts"),
        recipients=email_recipients,
        alert_id=alert_id,
        device_id=device_id,
        tenant_id=tenant_id,
        severity=severity,
        message=message,
        alert_type=alert_type,
        timestamp=timestamp,
        subject_template=email_template.get("subject_template"),
        body_template=email_template.get("body_template"),
        body_format=email_template.get("format", "html"),
    )

    return result.success, result.error
```

Update `process_job` to handle email type:

```python
if integration_type == "snmp":
    ok, error = await deliver_snmp(integration, job)
elif integration_type == "email":
    ok, error = await deliver_email(integration, job)
else:
    # Webhook delivery (default)
    ok, http_status, error = await deliver_webhook(integration, job)
```

Update startup logging:

```python
print(
    "[worker] startup mode={} ssrf_strict={} snmp_available={} email_available={}".format(
        MODE,
        ssrf_strict,
        PYSNMP_AVAILABLE,
        AIOSMTPLIB_AVAILABLE,
    )
)
```

### 5.3 Update delivery_worker requirements

Add to `services/delivery_worker/requirements.txt`:

```
aiosmtplib>=3.0.0
```

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `services/delivery_worker/email_sender.py` |
| MODIFY | `services/delivery_worker/worker.py` |
| MODIFY | `services/delivery_worker/requirements.txt` |

---

## Acceptance Criteria

- [ ] Email sender module copied to delivery_worker
- [ ] Worker checks for email integration type
- [ ] Email integrations receive background delivery
- [ ] Worker logs email availability on startup
- [ ] aiosmtplib added to requirements
- [ ] Webhook and SNMP delivery unchanged

**Test**:
```bash
# Rebuild delivery worker
cd compose && docker compose build delivery_worker

# Restart and check logs
docker compose restart delivery_worker
docker compose logs -f delivery_worker
# Should see: email_available=True

# Create email integration with route, trigger alert, verify email sent
```

---

## Commit

```
Add email support to delivery worker

- Copy email_sender module to delivery_worker
- Handle email integration type in worker
- Log email availability on startup
- Add aiosmtplib to requirements

Part of Phase 6: Email Delivery
```
