# Prompt 006 — Verify Phase 59

## Step 1: Unit Tests

```bash
pytest -m unit -v 2>&1 | tail -40
```

## Step 2: TypeScript Build

```bash
cd frontend && npm run build 2>&1 | tail -10
```

## Step 3: Migration Check

```bash
ls db/migrations/059_alert_escalation.sql
```

## Step 4: Checklist

### Migration (001)
- [ ] `059_alert_escalation.sql` exists
- [ ] `fleet_alert` has `escalation_level` and `escalated_at`
- [ ] `alert_rules` has `escalation_minutes`

### Evaluator (002)
- [ ] `check_escalations()` in evaluator.py
- [ ] Runs every 60s in main loop
- [ ] Only escalates OPEN, non-silenced, escalation_level=0 alerts

### Dispatcher (003)
- [ ] `dispatch_escalated_alerts()` in dispatcher.py
- [ ] Called in main loop
- [ ] No duplicate delivery jobs

### Frontend (004)
- [ ] `escalation_level` and `escalated_at` in Alert type
- [ ] "Escalated" badge shown on escalated alerts

### Unit Tests (005)
- [ ] test_alert_escalation.py with 8 tests

## Report

Output PASS / FAIL per criterion.
