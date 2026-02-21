# Prompt 002 — Webhook Body Template in worker.py

Read `services/delivery_worker/worker.py` fully — find the webhook delivery section.
Read `services/delivery_worker/email_sender.py` (just updated) to use `render_template`.

## Update Webhook Delivery

In the webhook delivery code path in `worker.py`, check if `config_json` contains a `body_template` key. If so, render it with Jinja2 instead of sending `payload_json` directly:

```python
from email_sender import render_template  # import the shared helper

# In the webhook delivery function:
config = integration["config_json"] or {}
body_template = config.get("body_template")

if body_template:
    # Render the template with alert variables
    payload = job["payload_json"] or {}
    variables = {
        "alert_id": payload.get("alert_id"),
        "device_id": payload.get("device_id"),
        "site_id": payload.get("site_id", ""),
        "tenant_id": payload.get("tenant_id", ""),
        "severity": payload.get("severity", 3),
        "severity_label": {0: "CRITICAL", 1: "CRITICAL", 2: "WARNING", 3: "INFO"}.get(
            payload.get("severity", 3), "UNKNOWN"
        ),
        "alert_type": payload.get("alert_type", ""),
        "summary": payload.get("summary", payload.get("message", "")),
        "status": payload.get("status", "OPEN"),
        "created_at": payload.get("created_at", ""),
        "details": payload.get("details", {}),
    }
    rendered = render_template(body_template, variables)
    # Try to parse as JSON; if not valid JSON, send as plain text
    try:
        import json
        body = json.loads(rendered)
    except Exception:
        body = {"message": rendered}
    request_body = body
else:
    request_body = job["payload_json"]
```

## Acceptance Criteria

- [ ] Webhook uses `body_template` from config_json if set
- [ ] Template rendered with all variables
- [ ] Invalid JSON template falls back to `{"message": rendered}`
- [ ] No `body_template` → existing behavior (send payload_json unchanged)
- [ ] `pytest -m unit -v` passes
