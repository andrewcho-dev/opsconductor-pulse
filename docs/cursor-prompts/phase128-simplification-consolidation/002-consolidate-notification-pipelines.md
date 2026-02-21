# 002: Consolidate Notification Pipelines

## Goal

Create a single unified notification path: **alert -> routing engine -> senders.py -> all delivery types**. Currently, the system has two pipelines running simultaneously:

1. **Legacy pipeline**: `dispatcher/dispatcher.py` reads `fleet_alert` -> creates `delivery_jobs` -> `delivery_worker/worker.py` reads `delivery_jobs` -> calls email_sender/snmp_sender/mqtt_sender
2. **New pipeline**: `notifications/dispatcher.py` creates `notification_jobs` -> `delivery_worker/worker.py` reads `notification_jobs` -> calls inline sender logic for all channel types

After this change:
- `notifications/senders.py` will have **all** sender functions: `send_slack`, `send_pagerduty`, `send_teams`, `send_webhook`, `send_email`, `send_snmp`, `send_mqtt_alert`
- The notification routing engine (notification_channels + notification_routing_rules) will use these senders for all channel types
- The test endpoint in `routes/notifications.py` will be able to test all channel types directly
- The legacy dispatcher + delivery_worker are marked DEPRECATED but NOT removed (backward compat -- removal in Phase 129)

## Current State Analysis

### `services/ui_iot/notifications/senders.py` (current)
Currently has 4 sender functions:
- `send_slack(webhook_url, alert)` -- posts to Slack webhook
- `send_pagerduty(integration_key, alert)` -- posts to PagerDuty Events API
- `send_teams(webhook_url, alert)` -- posts to Teams webhook
- `send_webhook(url, method, headers, secret, alert)` -- generic HTTP webhook with HMAC signature

Missing: `send_email`, `send_snmp`, `send_mqtt_alert`

### `services/delivery_worker/email_sender.py`
Contains the full email sending implementation:
- `EmailResult` dataclass
- `send_alert_email()` function with SMTP support, TLS, Jinja2 templates, HTML/text formats
- `render_template()` helper
- `severity_label_for()` helper
- Default HTML and text templates
- Depends on `aiosmtplib` (optional import)

### `services/delivery_worker/snmp_sender.py`
Contains the full SNMP trap implementation:
- `SNMPTrapResult` dataclass
- `send_alert_trap()` function supporting SNMP v2c and v3
- Depends on `pysnmp` (optional import)
- v2c uses CommunityData, v3 uses UsmUserData with SHA auth and AES/DES priv

### `services/delivery_worker/mqtt_sender.py`
Contains the MQTT publish implementation:
- `MQTTResult` dataclass
- `publish_alert()` function using paho.mqtt
- Parses broker_url, connects, publishes, disconnects
- Runs blocking MQTT in executor

### `services/delivery_worker/worker.py`
The worker already processes BOTH pipelines:
- `process_job()` handles legacy `delivery_jobs` (webhook, snmp, email, mqtt via `deliver_*` functions)
- `process_notification_job()` handles new `notification_jobs` -- inline logic for each channel type
- Already imports and uses all three sender modules

### `services/ui_iot/notifications/dispatcher.py`
The routing engine creates `notification_jobs` entries in the DB. It matches alerts against `notification_routing_rules` joined with `notification_channels`. This is the path we want everything to flow through.

### `services/ui_iot/routes/notifications.py`
The `/customer/notification-channels/{channel_id}/test` endpoint currently:
- Tests slack, pagerduty, teams, webhook via `senders.py`
- Returns "queued" for email, snmp, mqtt (cannot test directly because senders are in delivery_worker)

## Step-by-Step Changes

### Step 1: Add `send_email` to `services/ui_iot/notifications/senders.py`

Add the email sender function. This should be a simplified version that takes configuration and alert data directly. Add at the end of the file, after the existing functions.

```python
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
        smtp_client = aiosmtplib.SMTP(hostname=smtp_host, port=smtp_port, start_tls=True, timeout=30)
    else:
        smtp_client = aiosmtplib.SMTP(hostname=smtp_host, port=smtp_port, timeout=30)

    async with smtp_client:
        if smtp_user and smtp_password:
            await smtp_client.login(smtp_user, smtp_password)
        await smtp_client.send_message(msg, recipients=all_recipients)
```

### Step 2: Add `send_snmp` to `services/ui_iot/notifications/senders.py`

Add the SNMP sender function after `send_email`:

```python
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
            usmHMACSHAAuthProtocol,
            usmAesCfb128Protocol,
            usmDESPrivProtocol,
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
                username, authKey=auth_password, privKey=priv_password,
                authProtocol=auth_proto, privProtocol=priv_proto,
            )
        elif auth_password:
            auth_data = UsmUserData(username, authKey=auth_password, authProtocol=auth_proto)
        else:
            auth_data = UsmUserData(username)
    else:
        raise ValueError(f"Unsupported SNMP version: {version}")

    transport = UdpTransportTarget((host, port), timeout=10, retries=1)

    alert_id = str(alert.get("alert_id", "unknown"))
    device_id = alert.get("device_id", "unknown")
    tenant_id = alert.get("tenant_id", "unknown")
    severity_str = str(alert.get("severity", "info"))
    message = alert.get("message", alert.get("summary", "Alert"))
    triggered_at = str(alert.get("triggered_at", alert.get("created_at", "")))

    severity_map = {"critical": 1, "4": 1, "5": 1, "warning": 2, "3": 2, "info": 3, "2": 3}
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
    error_indication, error_status, error_index, var_binds_out = await sendNotification(
        snmp_engine, auth_data, transport, ContextData(), "trap",
        NotificationType(ObjectIdentity(f"{oid_prefix}.0.1")),
        *var_binds,
    )

    if error_indication:
        raise RuntimeError(f"SNMP error: {error_indication}")
    if error_status:
        raise RuntimeError(f"SNMP error: {error_status.prettyPrint()} at {error_index}")
```

### Step 3: Add `send_mqtt_alert` to `services/ui_iot/notifications/senders.py`

Add the MQTT sender function after `send_snmp`:

```python
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

    # Resolve topic placeholders
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

    def _publish_blocking():
        client = paho_mqtt.Client()
        if username and password:
            client.username_pw_set(username, password)
        client.connect(broker_host, broker_port, keepalive=10)
        client.publish(resolved_topic, payload_json, qos=qos, retain=retain)
        client.disconnect()

    await asyncio.get_event_loop().run_in_executor(None, _publish_blocking)
```

### Step 4: Update the test endpoint in `services/ui_iot/routes/notifications.py`

Currently the test endpoint at `/customer/notification-channels/{channel_id}/test` returns "queued" for email, snmp, and mqtt because it cannot test directly. Now that we have all senders in `senders.py`, update the imports and the test handler.

**File**: `services/ui_iot/routes/notifications.py`

**Change the import** at line 13 from:
```python
from notifications.senders import send_pagerduty, send_slack, send_teams, send_webhook
```
to:
```python
from notifications.senders import (
    send_pagerduty,
    send_slack,
    send_teams,
    send_webhook,
    send_email,
    send_snmp,
    send_mqtt_alert,
)
```

**Update the `test_channel` function** (around line 203). Replace the existing handler body's channel type branches. The full function should become:

```python
@router.post("/notification-channels/{channel_id}/test")
async def test_channel(channel_id: int, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        channel = await conn.fetchrow(
            """
            SELECT channel_id, tenant_id, name, channel_type, config, is_enabled
            FROM notification_channels
            WHERE tenant_id = $1 AND channel_id = $2
            """,
            tenant_id,
            channel_id,
        )
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    test_alert = {
        "alert_id": 0,
        "alert_type": "TEST",
        "severity": 3,
        "device_id": "test-device",
        "site_id": None,
        "tenant_id": tenant_id,
        "message": "This is a test notification from OpsConductor-Pulse",
        "summary": "This is a test notification from OpsConductor-Pulse",
        "details": {},
        "triggered_at": datetime.now(timezone.utc).isoformat(),
    }
    ch = dict(channel)
    cfg = ch.get("config") or {}
    try:
        if ch["channel_type"] == "slack":
            await send_slack(cfg["webhook_url"], test_alert)
        elif ch["channel_type"] == "pagerduty":
            await send_pagerduty(cfg["integration_key"], test_alert)
        elif ch["channel_type"] == "teams":
            await send_teams(cfg["webhook_url"], test_alert)
        elif ch["channel_type"] in ("webhook", "http"):
            await send_webhook(
                cfg["url"],
                cfg.get("method", "POST"),
                cfg.get("headers", {}),
                cfg.get("secret"),
                test_alert,
            )
        elif ch["channel_type"] == "email":
            await send_email(
                smtp_config=cfg.get("smtp", {}),
                recipients=cfg.get("recipients", {}),
                alert=test_alert,
                template=cfg.get("template"),
            )
        elif ch["channel_type"] == "snmp":
            await send_snmp(snmp_config=cfg, alert=test_alert)
        elif ch["channel_type"] == "mqtt":
            await send_mqtt_alert(mqtt_config=cfg, alert=test_alert)
        return {"status": "ok", "message": "Test notification sent successfully"}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Test send failed: {str(exc)}")
```

### Step 5: Mark `dispatcher` service as DEPRECATED in docker-compose

**File**: `compose/docker-compose.yml`

Add deprecation labels and a deprecation startup log to the `dispatcher` service. Modify the `dispatcher` service definition:

Add these labels under the `dispatcher` service:
```yaml
  dispatcher:
    build:
      context: ../services
      dockerfile: dispatcher/Dockerfile
    container_name: iot-dispatcher
    labels:
      com.opsconductor.status: "DEPRECATED"
      com.opsconductor.deprecated-since: "2026-02-16"
      com.opsconductor.removal-phase: "phase129"
    environment:
      # ... existing env vars unchanged ...
```

### Step 6: Mark `delivery_worker` service as DEPRECATED in docker-compose

**File**: `compose/docker-compose.yml`

Add the same deprecation labels to the `delivery_worker` service:
```yaml
  delivery_worker:
    build:
      context: ../services
      dockerfile: delivery_worker/Dockerfile
    container_name: iot-delivery-worker
    labels:
      com.opsconductor.status: "DEPRECATED"
      com.opsconductor.deprecated-since: "2026-02-16"
      com.opsconductor.removal-phase: "phase129"
    environment:
      # ... existing env vars unchanged ...
```

### Step 7: Add deprecation logging to dispatcher

**File**: `services/dispatcher/dispatcher.py`

At the very top of the `main()` function (line 387, right after `async def main() -> None:`), add:
```python
    logger.warning(
        "DEPRECATED: The dispatcher service is deprecated and will be removed in Phase 129. "
        "Use notification_channels + notification_routing_rules pipeline instead."
    )
```

### Step 8: Add deprecation logging to delivery_worker

**File**: `services/delivery_worker/worker.py`

At the very top of the `run_worker()` function (line 887, right after `async def run_worker() -> None:`), add:
```python
    logger.warning(
        "DEPRECATED: The delivery_worker service is deprecated and will be removed in Phase 129. "
        "Notification delivery is being consolidated into the notification_channels pipeline."
    )
```

### Step 9: Ensure `aiosmtplib` and `paho-mqtt` are in ui_iot requirements

Check if `services/ui_iot/requirements.txt` (or `pyproject.toml`) includes `aiosmtplib` and `paho-mqtt`. If not, add them as optional dependencies. The senders use lazy imports with try/except, so they will gracefully degrade if not installed, but for full functionality they should be present.

```bash
grep -i "aiosmtplib\|paho" services/ui_iot/requirements.txt 2>/dev/null || echo "Not found"
```

If missing, add these lines to `services/ui_iot/requirements.txt`:
```
aiosmtplib>=2.0
paho-mqtt>=1.6
```

Note: `pysnmp` has complex dependencies and may not be practical to install in the ui_iot container. The `send_snmp` function uses a lazy import with a clear error message, so SNMP test will fail gracefully if pysnmp is not installed. For now, SNMP test delivery will still be queued via the delivery_worker. This is acceptable -- full SNMP consolidation can happen when the delivery_worker is removed in Phase 129.

## Verification

```bash
# 1. Validate compose
cd compose && docker compose config --quiet && echo "PASS"

# 2. Build and start
docker compose up -d --build

# 3. Check deprecation warnings in logs
docker compose logs dispatcher --tail 5 | grep -i "DEPRECATED"
docker compose logs delivery_worker --tail 5 | grep -i "DEPRECATED"

# 4. Check deprecation labels
docker inspect iot-dispatcher --format '{{.Config.Labels}}' | grep -i deprecated
docker inspect iot-delivery-worker --format '{{.Config.Labels}}' | grep -i deprecated

# 5. Test all channel types via the /customer/notification-channels/{id}/test endpoint
# (Requires a running system with auth -- use E2E tests or curl with JWT)

# 6. Verify senders.py has all functions
grep -E "^async def send_" services/ui_iot/notifications/senders.py
# Expected output:
# async def send_slack(webhook_url: str, alert: dict) -> None:
# async def send_pagerduty(integration_key: str, alert: dict) -> None:
# async def send_teams(webhook_url: str, alert: dict) -> None:
# async def send_webhook(
# async def send_email(
# async def send_snmp(
# async def send_mqtt_alert(
```

## Commit

```
feat: consolidate all notification senders into unified pipeline

Add send_email, send_snmp, and send_mqtt_alert to
notifications/senders.py, copying core logic from
delivery_worker/{email,snmp,mqtt}_sender.py.

Update /customer/notification-channels/{id}/test to directly test
all channel types (email, SNMP, MQTT) instead of returning "queued".

Mark dispatcher and delivery_worker as DEPRECATED in docker-compose
labels and startup logging. These services will be removed in Phase 129.

The notification_channels + notification_routing_rules pipeline is now
the single path for all alert delivery types.
```
