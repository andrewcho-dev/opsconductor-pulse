# Phase 49: Alert Acknowledgement UX

## What Exists

- `fleet_alert.status` already has values: `OPEN`, `ACKNOWLEDGED`, `CLOSED` (in base schema)
- `AlertListPage.tsx` exists but has no acknowledge/silence/close actions
- `DeviceAlertsSection.tsx` shows open alerts read-only
- No API endpoints for status transitions exist yet
- No silence/snooze concept in the DB schema

## What This Phase Adds

1. **Acknowledge** — mark an alert as seen. Status: OPEN → ACKNOWLEDGED. Alert stays visible but visually de-emphasized. Evaluator will NOT re-open an ACKNOWLEDGED alert for the same fingerprint until it closes and re-triggers.
2. **Close** — manually close an alert. Status: OPEN/ACKNOWLEDGED → CLOSED. Evaluator can re-open it if the condition persists.
3. **Silence** — snooze an alert for N minutes. New `silenced_until TIMESTAMPTZ` column. Evaluator skips re-alerting while silenced.
4. **Alert history** — view closed/acknowledged alerts, not just OPEN ones.
5. **Audit trail** — who acknowledged/closed what and when.

## Schema Change

Migration adds `silenced_until` and `acknowledged_by` to `fleet_alert`:
```sql
ALTER TABLE fleet_alert ADD COLUMN IF NOT EXISTS silenced_until TIMESTAMPTZ NULL;
ALTER TABLE fleet_alert ADD COLUMN IF NOT EXISTS acknowledged_by TEXT NULL;  -- user sub/email
ALTER TABLE fleet_alert ADD COLUMN IF NOT EXISTS acknowledged_at TIMESTAMPTZ NULL;
```

## Evaluator Change (small)

In the evaluator's `open_or_update_alert()` call: if an existing alert is `ACKNOWLEDGED`, do NOT downgrade it back to `OPEN` on the next evaluation cycle. Only re-open it if it closed and re-triggered.

Also: if `silenced_until > now()`, skip firing the alert entirely for that fingerprint.

## Execution Order

| Prompt | Description |
|--------|-------------|
| 001 | Migration: add `silenced_until`, `acknowledged_by`, `acknowledged_at` |
| 002 | Backend: PATCH /customer/alerts/{id}/acknowledge, /close, /silence |
| 003 | Backend: update list_alerts to support status filter (OPEN/ACKNOWLEDGED/CLOSED/ALL) |
| 004 | Evaluator: respect ACKNOWLEDGED status + silenced_until |
| 005 | Frontend: acknowledge/close/silence buttons on AlertListPage + DeviceAlertsSection |
| 006 | Frontend: alert history view (status filter tabs) |
| 007 | Unit tests |
| 008 | Verify |

## Key Files

- `db/migrations/` — prompt 001
- `services/ui_iot/routes/customer.py` — prompts 002, 003
- `services/evaluator_iot/evaluator.py` — prompt 004
- `frontend/src/features/alerts/AlertListPage.tsx` — prompts 005, 006
- `frontend/src/features/devices/DeviceAlertsSection.tsx` — prompt 005
