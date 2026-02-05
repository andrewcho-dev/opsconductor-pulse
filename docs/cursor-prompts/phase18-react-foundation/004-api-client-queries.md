# Task 004: TanStack Query + API Services + First Real Pages

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Create only the files listed in "Files to Create/Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

Tasks 1-3 created the project scaffold, auth, and app shell. The pages are currently stubs. This task wires up real data by creating API service modules, TanStack Query hooks, and implementing three real pages: Dashboard (stat cards), Device List (table), and Alert List (table with filters).

**Read first**:
- `frontend/src/services/api/client.ts` — the `apiGet` function with auth header injection
- `frontend/src/components/shared/` — StatusBadge, SeverityBadge, EmptyState, PageHeader

**API v2 response shapes** (from existing backend, no changes):

```
GET /api/v2/devices?limit=100&offset=0
→ { tenant_id, devices: [...], count, limit, offset }

Each device: { device_id, tenant_id, site_id, status, last_seen_at,
              last_heartbeat_at, last_telemetry_at, state: { battery_pct, temp_c, ... } }

GET /api/v2/alerts?status=OPEN&limit=100&offset=0
→ { tenant_id, alerts: [...], count, status, limit, offset }

Each alert: { alert_id, tenant_id, device_id, alert_type, severity,
             summary, status, created_at, fingerprint, details, closed_at }
```

---

## Task

### 4.1 Install TanStack Query

```bash
cd /home/opsconductor/simcloud/frontend
npm install @tanstack/react-query
```

### 4.2 Create API type definitions

**File**: `frontend/src/services/api/types.ts` (NEW)

```typescript
// Device types
export interface DeviceState {
  battery_pct?: number;
  temp_c?: number;
  rssi_dbm?: number;
  snr_db?: number;
  [key: string]: number | boolean | string | undefined;
}

export interface Device {
  device_id: string;
  tenant_id: string;
  site_id: string;
  status: string;
  last_seen_at: string | null;
  last_heartbeat_at: string | null;
  last_telemetry_at: string | null;
  state: DeviceState | null;
}

export interface DeviceListResponse {
  tenant_id: string;
  devices: Device[];
  count: number;
  limit: number;
  offset: number;
}

export interface DeviceDetailResponse {
  tenant_id: string;
  device: Device;
}

// Alert types
export interface Alert {
  alert_id: number;
  tenant_id: string;
  device_id: string;
  alert_type: string;
  severity: number;
  summary: string;
  status: string;
  created_at: string;
  fingerprint: string;
  details: Record<string, unknown> | null;
  closed_at: string | null;
}

export interface AlertListResponse {
  tenant_id: string;
  alerts: Alert[];
  count: number;
  status: string;
  limit: number;
  offset: number;
}

export interface AlertDetailResponse {
  tenant_id: string;
  alert: Alert;
}

// Alert rule types
export interface AlertRule {
  rule_id: number;
  tenant_id: string;
  name: string;
  metric_name: string;
  operator: string;
  threshold: number;
  severity: number;
  enabled: boolean;
  description: string | null;
  site_ids: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface AlertRuleListResponse {
  tenant_id: string;
  rules: AlertRule[];
  count: number;
}

// Telemetry types
export interface TelemetryPoint {
  timestamp: string;
  metrics: Record<string, number | boolean>;
}

export interface TelemetryResponse {
  tenant_id: string;
  device_id: string;
  telemetry: TelemetryPoint[];
  count: number;
}
```

### 4.3 Create API service modules

**File**: `frontend/src/services/api/devices.ts` (NEW)

```typescript
import { apiGet } from "./client";
import type { DeviceListResponse, DeviceDetailResponse } from "./types";

export async function fetchDevices(
  limit = 100,
  offset = 0
): Promise<DeviceListResponse> {
  return apiGet(`/api/v2/devices?limit=${limit}&offset=${offset}`);
}

export async function fetchDevice(
  deviceId: string
): Promise<DeviceDetailResponse> {
  return apiGet(`/api/v2/devices/${encodeURIComponent(deviceId)}`);
}
```

**File**: `frontend/src/services/api/alerts.ts` (NEW)

```typescript
import { apiGet } from "./client";
import type { AlertListResponse, AlertDetailResponse } from "./types";

export async function fetchAlerts(
  status = "OPEN",
  limit = 100,
  offset = 0,
  alertType?: string
): Promise<AlertListResponse> {
  let url = `/api/v2/alerts?status=${status}&limit=${limit}&offset=${offset}`;
  if (alertType) url += `&alert_type=${encodeURIComponent(alertType)}`;
  return apiGet(url);
}

export async function fetchAlert(
  alertId: number
): Promise<AlertDetailResponse> {
  return apiGet(`/api/v2/alerts/${alertId}`);
}
```

**File**: `frontend/src/services/api/telemetry.ts` (NEW)

```typescript
import { apiGet } from "./client";
import type { TelemetryResponse } from "./types";

export async function fetchTelemetry(
  deviceId: string,
  start?: string,
  end?: string,
  limit = 120
): Promise<TelemetryResponse> {
  let url = `/api/v2/devices/${encodeURIComponent(deviceId)}/telemetry?limit=${limit}`;
  if (start) url += `&start=${encodeURIComponent(start)}`;
  if (end) url += `&end=${encodeURIComponent(end)}`;
  return apiGet(url);
}

export async function fetchLatestTelemetry(
  deviceId: string,
  count = 1
): Promise<TelemetryResponse> {
  return apiGet(
    `/api/v2/devices/${encodeURIComponent(deviceId)}/telemetry/latest?count=${count}`
  );
}
```

**File**: `frontend/src/services/api/index.ts` (NEW)

```typescript
export * from "./types";
export * from "./client";
export * from "./devices";
export * from "./alerts";
export * from "./telemetry";
```

### 4.4 Create QueryClient provider

**File**: `frontend/src/app/providers.tsx` (NEW)

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/services/auth/AuthProvider";
import type { ReactNode } from "react";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,       // 30 seconds — data is "fresh" for this long
      refetchInterval: 60_000, // Auto-refetch every 60 seconds
      retry: 1,
      refetchOnWindowFocus: true,
    },
  },
});

interface ProvidersProps {
  children: ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  return (
    <AuthProvider>
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    </AuthProvider>
  );
}
```

### 4.5 Create data hooks

**File**: `frontend/src/hooks/use-devices.ts` (NEW)

```typescript
import { useQuery } from "@tanstack/react-query";
import { fetchDevices, fetchDevice } from "@/services/api/devices";

export function useDevices(limit = 100, offset = 0) {
  return useQuery({
    queryKey: ["devices", limit, offset],
    queryFn: () => fetchDevices(limit, offset),
  });
}

export function useDevice(deviceId: string) {
  return useQuery({
    queryKey: ["device", deviceId],
    queryFn: () => fetchDevice(deviceId),
    enabled: !!deviceId,
  });
}
```

**File**: `frontend/src/hooks/use-alerts.ts` (NEW)

```typescript
import { useQuery } from "@tanstack/react-query";
import { fetchAlerts } from "@/services/api/alerts";

export function useAlerts(
  status = "OPEN",
  limit = 100,
  offset = 0,
  alertType?: string
) {
  return useQuery({
    queryKey: ["alerts", status, limit, offset, alertType],
    queryFn: () => fetchAlerts(status, limit, offset, alertType),
  });
}
```

**File**: `frontend/src/hooks/use-telemetry.ts` (NEW)

```typescript
import { useQuery } from "@tanstack/react-query";
import { fetchTelemetry, fetchLatestTelemetry } from "@/services/api/telemetry";

export function useTelemetry(
  deviceId: string,
  start?: string,
  end?: string,
  limit = 120
) {
  return useQuery({
    queryKey: ["telemetry", deviceId, start, end, limit],
    queryFn: () => fetchTelemetry(deviceId, start, end, limit),
    enabled: !!deviceId,
  });
}

export function useLatestTelemetry(deviceId: string, count = 1) {
  return useQuery({
    queryKey: ["telemetry-latest", deviceId, count],
    queryFn: () => fetchLatestTelemetry(deviceId, count),
    enabled: !!deviceId,
    refetchInterval: 10_000, // Refresh every 10 seconds for latest
  });
}
```

### 4.6 Build DashboardPage with stat cards

**File**: `frontend/src/features/dashboard/DashboardPage.tsx` (REPLACE)

Replace the stub with a real dashboard showing stat cards with device counts and a recent alerts summary.

```tsx
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/shared";
import { useDevices } from "@/hooks/use-devices";
import { useAlerts } from "@/hooks/use-alerts";
import { Skeleton } from "@/components/ui/skeleton";
import { Cpu, Wifi, AlertTriangle, Bell } from "lucide-react";

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

export default function DashboardPage() {
  const { data: deviceData, isLoading: devicesLoading } = useDevices(500, 0);
  const { data: alertData, isLoading: alertsLoading } = useAlerts("OPEN", 100, 0);

  const devices = deviceData?.devices || [];
  const alerts = alertData?.alerts || [];

  const totalDevices = devices.length;
  const onlineDevices = devices.filter((d) => d.status === "ONLINE").length;
  const staleDevices = devices.filter((d) => d.status === "STALE").length;
  const openAlerts = alerts.length;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description="Real-time overview of your IoT fleet"
      />

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
          loading={alertsLoading}
          className="text-red-400"
        />
      </div>

      {/* Recent alerts summary */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Recent Alerts</CardTitle>
        </CardHeader>
        <CardContent>
          {alertsLoading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-6 w-full" />
              ))}
            </div>
          ) : alerts.length === 0 ? (
            <p className="text-sm text-muted-foreground">No open alerts.</p>
          ) : (
            <div className="space-y-2">
              {alerts.slice(0, 5).map((a) => (
                <div
                  key={a.alert_id}
                  className="flex items-center justify-between text-sm border-b border-border pb-2 last:border-0"
                >
                  <div className="flex items-center gap-3">
                    <span
                      className={`inline-block w-2 h-2 rounded-full ${
                        a.severity >= 5
                          ? "bg-red-500"
                          : a.severity >= 3
                          ? "bg-orange-500"
                          : "bg-blue-500"
                      }`}
                    />
                    <span className="font-mono text-xs text-muted-foreground">
                      {a.device_id}
                    </span>
                    <span>{a.summary}</span>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {a.alert_type}
                  </span>
                </div>
              ))}
              {alerts.length > 5 && (
                <p className="text-xs text-muted-foreground pt-1">
                  + {alerts.length - 5} more alerts
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
```

### 4.7 Build DeviceListPage with table

**File**: `frontend/src/features/devices/DeviceListPage.tsx` (REPLACE)

```tsx
import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader, StatusBadge, EmptyState } from "@/components/shared";
import { useDevices } from "@/hooks/use-devices";
import { Cpu } from "lucide-react";

export default function DeviceListPage() {
  const [offset, setOffset] = useState(0);
  const limit = 50;
  const { data, isLoading, error } = useDevices(limit, offset);

  const devices = data?.devices || [];
  const totalCount = data?.count || 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Devices"
        description={
          isLoading ? "Loading..." : `${totalCount} devices in your fleet`
        }
      />

      {error ? (
        <div className="text-destructive">
          Failed to load devices: {(error as Error).message}
        </div>
      ) : isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : devices.length === 0 ? (
        <EmptyState
          title="No devices found"
          description="Devices will appear here once they connect and send data."
          icon={<Cpu className="h-12 w-12" />}
        />
      ) : (
        <>
          <div className="rounded-md border border-border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Device ID</TableHead>
                  <TableHead>Site</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Last Seen</TableHead>
                  <TableHead className="text-right">Battery</TableHead>
                  <TableHead className="text-right">Metrics</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {devices.map((d) => (
                  <TableRow key={d.device_id}>
                    <TableCell>
                      <Link
                        to={`/app/devices/${d.device_id}`}
                        className="font-mono text-sm text-primary hover:underline"
                      >
                        {d.device_id}
                      </Link>
                    </TableCell>
                    <TableCell className="text-sm">{d.site_id}</TableCell>
                    <TableCell>
                      <StatusBadge status={d.status} />
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {d.last_seen_at || "—"}
                    </TableCell>
                    <TableCell className="text-right text-sm">
                      {d.state?.battery_pct != null
                        ? `${d.state.battery_pct}%`
                        : "—"}
                    </TableCell>
                    <TableCell className="text-right text-sm text-muted-foreground">
                      {d.state ? Object.keys(d.state).length : 0}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          {totalCount > limit && (
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">
                Showing {offset + 1}–{Math.min(offset + limit, totalCount)} of{" "}
                {totalCount}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setOffset(Math.max(0, offset - limit))}
                  disabled={offset === 0}
                  className="px-3 py-1 rounded border border-border hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                <button
                  onClick={() => setOffset(offset + limit)}
                  disabled={offset + limit >= totalCount}
                  className="px-3 py-1 rounded border border-border hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
```

### 4.8 Build AlertListPage with status filter

**File**: `frontend/src/features/alerts/AlertListPage.tsx` (REPLACE)

```tsx
import { useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader, SeverityBadge, EmptyState } from "@/components/shared";
import { Badge } from "@/components/ui/badge";
import { useAlerts } from "@/hooks/use-alerts";
import { Bell } from "lucide-react";

const STATUS_OPTIONS = ["OPEN", "CLOSED", "ALL"] as const;

export default function AlertListPage() {
  const [status, setStatus] = useState<string>("OPEN");
  const [offset, setOffset] = useState(0);
  const limit = 50;

  // The API v2 uses "OPEN" and "CLOSED". For "ALL", we pass "OPEN" and show both.
  // Actually, check if the API supports other values — if not, just filter OPEN/CLOSED.
  const queryStatus = status === "ALL" ? "OPEN" : status;
  const { data, isLoading, error } = useAlerts(queryStatus, limit, offset);

  const alerts = data?.alerts || [];
  const totalCount = data?.count || 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Alerts"
        description={
          isLoading
            ? "Loading..."
            : `${totalCount} ${status.toLowerCase()} alerts`
        }
      />

      {/* Status filter */}
      <div className="flex gap-2">
        {STATUS_OPTIONS.map((s) => (
          <button
            key={s}
            onClick={() => {
              setStatus(s);
              setOffset(0);
            }}
            className={`px-3 py-1.5 text-sm rounded-md border transition-colors ${
              status === s
                ? "bg-primary text-primary-foreground border-primary"
                : "border-border text-muted-foreground hover:bg-accent"
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {error ? (
        <div className="text-destructive">
          Failed to load alerts: {(error as Error).message}
        </div>
      ) : isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : alerts.length === 0 ? (
        <EmptyState
          title={`No ${status.toLowerCase()} alerts`}
          description="Alerts appear when devices trigger threshold rules or miss heartbeats."
          icon={<Bell className="h-12 w-12" />}
        />
      ) : (
        <>
          <div className="rounded-md border border-border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Time</TableHead>
                  <TableHead>Device</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Severity</TableHead>
                  <TableHead>Summary</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {alerts.map((a) => (
                  <TableRow key={a.alert_id}>
                    <TableCell className="text-sm text-muted-foreground whitespace-nowrap">
                      {a.created_at}
                    </TableCell>
                    <TableCell className="font-mono text-sm">
                      {a.device_id}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-xs">
                        {a.alert_type}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <SeverityBadge severity={a.severity} />
                    </TableCell>
                    <TableCell className="text-sm max-w-md truncate">
                      {a.summary}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className={
                          a.status === "OPEN"
                            ? "text-orange-400 border-orange-700"
                            : "text-green-400 border-green-700"
                        }
                      >
                        {a.status}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          {totalCount > limit && (
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">
                Showing {offset + 1}–{Math.min(offset + limit, totalCount)} of{" "}
                {totalCount}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setOffset(Math.max(0, offset - limit))}
                  disabled={offset === 0}
                  className="px-3 py-1 rounded border border-border hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                <button
                  onClick={() => setOffset(offset + limit)}
                  disabled={offset + limit >= totalCount}
                  className="px-3 py-1 rounded border border-border hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
```

### 4.9 Update App.tsx with Providers

**File**: `frontend/src/App.tsx` (MODIFY)

Replace to use the new `Providers` wrapper (which includes both AuthProvider and QueryClientProvider):

```tsx
import { RouterProvider } from "react-router-dom";
import { Providers } from "@/app/providers";
import { router } from "@/app/router";

function App() {
  return (
    <Providers>
      <RouterProvider router={router} />
    </Providers>
  );
}

export default App;
```

**Note**: If `RouterProvider` inside `Providers` causes issues (RouterProvider renders its own tree), restructure so that `QueryClientProvider` wraps `RouterProvider` but `AuthProvider` wraps the route tree via the `AppShell` component or a route-level wrapper. The key requirement is:
1. `QueryClientProvider` must be an ancestor of any component using `useQuery`
2. `AuthProvider` must be an ancestor of any component using `useAuth`
3. Both must be ancestors of the page components

A working alternative structure:

```tsx
import { RouterProvider } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/services/auth/AuthProvider";
import { router } from "@/app/router";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchInterval: 60_000,
      retry: 1,
      refetchOnWindowFocus: true,
    },
  },
});

function App() {
  return (
    <AuthProvider>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </AuthProvider>
  );
}

export default App;
```

Choose whichever pattern compiles and works.

---

## Files to Create/Modify

| Action | Path | What |
|--------|------|------|
| CREATE | `frontend/src/services/api/types.ts` | API type definitions |
| CREATE | `frontend/src/services/api/devices.ts` | Device API functions |
| CREATE | `frontend/src/services/api/alerts.ts` | Alert API functions |
| CREATE | `frontend/src/services/api/telemetry.ts` | Telemetry API functions |
| CREATE | `frontend/src/services/api/index.ts` | API module exports |
| CREATE | `frontend/src/app/providers.tsx` | QueryClient + provider wrapper |
| CREATE | `frontend/src/hooks/use-devices.ts` | Device data hooks |
| CREATE | `frontend/src/hooks/use-alerts.ts` | Alert data hooks |
| CREATE | `frontend/src/hooks/use-telemetry.ts` | Telemetry data hooks |
| REPLACE | `frontend/src/features/dashboard/DashboardPage.tsx` | Dashboard with stat cards + recent alerts |
| REPLACE | `frontend/src/features/devices/DeviceListPage.tsx` | Device table with pagination |
| REPLACE | `frontend/src/features/alerts/AlertListPage.tsx` | Alert table with status filter |
| MODIFY | `frontend/src/App.tsx` | Add QueryClientProvider |

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

### Step 3: Verify all service files exist

```bash
ls /home/opsconductor/simcloud/frontend/src/services/api/
ls /home/opsconductor/simcloud/frontend/src/hooks/
```

API directory should have: client.ts, types.ts, devices.ts, alerts.ts, telemetry.ts, index.ts
Hooks directory should have: use-devices.ts, use-alerts.ts, use-telemetry.ts

### Step 4: Verify backend tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

All 395 tests must pass.

---

## Acceptance Criteria

- [ ] `npm run build` succeeds
- [ ] `@tanstack/react-query` installed
- [ ] API type definitions cover Device, Alert, AlertRule, Telemetry
- [ ] API service modules for devices, alerts, telemetry
- [ ] Custom hooks: `useDevices`, `useDevice`, `useAlerts`, `useTelemetry`, `useLatestTelemetry`
- [ ] Dashboard page shows 4 stat cards (Total, Online, Stale, Open Alerts)
- [ ] Dashboard shows 5 most recent alerts with severity dots
- [ ] Dashboard uses skeleton loaders during fetch
- [ ] Device list page shows table with 6 columns (ID, Site, Status, Last Seen, Battery, Metrics)
- [ ] Device list has pagination (Previous/Next)
- [ ] Device IDs link to `/app/devices/{id}`
- [ ] Alert list page shows table with 6 columns (Time, Device, Type, Severity, Summary, Status)
- [ ] Alert list has status filter buttons (OPEN, CLOSED, ALL)
- [ ] Alert list has pagination
- [ ] Empty states shown when no data
- [ ] Error states shown on API failure
- [ ] `QueryClientProvider` wraps the app
- [ ] Default staleTime: 30s, refetchInterval: 60s
- [ ] All Python tests pass

---

## Commit

```
Add TanStack Query API layer and first real pages

API service modules for devices, alerts, telemetry with typed
responses. Dashboard with stat cards and recent alerts. Device
list with pagination. Alert list with status filter. TanStack
Query for data fetching with 30s stale time.

Phase 18 Task 4: API Client and Queries
```
