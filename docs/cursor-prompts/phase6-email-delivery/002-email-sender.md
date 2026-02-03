# Task 002: Email Sender Service

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Create/Modify".
> Verify your work against the acceptance criteria.
> Commit with the exact message in the "Commit" section when done.

---

## Context

We need an async email sender service that can send alert emails via SMTP. This follows the same pattern as the SNMP sender.

**Read first**:
- `services/ui_iot/services/snmp_sender.py` (similar pattern)
- `services/ui_iot/services/alert_dispatcher.py` (integration point)

**Depends on**: Task 001

---

## Task

### 2.1 Create email sender service

Create `services/ui_iot/services/email_sender.py`:

```python
"""Email sender for alert delivery."""

import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

# Check for aiosmtplib availability
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


# Default email templates
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
        <div class="field">
            <div class="field-label">Alert ID</div>
            <div class="field-value">{alert_id}</div>
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
Alert ID: {alert_id}

--
This alert was sent by OpsConductor Pulse.
"""


def render_template(template: str, **kwargs) -> str:
    """Render a template with the given variables."""
    try:
        # Add derived fields
        kwargs['severity_lower'] = kwargs.get('severity', 'info').lower()
        return template.format(**kwargs)
    except KeyError as e:
        logger.warning(f"Template variable not found: {e}")
        # Return template with unfilled variables rather than failing
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
        # Prepare template variables
        template_vars = {
            "alert_id": alert_id,
            "device_id": device_id,
            "tenant_id": tenant_id,
            "severity": severity,
            "message": message,
            "alert_type": alert_type,
            "timestamp": timestamp.isoformat() if isinstance(timestamp, datetime) else str(timestamp),
        }

        # Render subject
        subject = render_template(
            subject_template or DEFAULT_SUBJECT_TEMPLATE,
            **template_vars
        )

        # Render body
        if body_template:
            body = render_template(body_template, **template_vars)
        elif body_format == "html":
            body = render_template(DEFAULT_HTML_TEMPLATE, **template_vars)
        else:
            body = render_template(DEFAULT_TEXT_TEMPLATE, **template_vars)

        # Build email
        if body_format == "html":
            msg = MIMEMultipart("alternative")
            # Add plain text fallback
            text_body = render_template(DEFAULT_TEXT_TEMPLATE, **template_vars)
            msg.attach(MIMEText(text_body, "plain"))
            msg.attach(MIMEText(body, "html"))
        else:
            msg = MIMEText(body, "plain")

        msg["Subject"] = subject
        msg["From"] = f"{from_name} <{from_address}>" if from_name else from_address

        # Collect all recipients
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

        # Send email
        if smtp_tls:
            # STARTTLS on port 587
            smtp = aiosmtplib.SMTP(
                hostname=smtp_host,
                port=smtp_port,
                start_tls=True,
                timeout=30,
            )
        else:
            smtp = aiosmtplib.SMTP(
                hostname=smtp_host,
                port=smtp_port,
                timeout=30,
            )

        async with smtp:
            if smtp_user and smtp_password:
                await smtp.login(smtp_user, smtp_password)

            await smtp.send_message(msg, recipients=all_recipients)

        duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000

        return EmailResult(
            success=True,
            duration_ms=duration_ms,
            recipients_count=len(all_recipients),
        )

    except aiosmtplib.SMTPAuthenticationError as e:
        duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
        logger.error(f"SMTP authentication failed: {e}")
        return EmailResult(success=False, error="SMTP authentication failed", duration_ms=duration_ms)

    except aiosmtplib.SMTPConnectError as e:
        duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
        logger.error(f"SMTP connection failed: {e}")
        return EmailResult(success=False, error=f"SMTP connection failed: {e}", duration_ms=duration_ms)

    except Exception as e:
        duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
        logger.exception("Email send failed")
        return EmailResult(success=False, error=str(e), duration_ms=duration_ms)
```

### 2.2 Add aiosmtplib to requirements

Add to `services/ui_iot/requirements.txt`:

```
aiosmtplib>=3.0.0
```

### 2.3 Create unit tests

Create `tests/unit/test_email_sender.py`:

```python
"""Unit tests for email sender."""

import pytest
from datetime import datetime
from unittest.mock import patch, AsyncMock, MagicMock

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class TestEmailSender:
    """Test email sender functionality."""

    async def test_render_template(self):
        """Test template rendering."""
        from services.ui_iot.services.email_sender import render_template

        result = render_template(
            "Alert: {alert_type} on {device_id}",
            alert_type="NO_HEARTBEAT",
            device_id="sensor-001",
        )
        assert result == "Alert: NO_HEARTBEAT on sensor-001"

    async def test_render_template_missing_var(self):
        """Test template with missing variable doesn't crash."""
        from services.ui_iot.services.email_sender import render_template

        # Should return template as-is when variable missing
        result = render_template(
            "Alert: {alert_type} on {missing_var}",
            alert_type="NO_HEARTBEAT",
        )
        # Returns original template due to KeyError handling
        assert "{missing_var}" in result or "NO_HEARTBEAT" in result

    @patch("services.ui_iot.services.email_sender.aiosmtplib")
    async def test_send_email_success(self, mock_aiosmtplib):
        """Test successful email send."""
        from services.ui_iot.services.email_sender import send_alert_email

        # Mock SMTP
        mock_smtp = AsyncMock()
        mock_aiosmtplib.SMTP.return_value = mock_smtp
        mock_smtp.__aenter__.return_value = mock_smtp

        result = await send_alert_email(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="user",
            smtp_password="pass",
            smtp_tls=True,
            from_address="alerts@example.com",
            from_name="Alerts",
            recipients={"to": ["admin@example.com"]},
            alert_id="alert-123",
            device_id="device-456",
            tenant_id="tenant-a",
            severity="critical",
            message="Test alert",
            alert_type="NO_HEARTBEAT",
            timestamp=datetime.utcnow(),
        )

        assert result.success
        assert result.recipients_count == 1

    async def test_send_email_no_recipients(self):
        """Test email with no recipients fails."""
        from services.ui_iot.services.email_sender import send_alert_email

        result = await send_alert_email(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user=None,
            smtp_password=None,
            smtp_tls=True,
            from_address="alerts@example.com",
            from_name="Alerts",
            recipients={"to": [], "cc": [], "bcc": []},
            alert_id="alert-123",
            device_id="device-456",
            tenant_id="tenant-a",
            severity="critical",
            message="Test alert",
            alert_type="NO_HEARTBEAT",
            timestamp=datetime.utcnow(),
        )

        assert not result.success
        assert "No recipients" in result.error
```

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `services/ui_iot/services/email_sender.py` |
| MODIFY | `services/ui_iot/requirements.txt` |
| CREATE | `tests/unit/test_email_sender.py` |

---

## Acceptance Criteria

- [ ] Email sender module created with async SMTP support
- [ ] Default HTML and text templates provided
- [ ] Template rendering handles missing variables gracefully
- [ ] TLS/STARTTLS supported
- [ ] Multiple recipients (to, cc, bcc) supported
- [ ] aiosmtplib added to requirements
- [ ] Unit tests pass

**Test**:
```bash
# Install dependency
pip install aiosmtplib

# Run unit tests
pytest tests/unit/test_email_sender.py -v
```

---

## Commit

```
Add email sender service

- Async SMTP sender with aiosmtplib
- HTML and text email templates
- Support for to, cc, bcc recipients
- TLS/STARTTLS support
- Unit tests

Part of Phase 6: Email Delivery
```
