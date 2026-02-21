# Phase 181: Standardize All Sub-Page Navigation on Tabs

## Overview

Eliminate the three inconsistent sub-page navigation patterns (left-nav, button links, tabs) and standardize on tabs everywhere. After this phase, every page that contains sub-pages uses the same hub pattern: `PageHeader` + `TabsList variant="line"` + `useSearchParams`.

## Problem

Three different navigation patterns exist for sub-page navigation:
1. **Left-side sub-nav** — Settings page (SettingsLayout with 200px left column)
2. **Button links row** — Devices page (fleet quick-links as outline buttons)
3. **Tabs** — Rules, Analytics, Updates, Tools, Notifications, Team

## Solution

Convert everything to tabs:

**Settings** (left-nav → tabs):
```
General | Billing | Notifications | Integrations | Team | Profile
```
Route: `/settings?tab=general`, `/settings?tab=billing`, etc.

**Devices** (button links → tabs):
```
Devices | Sites | Templates | Groups | Map | Updates | Tools
```
Route: `/devices?tab=list` (default), `/devices?tab=sites`, `/devices?tab=templates`, etc.

**Visual hierarchy for nested hubs:** When a hub page is rendered inside another hub's tab (e.g., UpdatesHubPage inside Devices, NotificationsHubPage inside Settings), its internal tabs switch from `variant="line"` to `variant="default"` (pill style). This visually subordinates inner tabs below the primary tab bar.

## Execution Order

1. `001-embedded-props.md` — Add `embedded` prop to 5 pages + update 4 hub pages for pill-variant tabs when nested
2. `002-devices-hub.md` — Create DevicesHubPage with 7 tabs, remove fleet quick-links
3. `003-settings-hub.md` — Create SettingsHubPage with 6 tabs, delete SettingsLayout
4. `004-route-updates.md` — Router restructure, redirects, CommandPalette, breadcrumbs
5. `005-update-docs.md` — Documentation updates

## Files Modified/Created Summary

| File | Change |
|------|--------|
| `frontend/src/features/devices/DeviceListPage.tsx` | Add `embedded` prop, remove fleet quick-links |
| `frontend/src/features/sites/SitesPage.tsx` | Add `embedded` prop |
| `frontend/src/features/templates/TemplateListPage.tsx` | Add `embedded` prop |
| `frontend/src/features/devices/DeviceGroupsPage.tsx` | Add `embedded` prop |
| `frontend/src/features/map/FleetMapPage.tsx` | Add `embedded` prop |
| `frontend/src/features/ota/UpdatesHubPage.tsx` | Use pill-variant tabs when `embedded` |
| `frontend/src/features/fleet/ToolsHubPage.tsx` | Use pill-variant tabs when `embedded` |
| `frontend/src/features/notifications/NotificationsHubPage.tsx` | Use pill-variant tabs when `embedded` |
| `frontend/src/features/users/TeamHubPage.tsx` | Use pill-variant tabs when `embedded` |
| `frontend/src/features/devices/DevicesHubPage.tsx` | **NEW** — Fleet hub with 7 tabs |
| `frontend/src/features/settings/SettingsHubPage.tsx` | **NEW** — Settings hub with 6 tabs |
| `frontend/src/components/layout/SettingsLayout.tsx` | **DELETE** |
| `frontend/src/app/router.tsx` | Restructure device/settings routes, add redirects |
| `frontend/src/components/shared/CommandPalette.tsx` | Update page hrefs |
| `frontend/src/components/layout/AppHeader.tsx` | Update breadcrumb labels |
| `docs/development/frontend.md` | Update navigation docs |
| `docs/index.md` | Update feature list |
| `docs/services/ui-iot.md` | Update route docs |

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```

- Every sub-page navigation uses tabs (no left-nav, no button rows)
- `/devices` shows fleet hub with 7 tabs (line variant)
- `/devices?tab=updates` shows Updates tab with internal pill-variant sub-tabs (Campaigns, Firmware)
- `/settings` shows settings hub with 6 tabs (line variant)
- `/settings?tab=notifications` shows Notifications tab with internal pill-variant sub-tabs
- All old paths (`/settings/general`, `/sites`, `/templates`, etc.) redirect to the correct hub tab
- `npx tsc --noEmit` passes with no errors
