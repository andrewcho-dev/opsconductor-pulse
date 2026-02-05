# Task 004: Device Detail Page

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Create/modify only the files listed in "Files to Create/Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

Tasks 1-3 created chart libraries, wrapper components, and the data layer hook. This task builds the full Device Detail Page — the primary visualization surface in the app. Users navigate here from the device list by clicking a device ID.

The page replaces the Phase 18 stub with a full layout containing:
1. **Device info header** — device ID, site, status, last seen timestamps
2. **Current metrics gauges** — ECharts gauge per metric showing latest value
3. **Time-series charts** — uPlot chart per metric showing historical data
4. **Time range selector** — tabs for 1h, 6h, 24h, 7d
5. **Live indicator** — badge showing when WS telemetry is streaming
6. **Device alerts** — recent alerts for this specific device

**Read first**:
- `frontend/src/features/devices/DeviceDetailPage.tsx` — current stub (to be replaced)
- `frontend/src/hooks/use-device-telemetry.ts` — data hook from Task 3
- `frontend/src/hooks/use-device-alerts.ts` — device alerts hook from Task 3
- `frontend/src/hooks/use-devices.ts` — `useDevice(deviceId)` for device info
- `frontend/src/lib/charts/index.ts` — chart components and utilities
- `frontend/src/components/shared/WidgetErrorBoundary.tsx` — error boundary wrapper
- `frontend/src/components/shared/StatusBadge.tsx` — device status badge
- `frontend/src/components/shared/SeverityBadge.tsx` — alert severity badge

---

## Task

### 4.1 Create DeviceInfoCard component

**File**: `frontend/src/features/devices/DeviceInfoCard.tsx` (NEW)

A card showing device metadata and current state. This is the top section of the device detail page.

```tsx
import { Card, CardContent } from "@/components/ui/card";
import { StatusBadge } from "@/components/shared";
import { Skeleton } from "@/components/ui/skeleton";
import type { Device } from "@/services/api/types";
import { Cpu, MapPin, Clock } from "lucide-react";

interface DeviceInfoCardProps {
  device: Device | undefined;
  isLoading: boolean;
}

function formatTimestamp(ts: string | null): string {
  if (!ts) return "Never";
  try {
    return new Date(ts).toLocaleString();
  } catch {
    return ts;
  }
}

export function DeviceInfoCard({ device, isLoading }: DeviceInfoCardProps) {
  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="space-y-3">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-4 w-64" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!device) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-muted-foreground">Device not found.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <Cpu className="h-8 w-8 text-muted-foreground shrink-0" />
            <div>
              <h2 className="text-xl font-bold font-mono">{device.device_id}</h2>
              <div className="flex items-center gap-2 text-sm text-muted-foreground mt-1">
                <MapPin className="h-3.5 w-3.5" />
                <span>{device.site_id}</span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <StatusBadge status={device.status} />
          </div>
        </div>

        <div className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Clock className="h-3.5 w-3.5 shrink-0" />
            <span>Last seen: {formatTimestamp(device.last_seen_at)}</span>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground">
            <Clock className="h-3.5 w-3.5 shrink-0" />
            <span>Last heartbeat: {formatTimestamp(device.last_heartbeat_at)}</span>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground">
            <Clock className="h-3.5 w-3.5 shrink-0" />
            <span>Last telemetry: {formatTimestamp(device.last_telemetry_at)}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
```

### 4.2 Create MetricGaugesSection component

**File**: `frontend/src/features/devices/MetricGaugesSection.tsx` (NEW)

A responsive grid of gauge charts showing the latest value for each discovered metric.

```tsx
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MetricGauge } from "@/lib/charts";
import { getLatestValue, getMetricValues } from "@/lib/charts/transforms";
import type { TelemetryPoint } from "@/services/api/types";
import { memo } from "react";

interface MetricGaugesSectionProps {
  metrics: string[];
  points: TelemetryPoint[];
}

function MetricGaugesSectionInner({
  metrics,
  points,
}: MetricGaugesSectionProps) {
  if (metrics.length === 0) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-sm text-muted-foreground text-center py-4">
            No metric data available.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Current Metrics</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid gap-2 grid-cols-2 lg:grid-cols-4">
          {metrics.map((metricName) => (
            <MetricGauge
              key={metricName}
              metricName={metricName}
              value={getLatestValue(points, metricName)}
              allValues={getMetricValues(points, metricName)}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export const MetricGaugesSection = memo(MetricGaugesSectionInner);
```

### 4.3 Create TelemetryChartsSection component

**File**: `frontend/src/features/devices/TelemetryChartsSection.tsx` (NEW)

A section containing one uPlot time-series chart per metric, with a time range selector at the top.

```tsx
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { TimeSeriesChart, TIME_RANGES, type TimeRange } from "@/lib/charts";
import type { TelemetryPoint } from "@/services/api/types";
import { memo } from "react";

interface TelemetryChartsSectionProps {
  metrics: string[];
  points: TelemetryPoint[];
  isLoading: boolean;
  isLive: boolean;
  liveCount: number;
  timeRange: TimeRange;
  onTimeRangeChange: (range: TimeRange) => void;
}

function TelemetryChartsSectionInner({
  metrics,
  points,
  isLoading,
  isLive,
  liveCount,
  timeRange,
  onTimeRangeChange,
}: TelemetryChartsSectionProps) {
  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <CardTitle className="text-lg">Telemetry History</CardTitle>
          {isLive && (
            <Badge
              variant="outline"
              className="text-[10px] text-green-400 border-green-700/50"
            >
              LIVE ({liveCount})
            </Badge>
          )}
        </div>

        <Tabs
          value={timeRange}
          onValueChange={(v) => onTimeRangeChange(v as TimeRange)}
        >
          <TabsList>
            {TIME_RANGES.map((tr) => (
              <TabsTrigger key={tr.value} value={tr.value}>
                {tr.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </CardHeader>

      <CardContent className="space-y-6">
        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-[200px] w-full" />
            ))}
          </div>
        ) : metrics.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8">
            No telemetry data in the selected time range.
          </p>
        ) : (
          metrics.map((metricName, idx) => (
            <div key={metricName}>
              <TimeSeriesChart
                metricName={metricName}
                points={points}
                colorIndex={idx}
                height={200}
              />
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}

export const TelemetryChartsSection = memo(TelemetryChartsSectionInner);
```

### 4.4 Create DeviceAlertsSection component

**File**: `frontend/src/features/devices/DeviceAlertsSection.tsx` (NEW)

Shows recent alerts for this specific device.

```tsx
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { SeverityBadge } from "@/components/shared";
import { useDeviceAlerts } from "@/hooks/use-device-alerts";
import { Bell } from "lucide-react";
import { memo } from "react";

interface DeviceAlertsSectionProps {
  deviceId: string;
}

function formatTime(ts: string): string {
  try {
    return new Date(ts).toLocaleString();
  } catch {
    return ts;
  }
}

function DeviceAlertsSectionInner({ deviceId }: DeviceAlertsSectionProps) {
  const { data, isLoading } = useDeviceAlerts(deviceId, "OPEN", 50);
  const alerts = data?.alerts || [];

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-lg">Device Alerts</CardTitle>
        <Link
          to="/alerts"
          className="text-xs text-primary hover:underline"
        >
          View all alerts
        </Link>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
        ) : alerts.length === 0 ? (
          <div className="flex flex-col items-center py-6 text-center">
            <Bell className="h-6 w-6 text-muted-foreground mb-2" />
            <p className="text-sm text-muted-foreground">
              No open alerts for this device
            </p>
          </div>
        ) : (
          <div className="space-y-1">
            {alerts.map((a) => (
              <div
                key={a.alert_id}
                className="flex items-center gap-3 py-2 px-2 rounded-md hover:bg-accent/50 transition-colors text-sm"
              >
                <SeverityBadge severity={a.severity} className="shrink-0" />
                <span className="truncate flex-1">{a.summary}</span>
                <span className="text-xs text-muted-foreground shrink-0">
                  {a.alert_type}
                </span>
                <span className="text-xs text-muted-foreground shrink-0 hidden md:inline">
                  {formatTime(a.created_at)}
                </span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export const DeviceAlertsSection = memo(DeviceAlertsSectionInner);
```

### 4.5 Implement DeviceDetailPage

**File**: `frontend/src/features/devices/DeviceDetailPage.tsx` (REPLACE)

Replace the entire stub with the full implementation. This is the main page component that composes all sections.

```tsx
import { useParams, Link } from "react-router-dom";
import { useDevice } from "@/hooks/use-devices";
import { useDeviceTelemetry } from "@/hooks/use-device-telemetry";
import { WidgetErrorBoundary } from "@/components/shared/WidgetErrorBoundary";
import { DeviceInfoCard } from "./DeviceInfoCard";
import { MetricGaugesSection } from "./MetricGaugesSection";
import { TelemetryChartsSection } from "./TelemetryChartsSection";
import { DeviceAlertsSection } from "./DeviceAlertsSection";
import { ArrowLeft } from "lucide-react";

export default function DeviceDetailPage() {
  const { deviceId } = useParams<{ deviceId: string }>();

  // Device info from REST
  const { data: deviceData, isLoading: deviceLoading } = useDevice(deviceId || "");

  // Telemetry data (REST + WS fused)
  const {
    points,
    metrics,
    isLoading: telemetryLoading,
    isLive,
    liveCount,
    timeRange,
    setTimeRange,
  } = useDeviceTelemetry(deviceId || "");

  return (
    <div className="space-y-6">
      {/* Back navigation */}
      <Link
        to="/devices"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Devices
      </Link>

      {/* Device Info */}
      <WidgetErrorBoundary widgetName="Device Info">
        <DeviceInfoCard
          device={deviceData?.device}
          isLoading={deviceLoading}
        />
      </WidgetErrorBoundary>

      {/* Current Metric Gauges */}
      <WidgetErrorBoundary widgetName="Metric Gauges">
        <MetricGaugesSection
          metrics={metrics}
          points={points}
        />
      </WidgetErrorBoundary>

      {/* Telemetry Time-Series Charts */}
      <WidgetErrorBoundary widgetName="Telemetry Charts">
        <TelemetryChartsSection
          metrics={metrics}
          points={points}
          isLoading={telemetryLoading}
          isLive={isLive}
          liveCount={liveCount}
          timeRange={timeRange}
          onTimeRangeChange={setTimeRange}
        />
      </WidgetErrorBoundary>

      {/* Device Alerts */}
      {deviceId && (
        <WidgetErrorBoundary widgetName="Device Alerts">
          <DeviceAlertsSection deviceId={deviceId} />
        </WidgetErrorBoundary>
      )}
    </div>
  );
}
```

---

## Files to Create/Modify

| Action | Path | What |
|--------|------|------|
| CREATE | `frontend/src/features/devices/DeviceInfoCard.tsx` | Device metadata card |
| CREATE | `frontend/src/features/devices/MetricGaugesSection.tsx` | Gauge grid for current metrics |
| CREATE | `frontend/src/features/devices/TelemetryChartsSection.tsx` | Time-series charts with range selector |
| CREATE | `frontend/src/features/devices/DeviceAlertsSection.tsx` | Device-specific alert list |
| MODIFY | `frontend/src/features/devices/DeviceDetailPage.tsx` | Full page implementation (replace stub) |

---

## Test

### Step 1: Verify build

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
```

Must succeed with zero errors.

### Step 2: Verify TypeScript

```bash
cd /home/opsconductor/simcloud/frontend && npx tsc --noEmit
```

Must succeed with zero type errors.

### Step 3: Verify files exist

```bash
ls /home/opsconductor/simcloud/frontend/src/features/devices/
```

Should show: DeviceDetailPage.tsx, DeviceInfoCard.tsx, DeviceListPage.tsx, MetricGaugesSection.tsx, TelemetryChartsSection.tsx, DeviceAlertsSection.tsx

### Step 4: Verify implementation

Read the files and confirm:
- [ ] `DeviceDetailPage` composes all sections with ErrorBoundary wrappers
- [ ] Back navigation link to `/devices` at the top
- [ ] `DeviceInfoCard` shows device_id, site_id, status, timestamps
- [ ] `DeviceInfoCard` has loading skeleton state
- [ ] `MetricGaugesSection` renders one gauge per discovered metric
- [ ] Gauges use `getLatestValue()` for current reading
- [ ] `TelemetryChartsSection` renders one uPlot chart per metric
- [ ] Time range selector using shadcn Tabs (1h, 6h, 24h, 7d)
- [ ] LIVE badge shown when WebSocket data is streaming
- [ ] Live count displayed next to LIVE badge
- [ ] `DeviceAlertsSection` shows open alerts filtered to this device
- [ ] All sections wrapped in React.memo
- [ ] `useDeviceTelemetry` called with deviceId from URL params
- [ ] `useDevice` called for device info

### Step 5: Verify backend tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

All 395 tests must pass.

---

## Acceptance Criteria

- [ ] Device detail page replaces Phase 18 stub
- [ ] Device info card with status, site, timestamps
- [ ] Dynamic metric gauges (ECharts) — one per discovered metric
- [ ] Known metrics (battery, temp, rssi, snr) have proper gauge ranges/zones
- [ ] Unknown metrics auto-scale from data
- [ ] Time-series charts (uPlot) — one per metric
- [ ] Time range selector (1h, 6h, 24h, 7d) triggers REST refetch
- [ ] LIVE badge when WebSocket telemetry is streaming
- [ ] Device-specific alerts section
- [ ] ErrorBoundary wrapping each section
- [ ] Back navigation to device list
- [ ] Responsive layout (2-col gauges on mobile, 4-col on desktop)
- [ ] `npm run build` succeeds
- [ ] All Python tests pass

---

## Commit

```
Implement device detail page with gauge and time-series charts

ECharts gauges show current metric values with color zones.
uPlot charts display historical telemetry with time-range
selector (1h/6h/24h/7d). Live WebSocket telemetry streaming
with LIVE badge. Device alerts section. ErrorBoundary isolation.

Phase 20 Task 4: Device Detail Page
```
