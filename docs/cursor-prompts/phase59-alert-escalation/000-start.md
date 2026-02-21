# Phase 59: Alert Escalation

## What Exists

- `fleet_alert` table: id, tenant_id, status (OPEN/ACKNOWLEDGED/CLOSED), severity (int), created_at, acknowledged_at, silenced_until
- `alert_rules` table: metric_name, operator, threshold, severity, duration_seconds
- No escalation columns exist
- Evaluator runs every ~1s (LISTEN/NOTIFY) or 30s (fallback poll)
- Dispatcher creates delivery_jobs when alerts open

## What This Phase Adds

1. **Migration**: Add `escalation_level INT DEFAULT 0` and `escalated_at TIMESTAMPTZ NULL` to `fleet_alert`
2. **Escalation config on alert_rules**: Add `escalation_minutes INT NULL` — if an OPEN alert is not acknowledged within N minutes, escalate
3. **Evaluator escalation check**: A periodic loop (separate from the trigger evaluation) that finds OPEN alerts past their escalation_minutes threshold, bumps their severity by 1 (max 1, i.e. severity - 1 clamped to ≥ 0), sets `escalation_level += 1`, sets `escalated_at = now()`
4. **Dispatcher re-notifies on escalation**: When `escalated_at` changes, dispatcher creates a new delivery_job for the escalated alert (treat escalation like a new OPEN event)
5. **Frontend**: Show escalation badge on alert rows ("Escalated" if escalation_level > 0)

## Escalation Logic

- Only escalates OPEN alerts (not ACKNOWLEDGED — user is aware)
- Only escalates once (escalation_level caps at 1 in this phase — keep it simple)
- Escalation check runs every 60 seconds in the evaluator's existing event loop
- `escalation_minutes` NULL on a rule = no escalation (opt-in)

## Execution Order

| Prompt | Description |
|--------|-------------|
| 001 | Migration: escalation columns on fleet_alert + alert_rules |
| 002 | Evaluator: escalation check loop |
| 003 | Dispatcher: re-notify on escalation |
| 004 | Frontend: escalation badge |
| 005 | Unit tests |
| 006 | Verify |

## Key Files

- `db/migrations/` — prompt 001
- `services/evaluator_iot/evaluator.py` — prompt 002
- `services/dispatcher/dispatcher.py` — prompt 003
- `frontend/src/features/alerts/AlertListPage.tsx` — prompt 004
