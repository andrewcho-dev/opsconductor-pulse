# Phase 185 — Devices Hub Tab Cleanup

## Problem

The Devices Hub (`DevicesHubPage.tsx`) has 9 flat tabs, 4 of which are unnecessary clutter:

| Tab | Why Remove |
|-----|-----------|
| **Sites** | Read-only grid of sites. No CRUD. Device list already has a `site_id` filter dropdown. Redundant. |
| **Groups** | Has full CRUD but belongs as a standalone page, not embedded in the device hub. Users access groups infrequently (setup, not daily). |
| **Guide** | Developer reference (MQTT connection info, code snippets). Not a fleet management workflow tab. |
| **MQTT** | Developer test tool (WebSocket MQTT client). Not a fleet management workflow tab. |

### Target: 9 tabs → 5 tabs

```
BEFORE (9 tabs):
Devices | Sites | Templates | Groups | Map | Campaigns | Firmware | Guide | MQTT

AFTER (5 tabs):
Devices | Templates | Map | Campaigns | Firmware
```

The removed pages remain accessible via standalone routes — they're just no longer tabs in the hub.

## Execution Order

| # | File | Description |
|---|------|-------------|
| 1 | `001-strip-hub-tabs.md` | Remove 4 tabs from DevicesHubPage |
| 2 | `002-update-routes.md` | Fix redirects and add standalone routes |
| 3 | `003-update-navigation.md` | Update CommandPalette and any sidebar references |
| 4 | `004-update-docs.md` | Documentation updates |

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```

- Devices Hub shows only 5 tabs: Devices, Templates, Map, Campaigns, Firmware
- `/sites` loads SitesPage as standalone page (not redirect to hub)
- `/device-groups` loads DeviceGroupsPage as standalone page (not redirect to hub)
- `/fleet/tools` loads ConnectionGuidePage as standalone page
- `/fleet/mqtt-client` loads MqttTestClientPage as standalone page
- All existing direct routes (`/sites/:siteId`, `/device-groups/:groupId`) still work
- CommandPalette entries updated to point to standalone routes
