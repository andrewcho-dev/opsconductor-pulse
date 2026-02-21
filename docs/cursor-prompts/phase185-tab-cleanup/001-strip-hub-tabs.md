# Task 1: Strip 4 Tabs from DevicesHubPage

## File

`frontend/src/features/devices/DevicesHubPage.tsx`

## Current State (9 tabs)

```tsx
<TabsTrigger value="list">Devices</TabsTrigger>
<TabsTrigger value="sites">Sites</TabsTrigger>          // REMOVE
<TabsTrigger value="templates">Templates</TabsTrigger>
<TabsTrigger value="groups">Groups</TabsTrigger>         // REMOVE
<TabsTrigger value="map">Map</TabsTrigger>
<TabsTrigger value="campaigns">Campaigns</TabsTrigger>
<TabsTrigger value="firmware">Firmware</TabsTrigger>
<TabsTrigger value="guide">Guide</TabsTrigger>           // REMOVE
<TabsTrigger value="mqtt">MQTT</TabsTrigger>             // REMOVE
```

## Changes

### A. Remove 4 tab triggers (lines 24, 26, 30, 31)

Delete these lines:
```tsx
<TabsTrigger value="sites">Sites</TabsTrigger>
<TabsTrigger value="groups">Groups</TabsTrigger>
<TabsTrigger value="guide">Guide</TabsTrigger>
<TabsTrigger value="mqtt">MQTT</TabsTrigger>
```

### B. Remove 4 TabsContent blocks (lines 36-38, 42-44, 54-56, 57-59)

Delete these blocks:
```tsx
<TabsContent value="sites" className="mt-4">
  <SitesPage embedded />
</TabsContent>

<TabsContent value="groups" className="mt-4">
  <DeviceGroupsPage embedded />
</TabsContent>

<TabsContent value="guide" className="mt-4">
  <ConnectionGuidePage embedded />
</TabsContent>

<TabsContent value="mqtt" className="mt-4">
  <MqttTestClientPage embedded />
</TabsContent>
```

### C. Remove 4 unused imports (lines 5, 6, 11, 12)

Delete these imports:
```tsx
import DeviceGroupsPage from "./DeviceGroupsPage";
import SitesPage from "@/features/sites/SitesPage";
import ConnectionGuidePage from "@/features/fleet/ConnectionGuidePage";
import MqttTestClientPage from "@/features/fleet/MqttTestClientPage";
```

### D. Handle stale tab params

If someone navigates to `/devices?tab=sites` (from a bookmark or old link), the Tabs component will show no content because the value doesn't match any TabsTrigger. Add a fallback to default unknown tab values to `"list"`:

Replace:
```tsx
const tab = params.get("tab") ?? "list";
```

With:
```tsx
const validTabs = ["list", "templates", "map", "campaigns", "firmware"];
const rawTab = params.get("tab") ?? "list";
const tab = validTabs.includes(rawTab) ? rawTab : "list";
```

### Expected Result

```tsx
import { useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/shared";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import DeviceListPage from "./DeviceListPage";
import TemplateListPage from "@/features/templates/TemplateListPage";
import FleetMapPage from "@/features/map/FleetMapPage";
import OtaCampaignsPage from "@/features/ota/OtaCampaignsPage";
import FirmwareListPage from "@/features/ota/FirmwareListPage";

export default function DevicesHubPage() {
  const [params, setParams] = useSearchParams();
  const validTabs = ["list", "templates", "map", "campaigns", "firmware"];
  const rawTab = params.get("tab") ?? "list";
  const tab = validTabs.includes(rawTab) ? rawTab : "list";

  return (
    <div className="space-y-4">
      <PageHeader title="Devices" description="Manage your device fleet" />
      <Tabs value={tab} onValueChange={(v) => setParams({ tab: v }, { replace: true })}>
        <TabsList variant="line">
          <TabsTrigger value="list">Devices</TabsTrigger>
          <TabsTrigger value="templates">Templates</TabsTrigger>
          <TabsTrigger value="map">Map</TabsTrigger>
          <TabsTrigger value="campaigns">Campaigns</TabsTrigger>
          <TabsTrigger value="firmware">Firmware</TabsTrigger>
        </TabsList>
        <TabsContent value="list" className="mt-4">
          <DeviceListPage embedded />
        </TabsContent>
        <TabsContent value="templates" className="mt-4">
          <TemplateListPage embedded />
        </TabsContent>
        <TabsContent value="map" className="mt-4">
          <FleetMapPage embedded />
        </TabsContent>
        <TabsContent value="campaigns" className="mt-4">
          <OtaCampaignsPage embedded />
        </TabsContent>
        <TabsContent value="firmware" className="mt-4">
          <FirmwareListPage embedded />
        </TabsContent>
      </Tabs>
    </div>
  );
}

export const Component = DevicesHubPage;
```

## Verification

```bash
cd frontend && npx tsc --noEmit
```

- Hub shows only 5 tabs: Devices, Templates, Map, Campaigns, Firmware
- Navigating to `/devices?tab=sites` falls back to Devices tab (no blank content)
- Navigating to `/devices?tab=groups` falls back to Devices tab
- Existing tabs all still render correctly
