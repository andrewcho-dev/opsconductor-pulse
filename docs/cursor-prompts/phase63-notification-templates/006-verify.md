# Prompt 006 — Verify Phase 63

## Step 1: Unit Tests

```bash
pytest -m unit -v 2>&1 | tail -40
```

## Step 2: Import Check

```bash
cd services/delivery_worker && python -c "from jinja2 import Environment; print('Jinja2 OK')"
```

## Step 3: TypeScript Build

```bash
cd frontend && npm run build 2>&1 | tail -10
```

## Step 4: Checklist

- [ ] `jinja2>=3.1.0` in delivery_worker requirements.txt
- [ ] `render_template()` in email_sender.py uses Jinja2
- [ ] New template vars: site_id, summary, status, details, severity_label
- [ ] TemplateError falls back gracefully
- [ ] Webhook uses body_template from config_json if set
- [ ] GET /customer/integrations/{id}/template-variables returns 11 vars
- [ ] Frontend: subject/body template fields on email integration form
- [ ] Frontend: body template field on webhook integration form
- [ ] Variables reference panel with insert-at-cursor
- [ ] 9 unit tests in test_notification_templates.py

## Report

Output PASS / FAIL per criterion.
