import logging

from notifications.senders import (
    send_pagerduty,
    send_slack,
    send_teams,
    send_webhook,
)

logger = logging.getLogger(__name__)


def _matches_rule(rule: dict, alert: dict) -> bool:
    min_severity = rule.get("min_severity")
    if min_severity is not None and int(alert.get("severity", 0)) < int(min_severity):
        return False
    alert_type = rule.get("alert_type")
    if alert_type and alert.get("alert_type") != alert_type:
        return False
    # tag filters are optional; tags matching is best-effort based on alert details.
    tag_key = rule.get("device_tag_key")
    tag_val = rule.get("device_tag_val")
    if tag_key:
        tags = alert.get("details", {}).get("device_tags", {})
        if not isinstance(tags, dict):
            return False
        if tag_key not in tags:
            return False
        if tag_val and str(tags.get(tag_key)) != str(tag_val):
            return False
    return True


async def _send_channel(channel: dict, alert: dict) -> None:
    ctype = channel.get("channel_type")
    cfg = channel.get("config") or {}
    if ctype == "slack":
        await send_slack(cfg.get("webhook_url", ""), alert)
        return
    if ctype == "pagerduty":
        await send_pagerduty(cfg.get("integration_key", ""), alert)
        return
    if ctype == "teams":
        await send_teams(cfg.get("webhook_url", ""), alert)
        return
    if ctype == "webhook":
        await send_webhook(
            cfg.get("url", ""),
            cfg.get("method", "POST"),
            cfg.get("headers", {}) or {},
            cfg.get("secret"),
            alert,
        )
        return
    raise ValueError(f"Unsupported channel type: {ctype}")


async def dispatch_alert(pool, alert: dict, tenant_id: str) -> None:
    """
    Dispatch an alert through all enabled tenant routing rules/channels.
    """
    async with pool.acquire() as conn:
        rules = await conn.fetch(
            """
            SELECT rr.rule_id, rr.channel_id, rr.min_severity, rr.alert_type,
                   rr.device_tag_key, rr.device_tag_val, rr.throttle_minutes,
                   rr.is_enabled,
                   nc.channel_type, nc.config, nc.is_enabled AS channel_enabled
            FROM notification_routing_rules rr
            JOIN notification_channels nc
              ON nc.channel_id = rr.channel_id
            WHERE rr.tenant_id = $1 AND rr.is_enabled = TRUE
            """,
            tenant_id,
        )

        alert_id = int(alert.get("alert_id", 0))
        for row in rules:
            rule = dict(row)
            if not rule.get("channel_enabled"):
                continue
            if not _matches_rule(rule, alert):
                continue
            throttle = int(rule.get("throttle_minutes") or 0)
            if throttle > 0:
                recent = await conn.fetchval(
                    """
                    SELECT 1
                    FROM notification_log
                    WHERE channel_id = $1
                      AND alert_id = $2
                      AND sent_at >= NOW() - ($3 || ' minutes')::INTERVAL
                    LIMIT 1
                    """,
                    rule["channel_id"],
                    alert_id,
                    str(throttle),
                )
                if recent:
                    continue

            try:
                await _send_channel(rule, alert)
                await conn.execute(
                    """
                    INSERT INTO notification_log (channel_id, alert_id)
                    VALUES ($1, $2)
                    """,
                    rule["channel_id"],
                    alert_id,
                )
            except Exception:
                logger.exception(
                    "Notification dispatch failed",
                    extra={"tenant_id": tenant_id, "channel_id": rule["channel_id"], "alert_id": alert_id},
                )
