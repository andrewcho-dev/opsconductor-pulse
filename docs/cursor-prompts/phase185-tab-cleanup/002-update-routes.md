# Task 2: Update Routes for Standalone Pages

## File

`frontend/src/app/router.tsx`

## Current State

These routes redirect to hub tabs that no longer exist:

```tsx
{ path: "sites", element: <Navigate to="/devices?tab=sites" replace /> },           // line 82
{ path: "device-groups", element: <Navigate to="/devices?tab=groups" replace /> },   // line 90
{ path: "fleet/tools", element: <Navigate to="/devices?tab=guide" replace /> },      // line 81
```

There is no standalone route for the MQTT test client (it was only accessible via tab).

## Changes

### A. Make `/sites` render SitesPage directly (not redirect to hub)

Replace line 82:
```tsx
// OLD:
{ path: "sites", element: <Navigate to="/devices?tab=sites" replace /> },

// NEW:
{ path: "sites", element: <SitesPage /> },
```

`SitesPage` is already imported indirectly — but it's NOT imported in `router.tsx`. Add the import:

```tsx
import SitesPage from "@/features/sites/SitesPage";
```

When rendered standalone (without `embedded` prop), `SitesPage` already shows its own `PageHeader` via the `{!embedded && <PageHeader .../>}` pattern.

### B. Make `/device-groups` render DeviceGroupsPage directly (not redirect to hub)

Replace line 90:
```tsx
// OLD:
{ path: "device-groups", element: <Navigate to="/devices?tab=groups" replace /> },

// NEW:
{ path: "device-groups", element: <DeviceGroupsPage /> },
```

`DeviceGroupsPage` is already imported in `router.tsx` (line 11).

### C. Make `/fleet/tools` render ConnectionGuidePage directly

Replace line 81:
```tsx
// OLD:
{ path: "fleet/tools", element: <Navigate to="/devices?tab=guide" replace /> },

// NEW:
{ path: "fleet/tools", element: <ConnectionGuidePage /> },
```

Add the import:
```tsx
import ConnectionGuidePage from "@/features/fleet/ConnectionGuidePage";
```

### D. Add standalone route for MQTT test client

Add a new route after the `fleet/tools` route:
```tsx
{ path: "fleet/mqtt-client", element: <MqttTestClientPage /> },
```

Add the import:
```tsx
import MqttTestClientPage from "@/features/fleet/MqttTestClientPage";
```

### Summary of route changes

| Path | Before | After |
|------|--------|-------|
| `/sites` | `→ /devices?tab=sites` | Renders `SitesPage` standalone |
| `/device-groups` | `→ /devices?tab=groups` | Renders `DeviceGroupsPage` standalone |
| `/fleet/tools` | `→ /devices?tab=guide` | Renders `ConnectionGuidePage` standalone |
| `/fleet/mqtt-client` | _(did not exist)_ | Renders `MqttTestClientPage` standalone |
| `/device-groups/:groupId` | Renders `DeviceGroupsPage` | **No change** |
| `/sites/:siteId` | Renders `SiteDetailPage` | **No change** |

## Verification

```bash
cd frontend && npx tsc --noEmit
```

- `/sites` loads SitesPage with its own PageHeader
- `/device-groups` loads DeviceGroupsPage with its own PageHeader
- `/fleet/tools` loads ConnectionGuidePage with its own PageHeader
- `/fleet/mqtt-client` loads MqttTestClientPage with its own PageHeader
- `/sites/:siteId` still loads SiteDetailPage
- `/device-groups/:groupId` still loads DeviceGroupsPage with pre-selected group
