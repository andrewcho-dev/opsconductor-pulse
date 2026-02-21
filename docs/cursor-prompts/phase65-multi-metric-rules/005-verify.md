# Prompt 005 — Verify Phase 65

## Step 1: Unit Tests

```bash
pytest -m unit -v 2>&1 | tail -40
```

## Step 2: TypeScript Build

```bash
cd frontend && npm run build 2>&1 | tail -10
```

## Step 3: Checklist

### Evaluator
- [ ] `evaluate_conditions()` in evaluator.py
- [ ] AND/OR combinator supported
- [ ] Missing metric evaluates to False
- [ ] Single-condition mode unchanged

### Backend API
- [ ] `RuleCondition` and `RuleConditions` models
- [ ] `conditions` field in AlertRuleCreate/Update
- [ ] conditions stored in DB as JSONB
- [ ] conditions returned in GET responses

### Frontend
- [ ] Simple/Multi toggle in AlertRuleDialog
- [ ] Multi-condition condition list with add/remove
- [ ] AND/OR selector
- [ ] `conditions` in AlertRule TypeScript type

### Unit Tests
- [ ] test_multi_metric_rules.py with 9 tests

## Report

Output PASS / FAIL per criterion.
