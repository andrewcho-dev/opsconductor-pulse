# Prompt 006 — Verify Phase 67

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
- [ ] `060_anomaly_alert_type.sql` exists
- [ ] ANOMALY allowed in fleet_alert.alert_type
- [ ] `idx_alert_rules_anomaly` index created

### Evaluator
- [ ] `compute_rolling_stats()` in evaluator.py
- [ ] `compute_z_score()` in evaluator.py
- [ ] Anomaly rules evaluated in main loop
- [ ] Alert type ANOMALY used

### Backend API
- [ ] `AnomalyConditions` Pydantic model
- [ ] `rule_type='anomaly'` requires anomaly_conditions
- [ ] conditions stored as JSONB

### Frontend
- [ ] "Anomaly Detection" mode in AlertRuleDialog
- [ ] metric/window/z_threshold/min_samples fields
- [ ] `AnomalyConditions` in types.ts

### Unit Tests
- [ ] test_anomaly_detection.py with 9 tests

## Report

Output PASS / FAIL per criterion.
