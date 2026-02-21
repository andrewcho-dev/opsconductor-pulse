# Task 2: Restructure DeviceDetailPage — 3 Tabs

## File to Modify

`frontend/src/features/devices/DeviceDetailPage.tsx`

## Changes

### 1. Update imports

**Remove these imports** (no longer directly used):
```tsx
import { DeviceTransportTab } from "./DeviceTransportTab";
import { DeviceHealthTab } from "./DeviceHealthTab";
import { DeviceTwinCommandsTab } from "./DeviceTwinCommandsTab";
import { DeviceSecurityTab } from "./DeviceSecurityTab";
```

**Add these imports:**
```tsx
import { DeviceHealthPanel } from "./DeviceHealthPanel";
import { DeviceUptimePanel } from "./DeviceUptimePanel";
import { DeviceManageTab } from "./DeviceManageTab";
```

**Remove `DevicePlanPanel` import** — it's now rendered by DeviceManageTab, not directly.

### 2. Simplify KPI strip from 5 cards to 3

Replace the `grid grid-cols-5 gap-3` KPI strip with `grid grid-cols-3 gap-3` containing only:

1. **Status + Last Seen** (keep as-is)
2. **Open Alerts** (keep as-is, red when > 0)
3. **Sensors** (keep as-is)

**Remove** the Firmware card and Plan card. (Firmware is visible in the Hardware property card on Overview. Plan is visible in the Manage tab.)

```tsx
{/* KPI strip — above tabs */}
<div className="grid grid-cols-3 gap-3">
  <div className="rounded-md border border-border p-3">
    <div className="flex items-center gap-2">
      <span className={`h-3 w-3 rounded-full ${statusDot(device?.status)}`} />
      <span className="text-sm font-semibold">{device?.status ?? "—"}</span>
    </div>
    <div className="mt-1 text-xs text-muted-foreground">{relativeTime(device?.last_seen_at)}</div>
  </div>
  <div className="rounded-md border border-border p-3">
    <div className={`text-lg font-semibold ${openAlertCount > 0 ? "text-destructive" : ""}`}>
      {openAlertCount}
    </div>
    <div className="text-xs text-muted-foreground">Open Alerts</div>
  </div>
  <div className="rounded-md border border-border p-3">
    <div className="text-lg font-semibold">{device?.sensor_count ?? "—"}</div>
    <div className="text-xs text-muted-foreground">Sensors</div>
  </div>
</div>
```

### 3. Change TabsList from 6 tabs to 3

Replace the entire `<TabsList>` block:

```tsx
<TabsList>
  <TabsTrigger value="overview">Overview</TabsTrigger>
  <TabsTrigger value="data">Data</TabsTrigger>
  <TabsTrigger value="manage">Manage</TabsTrigger>
</TabsList>
```

### 4. Restructure Overview TabsContent

Add DeviceHealthPanel and DeviceUptimePanel to the Overview tab. Remove DevicePlanPanel (now in Manage).

```tsx
<TabsContent value="overview" className="pt-2 space-y-4">
  {/* DeviceInfoCard — property cards + tags/notes (fragment-based from Phase 188) */}
  <DeviceInfoCard
    device={device}
    isLoading={deviceLoading}
    tags={deviceTags}
    onTagsChange={(next) => {
      setDeviceTagsState(next);
      void handleSaveTags(next);
    }}
    notesValue={notesValue}
    onNotesChange={handleNotesChange}
    onNotesBlur={handleSaveNotes}
    onEdit={() => setEditModalOpen(true)}
  />

  {/* Device Health — diagnostics strip + signal chart */}
  {deviceId && <DeviceHealthPanel deviceId={deviceId} />}

  {/* Latest Telemetry — full width 4-column metric grid */}
  <div className="rounded-md border border-border p-4">
    <h4 className="mb-3 text-sm font-semibold">Latest Telemetry</h4>
    {latestMetrics.length === 0 ? (
      <p className="text-sm text-muted-foreground">No telemetry data yet.</p>
    ) : (
      <div className="grid gap-x-6 gap-y-1 sm:grid-cols-2 md:grid-cols-4">
        {latestMetrics.map(([name, value]) => (
          <div key={name} className="flex items-center justify-between py-1 text-sm">
            <span className="text-muted-foreground">{name}</span>
            <span className="font-mono font-medium">{String(value)}</span>
          </div>
        ))}
      </div>
    )}
    {latestMetrics.length > 0 && (
      <div className="mt-2 text-right text-xs text-muted-foreground">
        Updated {relativeTime(points.at(-1)?.timestamp)}
      </div>
    )}
  </div>

  {/* Uptime — availability bar + stats */}
  {deviceId && <DeviceUptimePanel deviceId={deviceId} />}

  {/* Map — full width, only if coordinates exist */}
  {device?.latitude != null && device?.longitude != null && (
    <div className="relative h-[200px]">
      <DeviceMapCard
        latitude={pendingLocation?.lat ?? device.latitude}
        longitude={pendingLocation?.lng ?? device.longitude}
        address={device.address}
        editable
        onLocationChange={handleMapLocationChange}
      />
      {pendingLocation && (
        <div className="absolute bottom-2 right-2 z-[1000] flex gap-1">
          <Button size="sm" className="h-8" onClick={handleSaveLocation}>
            Save Location
          </Button>
          <Button size="sm" variant="outline" className="h-8" onClick={() => setPendingLocation(null)}>
            Cancel
          </Button>
        </div>
      )}
    </div>
  )}
</TabsContent>
```

**Note:** DevicePlanPanel is gone from Overview — it's now inside DeviceManageTab.

### 5. Rename Sensors tab value and add Manage tab

Replace the `sensors`, `transport`, `health`, `twin`, `security` TabsContent blocks with:

```tsx
<TabsContent value="data">
  {deviceId ? (
    <DeviceSensorsDataTab
      deviceId={deviceId}
      templateId={device?.template_id ?? null}
      telemetry={{
        points,
        metrics,
        isLoading: telemetryLoading,
        isLive,
        liveCount,
        timeRange,
        onTimeRangeChange: setTimeRange,
      }}
    />
  ) : null}
</TabsContent>

<TabsContent value="manage">
  {deviceId ? <DeviceManageTab deviceId={deviceId} /> : null}
</TabsContent>
```

**Delete** the 4 old TabsContent blocks for `transport`, `health`, `twin`, `security`.

### 6. Summary of what changes

| Before | After |
|--------|-------|
| 6 tabs: Overview, Sensors & Data, Transport, Health, Twin & Commands, Security | 3 tabs: Overview, Data, Manage |
| KPI strip: 5 cards (Status, Sensors, Alerts, Firmware, Plan) | KPI strip: 3 cards (Status, Alerts, Sensors) |
| Health data on separate tab | Health data on Overview (DeviceHealthPanel + DeviceUptimePanel) |
| Transport, Twin, Commands, Security each on own tab | All 4 under Manage tab with section headers |
| DevicePlanPanel on Overview | DevicePlanPanel inside Manage tab |

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```

- Only 3 tabs: Overview, Data, Manage
- Overview shows: property cards → health panel → telemetry → uptime → map
- Data tab: modules + sensors + charts (unchanged)
- Manage tab: 4 sections with icon headers (Connectivity, Control, Security, Subscription)
- KPI strip has 3 cards only
- No TypeScript errors, no unused imports
