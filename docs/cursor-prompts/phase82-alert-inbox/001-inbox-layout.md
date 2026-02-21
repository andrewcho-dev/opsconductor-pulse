# Prompt 001 — Alert Inbox Layout

Read `frontend/src/features/alerts/AlertListPage.tsx` fully before making changes.

## Redesign AlertListPage with the following layout:

```
┌─────────────────────────────────────────────────────────────┐
│  Alerts                                    [Refresh] [Rules]│
├─────┬──────────┬──────────────┬────────────┬───────────────┤
│ ALL │ CRITICAL │ HIGH │ MEDIUM │ LOW │ ACK'd │ CLOSED       │
│ (n) │   (n)    │  (n) │  (n)  │ (n) │  (n)  │              │
├─────┴──────────┴──────────────┴────────────┴───────────────┤
│ ☐  [Ack All] [Close All]        Search: [_______________]  │
├──────┬───────────┬──────────────┬────────────┬─────────────┤
│ ☐   │ SEVERITY  │ DEVICE       │ TYPE       │ TIME   │ ··· │
├──────┼───────────┼──────────────┼────────────┼─────────────┤
│ ☐ ▶ │ ● CRITICAL│ pump-alpha   │ THRESHOLD  │ 3m ago │ ··· │
│ ☐ ▶ │ ● HIGH    │ sensor-b     │ NO_TELEMETRY│ 12m ago│ ··· │
└──────┴───────────┴──────────────┴────────────┴─────────────┘
```

### Implementation details:

**Severity tabs with counts:**
```typescript
const TABS = [
  { key: 'ALL', label: 'All' },
  { key: 'OPEN:CRITICAL', label: 'Critical', severity: 'CRITICAL' },
  { key: 'OPEN:HIGH', label: 'High', severity: 'HIGH' },
  { key: 'OPEN:MEDIUM', label: 'Medium', severity: 'MEDIUM' },
  { key: 'OPEN:LOW', label: 'Low', severity: 'LOW' },
  { key: 'ACKNOWLEDGED', label: "Ack'd" },
  { key: 'CLOSED', label: 'Closed' },
]
```
Each tab shows a count badge. Counts come from the current alerts fetch (compute from
results or use a summary endpoint if available).

**Bulk selection:**
- Checkbox per row + "select all" header checkbox
- When any selected: show "[Ack Selected] [Close Selected]" action bar above table
- Bulk actions call acknowledge/close for each selected alert_id in sequence
- After bulk action: clear selection, refetch

**Search/filter bar:**
- Text input that filters by device name or alert type client-side
- Clears on tab change

**Action menu (··· per row):**
- Acknowledge
- Close
- Silence → submenu (15m / 1h / 4h / 24h)
- View Device (navigate to /devices/:device_id)

**Remove DigestSettingsCard from this page** — move it to the Settings group
(it belongs in notification preferences, not the alert inbox).

**Severity color dots:**
- CRITICAL: red filled circle
- HIGH: orange filled circle
- MEDIUM: yellow filled circle
- LOW: blue filled circle

**"Rules" button** in page header links to /alert-rules.

## Acceptance Criteria
- [ ] Severity tabs with counts
- [ ] Bulk select + Ack All / Close All actions
- [ ] Search/filter input
- [ ] Action menu per row with Ack/Close/Silence/View Device
- [ ] DigestSettingsCard removed from this page
- [ ] `npm run build` passes
