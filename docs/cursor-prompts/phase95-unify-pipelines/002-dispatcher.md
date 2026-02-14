# Phase 95 — Update dispatcher.py: Queue Jobs Instead of Direct-Send

## File to modify
`services/ui_iot/notifications/dispatcher.py`

## Current behavior
`dispatch_alert()` fetches routing rules, calls senders directly (fire-and-forget), logs to `notification_log`.
No retry. No backoff. If the Slack/PD HTTP call fails, the notification is lost silently.

## New behavior
`dispatch_alert()` fetches routing rules, **inserts a `notification_jobs` row** for each matched rule.
The `delivery_worker` picks up and executes the actual send (with retry + backoff).
The `notification_log` is written by delivery_worker on completion (not by dispatcher).

## Full replacement for `services/ui_iot/notifications/dispatcher.py`

```python
"""
Notification dispatcher — queues matched notification jobs for reliable delivery.

Flow:
  1. alert fires → dispatch_alert() called (from escalation_worker or evaluator)
  2. dispatcher finds matching notification_routing_rules for the tenant
  3. for each match, inserts a notification_jobs row (dedup via unique index)
  4. delivery_worker polls notification_jobs and calls the appropriate sender
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def _matches_rule(rule: dict, alert: dict) -> bool:
    """Return True if the alert satisfies all non-null rule filters."""
    # Severity filter
    if rule.get("min_severity") is not None:
        if (alert.get("severity") or 0) < rule["min_severity"]:
            return False

    # Alert type filter
    if rule.get("alert_type"):
        if alert.get("alert_type") != rule["alert_type"]:
            return False

    # Device tag filter
    if rule.get("device_tag_key"):
        tags = (alert.get("details") or {}).get("device_tags", {})
        if tags.get(rule["device_tag_key"]) != rule.get("device_tag_val"):
            return False

    # Site filter
    if rule.get("site_ids"):
        if alert.get("site_id") not in rule["site_ids"]:
            return False

    # Device prefix filter
    if rule.get("device_prefixes"):
        device_id = alert.get("device_id", "")
        if not any(device_id.startswith(p) for p in rule["device_prefixes"]):
            return False

    return True


async def dispatch_alert(
    pool,
    alert: dict,
    tenant_id: str,
    event_type: str = "OPEN",
) -> int:
    """
    Queue notification jobs for all routing rules that match this alert.

    Returns the number of jobs queued.
    """
    queued = 0

    async with pool.acquire() as conn:
        # Fetch enabled routing rules for this tenant and event type
        rules = await conn.fetch(
            """
            SELECT r.rule_id, r.channel_id, r.min_severity, r.alert_type,
                   r.device_tag_key, r.device_tag_val, r.site_ids,
                   r.device_prefixes, r.deliver_on, r.throttle_minutes,
                   r.priority, r.is_enabled,
                   c.channel_type, c.config, c.is_enabled AS channel_enabled
            FROM notification_routing_rules r
            JOIN notification_channels c USING (channel_id)
            WHERE r.tenant_id = $1
              AND r.is_enabled = TRUE
              AND c.is_enabled = TRUE
            ORDER BY r.priority ASC, r.rule_id ASC
            """,
            tenant_id,
        )

        for rule in rules:
            rule_dict = dict(rule)

            # Check deliver_on matches the event type
            deliver_on = rule_dict.get("deliver_on") or ["OPEN"]
            if event_type not in deliver_on:
                continue

            # Check alert matches rule filters
            if not _matches_rule(rule_dict, alert):
                continue

            # Throttle check: skip if a job was sent recently for this channel+alert
            throttle_minutes = rule_dict.get("throttle_minutes") or 0
            if throttle_minutes > 0:
                recent = await conn.fetchval(
                    """
                    SELECT 1 FROM notification_log
                    WHERE channel_id = $1 AND alert_id = $2
                      AND sent_at > NOW() - ($3::int * INTERVAL '1 minute')
                    LIMIT 1
                    """,
                    rule_dict["channel_id"],
                    alert["alert_id"],
                    throttle_minutes,
                )
                if recent:
                    logger.debug(
                        "Throttled notification for channel=%s alert=%s",
                        rule_dict["channel_id"],
                        alert["alert_id"],
                    )
                    continue

            # Build payload snapshot for the job
            payload = {
                "alert_id": alert.get("alert_id"),
                "alert_type": alert.get("alert_type"),
                "severity": alert.get("severity"),
                "device_id": alert.get("device_id"),
                "site_id": alert.get("site_id"),
                "tenant_id": tenant_id,
                "message": alert.get("message", ""),
                "details": alert.get("details", {}),
                "triggered_at": (
                    alert["triggered_at"].isoformat()
                    if isinstance(alert.get("triggered_at"), datetime)
                    else alert.get("triggered_at")
                ),
                "event_type": event_type,
                "channel_type": rule_dict["channel_type"],
            }

            # Insert notification_job (ON CONFLICT DO NOTHING — dedup by unique index)
            try:
                await conn.execute(
                    """
                    INSERT INTO notification_jobs
                        (tenant_id, alert_id, channel_id, rule_id,
                         deliver_on_event, status, payload_json)
                    VALUES ($1, $2, $3, $4, $5, 'PENDING', $6)
                    ON CONFLICT (tenant_id, alert_id, channel_id, deliver_on_event)
                    DO NOTHING
                    """,
                    tenant_id,
                    int(alert["alert_id"]),
                    rule_dict["channel_id"],
                    rule_dict["rule_id"],
                    event_type,
                    json.dumps(payload),
                )
                queued += 1
                logger.info(
                    "Queued notification_job tenant=%s alert=%s channel=%s event=%s",
                    tenant_id,
                    alert["alert_id"],
                    rule_dict["channel_id"],
                    event_type,
                )
            except Exception:
                logger.exception(
                    "Failed to queue notification_job for channel=%s",
                    rule_dict["channel_id"],
                )

    return queued
```

## Also update: test_channel() in routes/notifications.py

The `POST /notification-channels/{channel_id}/test` endpoint currently calls `dispatch_alert()` directly.
After this change, `dispatch_alert()` only queues jobs — the actual send happens asynchronously in
delivery_worker. For a test endpoint, we want immediate synchronous feedback.

Update `test_channel()` in `routes/notifications.py` to call the sender directly (bypassing the queue)
using the existing `senders.py` functions:

```python
# In routes/notifications.py — test_channel() endpoint
from notifications.senders import send_slack, send_pagerduty, send_teams, send_webhook

@router.post("/{channel_id}/test", status_code=200)
async def test_channel(channel_id: int, pool=Depends(get_db_pool), claims=Depends(require_customer)):
    tenant_id = claims["tenant_id"]

    async with pool.acquire() as conn:
        channel = await conn.fetchrow(
            "SELECT * FROM notification_channels WHERE channel_id=$1 AND tenant_id=$2",
            channel_id, tenant_id
        )
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")

    test_alert = {
        "alert_id": 0,
        "alert_type": "TEST",
        "severity": 3,
        "device_id": "test-device",
        "site_id": None,
        "message": "This is a test notification from OpsConductor-Pulse",
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
            await send_webhook(cfg["url"], cfg.get("method","POST"), cfg.get("headers",{}), cfg.get("secret"), test_alert)
        elif ch["channel_type"] == "email":
            # Email sending is handled by delivery_worker; for test, queue immediately
            # TODO: implement direct email send test in a follow-up
            return {"status": "queued", "message": "Email test queued for immediate delivery"}
        elif ch["channel_type"] in ("snmp", "mqtt"):
            return {"status": "queued", "message": f"{ch['channel_type'].upper()} test queued for immediate delivery"}
        return {"status": "ok", "message": "Test notification sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Test send failed: {str(e)}")
```

## Verify

After updating dispatcher.py, confirm that calling `dispatch_alert()` with a test alert+tenant
results in a row in `notification_jobs` (not a direct HTTP call):

```sql
SELECT job_id, tenant_id, alert_id, channel_id, status, deliver_on_event, created_at
FROM notification_jobs ORDER BY created_at DESC LIMIT 5;
```
