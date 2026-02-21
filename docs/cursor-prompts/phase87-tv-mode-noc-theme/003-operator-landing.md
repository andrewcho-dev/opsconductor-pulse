# Prompt 003 — Redesign OperatorDashboard Landing Page

Read `frontend/src/features/operator/OperatorDashboard.tsx` fully.

## Replace OperatorDashboard with a proper operator landing page

The current OperatorDashboard is a simple overview. Replace it with a
command center landing page that orientates the operator and links to the
key tools.

### New layout:
```
┌──────────────────────────────────────────────────────────────┐
│  Operator Console          ● HEALTHY    [Last: 14:32:01]     │
├──────────────────┬───────────────────┬───────────────────────┤
│  QUICK STATS     │  QUICK STATS      │  QUICK STATS          │
│  10 Tenants      │  247 Devices      │  12 Open Alerts       │
│  8 active        │  198 online (80%) │  3 CRITICAL           │
├──────────────────┴───────────────────┴───────────────────────┤
│  ┌──────────────────┐  ┌──────────────────────────────────┐  │
│  │  🖥 NOC Console  │  │  📊 Tenant Health Matrix         │  │
│  │  Full system     │  │  All tenant health at a glance   │  │
│  │  monitoring      │  │                                  │  │
│  │  [Open NOC →]    │  │  [Open Matrix →]                 │  │
│  └──────────────────┘  └──────────────────────────────────┘  │
│  ┌──────────────────┐  ┌──────────────────────────────────┐  │
│  │  👥 Tenants      │  │  🔔 System Alerts                │  │
│  │  Manage tenants  │  │  3 critical, 9 high              │  │
│  │  [View Tenants→] │  │  [View Alerts →]                 │  │
│  └──────────────────┘  └──────────────────────────────────┘  │
│                                                              │
│  Recent Errors (last hour)                                   │
│  [error feed — last 5 errors from /operator/system/errors]   │
└──────────────────────────────────────────────────────────────┘
```

### Implementation:
- Fetch from /operator/system/health, /operator/system/aggregates
- Quick stats row: 3 KPI cards
- 4 navigation cards linking to NOC, tenant matrix, tenants list, system alerts
- Recent errors section at bottom (last 5 from /operator/system/errors?hours=1)
- Auto-refresh: 30s

### Quick stat cards: use existing data from systemAggregates
- Tenants: `aggregates.tenants.active` / `aggregates.tenants.total`
- Devices: `aggregates.devices.online` / `aggregates.devices.registered`
- Alerts: open alerts by severity from /operator/alerts?status=OPEN&limit=1

### Navigation cards: use Link from react-router-dom, styled as large clickable cards

## Acceptance Criteria
- [ ] OperatorDashboard shows 3 KPI cards
- [ ] 4 navigation cards linking to NOC/Matrix/Tenants/Alerts
- [ ] Recent errors feed at bottom
- [ ] Refreshes every 30s
- [ ] `npm run build` passes
