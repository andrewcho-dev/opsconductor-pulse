# Prompt 005 — Frontend: Acknowledge / Close / Silence Buttons

Read `frontend/src/features/alerts/AlertListPage.tsx` and `frontend/src/features/devices/DeviceAlertsSection.tsx` fully.

Also read `frontend/src/services/api/` to understand the existing API client pattern.

## Add API Client Functions

In `frontend/src/services/api/alerts.ts` (create if not exists, or add to existing):

```typescript
export async function acknowledgeAlert(alertId: string): Promise<void> {
  await apiFetch(`/customer/alerts/${alertId}/acknowledge`, { method: 'PATCH' });
}

export async function closeAlert(alertId: string): Promise<void> {
  await apiFetch(`/customer/alerts/${alertId}/close`, { method: 'PATCH' });
}

export async function silenceAlert(alertId: string, minutes: number): Promise<void> {
  await apiFetch(`/customer/alerts/${alertId}/silence`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ minutes }),
  });
}
```

## Update AlertListPage.tsx

Add three action buttons to each alert row:
- **Acknowledge** — shown only when `status === 'OPEN'`. On click: calls `acknowledgeAlert(alert.id)`, then refetches.
- **Close** — shown when `status === 'OPEN'` or `status === 'ACKNOWLEDGED'`. On click: calls `closeAlert(alert.id)`, then refetches.
- **Silence** — shown when `status === 'OPEN'` or `status === 'ACKNOWLEDGED'`. On click: opens a small inline dropdown/select for duration (15 min, 30 min, 1 hour, 4 hours, 24 hours), then calls `silenceAlert(alert.id, minutes)`, then refetches.

Visual treatment:
- ACKNOWLEDGED alerts should be visually de-emphasized (e.g. `opacity-60` or muted text color)
- Silenced alerts (where `silenced_until` is set and in the future) should show a "Silenced until HH:MM" badge

Use the existing button/badge styling patterns already present in the file.

## Update DeviceAlertsSection.tsx

Add the same three action buttons (Acknowledge, Close, Silence) to each alert row, following the same logic as AlertListPage.

## Acceptance Criteria

- [ ] Acknowledge button appears on OPEN alerts, calls PATCH /acknowledge
- [ ] Close button appears on OPEN and ACKNOWLEDGED alerts
- [ ] Silence button opens duration picker, calls PATCH /silence
- [ ] After each action, alert list refetches
- [ ] ACKNOWLEDGED alerts visually de-emphasized
- [ ] Silenced alerts show badge with expiry time
- [ ] `npm run build` passes with no TypeScript errors
