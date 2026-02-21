# Prompt 002 — Inline Expandable Alert Detail

Read `frontend/src/features/alerts/AlertListPage.tsx` after Prompt 001 changes.

## Add expandable row detail

Each alert row has a ▶ expand chevron (left of checkbox). Clicking it expands
an inline detail panel below that row (not a modal, not a new page).

Expanded detail shows:
```
┌─────────────────────────────────────────────────────┐
│  Alert Details                                       │
│  ─────────────────────────────────────────────────  │
│  Device: pump-alpha          Tenant: acme-corp       │
│  Rule: "pressure > 120 psi"  Type: THRESHOLD         │
│  Opened: Jan 15 2026 14:23   Duration: 3m 42s        │
│  Silenced until: —           Escalation level: 0     │
│                                                      │
│  Summary: pressure metric exceeded threshold         │
│  Details: {"metric": "pressure", "value": 127.3, ... │
│                                                      │
│  [Acknowledge]  [Close]  [Silence ▾]  [View Device →]│
└─────────────────────────────────────────────────────┘
```

Implementation:
- `expandedAlertId` state (string | null)
- Click ▶ toggles expanded state for that row
- Detail panel uses `Collapsible` or just conditional render with transition
- All action buttons in detail panel call same handlers as row action menu
- Duration computed as `now - opened_at` formatted as "Xm Ys" or "Xh Ym"
- Details JSON shown in a `<pre className="text-xs bg-muted p-2 rounded max-h-32 overflow-auto">`

## Acceptance Criteria
- [ ] Expand chevron on each row
- [ ] Inline detail panel shows all fields
- [ ] Action buttons in detail work (ack/close/silence)
- [ ] Only one row expanded at a time
- [ ] `npm run build` passes
