# Phase 29.7: System Dashboard UI

## Task

Create the Operator System Dashboard page with service health grid, throughput metrics, capacity gauges, and error feed.

---

## Create API Client

**File:** `frontend/src/services/api/system.ts`

```typescript
import { apiClient } from "./client";

export interface ComponentHealth {
  status: "healthy" | "degraded" | "down" | "unknown";
  latency_ms?: number;
  error?: string;
  connections?: number;
  max_connections?: number;
  counters?: Record<string, number>;
}

export interface SystemHealth {
  status: "healthy" | "degraded";
  components: {
    postgres: ComponentHealth;
    influxdb: ComponentHealth;
    mqtt: ComponentHealth;
    keycloak: ComponentHealth;
    ingest: ComponentHealth;
    evaluator: ComponentHealth;
    dispatcher: ComponentHealth;
    delivery: ComponentHealth;
  };
  checked_at: string;
}

export interface SystemMetrics {
  throughput: {
    ingest_rate_per_sec: number;
    messages_received_total: number;
    messages_written_total: number;
    messages_rejected_total: number;
    alerts_created_total: number;
    deliveries_succeeded_total: number;
    deliveries_failed_total: number;
  };
  queues: {
    ingest_queue_depth: number;
    delivery_pending: number;
  };
  last_activity: {
    last_ingest: string | null;
    last_evaluation: string | null;
    last_dispatch: string | null;
    last_delivery: string | null;
  };
}

export interface SystemCapacity {
  postgres: {
    db_size_mb: number;
    connections_used: number;
    connections_max: number;
    connections_pct: number;
    top_tables: { name: string; total_mb: number }[];
  };
  influxdb: {
    file_limit: number;
    database_count: number;
  };
  disk: {
    volumes: Record<string, {
      total_gb: number;
      used_gb: number;
      free_gb: number;
      used_pct: number;
    }>;
  };
}

export interface SystemAggregates {
  tenants: { active: number; suspended: number; total: number };
  devices: { registered: number; online: number; stale: number };
  alerts: { open: number; triggered_24h: number };
  integrations: { total: number; active: number };
  rules: { total: number; active: number };
  deliveries: { pending: number; succeeded: number; failed: number };
}

export interface SystemError {
  source: string;
  error_type: string;
  timestamp: string;
  tenant_id: string;
  details: Record<string, unknown>;
}

export interface SystemErrors {
  errors: SystemError[];
  counts: {
    delivery_failures: number;
    quarantined: number;
    stuck_deliveries: number;
  };
  period_hours: number;
}

export async function fetchSystemHealth(): Promise<SystemHealth> {
  const response = await apiClient.get("/operator/system/health");
  return response.data;
}

export async function fetchSystemMetrics(): Promise<SystemMetrics> {
  const response = await apiClient.get("/operator/system/metrics");
  return response.data;
}

export async function fetchSystemCapacity(): Promise<SystemCapacity> {
  const response = await apiClient.get("/operator/system/capacity");
  return response.data;
}

export async function fetchSystemAggregates(): Promise<SystemAggregates> {
  const response = await apiClient.get("/operator/system/aggregates");
  return response.data;
}

export async function fetchSystemErrors(hours = 1): Promise<SystemErrors> {
  const response = await apiClient.get(`/operator/system/errors?hours=${hours}`);
  return response.data;
}
```

---

## Create Dashboard Page

**File:** `frontend/src/features/operator/SystemDashboard.tsx`

```typescript
import { useQuery } from "@tanstack/react-query";
import {
  fetchSystemHealth,
  fetchSystemMetrics,
  fetchSystemCapacity,
  fetchSystemAggregates,
  fetchSystemErrors,
  type SystemHealth,
  type ComponentHealth,
} from "@/services/api/system";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Database,
  Server,
  Wifi,
  Shield,
  Upload,
  AlertTriangle,
  Send,
  Truck,
  Activity,
  Users,
  Radio,
  Bell,
  Zap,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";

function StatusBadge({ status }: { status: string }) {
  const variant = {
    healthy: "default",
    degraded: "secondary",
    down: "destructive",
    unknown: "outline",
  }[status] as "default" | "secondary" | "destructive" | "outline";

  const icon = {
    healthy: "🟢",
    degraded: "🟡",
    down: "🔴",
    unknown: "⚪",
  }[status];

  return (
    <Badge variant={variant} className="gap-1">
      <span>{icon}</span>
      <span className="capitalize">{status}</span>
    </Badge>
  );
}

function ServiceHealthCard({
  name,
  icon: Icon,
  health,
}: {
  name: string;
  icon: React.ElementType;
  health?: ComponentHealth;
}) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Icon className="h-5 w-5 text-muted-foreground" />
            <span className="font-medium">{name}</span>
          </div>
          <StatusBadge status={health?.status || "unknown"} />
        </div>
        {health?.latency_ms !== undefined && (
          <p className="text-xs text-muted-foreground mt-2">
            Latency: {health.latency_ms}ms
          </p>
        )}
        {health?.connections !== undefined && (
          <p className="text-xs text-muted-foreground">
            Connections: {health.connections}/{health.max_connections}
          </p>
        )}
        {health?.error && (
          <p className="text-xs text-destructive mt-2">{health.error}</p>
        )}
      </CardContent>
    </Card>
  );
}

function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
}: {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ElementType;
}) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center gap-2 text-muted-foreground mb-2">
          <Icon className="h-4 w-4" />
          <span className="text-sm">{title}</span>
        </div>
        <p className="text-2xl font-bold">{value}</p>
        {subtitle && (
          <p className="text-xs text-muted-foreground">{subtitle}</p>
        )}
      </CardContent>
    </Card>
  );
}

function CapacityGauge({
  label,
  used,
  max,
  unit,
}: {
  label: string;
  used: number;
  max: number;
  unit: string;
}) {
  const pct = max > 0 ? Math.round((used / max) * 100) : 0;
  const color = pct > 80 ? "bg-destructive" : pct > 60 ? "bg-yellow-500" : "bg-primary";

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span>{label}</span>
        <span className="text-muted-foreground">
          {used.toFixed(1)} / {max.toFixed(1)} {unit} ({pct}%)
        </span>
      </div>
      <Progress value={pct} className="h-2" />
    </div>
  );
}

export function SystemDashboard() {
  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ["system-health"],
    queryFn: fetchSystemHealth,
    refetchInterval: 10000, // Refresh every 10 seconds
  });

  const { data: metrics } = useQuery({
    queryKey: ["system-metrics"],
    queryFn: fetchSystemMetrics,
    refetchInterval: 10000,
  });

  const { data: capacity } = useQuery({
    queryKey: ["system-capacity"],
    queryFn: fetchSystemCapacity,
    refetchInterval: 30000, // Less frequent
  });

  const { data: aggregates } = useQuery({
    queryKey: ["system-aggregates"],
    queryFn: fetchSystemAggregates,
    refetchInterval: 15000,
  });

  const { data: errors } = useQuery({
    queryKey: ["system-errors"],
    queryFn: () => fetchSystemErrors(1),
    refetchInterval: 15000,
  });

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">System Dashboard</h1>
          <p className="text-muted-foreground">
            Platform health and performance overview
          </p>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={health?.status || "unknown"} />
          {health?.checked_at && (
            <span className="text-sm text-muted-foreground">
              Updated {formatDistanceToNow(new Date(health.checked_at))} ago
            </span>
          )}
        </div>
      </div>

      {/* Service Health Grid */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Service Health</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <ServiceHealthCard
              name="PostgreSQL"
              icon={Database}
              health={health?.components.postgres}
            />
            <ServiceHealthCard
              name="InfluxDB"
              icon={Database}
              health={health?.components.influxdb}
            />
            <ServiceHealthCard
              name="MQTT"
              icon={Wifi}
              health={health?.components.mqtt}
            />
            <ServiceHealthCard
              name="Keycloak"
              icon={Shield}
              health={health?.components.keycloak}
            />
            <ServiceHealthCard
              name="Ingest"
              icon={Upload}
              health={health?.components.ingest}
            />
            <ServiceHealthCard
              name="Evaluator"
              icon={AlertTriangle}
              health={health?.components.evaluator}
            />
            <ServiceHealthCard
              name="Dispatcher"
              icon={Send}
              health={health?.components.dispatcher}
            />
            <ServiceHealthCard
              name="Delivery"
              icon={Truck}
              health={health?.components.delivery}
            />
          </div>
        </CardContent>
      </Card>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          title="Ingest Rate"
          value={`${metrics?.throughput.ingest_rate_per_sec || 0}/s`}
          subtitle="messages per second"
          icon={Activity}
        />
        <MetricCard
          title="Queue Depth"
          value={metrics?.queues.ingest_queue_depth || 0}
          subtitle="pending messages"
          icon={Upload}
        />
        <MetricCard
          title="Pending Deliveries"
          value={metrics?.queues.delivery_pending || 0}
          subtitle="webhook jobs"
          icon={Send}
        />
        <MetricCard
          title="Failed Deliveries"
          value={metrics?.throughput.deliveries_failed_total || 0}
          subtitle="total failures"
          icon={AlertTriangle}
        />
      </div>

      {/* Aggregates and Capacity */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Platform Aggregates */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Platform Totals</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="flex items-center gap-2">
                <Users className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="font-medium">{aggregates?.tenants.active || 0}</p>
                  <p className="text-xs text-muted-foreground">Active Tenants</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Radio className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="font-medium">
                    {aggregates?.devices.online || 0} / {aggregates?.devices.registered || 0}
                  </p>
                  <p className="text-xs text-muted-foreground">Devices Online</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Bell className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="font-medium">{aggregates?.alerts.open || 0}</p>
                  <p className="text-xs text-muted-foreground">Open Alerts</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Zap className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="font-medium">
                    {aggregates?.integrations.active || 0} / {aggregates?.integrations.total || 0}
                  </p>
                  <p className="text-xs text-muted-foreground">Integrations</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Capacity */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Capacity</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {capacity?.disk?.volumes?.root && (
              <CapacityGauge
                label="Disk Usage"
                used={capacity.disk.volumes.root.used_gb}
                max={capacity.disk.volumes.root.total_gb}
                unit="GB"
              />
            )}
            {capacity?.postgres && (
              <CapacityGauge
                label="DB Connections"
                used={capacity.postgres.connections_used}
                max={capacity.postgres.connections_max}
                unit=""
              />
            )}
            {capacity?.postgres?.db_size_mb && (
              <div className="flex justify-between text-sm">
                <span>Database Size</span>
                <span className="text-muted-foreground">
                  {capacity.postgres.db_size_mb.toFixed(1)} MB
                </span>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent Errors */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center justify-between">
            <span>Recent Errors</span>
            <div className="flex gap-2 text-sm font-normal">
              {errors?.counts && (
                <>
                  <Badge variant="destructive">
                    {errors.counts.delivery_failures} delivery failures
                  </Badge>
                  <Badge variant="secondary">
                    {errors.counts.quarantined} quarantined
                  </Badge>
                </>
              )}
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {errors?.errors && errors.errors.length > 0 ? (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {errors.errors.slice(0, 10).map((error, idx) => (
                <div
                  key={idx}
                  className="flex items-start gap-3 p-2 rounded bg-muted/50 text-sm"
                >
                  <span className="text-muted-foreground whitespace-nowrap">
                    {new Date(error.timestamp).toLocaleTimeString()}
                  </span>
                  <Badge variant="outline">{error.source}</Badge>
                  <span className="font-medium">{error.error_type}</span>
                  <span className="text-muted-foreground truncate">
                    {error.tenant_id && `[${error.tenant_id}]`}
                    {error.details?.device_id && ` ${error.details.device_id}`}
                    {error.details?.last_error && ` - ${error.details.last_error}`}
                    {error.details?.reason && ` - ${error.details.reason}`}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-muted-foreground text-center py-4">
              No errors in the last hour
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
```

---

## Add Route

**File:** `frontend/src/app/router.tsx`

Add import and route:

```typescript
import { SystemDashboard } from "@/features/operator/SystemDashboard";

// In routes array, under operator section:
{
  path: "/operator/system",
  element: <SystemDashboard />,
},
```

---

## Add Sidebar Link

**File:** `frontend/src/components/layout/AppSidebar.tsx`

Add to operator section:

```typescript
import { Activity } from "lucide-react";

// In operator nav items:
{
  title: "System",
  url: "/operator/system",
  icon: Activity,
},
```

---

## Rebuild

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
cp -r dist/* ../services/ui_iot/spa/
cd ../compose && docker compose restart ui
```

---

## Files

| Action | File |
|--------|------|
| CREATE | `frontend/src/services/api/system.ts` |
| CREATE | `frontend/src/features/operator/SystemDashboard.tsx` |
| MODIFY | `frontend/src/app/router.tsx` |
| MODIFY | `frontend/src/components/layout/AppSidebar.tsx` |
