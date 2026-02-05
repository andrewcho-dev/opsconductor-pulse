# Task 004: Dashboard Widgets with Live Alert Stream

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Create only the files listed in "Files to Create/Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

The dashboard is currently a single monolithic component (`DashboardPage.tsx`) that fetches everything via TanStack Query. This task splits it into isolated widget components, adds a live alert stream that reads from the Zustand AlertStore (populated by WebSocket), and wraps each widget in an ErrorBoundary.

**Read first**:
- `frontend/src/features/dashboard/DashboardPage.tsx` — current monolithic dashboard
- `frontend/src/stores/alert-store.ts` — `useAlertStore` with `liveAlerts` and `hasWsData`
- `frontend/src/stores/ui-store.ts` — `useUIStore` with `wsStatus`
- `frontend/src/hooks/use-devices.ts` — `useDevices()` TanStack Query hook
- `frontend/src/hooks/use-alerts.ts` — `useAlerts()` TanStack Query hook
- `frontend/src/components/shared/` — StatusBadge, SeverityBadge, EmptyState, PageHeader

---

## Task

### 4.1 Create WidgetErrorBoundary

**File**: `frontend/src/components/shared/WidgetErrorBoundary.tsx` (NEW)

An error boundary that catches errors in individual widgets and shows a fallback UI instead of crashing the entire dashboard.

```tsx
import { Component, type ReactNode, type ErrorInfo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertTriangle } from "lucide-react";

interface Props {
  children: ReactNode;
  widgetName?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class WidgetErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(
      `Widget "${this.props.widgetName || "unknown"}" crashed:`,
      error,
      info.componentStack
    );
  }

  render() {
    if (this.state.hasError) {
      return (
        <Card className="border-destructive/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-destructive flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" />
              {this.props.widgetName || "Widget"} Error
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">
              This widget encountered an error and could not render.
            </p>
            <button
              onClick={() => this.setState({ hasError: false, error: null })}
              className="mt-2 text-xs text-primary hover:underline"
            >
              Try again
            </button>
          </CardContent>
        </Card>
      );
    }

    return this.props.children;
  }
}
```

### 4.2 Create StatCardsWidget

**File**: `frontend/src/features/dashboard/widgets/StatCardsWidget.tsx` (NEW)

Extracted from the current DashboardPage. Shows 4 stat cards. Uses TanStack Query for data (no WebSocket needed — device counts don't stream via WS).

```tsx
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useDevices } from "@/hooks/use-devices";
import { useAlertStore } from "@/stores/alert-store";
import { useAlerts } from "@/hooks/use-alerts";
import { Cpu, Wifi, AlertTriangle, Bell } from "lucide-react";
import { memo } from "react";

function StatCard({
  title,
  value,
  icon: Icon,
  loading,
  className,
}: {
  title: string;
  value: string | number;
  icon: React.ElementType;
  loading?: boolean;
  className?: string;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <Icon className={`h-4 w-4 ${className || "text-muted-foreground"}`} />
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-8 w-16" />
        ) : (
          <div className="text-3xl font-bold">{value}</div>
        )}
      </CardContent>
    </Card>
  );
}

function StatCardsWidgetInner() {
  const { data: deviceData, isLoading: devicesLoading } = useDevices(500, 0);

  // For alert count, prefer live WS data if available, fallback to REST
  const hasWsData = useAlertStore((s) => s.hasWsData);
  const liveAlerts = useAlertStore((s) => s.liveAlerts);
  const { data: alertData, isLoading: alertsLoading } = useAlerts("OPEN", 100, 0);

  const devices = deviceData?.devices || [];
  const totalDevices = devices.length;
  const onlineDevices = devices.filter((d) => d.status === "ONLINE").length;
  const staleDevices = devices.filter((d) => d.status === "STALE").length;

  // Use WS alert count if available, otherwise REST
  const openAlerts = hasWsData ? liveAlerts.length : (alertData?.alerts?.length || 0);
  const alertsReady = hasWsData || !alertsLoading;

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatCard
        title="Total Devices"
        value={totalDevices}
        icon={Cpu}
        loading={devicesLoading}
      />
      <StatCard
        title="Online"
        value={onlineDevices}
        icon={Wifi}
        loading={devicesLoading}
        className="text-green-400"
      />
      <StatCard
        title="Stale"
        value={staleDevices}
        icon={AlertTriangle}
        loading={devicesLoading}
        className="text-orange-400"
      />
      <StatCard
        title="Open Alerts"
        value={openAlerts}
        icon={Bell}
        loading={!alertsReady}
        className="text-red-400"
      />
    </div>
  );
}

export const StatCardsWidget = memo(StatCardsWidgetInner);
```

### 4.3 Create AlertStreamWidget

**File**: `frontend/src/features/dashboard/widgets/AlertStreamWidget.tsx` (NEW)

Shows a live stream of open alerts. When WebSocket data is available (`hasWsData === true`), it reads from the Zustand AlertStore. Otherwise falls back to TanStack Query.

The key difference from the old dashboard: alerts update in real-time without any polling delay.

```tsx
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { SeverityBadge } from "@/components/shared";
import { useAlertStore } from "@/stores/alert-store";
import { useUIStore } from "@/stores/ui-store";
import { useAlerts } from "@/hooks/use-alerts";
import { Bell } from "lucide-react";
import { Link } from "react-router-dom";
import { memo } from "react";

function AlertStreamWidgetInner() {
  // Live data from WebSocket (via Zustand store)
  const hasWsData = useAlertStore((s) => s.hasWsData);
  const liveAlerts = useAlertStore((s) => s.liveAlerts);
  const lastWsUpdate = useAlertStore((s) => s.lastWsUpdate);
  const wsStatus = useUIStore((s) => s.wsStatus);

  // Fallback: REST data via TanStack Query
  const { data: restData, isLoading: restLoading } = useAlerts("OPEN", 50, 0);

  // Prefer WS data if available
  const alerts = hasWsData ? liveAlerts : (restData?.alerts || []);
  const isLoading = !hasWsData && restLoading;

  // Format relative time for last update
  const lastUpdateText = lastWsUpdate
    ? `${Math.round((Date.now() - lastWsUpdate) / 1000)}s ago`
    : null;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div className="flex items-center gap-2">
          <CardTitle className="text-lg">Open Alerts</CardTitle>
          {wsStatus === "connected" && (
            <Badge
              variant="outline"
              className="text-[10px] text-green-400 border-green-700/50"
            >
              LIVE
            </Badge>
          )}
        </div>
        <div className="text-xs text-muted-foreground">
          {lastUpdateText && `Updated ${lastUpdateText}`}
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
        ) : alerts.length === 0 ? (
          <div className="flex flex-col items-center py-8 text-center">
            <Bell className="h-8 w-8 text-muted-foreground mb-2" />
            <p className="text-sm text-muted-foreground">No open alerts</p>
          </div>
        ) : (
          <div className="space-y-1">
            {alerts.slice(0, 20).map((a) => (
              <div
                key={a.alert_id}
                className="flex items-center gap-3 py-2 px-2 rounded-md hover:bg-accent/50 transition-colors text-sm"
              >
                <SeverityBadge severity={a.severity} className="shrink-0" />
                <Link
                  to={`/devices/${a.device_id}`}
                  className="font-mono text-xs text-primary hover:underline shrink-0"
                >
                  {a.device_id}
                </Link>
                <span className="truncate flex-1">{a.summary}</span>
                <span className="text-xs text-muted-foreground shrink-0 hidden md:inline">
                  {a.alert_type}
                </span>
              </div>
            ))}
            {alerts.length > 20 && (
              <div className="pt-2 text-center">
                <Link
                  to="/alerts"
                  className="text-xs text-primary hover:underline"
                >
                  View all {alerts.length} alerts
                </Link>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export const AlertStreamWidget = memo(AlertStreamWidgetInner);
```

### 4.4 Create DeviceTableWidget

**File**: `frontend/src/features/dashboard/widgets/DeviceTableWidget.tsx` (NEW)

Shows the top devices on the dashboard. Uses TanStack Query (device data doesn't stream via WS for the list view).

```tsx
import { Link } from "react-router-dom";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/shared";
import { useDevices } from "@/hooks/use-devices";
import { memo } from "react";

function DeviceTableWidgetInner() {
  const { data, isLoading } = useDevices(10, 0); // Show top 10 on dashboard
  const devices = data?.devices || [];
  const totalCount = data?.count || 0;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-lg">Devices</CardTitle>
        {totalCount > 10 && (
          <Link to="/devices" className="text-xs text-primary hover:underline">
            View all {totalCount}
          </Link>
        )}
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : devices.length === 0 ? (
          <p className="text-sm text-muted-foreground py-4 text-center">
            No devices found.
          </p>
        ) : (
          <div className="rounded-md border border-border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Device</TableHead>
                  <TableHead>Site</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Battery</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {devices.map((d) => (
                  <TableRow key={d.device_id}>
                    <TableCell>
                      <Link
                        to={`/devices/${d.device_id}`}
                        className="font-mono text-xs text-primary hover:underline"
                      >
                        {d.device_id}
                      </Link>
                    </TableCell>
                    <TableCell className="text-sm">{d.site_id}</TableCell>
                    <TableCell>
                      <StatusBadge status={d.status} />
                    </TableCell>
                    <TableCell className="text-right text-sm">
                      {d.state?.battery_pct != null
                        ? `${d.state.battery_pct}%`
                        : "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export const DeviceTableWidget = memo(DeviceTableWidgetInner);
```

### 4.5 Create widget index

**File**: `frontend/src/features/dashboard/widgets/index.ts` (NEW)

```typescript
export { StatCardsWidget } from "./StatCardsWidget";
export { AlertStreamWidget } from "./AlertStreamWidget";
export { DeviceTableWidget } from "./DeviceTableWidget";
```

### 4.6 Rewrite DashboardPage with widgets

**File**: `frontend/src/features/dashboard/DashboardPage.tsx` (REPLACE)

Replace the monolithic dashboard with a clean layout using the widget components. Each widget is wrapped in a WidgetErrorBoundary.

```tsx
import { PageHeader } from "@/components/shared";
import { WidgetErrorBoundary } from "@/components/shared/WidgetErrorBoundary";
import {
  StatCardsWidget,
  AlertStreamWidget,
  DeviceTableWidget,
} from "./widgets";

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description="Real-time overview of your IoT fleet"
      />

      <WidgetErrorBoundary widgetName="Stat Cards">
        <StatCardsWidget />
      </WidgetErrorBoundary>

      <div className="grid gap-6 lg:grid-cols-2">
        <WidgetErrorBoundary widgetName="Alert Stream">
          <AlertStreamWidget />
        </WidgetErrorBoundary>

        <WidgetErrorBoundary widgetName="Device Table">
          <DeviceTableWidget />
        </WidgetErrorBoundary>
      </div>
    </div>
  );
}
```

### 4.7 Export WidgetErrorBoundary

**File**: `frontend/src/components/shared/index.ts` (MODIFY)

Add the export (if not already added in 3.5):

```typescript
export { WidgetErrorBoundary } from "./WidgetErrorBoundary";
```

---

## Files to Create/Modify

| Action | Path | What |
|--------|------|------|
| CREATE | `frontend/src/components/shared/WidgetErrorBoundary.tsx` | Error boundary for widgets |
| CREATE | `frontend/src/features/dashboard/widgets/StatCardsWidget.tsx` | Stat cards (4 cards, TanStack Query + WS alert count) |
| CREATE | `frontend/src/features/dashboard/widgets/AlertStreamWidget.tsx` | Live alert stream (Zustand AlertStore + TanStack Query fallback) |
| CREATE | `frontend/src/features/dashboard/widgets/DeviceTableWidget.tsx` | Device summary table (TanStack Query) |
| CREATE | `frontend/src/features/dashboard/widgets/index.ts` | Widget exports |
| REPLACE | `frontend/src/features/dashboard/DashboardPage.tsx` | Compose widgets with error boundaries |
| MODIFY | `frontend/src/components/shared/index.ts` | Export WidgetErrorBoundary |

---

## Test

### Step 1: Verify build

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
```

### Step 2: Verify TypeScript

```bash
cd /home/opsconductor/simcloud/frontend && npx tsc --noEmit
```

### Step 3: Verify widget files exist

```bash
ls /home/opsconductor/simcloud/frontend/src/features/dashboard/widgets/
```

Should show: StatCardsWidget.tsx, AlertStreamWidget.tsx, DeviceTableWidget.tsx, index.ts

### Step 4: Verify implementation

Read the files and confirm:
- [ ] `DashboardPage` uses widget components (not inline code)
- [ ] Each widget wrapped in `WidgetErrorBoundary`
- [ ] `StatCardsWidget` uses `useDevices(500, 0)` for device counts
- [ ] `StatCardsWidget` uses WS alert count when `hasWsData` is true
- [ ] `AlertStreamWidget` reads from `useAlertStore` when WS data available
- [ ] `AlertStreamWidget` falls back to `useAlerts()` TanStack Query when no WS data
- [ ] `AlertStreamWidget` shows "LIVE" badge when WebSocket connected
- [ ] `AlertStreamWidget` shows "Updated Xs ago" timestamp
- [ ] `AlertStreamWidget` limits display to 20 alerts with "View all" link
- [ ] `DeviceTableWidget` shows top 10 devices with "View all" link
- [ ] `WidgetErrorBoundary` catches errors and shows fallback with "Try again" button
- [ ] All widgets use `memo()` for render optimization
- [ ] Dashboard layout: stat cards full width, alerts + devices in 2-column grid

### Step 5: Verify backend tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

All 395 tests must pass.

---

## Acceptance Criteria

- [ ] `npm run build` succeeds
- [ ] Dashboard split into 3 widget components + DashboardPage compositor
- [ ] StatCardsWidget: 4 stat cards with skeleton loading
- [ ] AlertStreamWidget: reads live data from Zustand, falls back to TanStack Query
- [ ] AlertStreamWidget: "LIVE" badge when WS connected
- [ ] AlertStreamWidget: shows last update time
- [ ] DeviceTableWidget: top 10 devices with link to full list
- [ ] Each widget wrapped in ErrorBoundary
- [ ] ErrorBoundary shows widget name and "Try again" button
- [ ] Widget crash doesn't take down the entire dashboard
- [ ] All widgets use `React.memo`
- [ ] Responsive layout (2-column on lg, stacked on mobile)
- [ ] All Python tests pass

---

## Commit

```
Split dashboard into live-updating widget components

StatCardsWidget, AlertStreamWidget, DeviceTableWidget as
isolated components. AlertStream reads from Zustand store
for real-time WebSocket data with REST fallback. Error
boundaries prevent widget crashes from breaking the page.

Phase 19 Task 4: Dashboard Widgets
```
