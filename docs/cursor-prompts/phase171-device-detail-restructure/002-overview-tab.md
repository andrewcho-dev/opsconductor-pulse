# Task 2: Overview Tab

## Modify file: `frontend/src/features/devices/DeviceDetailPage.tsx`

Restructure the page to use a tabbed layout. This task sets up the tab structure and implements the Overview tab.

### New Page Structure

Replace the current vertical panel layout with tabs:

```tsx
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";

// ... inside the component return:
<div className="space-y-6">
  {/* Page header with breadcrumb */}
  <div className="flex items-center justify-between">
    <div>
      <nav className="text-sm text-muted-foreground">
        <a href="/app/devices">Devices</a> / {device.device_id}
      </nav>
      <h1 className="text-2xl font-bold">{device.name || device.device_id}</h1>
    </div>
    <div className="flex gap-2">
      {/* Template badge if assigned */}
      {device.template && (
        <Badge variant="outline">
          <a href={`/app/templates/${device.template.id}`}>{device.template.name}</a>
        </Badge>
      )}
      <Button variant="outline" onClick={() => setEditOpen(true)}>Edit</Button>
    </div>
  </div>

  <Tabs defaultValue="overview">
    <TabsList>
      <TabsTrigger value="overview">Overview</TabsTrigger>
      <TabsTrigger value="sensors">Sensors & Data</TabsTrigger>
      <TabsTrigger value="transport">Transport</TabsTrigger>
      <TabsTrigger value="health">Health</TabsTrigger>
      <TabsTrigger value="twin">Twin & Commands</TabsTrigger>
      <TabsTrigger value="security">Security</TabsTrigger>
    </TabsList>

    <TabsContent value="overview">
      <OverviewTab device={device} onUpdate={refetch} />
    </TabsContent>
    <TabsContent value="sensors">
      <SensorsDataTab deviceId={device.device_id} templateId={device.template_id} />
    </TabsContent>
    <TabsContent value="transport">
      <TransportTab deviceId={device.device_id} />
    </TabsContent>
    <TabsContent value="health">
      <HealthTab deviceId={device.device_id} />
    </TabsContent>
    <TabsContent value="twin">
      <TwinCommandsTab deviceId={device.device_id} templateId={device.template_id} />
    </TabsContent>
    <TabsContent value="security">
      <SecurityTab deviceId={device.device_id} />
    </TabsContent>
  </Tabs>
</div>
```

### Overview Tab Content

Create a component (inline in DeviceDetailPage or as a separate file like `DeviceOverviewTab.tsx` in the same directory):

```
OverviewTab
├── 2-column grid
│   ├── Left column: Device Identity Card
│   │   ├── Name / Serial Number / MAC / IMEI
│   │   ├── Template badge (clickable → template detail)
│   │   ├── Device type (from template category)
│   │   ├── Firmware version / HW revision
│   │   ├── Parent device link (if child device)
│   │   └── Tags (editable badges)
│   └── Right column: Location Map Card
│       ├── Leaflet map with marker
│       └── Editable location (reuse DeviceMapCard)
├── Status row
│   ├── Online/Offline/Stale badge with last_seen_at
│   ├── Uptime display
│   └── Quick stats cards: sensor count, module count, last telemetry
└── Notes section (editable textarea)
```

Reuse existing `DeviceInfoCard` and `DeviceMapCard` components where possible — just move them into the Overview tab content area. The `DevicePlanPanel` content (tier info) can be displayed as a small card within the overview.

### Edit Modal

Keep the `DeviceEditModal` (the 448-line full editor) as the primary edit modal. Remove the simpler `EditDeviceModal` (182 lines) — it's a duplicate. Update any imports that referenced `EditDeviceModal` to use `DeviceEditModal` instead.

Add `template_id` to the edit modal:
- Add a template selector dropdown (shows templates visible to tenant)
- When template changes, show a warning: "Changing the template will not remove existing sensors."

## Verification

1. Overview tab renders device identity and map
2. Template badge links to template detail page
3. Tags are editable
4. Notes save correctly
5. Edit modal opens and saves
