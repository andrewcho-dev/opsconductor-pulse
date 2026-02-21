# Task 1: Restructure DeviceDetailPage Overview Layout

## File

`frontend/src/features/devices/DeviceDetailPage.tsx`

## Current Problems

1. Overview tab is `grid grid-cols-2` — DeviceInfoCard (left) + DeviceMapCard (right). Map takes 50% even when empty.
2. DevicePlanPanel is a separate Card below the grid — buried after scrolling.
3. No telemetry snapshot on the overview tab.
4. "Saving notes..." and "Saving tags..." are raw text floating below.
5. Alert count is a plain text link at the bottom.
6. No status banner or KPI row above the tabs.

## Changes

### A. Add KPI row above the Tabs (between PageHeader and TabsList)

Insert a row of 5 compact stat cards above the tabs. These show at-a-glance health info:

```tsx
{/* KPI strip — above tabs */}
<div className="grid grid-cols-5 gap-3">
  <div className="rounded-md border border-border p-3">
    <div className="flex items-center gap-2">
      <span className={`h-3 w-3 rounded-full ${statusDot(device?.status)}`} />
      <span className="text-sm font-semibold">{device?.status ?? "—"}</span>
    </div>
    <div className="mt-1 text-xs text-muted-foreground">
      {relativeTime(device?.last_seen_at)}
    </div>
  </div>
  <div className="rounded-md border border-border p-3">
    <div className="text-lg font-semibold">{device?.sensor_count ?? "—"}</div>
    <div className="text-xs text-muted-foreground">Sensors</div>
  </div>
  <div className="rounded-md border border-border p-3">
    <div className={`text-lg font-semibold ${openAlertCount > 0 ? "text-destructive" : ""}`}>
      {openAlertCount}
    </div>
    <div className="text-xs text-muted-foreground">Open Alerts</div>
  </div>
  <div className="rounded-md border border-border p-3">
    <div className="text-lg font-semibold">{device?.fw_version ?? "—"}</div>
    <div className="text-xs text-muted-foreground">Firmware</div>
  </div>
  <div className="rounded-md border border-border p-3">
    <div className="text-lg font-semibold">
      {device?.plan_id ?? "—"}
    </div>
    <div className="text-xs text-muted-foreground">Plan</div>
  </div>
</div>
```

Add the `relativeTime` helper function (copy from the deleted DeviceDetailPane, or inline):

```tsx
function relativeTime(input?: string | null) {
  if (!input) return "never";
  const deltaMs = Date.now() - new Date(input).getTime();
  if (!Number.isFinite(deltaMs) || deltaMs < 0) return "just now";
  const minutes = Math.floor(deltaMs / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function statusDot(status?: string) {
  if (status === "ONLINE") return "bg-status-online";
  if (status === "STALE") return "bg-status-stale";
  return "bg-status-offline";
}
```

### B. Restructure Overview tab to 2-column: Properties (left) + Telemetry/Map (right)

Replace the current Overview TabsContent (lines 181-231):

```tsx
<TabsContent value="overview" className="pt-2 space-y-4">
  <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
    {/* Left: Device Properties */}
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

    {/* Right: Latest Telemetry + Map */}
    <div className="space-y-4">
      {/* Telemetry snapshot */}
      <div className="rounded-md border border-border p-4">
        <h4 className="text-sm font-semibold mb-3">Latest Telemetry</h4>
        {latestMetrics.length === 0 ? (
          <p className="text-sm text-muted-foreground">No telemetry data yet.</p>
        ) : (
          <div className="space-y-2">
            {latestMetrics.map(([name, value]) => (
              <div key={name} className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">{name}</span>
                <span className="font-mono font-medium">{String(value)}</span>
              </div>
            ))}
            <div className="pt-1 text-xs text-muted-foreground text-right">
              Updated {relativeTime(points.at(-1)?.timestamp)}
            </div>
          </div>
        )}
      </div>

      {/* Map — only when coordinates exist */}
      {(device?.latitude != null && device?.longitude != null) && (
        <div className="relative">
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
              <Button
                size="sm"
                variant="outline"
                className="h-8"
                onClick={() => setPendingLocation(null)}
              >
                Cancel
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  </div>
</TabsContent>
```

### C. Compute latestMetrics from telemetry points

Add this useMemo (similar to what the deleted DeviceDetailPane had):

```tsx
const latestMetrics = useMemo(() => {
  const latest = points.at(-1);
  if (!latest) return [];
  return Object.entries(latest.metrics).slice(0, 12);
}, [points]);
```

### D. Remove DevicePlanPanel from the overview

The plan info is already surfaced in the KPI strip (plan_id card). The full DevicePlanPanel with "Change Plan" dialog should move to a more appropriate location — either:
- Keep it at the bottom of the overview tab (below the 2-column grid), or
- Keep it as-is below the grid

For now, keep `DevicePlanPanel` below the 2-column grid but wrap it with a section header:

```tsx
{/* Below the 2-column grid, full width */}
{deviceId && (
  <section>
    <DevicePlanPanel deviceId={deviceId} />
  </section>
)}
```

### E. Remove floating text

Remove these lines (they add nothing — toast notifications already cover this):
```tsx
{notesSaving && <div className="text-sm text-muted-foreground">Saving notes...</div>}
{tagsSaving && <div className="text-sm text-muted-foreground">Saving tags...</div>}
```

Remove the plain text alerts link — alerts are now shown as a KPI card count above:
```tsx
{openAlertCount > 0 && (
  <Link to="/alerts" className="text-sm text-primary hover:underline">
    View {openAlertCount} alerts
  </Link>
)}
```

### Page structure after changes

```
PageHeader (breadcrumbs + title + action buttons)
↓
KPI strip (5 cards: Status, Sensors, Alerts, Firmware, Plan)
↓
Tabs: [Overview] [Sensors & Data] [Transport] [Health] [Twin] [Security]
↓
Overview tab:
  ┌─────────────────────────────────┬──────────────────┐
  │ DeviceInfoCard (properties)      │ Latest Telemetry │
  │ (Identity, Hardware, Network,   │ (metric values)  │
  │  Tags, Notes)                    │                  │
  │                                  │ Map (if coords)  │
  └─────────────────────────────────┴──────────────────┘
  DevicePlanPanel (full width)
```

## Verification

```bash
cd frontend && npx tsc --noEmit
```

- 5 KPI cards visible above tabs (Status, Sensors, Alerts, Firmware, Plan)
- Overview tab: properties card left, telemetry + map right
- Map only shows when device has latitude/longitude
- No floating "Saving notes/tags" text
- No plain text alerts link
- All 6 tabs still work
- Edit modal still works
- Create Job modal still works
