# Prompt 002 — subscription_worker: Direct SMTP Send

Read `services/subscription_worker/worker.py` fully.
Read `services/delivery_worker/email_sender.py` for `send_alert_email()` function signature and aiosmtplib usage.

## Add aiosmtplib to requirements

Add to `services/subscription_worker/requirements.txt`:
```
aiosmtplib>=3.0.0
```

## Add env vars to `services/subscription_worker/.env.example`

```
# SMTP for subscription expiry notifications (optional — notifications skipped if not set)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_TLS=true
SMTP_FROM=noreply@example.com
NOTIFICATION_EMAIL_TO=admin@example.com
```

## Add `send_expiry_notification_email()` to worker.py

```python
import os
import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email_templates import (
    EXPIRY_SUBJECT_TEMPLATE, EXPIRY_HTML_TEMPLATE, EXPIRY_TEXT_TEMPLATE,
    GRACE_SUBJECT_TEMPLATE, GRACE_HTML_TEMPLATE
)

async def send_expiry_notification_email(notification: dict, subscription: dict, tenant: dict) -> bool:
    """
    Send an expiry notification email directly via SMTP.
    Returns True on success, False if SMTP not configured or send fails.
    """
    smtp_host = os.environ.get("SMTP_HOST")
    if not smtp_host:
        return False  # SMTP not configured

    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_password = os.environ.get("SMTP_PASSWORD", "")
    use_tls = os.environ.get("SMTP_TLS", "true").lower() == "true"
    from_address = os.environ.get("SMTP_FROM", "noreply@pulse.local")
    to_address = os.environ.get("NOTIFICATION_EMAIL_TO")
    if not to_address:
        return False

    import math
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    term_end = subscription.get("term_end")
    days_remaining = (term_end - now).days if term_end else 0
    notification_type = notification.get("notification_type", "expiry")
    is_grace = "grace" in notification_type.lower()

    vars = {
        "tenant_id": tenant.get("tenant_id", ""),
        "tenant_name": tenant.get("name", tenant.get("tenant_id", "")),
        "subscription_id": subscription.get("subscription_id", ""),
        "term_end": term_end.strftime("%Y-%m-%d") if term_end else "",
        "grace_end": subscription.get("grace_end", ""),
        "status": subscription.get("status", ""),
        "days_remaining": max(days_remaining, 0),
    }

    subject = (GRACE_SUBJECT_TEMPLATE if is_grace else EXPIRY_SUBJECT_TEMPLATE).format(**vars)
    html_body = (GRACE_HTML_TEMPLATE if is_grace else EXPIRY_HTML_TEMPLATE).format(**vars)
    text_body = EXPIRY_TEXT_TEMPLATE.format(**vars)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_address
    msg["To"] = to_address
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=smtp_host, port=smtp_port,
            username=smtp_user or None, password=smtp_password or None,
            use_tls=use_tls,
        )
        return True
    except Exception as e:
        logger.warning(f"Failed to send expiry email: {e}")
        return False
```

## Update `process_pending_notifications()`

In the existing loop that processes pending notifications, add email sending:

```python
# After the existing webhook/log logic, add:
email_sent = await send_expiry_notification_email(notification, subscription, tenant)
if email_sent:
    channel = "email"
    # mark notification as sent
```

## Acceptance Criteria

- [ ] `aiosmtplib` in subscription_worker requirements.txt
- [ ] `SMTP_*` and `NOTIFICATION_EMAIL_TO` in .env.example
- [ ] `send_expiry_notification_email()` in worker.py
- [ ] Email uses correct template (pre-expiry vs grace)
- [ ] Returns False gracefully if SMTP not configured
- [ ] `pytest -m unit -v` passes
