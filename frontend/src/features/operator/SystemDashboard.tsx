import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchSystemHealth,
  fetchSystemCapacity,
  fetchSystemAggregates,
  fetchSystemErrors,
  fetchMetricHistory,
  type ComponentHealth,
  type SystemHealth,
  type SystemCapacity,
  type SystemAggregates,
  type SystemErrors,
} from "@/services/api/system";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useOnlineStatus } from "@/hooks/useOnlineStatus";
import {
  Database,
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
  RefreshCw,
  Pause,
  Play,
} from "lucide-react";
import { MetricChartCard } from "./components/MetricChartCard";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

function formatRelativeTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown";
  const diffSeconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
  if (diffSeconds < 60) return `${diffSeconds}s ago`;
  const diffMinutes = Math.floor(diffSeconds / 60);
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

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

function MetricTimeSeriesChart({
  title,
  metric,
  minutes = 60,
  color = "#3b82f6",
  refreshInterval,
  rate = false,
}: {
  title: string;
  metric: string;
  minutes?: number;
  color?: string;
  refreshInterval: number;
  /** Set to true for counter metrics to compute rate (derivative) */
  rate?: boolean;
}) {
  const { data } = useQuery({
    queryKey: ["metric-history", metric, minutes, rate],
    queryFn: () => fetchMetricHistory(metric, minutes, rate),
    refetchInterval: refreshInterval,
  });

  const chartData = useMemo(() => {
    if (!data?.points) return [];
    return data.points.map((p) => ({
      time: new Date(p.time).toLocaleTimeString(),
      value: p.value,
    }));
  }, [data?.points]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={chartData}>
            <XAxis dataKey="time" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
            <YAxis tick={{ fontSize: 10 }} width={40} />
            <Tooltip />
            <Line type="monotone" dataKey="value" stroke={color} strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
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

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span>{label}</span>
        <span className="text-muted-foreground">
          {used.toFixed(1)} / {max.toFixed(1)} {unit} ({pct}%)
        </span>
      </div>
      <div className="h-2 w-full rounded bg-muted">
        <div
          className="h-2 rounded bg-primary transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export function SystemDashboard() {
  const [refreshInterval, setRefreshInterval] = useState<number>(10000);
  const [isPaused, setIsPaused] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [staleThreshold] = useState(60000);
  const queryClient = useQueryClient();
  const isOnline = useOnlineStatus();

  const { data: health, isFetching: healthFetching } = useQuery<SystemHealth>({
    queryKey: ["system-health"],
    queryFn: fetchSystemHealth,
    refetchInterval: isPaused ? false : refreshInterval,
  });

  const { data: capacity, isFetching: capacityFetching } = useQuery<SystemCapacity>({
    queryKey: ["system-capacity"],
    queryFn: fetchSystemCapacity,
    refetchInterval: isPaused ? false : refreshInterval * 3,
  });

  const { data: aggregates, isFetching: aggregatesFetching } = useQuery<SystemAggregates>({
    queryKey: ["system-aggregates"],
    queryFn: fetchSystemAggregates,
    refetchInterval: isPaused ? false : refreshInterval * 1.5,
  });

  const { data: errors, isFetching: errorsFetching } = useQuery<SystemErrors>({
    queryKey: ["system-errors"],
    queryFn: () => fetchSystemErrors(1),
    refetchInterval: isPaused ? false : refreshInterval * 1.5,
  });

  const isAnyFetching =
    healthFetching ||
    capacityFetching ||
    aggregatesFetching ||
    errorsFetching;

  const isDataStale =
    lastRefresh && Date.now() - lastRefresh.getTime() > staleThreshold;

  const handleRefreshAll = () => {
    queryClient.invalidateQueries({ queryKey: ["system-health"] });
    queryClient.invalidateQueries({ queryKey: ["system-metrics"] });
    queryClient.invalidateQueries({ queryKey: ["system-capacity"] });
    queryClient.invalidateQueries({ queryKey: ["system-aggregates"] });
    queryClient.invalidateQueries({ queryKey: ["system-errors"] });
  };

  useEffect(() => {
    if (health?.checked_at) {
      setLastRefresh(new Date(health.checked_at));
    }
  }, [health?.checked_at]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "r" && !e.metaKey && !e.ctrlKey) {
        handleRefreshAll();
      }
      if (e.key === " " && e.target === document.body) {
        e.preventDefault();
        setIsPaused((prev) => !prev);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">System Dashboard</h1>
          <p className="text-muted-foreground">Platform health and performance overview</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <StatusBadge status={health?.status || "unknown"} />
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span className="relative h-4 w-4">
              <RefreshCw
                className={`h-4 w-4 transition-opacity ${
                  isAnyFetching ? "animate-spin text-primary opacity-100" : "opacity-0"
                }`}
              />
              <span
                className={`absolute inset-0 m-auto h-2 w-2 rounded-full bg-green-500 transition-opacity ${
                  isAnyFetching ? "opacity-0" : "opacity-100"
                }`}
              />
            </span>
            <span className="hidden sm:inline min-w-[5.5rem] text-right">
              {formatRelativeTime(lastRefresh.toISOString())}
            </span>
          </div>
          <Select
            value={refreshInterval.toString()}
            onValueChange={(v) => setRefreshInterval(parseInt(v, 10))}
          >
            <SelectTrigger className="w-28">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="5000">5s</SelectItem>
              <SelectItem value="10000">10s</SelectItem>
              <SelectItem value="30000">30s</SelectItem>
              <SelectItem value="60000">60s</SelectItem>
            </SelectContent>
          </Select>
          <Button
            variant={isPaused ? "default" : "outline"}
            size="icon"
            onClick={() => setIsPaused(!isPaused)}
            title={isPaused ? "Resume auto-refresh" : "Pause auto-refresh"}
          >
            {isPaused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
          </Button>
          <Button
            variant="outline"
            size="icon"
            onClick={handleRefreshAll}
            disabled={isAnyFetching}
            title="Refresh now (R)"
          >
            <RefreshCw className={`h-4 w-4 ${isAnyFetching ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </div>

      {!isOnline && (
        <div className="bg-destructive/10 text-destructive p-3 rounded-md flex items-center gap-2">
          <AlertTriangle className="h-5 w-5" />
          <span>Connection lost. Updates paused.</span>
        </div>
      )}

      {isDataStale && !isPaused && isOnline && (
        <div className="bg-yellow-500/10 text-yellow-700 dark:text-yellow-400 p-3 rounded-md flex items-center gap-2">
          <AlertTriangle className="h-5 w-5" />
          <span>Data may be stale. Last updated over 1 minute ago.</span>
          <Button variant="ghost" size="sm" onClick={handleRefreshAll}>
            Refresh
          </Button>
        </div>
      )}

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
            <ServiceHealthCard name="MQTT" icon={Wifi} health={health?.components.mqtt} />
            <ServiceHealthCard
              name="Keycloak"
              icon={Shield}
              health={health?.components.keycloak}
            />
            <ServiceHealthCard name="Ingest" icon={Upload} health={health?.components.ingest} />
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

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricChartCard
          title="Ingest Rate"
          metric="messages_written"
          unit="/s"
          icon={Activity}
          color="#22c55e"
          minutes={15}
          refreshInterval={refreshInterval}
          rate={true}
        />
        <MetricChartCard
          title="Queue Depth"
          metric="queue_depth"
          icon={Upload}
          color="#3b82f6"
          minutes={15}
          refreshInterval={refreshInterval}
        />
        <MetricChartCard
          title="Pending Deliveries"
          metric="jobs_pending"
          icon={Send}
          color="#f59e0b"
          minutes={15}
          refreshInterval={refreshInterval}
        />
        <MetricChartCard
          title="Failed Deliveries"
          metric="jobs_failed"
          icon={AlertTriangle}
          color="#ef4444"
          minutes={15}
          refreshInterval={refreshInterval}
        />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricChartCard
          title="DB Connections"
          metric="connections"
          icon={Database}
          color="#8b5cf6"
          minutes={15}
          refreshInterval={refreshInterval}
        />
        <MetricChartCard
          title="Devices Online"
          metric="devices_online"
          icon={Radio}
          color="#22c55e"
          minutes={15}
          refreshInterval={refreshInterval}
        />
        <MetricChartCard
          title="Devices Stale"
          metric="devices_stale"
          icon={Radio}
          color="#f59e0b"
          minutes={15}
          refreshInterval={refreshInterval}
        />
        <MetricChartCard
          title="Open Alerts"
          metric="alerts_open"
          icon={Bell}
          color="#ef4444"
          minutes={15}
          refreshInterval={refreshInterval}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <MetricTimeSeriesChart
          title="Ingest Rate (Last Hour)"
          metric="messages_written"
          minutes={60}
          color="#22c55e"
          refreshInterval={refreshInterval}
          rate={true}
        />
        <MetricTimeSeriesChart
          title="Queue Depth (Last Hour)"
          metric="queue_depth"
          minutes={60}
          color="#3b82f6"
          refreshInterval={refreshInterval}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
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
                  <Badge variant="secondary">{errors.counts.quarantined} quarantined</Badge>
                </>
              )}
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {errors?.errors && errors.errors.length > 0 ? (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {errors.errors.slice(0, 10).map((error, idx) => {
                const details = (error.details || {}) as {
                  device_id?: string;
                  last_error?: string;
                  reason?: string;
                };
                return (
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
                      {details.device_id && ` ${details.device_id}`}
                      {details.last_error && ` - ${details.last_error}`}
                      {details.reason && ` - ${details.reason}`}
                    </span>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-muted-foreground text-center py-4">
              No errors in the last hour
            </p>
          )}
        </CardContent>
      </Card>

      <p className="text-xs text-muted-foreground text-center mt-4">
        Keyboard: <kbd className="px-1 bg-muted rounded">R</kbd> refresh,
        <kbd className="px-1 bg-muted rounded ml-1">Space</kbd> pause/resume
      </p>
    </div>
  );
}
