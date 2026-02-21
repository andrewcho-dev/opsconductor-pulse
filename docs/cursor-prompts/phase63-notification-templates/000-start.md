# Phase 63: Notification Templates (Jinja2)

## What Exists

- `services/delivery_worker/email_sender.py` — renders templates with Python's `.format(**kwargs)` 
- `DEFAULT_SUBJECT_TEMPLATE`, `DEFAULT_HTML_TEMPLATE`, `DEFAULT_TEXT_TEMPLATE` defined in email_sender.py
- Template variables: `alert_id`, `device_id`, `tenant_id`, `severity`, `message`, `alert_type`, `timestamp`, `severity_lower`
- `integrations` table `config_json` for email already stores `subject_template`, `body_template`, `body_format`
- Webhook `config_json` stores `url` and `headers` — no body template
- `jinja2==3.1.4` installed in ui_iot but NOT in delivery_worker
- `services/delivery_worker/worker.py` — sends webhooks; payload comes from `payload_json` in delivery_jobs

## What This Phase Adds

1. **Jinja2 in delivery_worker** — add `jinja2` to requirements, replace `.format()` with Jinja2 rendering in email_sender.py
2. **Webhook body template** — add optional `body_template` to webhook `config_json`; if set, render it with Jinja2 instead of sending raw `payload_json`
3. **Backend: GET /customer/integrations/{id}/template-variables** — returns the list of available template variables with descriptions
4. **Frontend: Template editor** — on email/webhook integration edit form, show a textarea for body_template with a variable reference panel

## Available Template Variables

```
{{ alert_id }}         — Numeric alert ID
{{ device_id }}        — Device identifier
{{ site_id }}          — Site identifier
{{ tenant_id }}        — Tenant identifier
{{ severity }}         — Severity level (integer)
{{ severity_label }}   — Severity label: CRITICAL / WARNING / INFO / UNKNOWN
{{ alert_type }}       — Alert type: THRESHOLD, NO_HEARTBEAT, etc.
{{ summary }}          — Alert summary text
{{ status }}           — Alert status: OPEN / ACKNOWLEDGED / CLOSED
{{ created_at }}       — ISO 8601 timestamp
{{ details }}          — Alert details dict (JSONB)
```

## Execution Order

| Prompt | Description |
|--------|-------------|
| 001 | Add Jinja2 to delivery_worker + upgrade email_sender.py |
| 002 | Webhook body template rendering in worker.py |
| 003 | Backend: GET /customer/integrations/{id}/template-variables |
| 004 | Frontend: Template editor on integration form |
| 005 | Unit tests |
| 006 | Verify |

## Key Files

- `services/delivery_worker/requirements.txt` — prompt 001
- `services/delivery_worker/email_sender.py` — prompt 001
- `services/delivery_worker/worker.py` — prompt 002
- `services/ui_iot/routes/customer.py` — prompt 003
- `frontend/src/features/integrations/` — prompt 004
