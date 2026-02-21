# Phase 91 — Backend: Channels CRUD + Notification Dispatcher

## 1. New router: `services/ui_iot/routes/notifications.py`

All endpoints require valid JWT and operate within tenant context.

### Channel endpoints
```
GET    /customer/notification-channels
POST   /customer/notification-channels
GET    /customer/notification-channels/{channel_id}
PUT    /customer/notification-channels/{channel_id}
DELETE /customer/notification-channels/{channel_id}
POST   /customer/notification-channels/{channel_id}/test
```

### Routing rule endpoints
```
GET    /customer/notification-routing-rules
POST   /customer/notification-routing-rules
PUT    /customer/notification-routing-rules/{rule_id}
DELETE /customer/notification-routing-rules/{rule_id}
```

### Pydantic models

```python
class ChannelIn(BaseModel):
    name: str
    channel_type: Literal["slack", "pagerduty", "teams", "webhook"]
    config: dict
    is_enabled: bool = True

class ChannelOut(ChannelIn):
    channel_id: int
    tenant_id: str
    created_at: datetime
    updated_at: datetime
    # IMPORTANT: strip sensitive config values (webhook secrets, integration keys)
    # from GET responses — return config with secret fields replaced by "***"

class RoutingRuleIn(BaseModel):
    channel_id: int
    min_severity: Optional[int] = None
    alert_type: Optional[str] = None
    device_tag_key: Optional[str] = None
    device_tag_val: Optional[str] = None
    throttle_minutes: int = 0
    is_enabled: bool = True

class RoutingRuleOut(RoutingRuleIn):
    rule_id: int
    tenant_id: str
    created_at: datetime
```

### POST /customer/notification-channels/{channel_id}/test
Send a test payload to the channel using the dispatcher (see below).
Return `{"ok": true}` or `{"ok": false, "error": "..."}`.

## 2. Dispatcher: `services/ui_iot/notifications/dispatcher.py`

```python
async def dispatch_alert(pool, alert: dict, tenant_id: str) -> None:
    """
    Called from the alert creation path and escalation worker.
    1. Load all enabled routing rules for tenant
    2. For each rule: check filters (severity, alert_type, tags)
    3. Check throttle: skip if notification_log has entry for
       (channel_id, alert_id) within throttle_minutes
    4. Send via the appropriate sender
    5. Insert into notification_log
    """
```

### Senders (in `services/ui_iot/notifications/senders.py`)

Use `httpx.AsyncClient` for all. Fire-and-forget from `dispatch_alert`
(log errors, don't raise).

**Slack:**
```python
async def send_slack(webhook_url: str, alert: dict) -> None:
    payload = {
        "text": f"*[{severity_label(alert['severity'])}]* {alert['device_id']} — {alert['alert_type']}",
        "attachments": [{
            "color": severity_color(alert['severity']),
            "fields": [
                {"title": "Summary", "value": alert.get("summary", "—"), "short": False},
                {"title": "Time", "value": alert["created_at"], "short": True},
            ]
        }]
    }
    await client.post(webhook_url, json=payload)
```

**PagerDuty (Events API v2):**
```python
async def send_pagerduty(integration_key: str, alert: dict) -> None:
    payload = {
        "routing_key": integration_key,
        "event_action": "trigger",
        "dedup_key": f"alert-{alert['alert_id']}",
        "payload": {
            "summary": f"{alert['alert_type']} on {alert['device_id']}",
            "severity": pd_severity(alert['severity']),  # critical/error/warning/info
            "source": alert['device_id'],
            "custom_details": alert,
        }
    }
    await client.post("https://events.pagerduty.com/v2/enqueue", json=payload)
```

**Teams (Adaptive Card):**
```python
async def send_teams(webhook_url: str, alert: dict) -> None:
    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": severity_hex(alert['severity']),
        "summary": f"Alert: {alert['alert_type']}",
        "sections": [{"activityTitle": alert['device_id'],
                      "activityText": alert.get("summary", "")}]
    }
    await client.post(webhook_url, json=payload)
```

**Generic Webhook:**
```python
async def send_webhook(url: str, method: str, headers: dict,
                       secret: Optional[str], alert: dict) -> None:
    body = json.dumps(alert).encode()
    if secret:
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        headers["X-Signature-SHA256"] = sig
    await client.request(method, url, content=body,
                         headers={"Content-Type": "application/json", **headers})
```

## 3. Wire dispatcher into alert creation

In the alert creation path (wherever `INSERT INTO alerts` is called and the
alert is committed), add:
```python
asyncio.create_task(dispatch_alert(pool, alert_dict, tenant_id))
```

Also call it from `escalation_worker.run_escalation_tick` after incrementing
the escalation level.

## 4. Register router

In `services/ui_iot/app.py`:
```python
from services.ui_iot.routes.notifications import router as notifications_router
app.include_router(notifications_router)
```
