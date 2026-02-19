# Phase 174 — Fleet Navigation Restructure & Getting Started Guide

## Goal

Restructure the Fleet sidebar from a flat 8-item list into a workflow-oriented layout with three labelled sub-groups (Setup / Monitor / Maintain), add a "Getting Started" onboarding page, add a fleet health summary strip to the device list, and add a deprecation tip to the Sensors page.

## Execution Order

| # | File | Summary |
|---|------|---------|
| 1 | `001-sidebar-restructure.md` | Restructure Fleet group into sub-group labels; add Getting Started link; remove Sensors |
| 2 | `002-getting-started-page.md` | Create GettingStartedPage with 5-step setup guide + route registration |
| 3 | `003-device-list-health.md` | Add fleet health summary strip to DeviceListPage; add deprecation tip to SensorListPage |
| 4 | `004-update-docs.md` | Update documentation for this phase |

## Verification

```bash
# Frontend builds cleanly
cd frontend && npx tsc --noEmit && npm run build
```

Manual checks:
- Sidebar shows Fleet with Setup / Monitor / Maintain sub-labels
- "Getting Started" link appears at top of Fleet group
- Getting Started page loads at `/app/fleet/getting-started`
- Steps show completion status (green check for completed, circle for incomplete)
- Dismissing Getting Started hides the sidebar link
- Device list shows health summary strip (Online / Stale / Offline counts)
- Sensors page shows tip banner
- "Sensors" link is gone from sidebar
- All existing Fleet pages still accessible via direct URL
