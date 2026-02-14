# Phase 96 — Extract alerts domain to routes/alerts.py

## File to create
`services/ui_iot/routes/alerts.py`

## Endpoints to move from customer.py

### Alerts
- `list_alerts()` — GET /alerts (line ~2405)
- `get_alert()` — GET /alerts/{alert_id} (line ~2456)
- `acknowledge_alert()` — PATCH /alerts/{alert_id}/acknowledge (line ~2482)
- `close_alert()` — PATCH /alerts/{alert_id}/close (line ~2523)
- `silence_alert()` — PATCH /alerts/{alert_id}/silence (line ~2558)

### Alert digest
- `get_alert_digest_settings()` — GET /alert-digest-settings (line ~847)
- `update_alert_digest_settings()` — PUT /alert-digest-settings (line ~873)

### Alert rule templates
- `list_alert_rule_templates()` — GET /alert-rule-templates (line ~4484)
- `apply_rule_templates()` — POST /alert-rule-templates/apply (line ~4492)

### Alert rules
- `list_alert_rules()` — GET /alert-rules (line ~4547)
- `get_alert_rule()` — GET /alert-rules/{rule_id} (line ~4561)
- `create_alert_rule()` — POST /alert-rules (line ~4579)
- `update_alert_rule()` — PATCH /alert-rules/{rule_id} (line ~4680)
- `delete_alert_rule()` — DELETE /alert-rules/{rule_id} (line ~4781)

## Structure of alerts.py

```python
"""Alert and alert rule management routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, Response
# ... copy all imports needed by the moved functions

from dependencies import get_db_pool, require_customer, require_customer_admin

router = APIRouter(prefix="/customer", tags=["alerts"])

# ── paste all alert functions here ───────────────────────────────────────────
```

## After creating alerts.py

1. **Delete** all moved functions from `customer.py`
2. **Remove** any imports in `customer.py` that are now only used by alerts.py
3. Do NOT register in app.py yet — that happens in `005-register-routers.md`
