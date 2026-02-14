import hashlib
import hmac
import json

import httpx


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


async def send_slack(webhook_url: str, alert: dict) -> None:
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
    async with httpx.AsyncClient(timeout=8.0) as client:
        await client.post(webhook_url, json=payload)


async def send_pagerduty(integration_key: str, alert: dict) -> None:
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
    async with httpx.AsyncClient(timeout=8.0) as client:
        await client.post("https://events.pagerduty.com/v2/enqueue", json=payload)


async def send_teams(webhook_url: str, alert: dict) -> None:
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
    async with httpx.AsyncClient(timeout=8.0) as client:
        await client.post(webhook_url, json=payload)


async def send_webhook(
    url: str,
    method: str,
    headers: dict,
    secret: str | None,
    alert: dict,
) -> None:
    body = json.dumps(alert).encode()
    req_headers = {"Content-Type": "application/json", **(headers or {})}
    if secret:
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        req_headers["X-Signature-SHA256"] = sig
    async with httpx.AsyncClient(timeout=8.0) as client:
        await client.request(method.upper(), url, content=body, headers=req_headers)
