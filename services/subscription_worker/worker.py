"""
Subscription Worker - Scheduled job for:
1. Sending renewal notifications at 90, 60, 30, 14, 7, 1 days before expiry
2. Transitioning ACTIVE -> GRACE when term_end passes
3. Transitioning GRACE -> SUSPENDED when grace_end passes
4. Reconciling device counts nightly
"""
import asyncio
import os
from datetime import datetime, timezone, timedelta
from typing import Any
import asyncpg
import httpx
import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
try:
    from .email_templates import (
        EXPIRY_SUBJECT_TEMPLATE,
        EXPIRY_HTML_TEMPLATE,
        EXPIRY_TEXT_TEMPLATE,
        GRACE_SUBJECT_TEMPLATE,
        GRACE_HTML_TEMPLATE,
    )
except ImportError:
    from email_templates import (
        EXPIRY_SUBJECT_TEMPLATE,
        EXPIRY_HTML_TEMPLATE,
        EXPIRY_TEXT_TEMPLATE,
        GRACE_SUBJECT_TEMPLATE,
        GRACE_HTML_TEMPLATE,
    )

from shared.log import configure_root_logger, get_logger

configure_root_logger()
logger = get_logger(__name__)

DATABASE_URL = os.environ["DATABASE_URL"]
NOTIFICATION_WEBHOOK_URL = os.getenv("NOTIFICATION_WEBHOOK_URL")
NOTIFICATION_DAYS = [90, 60, 30, 14, 7, 1]
GRACE_PERIOD_DAYS = 14


async def get_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)


async def schedule_renewal_notifications(pool: asyncpg.Pool) -> None:
    """Find subscriptions expiring within notification windows and create records."""
    async with pool.acquire() as conn:
        for days in NOTIFICATION_DAYS:
            notification_type = f"RENEWAL_{days}"
            target_date = datetime.now(timezone.utc) + timedelta(days=days)

            rows = await conn.fetch(
                """
                SELECT s.subscription_id, s.tenant_id, s.term_end, t.name as tenant_name
                FROM subscriptions s
                JOIN tenants t ON t.tenant_id = s.tenant_id
                WHERE s.status = 'ACTIVE'
                  AND s.term_end >= $1
                  AND s.term_end < $1 + interval '1 day'
                  AND NOT EXISTS (
                      SELECT 1 FROM subscription_notifications n
                      WHERE n.tenant_id = s.tenant_id
                        AND n.notification_type = $2
                        AND n.scheduled_at >= $1 - interval '1 day'
                  )
                """,
                target_date,
                notification_type,
            )

            for row in rows:
                await conn.execute(
                    """
                    INSERT INTO subscription_notifications
                        (tenant_id, notification_type, scheduled_at, channel, status)
                    VALUES ($1, $2, now(), 'email', 'PENDING')
                    """,
                    row["tenant_id"],
                    notification_type,
                )
                logger.info(
                    "Scheduled %s notification for %s",
                    notification_type,
                    row["tenant_id"],
                )


async def process_pending_notifications(pool: asyncpg.Pool) -> None:
    """Send pending notifications via configured channels."""
    async with pool.acquire() as conn:
        pending = await conn.fetch(
            """
            SELECT n.id, n.tenant_id, n.notification_type, t.name as tenant_name,
                   s.subscription_id, s.term_end, s.grace_end, s.status,
                   s.device_limit, s.active_device_count
            FROM subscription_notifications n
            JOIN tenants t ON t.tenant_id = n.tenant_id
            JOIN subscriptions s ON s.tenant_id = n.tenant_id AND s.subscription_type = 'MAIN'
            WHERE n.status = 'PENDING'
              AND n.scheduled_at <= now()
            ORDER BY n.scheduled_at
            LIMIT 100
            """
        )

        for row in pending:
            try:
                await send_notification(row)
                email_sent = await send_expiry_notification_email(
                    notification=dict(row),
                    subscription=dict(row),
                    tenant={"tenant_id": row["tenant_id"], "name": row["tenant_name"]},
                )
                channel = "email" if email_sent else ("webhook" if NOTIFICATION_WEBHOOK_URL else "log")

                await conn.execute(
                    """
                    UPDATE subscription_notifications
                    SET status = 'SENT', sent_at = now(), channel = $2
                    WHERE id = $1
                    """,
                    row["id"],
                    channel,
                )
                logger.info("Sent %s to %s", row["notification_type"], row["tenant_id"])
            except Exception as exc:
                await conn.execute(
                    """
                    UPDATE subscription_notifications
                    SET status = 'FAILED', error = $2
                    WHERE id = $1
                    """,
                    row["id"],
                    str(exc),
                )
                logger.error("Failed to send notification %s: %s", row["id"], exc)


async def send_notification(row: dict[str, Any]) -> None:
    """Send notification via configured channel."""
    if NOTIFICATION_WEBHOOK_URL:
        async with httpx.AsyncClient() as client:
            await client.post(
                NOTIFICATION_WEBHOOK_URL,
                json={
                    "tenant_id": row["tenant_id"],
                    "tenant_name": row["tenant_name"],
                    "notification_type": row["notification_type"],
                    "term_end": row["term_end"].isoformat() if row["term_end"] else None,
                    "device_limit": row["device_limit"],
                    "active_device_count": row["active_device_count"],
                },
                timeout=30.0,
            )
    else:
        logger.info(
            "NOTIFICATION: %s for tenant %s (%s)",
            row["notification_type"],
            row["tenant_name"],
            row["tenant_id"],
        )


async def send_expiry_notification_email(
    notification: dict,
    subscription: dict,
    tenant: dict,
) -> bool:
    """
    Send an expiry notification email directly via SMTP.
    Returns True on success, False if SMTP is not configured or send fails.
    """
    smtp_host = os.environ.get("SMTP_HOST")
    if not smtp_host:
        return False

    to_address = os.environ.get("NOTIFICATION_EMAIL_TO")
    if not to_address:
        return False

    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_password = os.environ.get("SMTP_PASSWORD", "")
    use_tls = os.environ.get("SMTP_TLS", "true").lower() == "true"
    from_address = os.environ.get("SMTP_FROM", "noreply@pulse.local")

    now = datetime.now(timezone.utc)
    term_end = subscription.get("term_end")
    days_remaining = (term_end - now).days if isinstance(term_end, datetime) else 0
    notification_type = str(notification.get("notification_type", "expiry"))
    is_grace = "grace" in notification_type.lower()

    grace_end_val = subscription.get("grace_end")
    if isinstance(grace_end_val, datetime):
        grace_end_text = grace_end_val.strftime("%Y-%m-%d")
    else:
        grace_end_text = str(grace_end_val or "")

    template_vars = {
        "tenant_id": tenant.get("tenant_id", ""),
        "tenant_name": tenant.get("name", tenant.get("tenant_id", "")),
        "subscription_id": subscription.get("subscription_id", ""),
        "term_end": term_end.strftime("%Y-%m-%d") if isinstance(term_end, datetime) else "",
        "grace_end": grace_end_text,
        "status": subscription.get("status", ""),
        "days_remaining": max(days_remaining, 0),
    }

    subject = (
        GRACE_SUBJECT_TEMPLATE if is_grace else EXPIRY_SUBJECT_TEMPLATE
    ).format(**template_vars)
    html_body = (
        GRACE_HTML_TEMPLATE if is_grace else EXPIRY_HTML_TEMPLATE
    ).format(**template_vars)
    text_body = EXPIRY_TEXT_TEMPLATE.format(**template_vars)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_address
    msg["To"] = to_address
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=smtp_host,
            port=smtp_port,
            username=smtp_user or None,
            password=smtp_password or None,
            use_tls=use_tls,
        )
        return True
    except Exception as exc:
        logger.warning("Failed to send expiry email: %s", exc)
        return False


async def send_alert_digest(pool: asyncpg.Pool) -> None:
    """
    Send daily/weekly alert digests to tenant-configured recipients.
    """
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_password = os.environ.get("SMTP_PASSWORD", "")
    use_tls = os.environ.get("SMTP_TLS", "true").lower() == "true"
    from_address = os.environ.get("SMTP_FROM", "noreply@pulse.local")
    if not smtp_host:
        return

    now = datetime.now(timezone.utc)
    async with pool.acquire() as conn:
        settings_rows = await conn.fetch(
            """
            SELECT tenant_id, frequency, email, last_sent_at
            FROM alert_digest_settings
            WHERE frequency != 'disabled'
            """
        )

        for settings in settings_rows:
            tenant_id = settings["tenant_id"]
            frequency = settings["frequency"]
            if frequency == "disabled":
                continue
            email = (settings["email"] or "").strip()
            if not email:
                continue

            last_sent_at = settings["last_sent_at"]
            min_interval = timedelta(days=1 if frequency == "daily" else 7)
            if last_sent_at and (now - last_sent_at) < min_interval:
                continue

            summary = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) FILTER (WHERE severity >= 4) AS critical_count,
                    COUNT(*) FILTER (WHERE severity = 3) AS high_count,
                    COUNT(*) FILTER (WHERE severity = 2) AS medium_count,
                    COUNT(*) FILTER (WHERE severity <= 1) AS low_count,
                    COUNT(*) AS total_count
                FROM fleet_alert
                WHERE tenant_id = $1
                  AND status = 'OPEN'
                """,
                tenant_id,
            )
            total = int(summary["total_count"] or 0) if summary else 0
            if total <= 0:
                continue

            body = (
                f"Alert Digest for {tenant_id}\n"
                f"Generated: {now.isoformat()}\n\n"
                "Open Alerts Summary:\n"
                f"  CRITICAL: {int(summary['critical_count'] or 0)}\n"
                f"  HIGH: {int(summary['high_count'] or 0)}\n"
                f"  MEDIUM: {int(summary['medium_count'] or 0)}\n"
                f"  LOW: {int(summary['low_count'] or 0)}\n\n"
                f"Total open alerts: {total}\n\n"
                "Log in to OpsConductor to view and manage alerts.\n"
            )
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[OpsConductor] Alert Digest - {total} open alerts"
            msg["From"] = from_address
            msg["To"] = email
            msg.attach(MIMEText(body, "plain"))

            try:
                await aiosmtplib.send(
                    msg,
                    hostname=smtp_host,
                    port=smtp_port,
                    username=smtp_user or None,
                    password=smtp_password or None,
                    use_tls=use_tls,
                )
                await conn.execute(
                    """
                    UPDATE alert_digest_settings
                    SET last_sent_at = now(), updated_at = now()
                    WHERE tenant_id = $1
                    """,
                    tenant_id,
                )
            except Exception as exc:
                logger.warning("Failed to send alert digest for %s: %s", tenant_id, exc)


async def process_grace_transitions(pool: asyncpg.Pool) -> None:
    """Transition subscriptions based on term_end and grace_end."""
    async with pool.acquire() as conn:
        now = datetime.now(timezone.utc)

        rows = await conn.fetch(
            """
            UPDATE subscriptions
            SET status = 'GRACE',
                grace_end = term_end + interval '14 days',
                updated_at = now()
            WHERE status = 'ACTIVE'
              AND term_end < $1
            RETURNING subscription_id, tenant_id
            """,
            now,
        )

        for row in rows:
            logger.info("Transitioned %s to GRACE", row["subscription_id"])
            await conn.execute(
                """
                INSERT INTO subscription_audit
                    (tenant_id, event_type, actor_type, actor_id, details)
                VALUES ($1, 'GRACE_STARTED', 'system', 'subscription-worker', $2)
                """,
                row["tenant_id"],
                f'{{"subscription_id": "{row["subscription_id"]}"}}',
            )
            await conn.execute(
                """
                INSERT INTO subscription_notifications
                    (tenant_id, notification_type, scheduled_at, channel, status)
                VALUES ($1, 'GRACE_START', now(), 'email', 'PENDING')
                """,
                row["tenant_id"],
            )

        rows = await conn.fetch(
            """
            UPDATE subscriptions
            SET status = 'SUSPENDED',
                updated_at = now()
            WHERE status = 'GRACE'
              AND grace_end < $1
            RETURNING subscription_id, tenant_id
            """,
            now,
        )

        for row in rows:
            logger.info("Transitioned %s to SUSPENDED", row["subscription_id"])
            await conn.execute(
                """
                INSERT INTO subscription_audit
                    (tenant_id, event_type, actor_type, actor_id, details)
                VALUES ($1, 'STATUS_SUSPENDED', 'system', 'subscription-worker', $2)
                """,
                row["tenant_id"],
                f'{{"subscription_id": "{row["subscription_id"]}", "reason": "grace_period_expired"}}',
            )
            await conn.execute(
                """
                INSERT INTO subscription_notifications
                    (tenant_id, notification_type, scheduled_at, channel, status)
                VALUES ($1, 'SUSPENDED', now(), 'email', 'PENDING')
                """,
                row["tenant_id"],
            )


async def reconcile_device_counts(pool: asyncpg.Pool) -> None:
    """Nightly reconciliation of active_device_count with device_registry counts."""
    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            UPDATE subscriptions s
            SET active_device_count = (
                SELECT COUNT(*)
                FROM device_registry dr
                WHERE dr.subscription_id = s.subscription_id
                  AND dr.status = 'ACTIVE'
            ),
            updated_at = now()
            WHERE active_device_count != (
                SELECT COUNT(*)
                FROM device_registry dr
                WHERE dr.subscription_id = s.subscription_id
                  AND dr.status = 'ACTIVE'
            )
            """
        )

        count = int(result.split()[-1]) if result else 0
        if count > 0:
            logger.info("Reconciled device counts for %s subscriptions", count)


async def run_once() -> None:
    """Run all worker tasks once."""
    pool = await get_pool()
    try:
        logger.info("Starting subscription worker run...")
        await schedule_renewal_notifications(pool)
        await process_pending_notifications(pool)
        await send_alert_digest(pool)
        await process_grace_transitions(pool)
        await reconcile_device_counts(pool)
        logger.info("Subscription worker run complete")
    finally:
        await pool.close()


async def run_loop(interval_seconds: int = 3600) -> None:
    """Run worker tasks in a loop."""
    pool = await get_pool()
    try:
        while True:
            logger.info("Starting subscription worker run...")
            try:
                await schedule_renewal_notifications(pool)
                await process_pending_notifications(pool)
                await send_alert_digest(pool)
                await process_grace_transitions(pool)
                await reconcile_device_counts(pool)
            except Exception as exc:
                logger.error("Worker run failed: %s", exc)

            logger.info("Sleeping for %s seconds...", interval_seconds)
            await asyncio.sleep(interval_seconds)
    finally:
        await pool.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        asyncio.run(run_once())
    else:
        interval = int(os.getenv("WORKER_INTERVAL_SECONDS", "3600"))
        asyncio.run(run_loop(interval))
