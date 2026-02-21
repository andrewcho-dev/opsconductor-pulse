# Prompt 003 — Verify Phase 70

## Step 1: Syntax Check

```bash
python -m py_compile tests/e2e/test_smoke.py && echo "Syntax OK"
```

## Step 2: Collection Check

```bash
pytest --collect-only -m "e2e and smoke" tests/e2e/test_smoke.py 2>&1 | tail -20
```

Expected: 10 tests collected.

## Step 3: Marker Check

```bash
pytest --markers 2>&1 | grep smoke
```

## Step 4: Unit Test Regression

```bash
pytest -m unit -q 2>&1 | tail -5
```

## Step 5: Checklist

- [ ] `test_smoke.py` has no Python syntax errors
- [ ] 10 tests collected by pytest
- [ ] `smoke` marker still registered
- [ ] xfail markers removed for routes that now exist
- [ ] xfail markers kept (with clear reason) for routes that still don't exist
- [ ] No xpass warnings (unexpected passes)
- [ ] Unit tests still passing

## Report

For each of the 10 smoke tests, output:
| Test | Status | Notes |
|------|--------|-------|
| test_ui_iot_healthz | PASS | |
| test_unauthenticated_api_returns_401 | PASS | |
| test_dashboard_loads | PASS | |
| test_devices_page_loads | PASS | |
| test_alerts_page_loads | PASS | |
| test_sites_page_loads | PASS | |
| test_delivery_log_page_loads | PASS | |
| test_operator_dashboard_loads | PASS | |
| test_integrations_page_loads | ? | xfail removed / kept |
| test_alert_rule_create_form_loads | ? | xfail removed / kept |
