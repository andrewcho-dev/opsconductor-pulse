# Phase 109 — Rules DSL v1: Multi-Condition AND/OR

## Goal

Alert rules currently support a single condition: one metric, one operator,
one threshold. Add support for multiple conditions per rule with AND/OR logic.

## Key discovery

`alert_rules` already has a `conditions` JSONB column (currently always `'{}'`)
and a `rule_type` column. This phase activates `conditions` as a proper array
and adds a `match_mode` column. **No new tables required.**

## Data model

Each condition in the `conditions` array is a single-metric check:

```json
{
  "conditions": [
    {"metric_name": "temp_c",      "operator": "GT",  "threshold": 40.0, "duration_minutes": 5},
    {"metric_name": "humidity_pct","operator": "GT",  "threshold": 80.0}
  ],
  "match_mode": "all"
}
```

- `match_mode: "all"` — ALL conditions must be true (AND)
- `match_mode: "any"` — ANY condition must be true (OR)
- `duration_minutes` per condition is optional (overrides rule-level `duration_minutes`)

## Backwards compatibility

Existing rules that have `metric_name`/`operator`/`threshold` set and `conditions = '{}'`
continue to work unchanged — the evaluator falls back to the single-condition
path when `conditions` is empty. New rules should use the `conditions` array.

## Operators

Existing constraint: `GT | LT | GTE | LTE` — use these exact strings throughout.
Do not introduce `>`, `>=` etc. The SQL mapping is:
- `GT` → `>`
- `GTE` → `>=`
- `LT` → `<`
- `LTE` → `<=`

## Files to execute in order

| File | What it does |
|------|-------------|
| `001-migration.md` | Migration 078: add match_mode; backfill conditions from existing single-condition rules |
| `002-evaluator.md` | Evaluator: multi-condition evaluation with AND/OR |
| `003-api.md` | API: conditions array + match_mode in AlertRule CRUD |
| `004-frontend.md` | Condition builder UI in alert rule modal |
| `005-verify.md` | AND/OR rules tested, backwards compat confirmed, commit |
