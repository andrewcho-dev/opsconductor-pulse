# Phase 180: Navigation Simplification + Rules Hub

## Overview

Radically simplify the sidebar to ~7 items by removing secondary fleet pages and introducing a Rules hub for alert/automation configuration.

**Current sidebar (~13 items):**
```
Home
── Monitoring ──
  Dashboard, Alerts, Analytics
── Fleet ──
  Getting Started*, Devices, Sites, Templates, Fleet Map, Device Groups, Updates, Tools
── Settings
```

**New sidebar (7 items):**
```
Home
── Monitoring ──
  Dashboard, Alerts, Analytics
── Fleet ──
  Devices, Rules
── Settings
```

## Key Design Decisions

- **Sites, Templates, Groups, Map, Updates, Tools** — Removed from sidebar. Accessible via a compact "fleet links" navigation row on the Devices page. All existing routes are preserved.
- **Getting Started** — Removed from sidebar. The `OnboardingChecklist` already renders on the Home page. The `/fleet/getting-started` route still works for direct access.
- **Rules Hub** — New page at `/rules` with 4 tabs: Alert Rules, Escalation, On-Call, Maintenance Windows. These tabs are moved out of the Alerts hub. Designed to be extensible for future automation/routing rules.
- **Alerts simplification** — With rules/escalation/oncall/maintenance moved to the Rules hub, the Alerts hub becomes a single-purpose alert inbox. The hub wrapper is simplified to render `AlertListPage` directly (no tab navigation needed for one view).

## Execution Order

1. `001-rules-hub.md` — Create RulesHubPage with 4 tabs
2. `002-alerts-simplify.md` — Simplify AlertsHubPage to inbox only, add redirects
3. `003-devices-fleet-nav.md` — Add fleet quick-links row to DeviceListPage
4. `004-sidebar-routes.md` — Sidebar cleanup, add Rules, route updates, CommandPalette, breadcrumbs
5. `005-update-docs.md` — Documentation updates

## Files Modified/Created Summary

| File | Change |
|------|--------|
| `frontend/src/features/rules/RulesHubPage.tsx` | **NEW** — Rules hub with 4 tabs |
| `frontend/src/features/alerts/AlertsHubPage.tsx` | Simplify to inbox only (remove 4 tabs) |
| `frontend/src/features/devices/DeviceListPage.tsx` | Add fleet quick-links navigation row |
| `frontend/src/components/layout/AppSidebar.tsx` | Remove 7 items, add Rules |
| `frontend/src/app/router.tsx` | Add `/rules` route, update redirects |
| `frontend/src/components/shared/CommandPalette.tsx` | Update page list |
| `frontend/src/components/layout/AppHeader.tsx` | Add `rules` breadcrumb label |
| `docs/development/frontend.md` | Update navigation structure, hub inventory |
| `docs/index.md` | Update feature list |
| `docs/services/ui-iot.md` | Document new routes |

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```

- Sidebar shows 7 items: Home, Dashboard, Alerts, Analytics, Devices, Rules, Settings
- `/rules` shows Rules hub with Alert Rules, Escalation, On-Call, Maintenance tabs
- `/alerts` shows just the alert inbox (no tab navigation)
- `/alerts?tab=rules` redirects to `/rules?tab=alert-rules`
- Devices page has a fleet quick-links row with access to Sites, Templates, Groups, Map, Updates, Tools
- All removed pages still accessible at their existing URLs
- Getting Started is gone from sidebar but OnboardingChecklist renders on Home page
