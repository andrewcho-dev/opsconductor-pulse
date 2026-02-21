# Phase 65: Multi-Metric Alert Rules

## What Exists

- `alert_rules` table: single `metric_name`, `operator`, `threshold` per rule
- `conditions JSONB` column exists in `alert_rules` (from original base schema migration 000) but is currently unused
- Evaluator uses `evaluate_threshold(value, operator, threshold)` — single condition
- `check_duration_window()` — validates single metric breach over time
- Rule operators: GT, LT, GTE, LTE (named form, constraint migration 055)

## What This Phase Adds

Multi-condition rules using the existing `conditions JSONB` column:

1. **Conditions schema**: `conditions` stores a list of condition objects + a `combinator` (AND/OR)
   ```json
   {
     "combinator": "AND",
     "conditions": [
       {"metric_name": "temperature", "operator": "GT", "threshold": 80.0},
       {"metric_name": "humidity",    "operator": "GT", "threshold": 85.0}
     ]
   }
   ```
2. **Backward compat**: If `conditions` is NULL, use `metric_name`/`operator`/`threshold` as before (single-condition mode)
3. **Evaluator**: When `conditions` is populated, evaluate all conditions against latest telemetry; apply AND/OR combinator
4. **API**: Accept `conditions` field in AlertRuleCreate/Update
5. **Frontend**: Multi-condition rule builder UI

## Execution Order

| Prompt | Description |
|--------|-------------|
| 001 | Evaluator: multi-condition evaluation |
| 002 | Backend API: accept conditions in create/update |
| 003 | Frontend: condition builder UI |
| 004 | Unit tests |
| 005 | Verify |

## Key Files

- `services/evaluator_iot/evaluator.py` — prompt 001
- `services/ui_iot/routes/customer.py` — prompt 002
- `frontend/src/features/alerts/AlertRuleDialog.tsx` — prompt 003
