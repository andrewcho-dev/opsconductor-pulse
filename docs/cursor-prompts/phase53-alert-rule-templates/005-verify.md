# Prompt 005 — Verify Phase 53

## Step 1: Unit Tests

```bash
pytest -m unit -v 2>&1 | tail -40
```

## Step 2: TypeScript Build

```bash
cd frontend && npm run build 2>&1 | tail -10
```

## Step 3: Checklist

- [ ] `ALERT_RULE_TEMPLATES` constant in customer.py with 12 entries
- [ ] GET /customer/alert-rule-templates exists
- [ ] `?device_type=` filter works
- [ ] POST /customer/alert-rule-templates/apply exists
- [ ] apply skips existing rules by name
- [ ] apply returns `created` + `skipped` lists
- [ ] Frontend: "Load from Template" dropdown in rule create form
- [ ] Frontend: "Add All Defaults" button exists
- [ ] 8 unit tests in test_alert_rule_templates.py

## Report

Output PASS / FAIL per criterion.
