# Prompt 004 — Frontend: Escalation Badge

Read `frontend/src/features/alerts/AlertListPage.tsx` fully.

## Add Escalation Badge

In the alert list table, add a visual indicator for escalated alerts:

- If `escalation_level > 0`: show an orange "Escalated" badge next to the alert status
- Tooltip on the badge: "Escalated at {escalated_at formatted as local time}"
- The badge should be distinct from the existing status badge (OPEN/ACKNOWLEDGED/CLOSED)

## Update Alert Type

Add `escalation_level` and `escalated_at` to the alert TypeScript type (wherever Alert is defined in `frontend/src/services/api/types.ts` or similar):

```typescript
escalation_level: number;
escalated_at: string | null;
```

These fields are now returned by `GET /customer/alerts` (the backend already selects all columns from fleet_alert).

## Acceptance Criteria

- [ ] `escalation_level` and `escalated_at` in Alert TypeScript type
- [ ] "Escalated" orange badge shown when escalation_level > 0
- [ ] Tooltip shows escalated_at timestamp
- [ ] `npm run build` passes
