# Phase 67: Telemetry Anomaly Detection

## What Exists

- `telemetry` table: TimescaleDB hypertable with `metrics JSONB` per reading
- `alert_rules` table: `rule_type TEXT DEFAULT 'threshold'`, `conditions JSONB` (unused for threshold rules)
- Evaluator: `evaluate_threshold()` for single-value threshold rules; `check_duration_window()` for duration
- Alert types: `NO_HEARTBEAT`, `THRESHOLD`, `SYSTEM_HEALTH`
- `conditions JSONB` column already exists on `alert_rules`

## What This Phase Adds

**Z-score based anomaly detection** — a new `rule_type='anomaly'` that fires when a metric deviates more than N standard deviations from its rolling mean.

The rule is stored in `alert_rules` with `rule_type='anomaly'` and anomaly config in `conditions`:
```json
{
  "metric_name": "temperature",
  "window_minutes": 60,
  "z_threshold": 3.0,
  "min_samples": 10
}
```

Alert fires when: `|current_value - rolling_mean| / rolling_stddev > z_threshold`

New alert type: `ANOMALY`

## Execution Order

| Prompt | Description |
|--------|-------------|
| 001 | Migration: add ANOMALY to alert_types check constraint |
| 002 | Evaluator: anomaly detection loop |
| 003 | Backend API: create anomaly rules |
| 004 | Frontend: anomaly rule form |
| 005 | Unit tests |
| 006 | Verify |

## Key Files

- `db/migrations/` — prompt 001
- `services/evaluator_iot/evaluator.py` — prompt 002
- `services/ui_iot/routes/customer.py` — prompt 003
- `frontend/src/features/alerts/AlertRuleDialog.tsx` — prompt 004
