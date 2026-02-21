# Phase 44: Time-Window Rules in the Evaluator

## Why This Phase

The architecture audit identified this as the highest-leverage rules enhancement:

> "What's genuinely missing: time-window rules, aggregate rules, composite AND/OR conditions. P2.1 should focus on adding time-window support (e.g., 'temp_c > 40 for 5 minutes'). That covers 80% of real alerting needs."

The current evaluator fires an alert the moment a threshold is crossed. This causes **alert storms and false positives** — a brief spike triggers an alert even if the condition resolves in seconds. Time-window rules let customers say: "only alert me if this condition persists for N minutes."

## What Exists Today

In `services/evaluator_iot/evaluator.py`:
- Threshold rules: `metric_name` + `operator` (>, <, >=, <=, ==, !=) + `threshold`
- Evaluated every 5 seconds by polling TimescaleDB
- Fingerprint-based deduplication prevents re-alerting on the same active alert
- `alert_rules` table has a `rule_type` column with `threshold`, `anomaly`, `pattern` — only `threshold` is implemented
- `alert_rules` table has `conditions JSONB` and `actions JSONB` columns — currently unused

## What We Are Adding

A new optional field on threshold rules: **`duration_seconds`**

Semantics: "this threshold must be continuously breached for at least N seconds before firing an alert."

Examples:
- `temp_c > 40 for 300 seconds` — only alert if temp stays above 40°C for 5+ minutes
- `humidity < 20 for 60 seconds` — only alert if humidity stays below 20% for 1+ minute
- `temp_c > 40 for 0 seconds` — existing behavior (fire immediately, same as no duration)

## Implementation Approach

Use TimescaleDB's existing `telemetry` hypertable. For a rule with `duration_seconds = 300`, the evaluator queries:

```sql
SELECT COUNT(*) FROM telemetry
WHERE tenant_id = $1
  AND device_id = $2
  AND metric_name = $3
  AND metric_value {operator} $4
  AND ts >= NOW() - INTERVAL '300 seconds'
  AND ts >= (SELECT MIN(ts) FROM telemetry WHERE tenant_id=$1 AND device_id=$2 AND metric_name=$3 AND ts >= NOW() - INTERVAL '300 seconds')
```

Simpler approach: query the MIN and MAX of the metric over the window, and check if the condition holds for the entire window duration by confirming the earliest reading in the window also breaches the threshold.

**Correct approach (use this):** Query whether ALL readings of the metric in the last `duration_seconds` breach the threshold AND there is at least one reading older than `(now - duration_seconds)` age — meaning the condition has been continuously true for the full window.

Actually the cleanest query: count readings in the window that DO NOT breach the threshold. If that count is 0 AND there are readings spanning at least `duration_seconds`, the condition is continuously met.

## Schema Change

Add `duration_seconds INTEGER NOT NULL DEFAULT 0` to `alert_rules` table via migration. Default 0 = fire immediately (backwards compatible with all existing rules).

## Execution Order

| Prompt | Description | Priority |
|--------|-------------|----------|
| 001 | Read and map evaluator.py — understand current evaluation loop | CRITICAL |
| 002 | DB migration: add `duration_seconds` to `alert_rules` | HIGH |
| 003 | Implement time-window query in evaluator | HIGH |
| 004 | Update alert rule CRUD API to accept/store `duration_seconds` | HIGH |
| 005 | Update frontend rule creation UI to expose duration field | MEDIUM |
| 006 | Unit tests for time-window evaluation logic | HIGH |
| 007 | Verify full suite + manual smoke test | CRITICAL |

## Verification After All Prompts Complete

```bash
# Unit tests
pytest -m unit -v

# Create a rule with duration_seconds=60 via API, send telemetry that breaches threshold
# Confirm no alert fires in first 60s
# Confirm alert fires after 60s of continuous breach
```

## Key Files

- `services/evaluator_iot/evaluator.py` — core evaluation loop (primary change target)
- `db/migrations/` — add duration_seconds column
- `services/ui_iot/routes/customer.py` — alert rule CRUD (accept duration_seconds)
- `frontend/src/features/` — alert rule creation form
- `tests/unit/test_evaluator.py` — existing evaluator tests (must not regress)
