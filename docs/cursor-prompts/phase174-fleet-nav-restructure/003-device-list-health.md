# Task 3: Device List Health Strip + Sensor Page Tip

## Objective

Add a compact fleet health summary bar to the device list page and a deprecation tip banner to the sensors page.

## Files to Modify

- `frontend/src/features/devices/DeviceListPage.tsx`
- `frontend/src/features/devices/SensorListPage.tsx`

---

## Part A: Device List Health Strip

### File: `frontend/src/features/devices/DeviceListPage.tsx`

### Current State

The page (line 43, `DeviceListPage` function) renders a `PageHeader` followed by `AddDeviceModal`, then either error, loading skeletons, empty state, or the device list grid. The `data` object from `useDevices` contains `devices` and `total`.

### Changes

Add a fleet health summary strip between the `AddDeviceModal` (line 115) and the error/loading conditional block (line 117). This strip should compute device counts by status from the already-loaded `devices` array.

1. **Compute status counts** — Add a `useMemo` that counts devices by status from `data.devices`:

   ```tsx
   const statusCounts = useMemo(() => {
     const counts = { online: 0, stale: 0, offline: 0 };
     for (const d of devices) {
       if (d.status === "ONLINE") counts.online++;
       else if (d.status === "STALE") counts.stale++;
       else counts.offline++;
     }
     return counts;
   }, [devices]);
   ```

   Add this after the existing `alertCountByDevice` useMemo (around line 82).

2. **Render the health strip** — Insert between the `<AddDeviceModal ... />` close tag (line 115) and the `{error ? (` conditional (line 117). Only show when devices are loaded and there are devices:

   ```tsx
   {!isLoading && devices.length > 0 && (
     <div className="flex items-center gap-4 rounded-md border border-border px-3 py-2 text-sm">
       <div className="flex items-center gap-1.5">
         <span className="h-2 w-2 rounded-full bg-status-online" />
         <span>{statusCounts.online} Online</span>
       </div>
       <div className="flex items-center gap-1.5">
         <span className="h-2 w-2 rounded-full bg-status-stale" />
         <span>{statusCounts.stale} Stale</span>
       </div>
       <div className="flex items-center gap-1.5">
         <span className="h-2 w-2 rounded-full bg-status-offline" />
         <span>{statusCounts.offline} Offline</span>
       </div>
       <span className="text-muted-foreground">|</span>
       <span className="text-muted-foreground">{totalCount} total devices</span>
     </div>
   )}
   ```

### Notes

- Uses the existing `bg-status-online`, `bg-status-stale`, `bg-status-offline` CSS classes that are already defined in the project's design tokens (same as `statusDot` function at line 25).
- Counts are from the currently-fetched page of devices. The `totalCount` comes from the API response total (all devices, not just the current page). This is acceptable for a quick visual summary.
- The strip renders as a compact single line, consistent with the project's design conventions.

---

## Part B: Sensor Page Deprecation Tip

### File: `frontend/src/features/devices/SensorListPage.tsx`

### Current State

The page (line 64, `SensorListPage` function) renders a `PageHeader` (line 150-153) followed by the filter/table area (line 155).

### Changes

Insert a tip banner between the `<PageHeader>` (line 153) and the filter/table `<div>` (line 155):

```tsx
<div className="rounded-md border border-blue-200 bg-blue-50 dark:border-blue-900 dark:bg-blue-950/30 p-3 text-sm">
  <strong>Tip:</strong> You can now manage sensors per-device on the{" "}
  <strong>Sensors & Data</strong> tab of each device's detail page.
</div>
```

This sits inside the existing `<div className="space-y-4">` wrapper so it will get proper spacing from the parent's `space-y-4`.

## Verification

- `npx tsc --noEmit` passes
- Device list page shows the health strip (colored dots + counts) between the header and the device list when devices are present
- Health strip is hidden during loading and when there are no devices
- Sensor page shows the blue tip banner below the page header
- No styling regressions on either page
