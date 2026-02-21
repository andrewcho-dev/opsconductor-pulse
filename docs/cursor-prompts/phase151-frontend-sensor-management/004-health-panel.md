# Task 004 — DeviceHealthPanel Component

## File

Create `frontend/src/features/devices/DeviceHealthPanel.tsx`

Then add to `DeviceDetailPage.tsx`.

## Component Design

A panel showing platform-collected device diagnostics: signal strength, battery, CPU, memory, uptime, data usage, and GPS. Combines a "latest snapshot" summary with time-series charts.

## Layout

```
┌───────────────────────────────────────────────────────────────┐
│  Device Health                           [1h] [6h] [24h] [7d]│
│                                                               │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐     │
│  │Signal  │ │Battery │ │CPU Temp│ │Memory  │ │Uptime  │     │
│  │ 78%    │ │ N/A    │ │ 42.3°C │ │ 34%    │ │ 30d    │     │
│  │ -67dBm │ │ (Line) │ │        │ │        │ │ 2 boots│     │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘     │
│                                                               │
│  Signal Quality                                               │
│  ┌───────────────────────────────────────────────────────┐   │
│  │  📈 Line chart: signal_quality over time               │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                               │
│  Network: LTE-M  │  Cell: 12345  │  Last attach: Feb 15      │
│  TX: 512 KB      │  RX: 1.0 MB   │  GPS: 41.878, -87.630    │
└───────────────────────────────────────────────────────────────┘
```

## Implementation

### Data Fetching

```tsx
const [range, setRange] = useState<"1h" | "6h" | "24h" | "7d" | "30d">("24h");

const { data, isLoading } = useQuery({
  queryKey: ["device-health", deviceId, range],
  queryFn: () => getDeviceHealth(deviceId, range, 200),
  enabled: !!deviceId,
  refetchInterval: 30_000,
});

const latest = data?.latest;
const points = data?.data_points ?? [];
```

### Top Row — Stat Cards

A horizontal row of 5 mini stat cards. Each shows:
- Icon (small, muted)
- Label (text-xs muted)
- Value (text-lg font-semibold)
- Sub-value (text-xs muted)

**Signal card:**
- Value: `signal_quality` + "%" (color: green ≥60, orange ≥30, red <30)
- Sub: `rssi` dBm

**Battery card:**
- If `battery_pct` is not null: show percentage + voltage
- If null and `power_source` is "line" or "poe": show "Line Powered" or "PoE"

**CPU Temp card:**
- Value: `cpu_temp_c` °C (color: green <60, orange <80, red ≥80)

**Memory card:**
- Value: `memory_used_pct` %
- Sub: storage used if available

**Uptime card:**
- Value: humanize `uptime_seconds` (e.g., "30d", "12h 45m")
- Sub: `reboot_count` reboots

### Signal Quality Chart

Use ECharts (via `EChartWrapper` already in the project) to plot `signal_quality` over time.

```tsx
const chartOption: EChartsOption = {
  tooltip: { trigger: "axis" },
  xAxis: {
    type: "time",
    data: points.map(p => p.time),
  },
  yAxis: {
    type: "value",
    min: 0,
    max: 100,
    name: "Signal %",
  },
  series: [{
    type: "line",
    data: points.map(p => [p.time, p.signal_quality]),
    smooth: true,
    areaStyle: { opacity: 0.15 },
    lineStyle: { width: 2 },
  }],
  grid: { left: 40, right: 20, top: 10, bottom: 30 },
};
```

Height: 150px. Only show if there are 2+ data points.

### Bottom Row — Network Details

A compact row of metadata:
- Network type (e.g., "LTE-M", "4G")
- Cell ID
- Last network attach time
- TX/RX bytes (humanized: KB, MB, GB)
- GPS coordinates (if gps_fix is true)

### Time Range Selector

Row of small buttons (1h, 6h, 24h, 7d, 30d). Use `Button variant="ghost"` for unselected, `variant="secondary"` for selected.

### Loading State

Show `Skeleton` components matching the layout while data loads.

### Empty State

If no health data exists: "No device health data available. Health telemetry is collected automatically when the device connects."

## Add to DeviceDetailPage.tsx

Place after `DeviceConnectionPanel` and before `DeviceUptimePanel` (or replace DeviceUptimePanel if it's redundant — the health panel now covers uptime):

```tsx
import { DeviceHealthPanel } from "./DeviceHealthPanel";

{deviceId && <DeviceHealthPanel deviceId={deviceId} />}
```

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```
