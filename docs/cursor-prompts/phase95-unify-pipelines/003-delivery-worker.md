# Phase 95 — Extend delivery_worker to Process notification_jobs

## File to modify
`services/delivery_worker/worker.py`

## Goal

Extend the delivery_worker to poll **both** `delivery_jobs` (old integrations pipeline) **and**
`notification_jobs` (new unified channel pipeline). No existing logic is changed. New logic is added
alongside it.

## What to add to worker.py

Add the following functions and integrate them into the main worker loop.

### Step 1: Add import at the top of worker.py

The worker needs access to the notification senders. Since `senders.py` lives in the ui_iot service,
copy the sender functions into delivery_worker OR re-implement them there. The cleanest approach
for now is to duplicate the four sender functions in worker.py (they are pure HTTP calls with no
service-specific dependencies). Add these near the bottom of the file, before `main()`.

```python
# ── Notification channel senders (for notification_jobs pipeline) ──────────

import hmac
import hashlib

async def _send_notification_channel(session, channel: dict, payload: dict) -> None:
    """
    Route notification to the correct sender based on channel_type.
    Raises on failure so the worker can retry.
    """
    ctype = channel["channel_type"]
    cfg = channel["config"] or {}

    if ctype == "slack":
        await _nc_send_slack(session, cfg["webhook_url"], payload)
    elif ctype == "pagerduty":
        await _nc_send_pagerduty(session, cfg["integration_key"], payload)
    elif ctype == "teams":
        await _nc_send_teams(session, cfg["webhook_url"], payload)
    elif ctype in ("webhook", "http"):
        await _nc_send_webhook(
            session,
            cfg["url"],
            cfg.get("method", "POST"),
            cfg.get("headers", {}),
            cfg.get("secret"),
            payload,
        )
    elif ctype == "email":
        # Delegate to existing email delivery logic
        # Build a minimal integration-compatible dict and call deliver_email()
        email_integration = {
            "integration_id": f"nc_{channel['channel_id']}",
            "type": "email",
            "email_config": cfg.get("smtp", {}),
            "email_recipients": cfg.get("recipients", {}),
            "email_template": cfg.get("template", {}),
        }
        fake_job = {"payload_json": payload, "tenant_id": payload.get("tenant_id", "")}
        await deliver_email(email_integration, fake_job)
    elif ctype == "snmp":
        snmp_integration = {
            "integration_id": f"nc_{channel['channel_id']}",
            "type": "snmp",
            "snmp_host": cfg.get("host", ""),
            "snmp_port": cfg.get("port", 162),
            "snmp_config": cfg,
        }
        fake_job = {"payload_json": payload, "tenant_id": payload.get("tenant_id", "")}
        await deliver_snmp(snmp_integration, fake_job)
    elif ctype == "mqtt":
        mqtt_integration = {
            "integration_id": f"nc_{channel['channel_id']}",
            "type": "mqtt",
            "mqtt_topic": cfg.get("topic", "pulse/alerts"),
            "mqtt_qos": cfg.get("qos", 1),
            "mqtt_retain": cfg.get("retain", False),
            "mqtt_config": cfg,
        }
        fake_job = {"payload_json": payload, "tenant_id": payload.get("tenant_id", "")}
        await deliver_mqtt(mqtt_integration, fake_job)
    else:
        raise ValueError(f"Unknown channel_type: {ctype!r}")


async def _nc_send_slack(session, webhook_url: str, alert: dict) -> None:
    severity = alert.get("severity", 0)
    color = "#e94560" if severity >= 4 else "#ff9800" if severity >= 3 else "#2196f3"
    payload = {
        "text": f"*[{_severity_label(severity)}]* {alert.get('message', 'Alert')}",
        "attachments": [{
            "color": color,
            "fields": [
                {"title": "Device", "value": alert.get("device_id", "unknown"), "short": True},
                {"title": "Type",   "value": alert.get("alert_type", ""), "short": True},
            ],
        }],
    }
    async with session.post(webhook_url, json=payload) as resp:
        if resp.status >= 400:
            text = await resp.text()
            raise RuntimeError(f"Slack returned {resp.status}: {text}")


async def _nc_send_pagerduty(session, integration_key: str, alert: dict) -> None:
    severity = alert.get("severity", 0)
    pd_sev = "critical" if severity >= 4 else "error" if severity >= 3 else "warning" if severity >= 2 else "info"
    payload = {
        "routing_key": integration_key,
        "event_action": "trigger",
        "dedup_key": f"pulse-alert-{alert.get('alert_id', 0)}",
        "payload": {
            "summary": alert.get("message", "Alert"),
            "severity": pd_sev,
            "source": alert.get("device_id", "unknown"),
            "custom_details": alert.get("details", {}),
        },
    }
    async with session.post(
        "https://events.pagerduty.com/v2/enqueue", json=payload
    ) as resp:
        if resp.status >= 400:
            text = await resp.text()
            raise RuntimeError(f"PagerDuty returned {resp.status}: {text}")


async def _nc_send_teams(session, webhook_url: str, alert: dict) -> None:
    severity = alert.get("severity", 0)
    color = "e94560" if severity >= 4 else "ff9800" if severity >= 3 else "2196f3"
    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": color,
        "sections": [{
            "activityTitle": f"[{_severity_label(severity)}] {alert.get('message', 'Alert')}",
            "activityText": f"Device: {alert.get('device_id', 'unknown')} | Type: {alert.get('alert_type', '')}",
        }],
    }
    async with session.post(webhook_url, json=payload) as resp:
        if resp.status >= 400:
            text = await resp.text()
            raise RuntimeError(f"Teams returned {resp.status}: {text}")


async def _nc_send_webhook(session, url: str, method: str, headers: dict, secret, alert: dict) -> None:
    body = json.dumps(alert).encode()
    req_headers = {"Content-Type": "application/json", **(headers or {})}
    if secret:
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        req_headers["X-Signature-SHA256"] = sig
    async with session.request(method, url, data=body, headers=req_headers) as resp:
        if resp.status >= 400:
            text = await resp.text()
            raise RuntimeError(f"Webhook returned {resp.status}: {text}")


def _severity_label(severity: int) -> str:
    if severity >= 4: return "CRITICAL"
    if severity >= 3: return "HIGH"
    if severity >= 2: return "MEDIUM"
    return "LOW"
```

### Step 2: Add notification_jobs fetch function

```python
async def fetch_notification_jobs(conn, batch_size: int = 10) -> list:
    """Fetch pending notification_jobs ready for processing."""
    return await conn.fetch(
        """
        UPDATE notification_jobs
        SET status = 'PROCESSING', updated_at = NOW()
        WHERE job_id IN (
            SELECT job_id FROM notification_jobs
            WHERE status = 'PENDING'
              AND next_run_at <= NOW()
            ORDER BY priority_order, next_run_at
            LIMIT $1
            FOR UPDATE SKIP LOCKED
        )
        RETURNING
            job_id, tenant_id, alert_id, channel_id, rule_id,
            deliver_on_event, attempts, payload_json
        """,
        batch_size,
    )
    # Note: notification_jobs has no priority column yet — remove ORDER BY priority_order
    # or use: ORDER BY next_run_at
```

**Correction** — use this simpler version since notification_jobs has no priority column:

```python
async def fetch_notification_jobs(conn, batch_size: int = 10) -> list:
    return await conn.fetch(
        """
        UPDATE notification_jobs
        SET status = 'PROCESSING', updated_at = NOW()
        WHERE job_id IN (
            SELECT job_id FROM notification_jobs
            WHERE status = 'PENDING'
              AND next_run_at <= NOW()
            ORDER BY next_run_at
            LIMIT $1
            FOR UPDATE SKIP LOCKED
        )
        RETURNING
            job_id, tenant_id, alert_id, channel_id, rule_id,
            deliver_on_event, attempts, payload_json
        """,
        batch_size,
    )
```

### Step 3: Add notification_job completion/retry/failure functions

```python
async def complete_notification_job(conn, job_id: int, channel_id: int, alert_id: int) -> None:
    await conn.execute(
        "UPDATE notification_jobs SET status='COMPLETED', updated_at=NOW() WHERE job_id=$1",
        job_id,
    )
    await conn.execute(
        """
        INSERT INTO notification_log (channel_id, alert_id, job_id, success)
        VALUES ($1, $2, $3, TRUE)
        ON CONFLICT DO NOTHING
        """,
        channel_id, alert_id, job_id,
    )


async def retry_notification_job(conn, job_id: int, attempts: int, error: str) -> None:
    backoff_base = int(os.getenv("WORKER_BACKOFF_BASE_SECONDS", 30))
    backoff_max  = int(os.getenv("WORKER_BACKOFF_MAX_SECONDS", 7200))
    delay = min(backoff_base * (2 ** attempts), backoff_max)
    await conn.execute(
        """
        UPDATE notification_jobs
        SET status='PENDING', attempts=$1, next_run_at=NOW() + ($2::int * INTERVAL '1 second'),
            last_error=$3, updated_at=NOW()
        WHERE job_id=$4
        """,
        attempts + 1, delay, error[:500], job_id,
    )


async def fail_notification_job(conn, job_id: int, channel_id: int, alert_id: int, error: str) -> None:
    await conn.execute(
        """
        UPDATE notification_jobs
        SET status='FAILED', last_error=$1, updated_at=NOW()
        WHERE job_id=$2
        """,
        error[:500], job_id,
    )
    await conn.execute(
        """
        INSERT INTO notification_log (channel_id, alert_id, job_id, success, error_msg)
        VALUES ($1, $2, $3, FALSE, $4)
        ON CONFLICT DO NOTHING
        """,
        channel_id, alert_id, job_id, error[:500],
    )
```

### Step 4: Add process_notification_job function

```python
async def process_notification_job(conn, session, job: dict) -> None:
    job_id     = job["job_id"]
    channel_id = job["channel_id"]
    alert_id   = job["alert_id"]
    attempts   = job["attempts"]
    max_attempts = int(os.getenv("WORKER_MAX_ATTEMPTS", 5))
    payload    = job["payload_json"]
    if isinstance(payload, str):
        payload = json.loads(payload)

    # Fetch the channel config
    channel = await conn.fetchrow(
        "SELECT channel_id, channel_type, config, is_enabled FROM notification_channels WHERE channel_id=$1",
        channel_id,
    )
    if not channel:
        await fail_notification_job(conn, job_id, channel_id, alert_id, "Channel not found")
        return
    if not channel["is_enabled"]:
        await fail_notification_job(conn, job_id, channel_id, alert_id, "Channel disabled")
        return

    try:
        await _send_notification_channel(session, dict(channel), payload)
        await complete_notification_job(conn, job_id, channel_id, alert_id)
        logger.info("notification_job %s completed (channel=%s)", job_id, channel_id)
    except Exception as exc:
        error = str(exc)
        logger.warning("notification_job %s failed attempt %d: %s", job_id, attempts + 1, error)
        if attempts + 1 >= max_attempts:
            await fail_notification_job(conn, job_id, channel_id, alert_id, error)
            logger.error("notification_job %s permanently failed", job_id)
        else:
            await retry_notification_job(conn, job_id, attempts, error)
```

### Step 5: Integrate into main worker loop

Find the main polling loop in worker.py — it currently fetches delivery_jobs and calls process_job().
Extend it to also process notification_jobs in the same loop iteration.

Look for the section that calls `fetch_jobs()`. After processing delivery_jobs, add:

```python
# Also process notification_jobs (new unified pipeline)
async with pool.acquire() as conn:
    notification_batch = await fetch_notification_jobs(conn, batch_size)
    for nj in notification_batch:
        await process_notification_job(conn, session, nj)
```

The existing aiohttp `session` object can be reused for notification jobs since they are also HTTP calls.

## Verify

```sql
-- After running a test notification:
SELECT job_id, channel_id, status, attempts, last_error, created_at
FROM notification_jobs ORDER BY created_at DESC LIMIT 10;

SELECT * FROM notification_log ORDER BY sent_at DESC LIMIT 10;
```

Confirm `status = 'COMPLETED'` and `notification_log.success = TRUE` for a successful send.
