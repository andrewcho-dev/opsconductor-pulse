"""
Notification dispatcher - queues matched notification jobs for reliable delivery.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def _matches_rule(rule: dict, alert: dict) -> bool:
    if rule.get("min_severity") is not None:
        if (alert.get("severity") or 0) < rule["min_severity"]:
            return False
    if rule.get("alert_type"):
        if alert.get("alert_type") != rule["alert_type"]:
            return False
    if rule.get("device_tag_key"):
        tags = (alert.get("details") or {}).get("device_tags", {})
        if tags.get(rule["device_tag_key"]) != rule.get("device_tag_val"):
            return False
    if rule.get("site_ids"):
        if alert.get("site_id") not in rule["site_ids"]:
            return False
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
    queued = 0
    async with pool.acquire() as conn:
        rules = await conn.fetch(
            """
            SELECT r.rule_id, r.channel_id, r.min_severity, r.alert_type,
                   r.device_tag_key, r.device_tag_val, r.site_ids, r.device_prefixes,
                   r.deliver_on, r.throttle_minutes, r.priority, r.is_enabled,
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
            deliver_on = rule_dict.get("deliver_on") or ["OPEN"]
            if event_type not in deliver_on:
                continue
            if not _matches_rule(rule_dict, alert):
                continue
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
                    continue
            payload = {
                "alert_id": alert.get("alert_id"),
                "alert_type": alert.get("alert_type"),
                "severity": alert.get("severity"),
                "device_id": alert.get("device_id"),
                "site_id": alert.get("site_id"),
                "tenant_id": tenant_id,
                "message": alert.get("message", alert.get("summary", "")),
                "details": alert.get("details", {}),
                "triggered_at": (
                    alert["triggered_at"].isoformat()
                    if isinstance(alert.get("triggered_at"), datetime)
                    else alert.get("triggered_at")
                ),
                "event_type": event_type,
                "channel_type": rule_dict["channel_type"],
            }
            try:
                result = await conn.execute(
                    """
                    INSERT INTO notification_jobs
                        (tenant_id, alert_id, channel_id, rule_id, deliver_on_event, status, payload_json)
                    VALUES ($1, $2, $3, $4, $5, 'PENDING', $6::jsonb)
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
                if result != "INSERT 0 0":
                    queued += 1
            except Exception:
                logger.exception(
                    "Failed to queue notification job",
                    extra={"tenant_id": tenant_id, "channel_id": rule_dict["channel_id"]},
                )
    return queued
