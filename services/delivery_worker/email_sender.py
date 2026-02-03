"""Email sender for alert delivery.

Copied from services/ui_iot/services/email_sender.py for use in delivery_worker.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import aiosmtplib

    AIOSMTPLIB_AVAILABLE = True
except ImportError:
    aiosmtplib = None
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
        kwargs["severity_lower"] = kwargs.get("severity", "info").lower()
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
