# Task 004 — Telemetry Charts Use Sensor Labels and Units

## Context

The telemetry charts on the device detail page (`TelemetryChartsSection.tsx`) currently show raw metric names (e.g., "hvac_supply_temp") on axis labels and legends. With sensor records now available, charts should show the sensor's human-readable label and unit.

## Files to Modify

### 1. `frontend/src/features/devices/TelemetryChartsSection.tsx`

**Current behavior:** Chart metric selector shows raw metric names from telemetry data.

**New behavior:**
1. Fetch sensors for the device: `listDeviceSensors(deviceId)`
2. Build a map: `metric_name → { label, unit, sensor_type }`
3. Use sensor labels in:
   - Metric selector dropdown options
   - Chart Y-axis label (include unit)
   - Chart legend entries
   - Tooltip formatters

**Implementation:**

```tsx
import { listDeviceSensors } from "@/services/api/sensors";

// Add sensor query alongside existing telemetry query:
const { data: sensorsData } = useQuery({
  queryKey: ["device-sensors", deviceId],
  queryFn: () => listDeviceSensors(deviceId),
  enabled: !!deviceId,
});

// Build lookup map:
const sensorMap = useMemo(() => {
  const map = new Map<string, { label: string; unit: string; type: string }>();
  for (const s of sensorsData?.sensors ?? []) {
    map.set(s.metric_name, {
      label: s.label || s.metric_name,
      unit: s.unit || "",
      type: s.sensor_type,
    });
  }
  return map;
}, [sensorsData]);

// Use in metric selector:
// Instead of: <SelectItem value={m}>{m}</SelectItem>
// Use:        <SelectItem value={m}>{sensorMap.get(m)?.label ?? m}</SelectItem>

// Use in chart Y-axis:
// yAxis: { name: sensorMap.get(selectedMetric)?.unit ?? "" }

// Use in tooltip:
// formatter: (params) => {
//   const info = sensorMap.get(selectedMetric);
//   return `${info?.label ?? selectedMetric}: ${params.value} ${info?.unit ?? ""}`;
// }
```

### 2. Also update `MetricGaugesSection.tsx` (if it exists)

If the device detail page has metric gauge cards, apply the same pattern — show sensor labels and units instead of raw metric names.

## Notes

- This is purely a UI label improvement. No API changes needed.
- If sensors haven't been discovered yet (no sensor records), fall back gracefully to raw metric names.
- The `sensorMap` lookup is a lightweight useMemo — no extra API calls per metric.

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```
