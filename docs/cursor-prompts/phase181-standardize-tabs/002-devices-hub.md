# Task 2: Devices Hub Page

## Objective

Create a DevicesHubPage that renders all fleet management pages as tabs, replacing the button-link row from Phase 180.

## File to Create

`frontend/src/features/devices/DevicesHubPage.tsx`

## Design

The hub follows the standard pattern: PageHeader + `TabsList variant="line"` + `useSearchParams`.

**Tabs (7):**
| Tab value | Label | Component | Notes |
|-----------|-------|-----------|-------|
| `list` (default) | Devices | `DeviceListPage` | The device list with master-detail layout |
| `sites` | Sites | `SitesPage` | Site management |
| `templates` | Templates | `TemplateListPage` | Device template management |
| `groups` | Groups | `DeviceGroupsPage` | Device group management |
| `map` | Map | `FleetMapPage` | Geographic fleet view |
| `updates` | Updates | `UpdatesHubPage` | OTA campaigns + firmware (nested hub with pill tabs) |
| `tools` | Tools | `ToolsHubPage` | Connection guide + MQTT test (nested hub with pill tabs) |

## Implementation

```tsx
import { useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/shared";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import DeviceListPage from "./DeviceListPage";
import { DeviceGroupsPage } from "./DeviceGroupsPage";
import SitesPage from "@/features/sites/SitesPage";
import TemplateListPage from "@/features/templates/TemplateListPage";
import FleetMapPage from "@/features/map/FleetMapPage";
import UpdatesHubPage from "@/features/ota/UpdatesHubPage";
import ToolsHubPage from "@/features/fleet/ToolsHubPage";

export default function DevicesHubPage() {
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") ?? "list";

  return (
    <div className="space-y-4">
      <PageHeader title="Devices" description="Manage your device fleet" />
      <Tabs value={tab} onValueChange={(v) => setParams({ tab: v }, { replace: true })}>
        <TabsList variant="line">
          <TabsTrigger value="list">Devices</TabsTrigger>
          <TabsTrigger value="sites">Sites</TabsTrigger>
          <TabsTrigger value="templates">Templates</TabsTrigger>
          <TabsTrigger value="groups">Groups</TabsTrigger>
          <TabsTrigger value="map">Map</TabsTrigger>
          <TabsTrigger value="updates">Updates</TabsTrigger>
          <TabsTrigger value="tools">Tools</TabsTrigger>
        </TabsList>
        <TabsContent value="list" className="mt-4">
          <DeviceListPage embedded />
        </TabsContent>
        <TabsContent value="sites" className="mt-4">
          <SitesPage embedded />
        </TabsContent>
        <TabsContent value="templates" className="mt-4">
          <TemplateListPage embedded />
        </TabsContent>
        <TabsContent value="groups" className="mt-4">
          <DeviceGroupsPage embedded />
        </TabsContent>
        <TabsContent value="map" className="mt-4">
          <FleetMapPage embedded />
        </TabsContent>
        <TabsContent value="updates" className="mt-4">
          <UpdatesHubPage embedded />
        </TabsContent>
        <TabsContent value="tools" className="mt-4">
          <ToolsHubPage embedded />
        </TabsContent>
      </Tabs>
    </div>
  );
}

export const Component = DevicesHubPage;
```

## Important Notes

- **DeviceGroupsPage** — Check if it's a named export or default export. The current code may use `export default` or `export function DeviceGroupsPage`. Adjust the import accordingly.
- **Default tab is `list`** — The device list is the primary view. When navigating to `/devices` without a tab param, users see the device list.
- **Deep links:** `/devices?tab=sites`, `/devices?tab=templates`, `/devices?tab=map`, etc.
- **Nested hubs:** UpdatesHubPage and ToolsHubPage render with `embedded` prop, which (from Task 1) makes their internal tabs use pill variant. This creates clear visual hierarchy: outer line tabs → inner pill tabs.
- **7 tabs may overflow on narrow screens** — shadcn TabsList handles horizontal overflow with scrolling. If not, the `flex-wrap` behavior may apply. Verify on narrow viewports.

## Verification

- `npx tsc --noEmit` passes
- File created at correct path
- `/devices` shows the Devices tab (device list) by default
- All 7 tabs render their embedded content without PageHeaders
- `/devices?tab=updates` shows Updates with pill-variant sub-tabs (Campaigns, Firmware)
- `/devices?tab=tools` shows Tools with pill-variant sub-tabs (Connection Guide, MQTT Test)
- Tab switching updates the URL `?tab=` parameter
