# Phase 148a — Device Selector Fix (Bug Fix)

## Problem

The WidgetConfigDialog shows metric and time range selectors for chart widgets (line_chart, area_chart, scatter) but has **no device selector**. The renderers read `config.devices[0]` to call `fetchTelemetryHistory()`, but since there's no way to set `config.devices` from the UI, the value is always `undefined`, the query is disabled, and the user sees "No devices selected" forever.

Similarly, StatCardRenderer reads `config.sparkline_device` for the sparkline background, but there's no way to set it.

This is a single-file fix to `WidgetConfigDialog.tsx`.

## Task 1: Add device selector to WidgetConfigDialog

**File:** `frontend/src/features/dashboard/WidgetConfigDialog.tsx`

### Step 1: Add imports

Add at the top of the file:

```tsx
import { useDevices } from "@/hooks/use-devices";
```

### Step 2: Fetch devices inside the component

Inside the `WidgetConfigDialog` function body (after the existing `useEffect`), add:

```tsx
const { data: deviceListResponse } = useDevices({ limit: 200 });
const availableDevices = deviceListResponse?.devices ?? [];
```

### Step 3: Add device selector to chart widget configs

In the `renderConfigFields()` function, find the block that handles `kpi_tile`, `line_chart`, and `bar_chart`:

```tsx
if (widgetType === "kpi_tile" || widgetType === "line_chart" || widgetType === "bar_chart") {
```

**Before** the metric selector `<div>` inside that block, add a device selector for the chart types that need it:

```tsx
{(widgetType === "line_chart" || widgetType === "bar_chart") && (
  <div className="space-y-2">
    <Label>Device</Label>
    <Select
      value={
        Array.isArray(config.devices) && (config.devices as string[]).length > 0
          ? (config.devices as string[])[0]
          : ""
      }
      onValueChange={(v) => updateConfig("devices", [v])}
    >
      <SelectTrigger>
        <SelectValue placeholder="Select a device" />
      </SelectTrigger>
      <SelectContent>
        {availableDevices.map((d) => (
          <SelectItem key={d.device_id} value={d.device_id}>
            <span className="flex items-center gap-2">
              <span
                className={`inline-block h-2 w-2 rounded-full ${
                  d.status === "online" || d.status === "ONLINE"
                    ? "bg-green-500"
                    : d.status === "STALE"
                      ? "bg-amber-500"
                      : "bg-red-500"
                }`}
              />
              {d.device_id}
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  </div>
)}
```

### Step 4: Add device selector for area_chart

In `renderConfigFields()`, add a new case for `area_chart` **before** the final fallback `return`. The area chart needs the same fields as line_chart (device, metric, time range):

```tsx
if (widgetType === "area_chart") {
  return (
    <>
      <div className="space-y-2">
        <Label>Device</Label>
        <Select
          value={
            Array.isArray(config.devices) && (config.devices as string[]).length > 0
              ? (config.devices as string[])[0]
              : ""
          }
          onValueChange={(v) => updateConfig("devices", [v])}
        >
          <SelectTrigger>
            <SelectValue placeholder="Select a device" />
          </SelectTrigger>
          <SelectContent>
            {availableDevices.map((d) => (
              <SelectItem key={d.device_id} value={d.device_id}>
                <span className="flex items-center gap-2">
                  <span
                    className={`inline-block h-2 w-2 rounded-full ${
                      d.status === "online" || d.status === "ONLINE"
                        ? "bg-green-500"
                        : d.status === "STALE"
                          ? "bg-amber-500"
                          : "bg-red-500"
                    }`}
                  />
                  {d.device_id}
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-2">
        <Label>Metric</Label>
        <Select
          value={(config.metric as string) || "temperature"}
          onValueChange={(v) => updateConfig("metric", v)}
        >
          <SelectTrigger>
            <SelectValue placeholder="Select metric" />
          </SelectTrigger>
          <SelectContent>
            {METRICS.map((m) => (
              <SelectItem key={m.value} value={m.value}>
                {m.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-2">
        <Label>Time Range</Label>
        <Select
          value={(config.time_range as string) || "24h"}
          onValueChange={(v) => updateConfig("time_range", v)}
        >
          <SelectTrigger>
            <SelectValue placeholder="Select range" />
          </SelectTrigger>
          <SelectContent>
            {TIME_RANGES.map((r) => (
              <SelectItem key={r.value} value={r.value}>
                {r.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </>
  );
}
```

### Step 5: Add sparkline device selector for stat_card

In the `stat_card` config section (added in Phase 148), add a device selector for the sparkline:

```tsx
if (widgetType === "stat_card") {
  return (
    <>
      <div className="space-y-2">
        <Label>Metric</Label>
        <Select
          value={(config.metric as string) || "device_count"}
          onValueChange={(v) => updateConfig("metric", v)}
        >
          <SelectTrigger>
            <SelectValue placeholder="Select metric" />
          </SelectTrigger>
          <SelectContent>
            {METRICS.map((m) => (
              <SelectItem key={m.value} value={m.value}>
                {m.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-2">
        <Label>Sparkline Device (optional)</Label>
        <Select
          value={(config.sparkline_device as string) ?? ""}
          onValueChange={(v) => updateConfig("sparkline_device", v)}
        >
          <SelectTrigger>
            <SelectValue placeholder="None (no sparkline)" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">None</SelectItem>
            {availableDevices.map((d) => (
              <SelectItem key={d.device_id} value={d.device_id}>
                <span className="flex items-center gap-2">
                  <span
                    className={`inline-block h-2 w-2 rounded-full ${
                      d.status === "online" || d.status === "ONLINE"
                        ? "bg-green-500"
                        : d.status === "STALE"
                          ? "bg-amber-500"
                          : "bg-red-500"
                    }`}
                  />
                  {d.device_id}
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </>
  );
}
```

### Step 6: Add device selector to gauge

The gauge currently fetches fleet-level data (uptime/health), but for device-specific metrics it would need a device. Update the gauge section to optionally accept a device:

This is optional — skip if gauges are fleet-level only.

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
cd frontend && npm run build
```

## Verify

1. Add a "Metric Trend" (line chart) widget → open config → **"Device" dropdown appears** with all devices
2. Select a device → chart populates with telemetry data
3. Add an "Area Chart" widget → open config → device selector appears
4. Add a "Stat Card" widget → open config → "Sparkline Device" dropdown appears
5. Scatter plot should still work (uses analytics API, not device-specific)
6. Radar should still work (uses analytics API, not device-specific)
7. All existing widgets (KPI, gauge, table, alert feed, fleet overview) still work unchanged
