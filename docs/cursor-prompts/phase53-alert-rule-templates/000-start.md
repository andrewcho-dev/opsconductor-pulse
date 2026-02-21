# Phase 53: Alert Rule Templates / Presets

## What Exists

- `alert_rules` table: id, tenant_id, name, description, enabled, metric_name, operator (GT/LT/GTE/LTE), threshold, severity, duration_seconds, device_type, site_ids
- Device types in seed data: temperature, humidity, pressure, vibration, power, flow, level, gateway
- Alert rule CRUD endpoints exist in `services/ui_iot/routes/customer.py`
- Alert rule create/edit form exists in the frontend

## What This Phase Adds

1. **Preset definitions** — a static catalog of sensible default thresholds per device_type (e.g., temperature > 85°C → severity 2, temperature < -10°C → severity 2)
2. **Backend: GET /customer/alert-rule-templates** — returns the preset catalog; no DB write required, purely in-code definitions
3. **Frontend: "Load Template" UX** — on the alert rule create form, a dropdown/selector that pre-fills fields from a chosen template
4. **One-click create from template** — optional "Add All Defaults" button that bulk-creates presets for the tenant

## Preset Catalog (implement in code)

| device_type | metric_name | operator | threshold | severity | duration_seconds | name |
|-------------|-------------|----------|-----------|----------|-----------------|------|
| temperature | temperature | GT | 85.0 | 1 | 60 | High Temperature |
| temperature | temperature | LT | -10.0 | 1 | 60 | Low Temperature |
| humidity | humidity | GT | 90.0 | 2 | 120 | High Humidity |
| humidity | humidity | LT | 10.0 | 2 | 120 | Low Humidity |
| pressure | pressure | GT | 1100.0 | 2 | 0 | High Pressure |
| pressure | pressure | LT | 900.0 | 2 | 0 | Low Pressure |
| vibration | vibration | GT | 5.0 | 1 | 30 | High Vibration |
| power | power | GT | 95.0 | 2 | 300 | High Power Usage |
| power | power | LT | 5.0 | 3 | 300 | Power Loss |
| flow | flow | LT | 1.0 | 2 | 120 | Low Flow Rate |
| level | level | GT | 90.0 | 1 | 60 | High Level |
| level | level | LT | 10.0 | 1 | 60 | Low Level |

## Execution Order

| Prompt | Description |
|--------|-------------|
| 001 | Backend: GET /customer/alert-rule-templates |
| 002 | Backend: POST /customer/alert-rule-templates/apply (bulk create) |
| 003 | Frontend: Load Template selector on rule form |
| 004 | Unit tests |
| 005 | Verify |

## Key Files

- `services/ui_iot/routes/customer.py` — prompts 001, 002
- `frontend/src/features/alerts/` — alert rule form components (prompt 003)
