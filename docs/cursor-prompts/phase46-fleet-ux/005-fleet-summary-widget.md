# Prompt 005 — Frontend: Fleet Status Summary Widget

## Context

`useFleetSummary()` is now available. This prompt adds a summary widget at the top of `DeviceListPage.tsx` showing real-time fleet health counts.

## Your Task

**Read `frontend/src/features/devices/DeviceListPage.tsx` fully** before making changes.

### Add a Fleet Summary Widget

At the top of the page, above the filters and table, add a row of status count cards:

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  ● 142      │  │  ● 23       │  │  ● 8        │  │    173      │
│  Online     │  │  Stale      │  │  Offline    │  │  Total      │
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
```

- **Online** — green dot, count from `summary.ONLINE`
- **Stale** — yellow/amber dot, count from `summary.STALE`
- **Offline** — red dot, count from `summary.OFFLINE`
- **Total** — neutral, count from `summary.total`

### Behavior

- Each status card is **clickable** — clicking it sets the `statusFilter` to that status (same as clicking the filter button). Clicking the active status card again clears the filter.
- The active status card gets a highlighted border/background.
- While `useFleetSummary()` is loading, show skeleton placeholders (4 gray boxes same size).
- If the summary fails to load, hide the widget silently (don't show an error — the table still works).

### Styling

Follow the existing card/panel style used elsewhere in the UI. Use Tailwind classes if the project uses Tailwind, or inline the existing CSS class patterns. Do NOT add new CSS frameworks.

### Integration

```tsx
const { data: summary } = useFleetSummary();

// Pass statusFilter setter from filters state to the widget
<FleetSummaryWidget
  summary={summary}
  activeStatus={filters.status ?? ""}
  onStatusClick={(s) => setFilters(f => ({
    ...f,
    status: f.status === s ? undefined : s,  // toggle
    offset: 0
  }))}
/>
```

Create this as a small component in the same file or as `frontend/src/features/devices/FleetSummaryWidget.tsx`.

## Acceptance Criteria

- [ ] Fleet summary widget visible at top of device list page
- [ ] Shows correct counts (live from API, refreshes every 30s)
- [ ] Clicking a status card filters the table to that status
- [ ] Clicking the active status card clears the filter
- [ ] Loading state shows skeleton placeholders
- [ ] `npm run build` clean
