# Prompt 003 — Frontend: Wire FleetSummaryWidget + Live Badge

Read `frontend/src/features/devices/FleetSummaryWidget.tsx` fully.

## Replace useFleetSummary with useFleetSummaryWS

Replace the existing `useFleetSummary()` (REST polling) import with `useFleetSummaryWS()`.

The data shape is the same (`online`, `stale`, `offline`, `total`, `active_alerts`) so the display code should not need to change.

## Add "Live" Badge

When `isConnected === true`, show a small green "● Live" indicator in the top-right corner of the widget.
When `isConnected === false` (fallback REST mode), show a grey "○ Polling" indicator.

Use a small badge/chip component consistent with the existing design system.

## Loading State

While `isLoading === true`, show skeleton loaders (or the existing spinner pattern from the codebase) instead of the count cards.

## Acceptance Criteria

- [ ] FleetSummaryWidget uses `useFleetSummaryWS`
- [ ] "● Live" green badge when WebSocket connected
- [ ] "○ Polling" badge when falling back to REST
- [ ] Loading skeleton while initial data loads
- [ ] `npm run build` passes
