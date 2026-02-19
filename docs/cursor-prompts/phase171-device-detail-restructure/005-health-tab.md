# Task 5: Health Tab

## Create component in `frontend/src/features/devices/` (e.g., `DeviceHealthTab.tsx`)

Consolidates DeviceHealthPanel + DeviceUptimePanel into a single Health tab.

### Component Structure

```
HealthTab
├── Time range selector (1h, 6h, 24h, 7d, 30d) — shared across all charts
├── Health metrics cards row (latest values)
│   ├── Battery Level (% gauge or large number)
│   ├── Signal Strength (dBm with color coding)
│   ├── CPU Temperature (°C)
│   └── Memory Usage (%)
├── Health charts (from device_health_telemetry hypertable)
│   ├── Battery chart (line)
│   ├── Signal strength chart (line)
│   ├── CPU temp chart (line)
│   └── Memory usage chart (line)
└── Uptime section
    ├── Uptime bar visualization (reuse UptimeBar or UptimeSummaryWidget)
    ├── Uptime percentage for selected range
    └── Connection events timeline
```

### Data Fetching

Reuse the existing health data fetching from `sensors.ts`:

```typescript
const [range, setRange] = useState<"1h" | "6h" | "24h" | "7d" | "30d">("24h");

const { data: healthData } = useQuery({
  queryKey: ["device-health", deviceId, range],
  queryFn: () => getDeviceHealth(deviceId, range),
});

const { data: latestHealth } = useQuery({
  queryKey: ["device-health-latest", deviceId],
  queryFn: () => getDeviceHealthLatest(deviceId),
});

const { data: uptimeData } = useQuery({
  queryKey: ["device-uptime", deviceId, range],
  queryFn: () => getDeviceUptime(deviceId, range),
});
```

### Chart Library

Use the same charting library already in the project (Echarts or Recharts — check which is used by `DeviceHealthPanel` and `TelemetryChartsSection`). Reuse or extract chart components from the existing panels.

### Signal Strength Color Coding

```typescript
function signalColor(rssi: number): string {
  if (rssi >= -50) return "text-green-500";   // Excellent
  if (rssi >= -70) return "text-yellow-500";  // Good
  if (rssi >= -85) return "text-orange-500";  // Fair
  return "text-red-500";                       // Poor
}
```

### Empty State

If no health data is available (device hasn't reported health telemetry):
```
No health data available for this device.
Health telemetry (battery, signal, CPU) is reported automatically by supported devices.
```

## Verification

1. Health tab shows latest metric values
2. Charts render with data from selected time range
3. Time range selector updates all charts
4. Uptime bar/percentage displays correctly
5. Empty state shows when no data
