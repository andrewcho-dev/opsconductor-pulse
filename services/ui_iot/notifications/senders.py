import asyncio
import hashlib
import hmac
import json
import logging
import time

import httpx

logger = logging.getLogger(__name__)

# Status codes that are retryable
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
# Status codes that should NOT be retried (client errors)
NON_RETRYABLE_STATUS_CODES = {400, 401, 403, 404}
# Retry delays in seconds (exponential backoff)
RETRY_DELAYS = [1, 5, 25]
MAX_ATTEMPTS = 3


def severity_label(severity: int) -> str:
    if severity >= 4:
        return "CRITICAL"
    if severity >= 3:
        return "HIGH"
    if severity >= 2:
        return "MEDIUM"
    return "LOW"


def severity_color(severity: int) -> str:
    if severity >= 4:
        return "#ef4444"
    if severity >= 3:
        return "#f97316"
    if severity >= 2:
        return "#f59e0b"
    return "#6b7280"


def pd_severity(severity: int) -> str:
    if severity >= 4:
        return "critical"
    if severity >= 3:
        return "error"
    if severity >= 2:
        return "warning"
    return "info"


async def send_slack(webhook_url: str, alert: dict) -> dict:
    """Send alert notification to Slack."""
    payload = {
        "text": f"*[{severity_label(int(alert.get('severity', 0)))}]* {alert.get('device_id', '-') } — {alert.get('alert_type', '-')}",
        "attachments": [
            {
                "color": severity_color(int(alert.get("severity", 0))),
                "fields": [
                    {"title": "Summary", "value": alert.get("summary", "—"), "short": False},
                    {"title": "Time", "value": str(alert.get("created_at", "—")), "short": True},
                ],
            }
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(webhook_url, json=payload)
        return {"success": 200 <= response.status_code < 300, "status_code": response.status_code}
    except Exception as exc:
        logger.warning("Slack delivery failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def send_pagerduty(integration_key: str, alert: dict) -> dict:
    """Send alert notification to PagerDuty."""
    payload = {
        "routing_key": integration_key,
        "event_action": "trigger",
        "dedup_key": f"alert-{alert.get('alert_id')}",
        "payload": {
            "summary": f"{alert.get('alert_type', 'ALERT')} on {alert.get('device_id', '-')}",
            "severity": pd_severity(int(alert.get("severity", 0))),
            "source": alert.get("device_id", "unknown-device"),
            "custom_details": alert,
        },
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post("https://events.pagerduty.com/v2/enqueue", json=payload)
        return {"success": 200 <= response.status_code < 300, "status_code": response.status_code}
    except Exception as exc:
        logger.warning("PagerDuty delivery failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def send_teams(webhook_url: str, alert: dict) -> dict:
    """Send alert notification to Microsoft Teams."""
    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": severity_color(int(alert.get("severity", 0))).replace("#", ""),
        "summary": f"Alert: {alert.get('alert_type', 'UNKNOWN')}",
        "sections": [
            {
                "activityTitle": alert.get("device_id", "-"),
                "activityText": alert.get("summary", ""),
            }
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(webhook_url, json=payload)
        return {"success": 200 <= response.status_code < 300, "status_code": response.status_code}
    except Exception as exc:
        logger.warning("Teams delivery failed: %s", exc)
        return {"success": False, "error": str(exc)}


def compute_webhook_signature(body: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature for webhook payload.

    Returns signature in format: sha256=<hex_digest>
    """
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


async def send_webhook(
    url: str,
    method: str,
    headers: dict,
    secret: str | None,
    alert: dict,
    *,
    audit_logger=None,
    channel_id: str | None = None,
    tenant_id: str | None = None,
) -> dict:
    """Send a webhook with HMAC-SHA256 signing and exponential backoff retry."""
    body = json.dumps(alert, default=str).encode()
    req_headers = {"Content-Type": "application/json", **(headers or {})}

    if secret:
        req_headers["X-Signature-256"] = compute_webhook_signature(body, secret)

    last_error: str | None = None
    last_status: int | None = None
    total_start = time.monotonic()

    for attempt in range(1, MAX_ATTEMPTS + 1):
        attempt_start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.request(
                    method.upper(), url, content=body, headers=req_headers
                )

            attempt_duration_ms = int((time.monotonic() - attempt_start) * 1000)
            last_status = response.status_code

            logger.info(
                "webhook_delivery_attempt",
                extra={
                    "url": url,
                    "method": method.upper(),
                    "status_code": response.status_code,
                    "attempt": attempt,
                    "duration_ms": attempt_duration_ms,
                    "channel_id": channel_id,
                    "tenant_id": tenant_id,
                },
            )

            # Success: 2xx
            if 200 <= response.status_code < 300:
                total_duration_ms = int((time.monotonic() - total_start) * 1000)
                if audit_logger and tenant_id:
                    audit_logger.notification_delivered(
                        tenant_id,
                        channel_type="webhook",
                        channel_id=channel_id,
                        status="delivered",
                        details={
                            "url": url,
                            "status_code": response.status_code,
                            "attempts": attempt,
                            "duration_ms": total_duration_ms,
                        },
                    )
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "attempts": attempt,
                    "duration_ms": total_duration_ms,
                    "error": None,
                }

            # Non-retryable client error
            if response.status_code in NON_RETRYABLE_STATUS_CODES:
                last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.warning(
                    "webhook_delivery_failed_non_retryable",
                    extra={
                        "url": url,
                        "status_code": response.status_code,
                        "attempt": attempt,
                        "response_body": response.text[:200],
                        "channel_id": channel_id,
                        "tenant_id": tenant_id,
                    },
                )
                break  # Do not retry

            # Retryable server error
            last_error = f"HTTP {response.status_code}"
            if response.status_code in RETRYABLE_STATUS_CODES and attempt < MAX_ATTEMPTS:
                delay = RETRY_DELAYS[attempt - 1]
                logger.warning(
                    "webhook_delivery_retry",
                    extra={
                        "url": url,
                        "status_code": response.status_code,
                        "attempt": attempt,
                        "retry_delay_s": delay,
                        "channel_id": channel_id,
                        "tenant_id": tenant_id,
                    },
                )
                await asyncio.sleep(delay)

        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
            attempt_duration_ms = int((time.monotonic() - attempt_start) * 1000)
            last_error = f"{type(exc).__name__}: {str(exc)[:200]}"

            logger.warning(
                "webhook_delivery_connection_error",
                extra={
                    "url": url,
                    "attempt": attempt,
                    "duration_ms": attempt_duration_ms,
                    "error": last_error,
                    "channel_id": channel_id,
                    "tenant_id": tenant_id,
                },
            )

            if attempt < MAX_ATTEMPTS:
                delay = RETRY_DELAYS[attempt - 1]
                await asyncio.sleep(delay)

        except Exception as exc:
            last_error = f"{type(exc).__name__}: {str(exc)[:200]}"
            logger.exception(
                "webhook_delivery_unexpected_error",
                extra={
                    "url": url,
                    "attempt": attempt,
                    "channel_id": channel_id,
                    "tenant_id": tenant_id,
                },
            )
            break  # Do not retry unknown errors

    # All attempts exhausted or non-retryable error
    total_duration_ms = int((time.monotonic() - total_start) * 1000)

    logger.error(
        "webhook_delivery_failed",
        extra={
            "url": url,
            "attempts": attempt,
            "last_status": last_status,
            "last_error": last_error,
            "duration_ms": total_duration_ms,
            "channel_id": channel_id,
            "tenant_id": tenant_id,
        },
    )

    if audit_logger and tenant_id:
        audit_logger.notification_failed(
            tenant_id,
            channel_type="webhook",
            channel_id=channel_id,
            error=last_error or "Unknown error",
            details={
                "url": url,
                "last_status": last_status,
                "attempts": attempt,
                "duration_ms": total_duration_ms,
            },
        )

    return {
        "success": False,
        "status_code": last_status,
        "attempts": attempt,
        "duration_ms": total_duration_ms,
        "error": last_error,
    }


# --- Email sender ---

async def send_email(
    smtp_config: dict,
    recipients: dict,
    alert: dict,
    template: dict | None = None,
) -> None:
    """Send an alert email via SMTP.

    Args:
        smtp_config: dict with keys smtp_host, smtp_port (default 587),
                     smtp_user, smtp_password, smtp_tls (default True),
                     from_address, from_name
        recipients: dict with keys to (list), cc (list), bcc (list)
        alert: standard alert payload dict
        template: optional dict with subject_template, body_template, format
    """
    try:
        import aiosmtplib
    except ImportError:
        raise RuntimeError("aiosmtplib not installed -- email delivery unavailable")

    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    smtp_host = smtp_config.get("smtp_host")
    if not smtp_host:
        raise ValueError("smtp_host is required")

    smtp_port = int(smtp_config.get("smtp_port", 587))
    smtp_user = smtp_config.get("smtp_user")
    smtp_password = smtp_config.get("smtp_password")
    smtp_tls = smtp_config.get("smtp_tls", True)
    from_address = smtp_config.get("from_address", "alerts@example.com")
    from_name = smtp_config.get("from_name", "OpsConductor Alerts")

    to_addrs = recipients.get("to", [])
    cc_addrs = recipients.get("cc", [])
    bcc_addrs = recipients.get("bcc", [])
    all_recipients = to_addrs + cc_addrs + bcc_addrs
    if not all_recipients:
        raise ValueError("No recipients specified")

    severity = int(alert.get("severity", 0))
    sev_label = severity_label(severity)
    device_id = alert.get("device_id", "-")
    alert_type = alert.get("alert_type", "ALERT")
    message = alert.get("message", alert.get("summary", ""))
    triggered_at = alert.get("triggered_at", alert.get("created_at", ""))

    template = template or {}
    subject_template = template.get("subject_template", "[{severity}] {alert_type}: {device_id}")
    body_format = template.get("format", "html")

    subject = subject_template.format(
        severity=sev_label,
        alert_type=alert_type,
        device_id=device_id,
    )

    body_text = (
        f"ALERT: {alert_type}\n"
        f"Device: {device_id}\n"
        f"Severity: {sev_label}\n"
        f"Message: {message}\n"
        f"Time: {triggered_at}\n"
        f"\n--\nSent by OpsConductor Pulse."
    )

    if body_format == "html":
        body_html = (
            f"<h2 style='color:{severity_color(severity)}'>{alert_type}</h2>"
            f"<p><b>Device:</b> {device_id}</p>"
            f"<p><b>Severity:</b> {sev_label}</p>"
            f"<p><b>Message:</b> {message}</p>"
            f"<p><b>Time:</b> {triggered_at}</p>"
            f"<hr><small>Sent by OpsConductor Pulse.</small>"
        )
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(body_text, "plain"))
        msg.attach(MIMEText(body_html, "html"))
    else:
        msg = MIMEText(body_text, "plain")

    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_address}>" if from_name else from_address
    if to_addrs:
        msg["To"] = ", ".join(to_addrs)
    if cc_addrs:
        msg["Cc"] = ", ".join(cc_addrs)

    if smtp_tls:
        smtp_client = aiosmtplib.SMTP(
            hostname=smtp_host, port=smtp_port, start_tls=True, timeout=30
        )
    else:
        smtp_client = aiosmtplib.SMTP(hostname=smtp_host, port=smtp_port, timeout=30)

    async with smtp_client:
        if smtp_user and smtp_password:
            await smtp_client.login(smtp_user, smtp_password)
        await smtp_client.send_message(msg, recipients=all_recipients)


# --- SNMP sender ---

async def send_snmp(
    snmp_config: dict,
    alert: dict,
) -> None:
    """Send an SNMP trap for an alert.

    Args:
        snmp_config: dict with keys:
            host (required), port (default 162),
            version ("2c" or "3"), community (for v2c),
            username, auth_password, priv_password (for v3),
            oid_prefix (default "1.3.6.1.4.1.99999")
        alert: standard alert payload dict
    """
    try:
        from pysnmp.hlapi.v3arch.asyncio import (
            CommunityData,
            ContextData,
            NotificationType,
            ObjectIdentity,
            ObjectType,
            OctetString,
            SnmpEngine,
            UdpTransportTarget,
            UsmUserData,
            sendNotification,
            usmAesCfb128Protocol,
            usmDESPrivProtocol,
            usmHMACSHAAuthProtocol,
        )
    except ImportError:
        raise RuntimeError("pysnmp not installed -- SNMP delivery unavailable")

    host = snmp_config.get("host")
    if not host:
        raise ValueError("SNMP host is required")

    port = int(snmp_config.get("port", 162))
    version = snmp_config.get("version", "2c")
    oid_prefix = snmp_config.get("oid_prefix", "1.3.6.1.4.1.99999")

    if version == "2c":
        community = snmp_config.get("community", "public")
        auth_data = CommunityData(community, mpModel=1)
    elif version == "3":
        username = snmp_config.get("username", "")
        auth_password = snmp_config.get("auth_password")
        priv_password = snmp_config.get("priv_password")
        priv_protocol = snmp_config.get("priv_protocol")

        auth_proto = usmHMACSHAAuthProtocol
        priv_proto = None
        if priv_password:
            priv_proto = usmAesCfb128Protocol if priv_protocol == "AES" else usmDESPrivProtocol

        if priv_password:
            auth_data = UsmUserData(
                username,
                authKey=auth_password,
                privKey=priv_password,
                authProtocol=auth_proto,
                privProtocol=priv_proto,
            )
        elif auth_password:
            auth_data = UsmUserData(username, authKey=auth_password, authProtocol=auth_proto)
        else:
            auth_data = UsmUserData(username)
    else:
        raise ValueError(f"Unsupported SNMP version: {version}")

    transport = UdpTransportTarget((host, port), timeout=10, retries=1)

    alert_id = str(alert.get("alert_id", "unknown"))
    device_id = str(alert.get("device_id", "unknown"))
    tenant_id = str(alert.get("tenant_id", "unknown"))
    severity_str = str(alert.get("severity", "info"))
    message = str(alert.get("message", alert.get("summary", "Alert")))
    triggered_at = str(alert.get("triggered_at", alert.get("created_at", "")))

    severity_map = {
        "critical": 1,
        "4": 1,
        "5": 1,
        "warning": 2,
        "3": 2,
        "info": 3,
        "2": 3,
    }
    severity_int = severity_map.get(severity_str.lower(), 4)

    var_binds = [
        ObjectType(ObjectIdentity(f"{oid_prefix}.1.1.0"), OctetString(alert_id)),
        ObjectType(ObjectIdentity(f"{oid_prefix}.1.2.0"), OctetString(device_id)),
        ObjectType(ObjectIdentity(f"{oid_prefix}.1.3.0"), OctetString(tenant_id)),
        ObjectType(ObjectIdentity(f"{oid_prefix}.1.4.0"), severity_int),
        ObjectType(ObjectIdentity(f"{oid_prefix}.1.5.0"), OctetString(message)),
        ObjectType(ObjectIdentity(f"{oid_prefix}.1.6.0"), OctetString(triggered_at)),
    ]

    snmp_engine = SnmpEngine()
    error_indication, error_status, error_index, _var_binds_out = await sendNotification(
        snmp_engine,
        auth_data,
        transport,
        ContextData(),
        "trap",
        NotificationType(ObjectIdentity(f"{oid_prefix}.0.1")),
        *var_binds,
    )

    if error_indication:
        raise RuntimeError(f"SNMP error: {error_indication}")
    if error_status:
        raise RuntimeError(f"SNMP error: {error_status.prettyPrint()} at {error_index}")


# --- MQTT alert sender ---

async def send_mqtt_alert(
    mqtt_config: dict,
    alert: dict,
) -> None:
    """Publish an alert to an MQTT broker.

    Args:
        mqtt_config: dict with keys:
            broker_host (required), broker_port (default 1883),
            topic (required -- may contain {tenant_id}, {device_id}, etc. placeholders),
            qos (default 1), retain (default False),
            username, password (optional auth)
        alert: standard alert payload dict
    """
    try:
        import paho.mqtt.client as paho_mqtt
    except ImportError:
        raise RuntimeError("paho-mqtt not installed -- MQTT delivery unavailable")

    import asyncio

    broker_host = mqtt_config.get("broker_host")
    if not broker_host:
        raise ValueError("broker_host is required")
    broker_port = int(mqtt_config.get("broker_port", 1883))
    topic = mqtt_config.get("topic")
    if not topic:
        raise ValueError("topic is required")
    qos = int(mqtt_config.get("qos", 1))
    retain = bool(mqtt_config.get("retain", False))
    username = mqtt_config.get("username")
    password = mqtt_config.get("password")

    replacements = {
        "tenant_id": alert.get("tenant_id"),
        "severity": alert.get("severity"),
        "site_id": alert.get("site_id"),
        "device_id": alert.get("device_id"),
        "alert_id": alert.get("alert_id"),
        "alert_type": alert.get("alert_type"),
    }
    resolved_topic = topic
    for key, value in replacements.items():
        if value is not None:
            resolved_topic = resolved_topic.replace(f"{{{key}}}", str(value))

    payload_json = json.dumps(alert)

    def _publish_blocking() -> None:
        client = paho_mqtt.Client()
        if username and password:
            client.username_pw_set(username, password)
        client.connect(broker_host, broker_port, keepalive=10)
        client.publish(resolved_topic, payload_json, qos=qos, retain=retain)
        client.disconnect()

    await asyncio.get_running_loop().run_in_executor(None, _publish_blocking)
