# Prompt 006 — Verify Phase 72

## Step 1: Unit Tests

```bash
pytest -m unit -v 2>&1 | tail -40
```

## Step 2: TypeScript Build

```bash
cd frontend && npm run build 2>&1 | tail -10
```

## Step 3: Checklist

### Migration
- [ ] `063_no_telemetry_alert_type.sql` exists
- [ ] `NO_TELEMETRY` in fleet_alert.alert_type constraint
- [ ] `idx_telemetry_device_metric_time` index created

### Evaluator
- [ ] `check_telemetry_gap()` in evaluator.py
- [ ] Gap rules evaluated in main loop
- [ ] Alert type `NO_TELEMETRY` used
- [ ] Maintenance window + silence checks applied

### Backend API
- [ ] `TelemetryGapConditions` model
- [ ] `rule_type='telemetry_gap'` validates and stores gap_conditions
- [ ] `NO_TELEMETRY` in ALERT_TYPES constant

### Frontend
- [ ] "Data Gap" fourth mode in AlertRuleDialog
- [ ] `TelemetryGapConditions` in types.ts

### Unit Tests
- [ ] test_telemetry_gap.py with 7 tests

## Report

Output PASS / FAIL per criterion.
