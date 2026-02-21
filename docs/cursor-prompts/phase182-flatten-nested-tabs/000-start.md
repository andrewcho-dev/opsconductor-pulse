# Phase 182: Flatten Nested Hub Tabs

## Overview

Eliminate the two-level tab nesting introduced in Phase 181 by promoting inner hub tabs to the outer hub level. After this phase, every hub has exactly one level of tabs — no nested hubs, no pill-variant inner tabs.

## Problem

Phase 181 embedded 4 hub pages (Updates, Tools, Notifications, Team) inside DevicesHubPage and SettingsHubPage. These nested hubs create a two-level tab stack:

```
[Devices] [Sites] [Templates] [Groups] [Map] [Updates] [Tools]   ← line tabs
    [Campaigns] [Firmware]                                         ← pill tabs
    ... content ...
```

Three layers of chrome (PageHeader → outer tabs → inner tabs) before content. That's excessive.

## Solution

Flatten everything to one level by replacing nested hub imports with their child components directly:

**Devices hub:** 7 tabs with 2 nested → **9 flat tabs**
```
Devices | Sites | Templates | Groups | Map | Campaigns | Firmware | Guide | MQTT
```

**Settings hub:** 6 tabs with 2 nested → **9 flat tabs**
```
General | Billing | Channels | Delivery Log | Dead Letter | Integrations | Members | Roles | Profile
```

The 4 nested hub pages (UpdatesHubPage, ToolsHubPage, NotificationsHubPage, TeamHubPage) become dead code and are deleted.

## Execution Order

1. `001-flatten-devices-hub.md` — Rewrite DevicesHubPage with 9 flat tabs
2. `002-flatten-settings-hub.md` — Rewrite SettingsHubPage with 9 flat tabs
3. `003-routes-cleanup.md` — Update redirects, CommandPalette, delete 4 unused hub pages
4. `004-update-docs.md` — Documentation updates

## Files Modified/Deleted Summary

| File | Change |
|------|--------|
| `frontend/src/features/devices/DevicesHubPage.tsx` | 7 tabs → 9 flat tabs |
| `frontend/src/features/settings/SettingsHubPage.tsx` | 6 tabs → 9 flat tabs |
| `frontend/src/app/router.tsx` | Update redirect targets for new tab values |
| `frontend/src/components/shared/CommandPalette.tsx` | Update hrefs for new tab values |
| `frontend/src/features/ota/UpdatesHubPage.tsx` | **DELETE** |
| `frontend/src/features/fleet/ToolsHubPage.tsx` | **DELETE** |
| `frontend/src/features/notifications/NotificationsHubPage.tsx` | **DELETE** |
| `frontend/src/features/users/TeamHubPage.tsx` | **DELETE** |
| `docs/development/frontend.md` | Update hub inventory, remove nested hub docs |
| `docs/index.md` | Update feature list |
| `docs/services/ui-iot.md` | Update route docs |

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```

- Every hub has exactly one level of tabs (no nested pills)
- `/devices` shows 9 flat tabs
- `/settings` shows up to 9 flat tabs (Members/Roles hidden by permissions)
- Tab switching updates URL `?tab=` parameter
- All old paths redirect to correct flat tab values
- No unused hub page files remain
- `npx tsc --noEmit` passes with no errors
