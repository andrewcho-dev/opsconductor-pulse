# Task 001 — Dashboard Widget Config Targets Sensors

## Context

Currently, chart widgets (line_chart, bar_chart, area_chart, scatter) have a device selector that lets users pick a device and a metric. With sensors as first-class entities, the config flow should be:

1. Pick a device (or "All devices")
2. Pick a sensor from that device (shows sensor label, type, unit)
3. The chart fetches telemetry for that device + metric_name

This is a UI improvement — the underlying telemetry API still queries by device_id + metric name.

## Files to Modify

### 1. `frontend/src/features/dashboard/WidgetConfigDialog.tsx`

Find the device/metric selection section in the Data tab (the section that handles chart widgets like line_chart, bar_chart, area_chart).

**Current flow:** User picks a device → picks a metric name from a hardcoded or telemetry-discovered list.

**New flow:**
1. User picks a device (existing device selector stays)
2. Once a device is selected, fetch sensors for that device: `listDeviceSensors(deviceId)`
3. Show a sensor selector dropdown populated from the sensor list
4. Each option shows: `{sensor.label || sensor.metric_name} ({sensor.sensor_type}, {sensor.unit})`
5. When a sensor is selected, set `config.metric` to `sensor.metric_name` (the chart renderer reads `config.metric`)

**Add a new query:**
```tsx
import { listDeviceSensors } from "@/services/api/sensors";

// Inside the dialog, when a device is selected:
const selectedDeviceId = (localConfig.devices as string[])?.[0];

const { data: sensorsData } = useQuery({
  queryKey: ["device-sensors", selectedDeviceId],
  queryFn: () => listDeviceSensors(selectedDeviceId!),
  enabled: !!selectedDeviceId,
});
```

**Replace the metric input** (if it's a text input or simple select) with a sensor-driven select:

```tsx
<div className="space-y-1">
  <Label className="text-xs">Sensor / Metric</Label>
  <Select
    value={localConfig.metric as string}
    onValueChange={(v) => updateConfig("metric", v)}
  >
    <SelectTrigger>
      <SelectValue placeholder="Select a sensor" />
    </SelectTrigger>
    <SelectContent>
      {sensorsData?.sensors?.map((s) => (
        <SelectItem key={s.sensor_id} value={s.metric_name}>
          {s.label || s.metric_name}
          <span className="text-xs text-muted-foreground ml-2">
            ({s.sensor_type}{s.unit ? `, ${s.unit}` : ""})
          </span>
        </SelectItem>
      ))}
    </SelectContent>
  </Select>
</div>
```

### 2. Scatter widget — two-sensor selection

The scatter widget needs two metrics (x and y). Apply the same pattern but with two sensor selectors:
- "X-Axis Sensor" → sets `config.x_metric`
- "Y-Axis Sensor" → sets `config.y_metric`

Both selectors are populated from the same device's sensor list.

### 3. Radar widget — multi-sensor selection

The radar widget needs 3-6 metrics. Use a multi-select or checkbox list populated from sensors. Each selected sensor adds its `metric_name` to the `config.radar_metrics` array.

## Notes

- The underlying telemetry query doesn't change — it still uses `device_id` + `metric_name`. The sensor selector is a UX improvement that shows users meaningful labels and units instead of raw metric keys.
- If a device has no sensor records yet (auto-discovery hasn't created them), fall back to showing available metric names from the telemetry API as before.
- Add the `listDeviceSensors` import at the top of WidgetConfigDialog.tsx.

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```
