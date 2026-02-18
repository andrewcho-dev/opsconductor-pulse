import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared";
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
  Radio,
  Bell,
  RefreshCw,
  Pause,
  Play,
  TrendingUp,
  TrendingDown,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

function StatusDot({ status }: { status: string }) {
  const color =
    { healthy: "bg-status-online", degraded: "bg-status-warning", down: "bg-status-critical", unknown: "bg-status-offline" }[
      status
    ] || "bg-status-offline";
  return <span className={`inline-block h-2 w-2 rounded-full ${color}`} />;
}

function ServiceChip({ name, icon: Icon, health }: { name: string; icon: React.ElementType; health?: ComponentHealth }) {
  const status = health?.status || "unknown";
  const isDown = status === "down";
  const isDegraded = status === "degraded";
  return (
    <div
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-sm border ${
        isDown ? "border-status-critical bg-status-critical/10 text-status-critical"
        : isDegraded ? "border-status-warning bg-status-warning/10 text-status-warning"
        : "border-border text-muted-foreground"
      }`}
      title={health?.error || (health?.latency_ms !== undefined ? `${name}: ${health.latency_ms}ms` : name)}
    >
      <StatusDot status={status} />
      <Icon className="h-3 w-3" />
      <span>{name}</span>
      {health?.latency_ms !== undefined && !isDown && (
        <span className="text-sm opacity-60">{health.latency_ms}ms</span>
      )}
    </div>
  );
}

function Sparkline({ data, color, height = 32 }: { data: number[]; color: string; height?: number }) {
  if (data.length < 2) return <div style={{ height }} className="w-full bg-muted/30 rounded" />;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  // Use viewBox for responsive scaling
  const w = 100;
  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = height - 2 - ((v - min) / range) * (height - 4);
    return `${x},${y}`;
  }).join(" ");
  const areaPoints = `0,${height} ${points} ${w},${height}`;

  return (
    <svg viewBox={`0 0 ${w} ${height}`} preserveAspectRatio="none" className="w-full block" style={{ height }}>
      <polygon points={areaPoints} fill={color} opacity={0.15} />
      <polyline points={points} fill="none" stroke={color} strokeWidth={1.5} vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

function MetricCard({
  label, value, unit, color, trend, sparkData, icon: Icon
}: {
  label: string;
  value: number;
  unit?: string;
  color: string;
  trend?: "up" | "down" | null;
  sparkData: number[];
  icon: React.ElementType;
}) {
  const formatValue = (n: number) => {
    if (n >= 1000000) return (n / 1000000).toFixed(1) + "M";
    if (n >= 1000) return (n / 1000).toFixed(1) + "K";
    return n.toFixed(n % 1 === 0 ? 0 : 1);
  };

  return (
    <div className="border border-border rounded px-2 py-1.5 bg-card">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1 text-sm text-muted-foreground">
          <Icon className="h-3 w-3" />
          <span>{label}</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="text-sm font-semibold tabular-nums" style={{ color }}>{formatValue(value)}{unit}</span>
          {trend === "up" && <TrendingUp className="h-3 w-3 text-status-online" />}
          {trend === "down" && <TrendingDown className="h-3 w-3 text-status-critical" />}
        </div>
      </div>
      <Sparkline data={sparkData} color={color} height={24} />
    </div>
  );
}

function useMetric(metric: string, refreshInterval: number, rate = false) {
  const { data } = useQuery({
    queryKey: ["metric-history", metric, 30, rate],
    queryFn: () => fetchMetricHistory(metric, 30, rate),
    refetchInterval: refreshInterval,
  });

  return useMemo(() => {
    if (!data?.points?.length) return { value: 0, trend: null as "up" | "down" | null, spark: [] as number[] };
    const values = data.points.map(p => p.value);
    const current = values[values.length - 1] || 0;
    const recent = values.slice(-6);
    const older = values.slice(-12, -6);
    let trend: "up" | "down" | null = null;
    if (recent.length && older.length) {
      const recentAvg = recent.reduce((a, b) => a + b, 0) / recent.length;
      const olderAvg = older.reduce((a, b) => a + b, 0) / older.length;
      const change = ((recentAvg - olderAvg) / (olderAvg || 1)) * 100;
      if (Math.abs(change) > 10) trend = change > 0 ? "up" : "down";
    }
    return { value: current, trend, spark: values };
  }, [data]);
}

function CapacityBar({ label, pct, detail }: { label: string; pct: number; detail?: string }) {
  const isHigh = pct > 80;
  const isCrit = pct > 95;
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="text-muted-foreground w-12">{label}</span>
      <div className="flex-1 h-2 bg-muted rounded overflow-hidden max-w-32">
        <div
          className={`h-full transition-all ${isCrit ? "bg-status-critical" : isHigh ? "bg-status-warning" : "bg-status-online"}`}
          style={{ width: `${Math.min(100, pct)}%` }}
        />
      </div>
      <span
        className={`tabular-nums w-10 text-right ${isCrit ? "text-status-critical font-medium" : isHigh ? "text-status-warning" : ""}`}
      >
        {pct}%
      </span>
      {detail && <span className="text-muted-foreground text-sm">{detail}</span>}
    </div>
  );
}

export function SystemDashboard() {
  const [refreshInterval, setRefreshInterval] = useState(10000);
  const [isPaused, setIsPaused] = useState(false);
  const queryClient = useQueryClient();
  const isOnline = useOnlineStatus();

  const { data: health, isFetching } = useQuery<SystemHealth>({
    queryKey: ["system-health"],
    queryFn: fetchSystemHealth,
    refetchInterval: isPaused ? false : refreshInterval,
  });

  const { data: capacity } = useQuery<SystemCapacity>({
    queryKey: ["system-capacity"],
    queryFn: fetchSystemCapacity,
    refetchInterval: isPaused ? false : refreshInterval * 3,
  });

  const { data: aggregates } = useQuery<SystemAggregates>({
    queryKey: ["system-aggregates"],
    queryFn: fetchSystemAggregates,
    refetchInterval: isPaused ? false : refreshInterval * 1.5,
  });

  const { data: errors } = useQuery<SystemErrors>({
    queryKey: ["system-errors"],
    queryFn: () => fetchSystemErrors(1),
    refetchInterval: isPaused ? false : refreshInterval * 1.5,
  });

  const ingest = useMetric("messages_written", isPaused ? 0 : refreshInterval, true);
  const queue = useMetric("queue_depth", isPaused ? 0 : refreshInterval);
  const pending = useMetric("jobs_pending", isPaused ? 0 : refreshInterval);
  const failed = useMetric("jobs_failed", isPaused ? 0 : refreshInterval);
  const online = useMetric("devices_online", isPaused ? 0 : refreshInterval);
  const stale = useMetric("devices_stale", isPaused ? 0 : refreshInterval);
  const alertsOpen = useMetric("alerts_open", isPaused ? 0 : refreshInterval);
  const dbConn = useMetric("connections", isPaused ? 0 : refreshInterval);

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ["system-health"] });
    queryClient.invalidateQueries({ queryKey: ["system-capacity"] });
    queryClient.invalidateQueries({ queryKey: ["system-aggregates"] });
    queryClient.invalidateQueries({ queryKey: ["system-errors"] });
    queryClient.invalidateQueries({ queryKey: ["metric-history"] });
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "r" && !e.metaKey && !e.ctrlKey) handleRefresh();
      if (e.key === " " && e.target === document.body) { e.preventDefault(); setIsPaused(p => !p); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const diskPct = capacity?.disk?.volumes?.root
    ? Math.round((capacity.disk.volumes.root.used_gb / capacity.disk.volumes.root.total_gb) * 100) : 0;
  const connPct = capacity?.postgres
    ? Math.round((capacity.postgres.connections_used / capacity.postgres.connections_max) * 100) : 0;
  const errCount = (errors?.counts?.delivery_failures || 0) + (errors?.counts?.quarantined || 0);

  return (
    <div className="space-y-4">
      <PageHeader
        title="System"
        description={
          health?.status
            ? `${health.status.toUpperCase()}${!isOnline ? " — OFFLINE" : ""}`
            : "Loading..."
        }
        action={
          <div className="flex items-center gap-2">
            <Select value={String(refreshInterval)} onValueChange={(v) => setRefreshInterval(Number(v))}>
              <SelectTrigger className="h-8 w-[84px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="5000">5s</SelectItem>
                <SelectItem value="10000">10s</SelectItem>
                <SelectItem value="30000">30s</SelectItem>
              </SelectContent>
            </Select>
            <Button
              variant={isPaused ? "default" : "outline"}
              size="sm"
              onClick={() => setIsPaused((p) => !p)}
              title={isPaused ? "Resume" : "Pause"}
            >
              {isPaused ? <Play className="h-3.5 w-3.5" /> : <Pause className="h-3.5 w-3.5" />}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={isFetching}
              title="Refresh (R)"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? "animate-spin" : ""}`} />
            </Button>
          </div>
        }
      />

      <div className="flex items-center gap-1 flex-wrap">
        <ServiceChip name="Postgres" icon={Database} health={health?.components.postgres} />
        <ServiceChip name="MQTT" icon={Wifi} health={health?.components.mqtt} />
        <ServiceChip name="Keycloak" icon={Shield} health={health?.components.keycloak} />
        <ServiceChip name="Ingest" icon={Upload} health={health?.components.ingest} />
        <ServiceChip name="Evaluator" icon={AlertTriangle} health={health?.components.evaluator} />
        <ServiceChip name="Dispatcher" icon={Send} health={health?.components.dispatcher} />
        <ServiceChip name="Delivery" icon={Truck} health={health?.components.delivery} />
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
        <MetricCard label="Ingest Rate" value={ingest.value} unit="/s" color="#22c55e" trend={ingest.trend} sparkData={ingest.spark} icon={Activity} />
        <MetricCard label="Queue Depth" value={queue.value} color={queue.value > 1000 ? "#ef4444" : "#3b82f6"} trend={queue.trend} sparkData={queue.spark} icon={Upload} />
        <MetricCard label="Pending Jobs" value={pending.value} color={pending.value > 100 ? "#f59e0b" : "#6b7280"} trend={pending.trend} sparkData={pending.spark} icon={Send} />
        <MetricCard label="Failed Jobs" value={failed.value} color={failed.value > 0 ? "#ef4444" : "#6b7280"} trend={failed.trend} sparkData={failed.spark} icon={AlertTriangle} />
        <MetricCard label="Devices Online" value={online.value} color="#22c55e" trend={online.trend} sparkData={online.spark} icon={Radio} />
        <MetricCard label="Devices Stale" value={stale.value} color={stale.value > 10 ? "#f59e0b" : "#6b7280"} trend={stale.trend} sparkData={stale.spark} icon={Radio} />
        <MetricCard label="Open Alerts" value={alertsOpen.value} color={alertsOpen.value > 0 ? "#ef4444" : "#6b7280"} trend={alertsOpen.trend} sparkData={alertsOpen.spark} icon={Bell} />
        <MetricCard label="DB Connections" value={dbConn.value} color="#8b5cf6" trend={dbConn.trend} sparkData={dbConn.spark} icon={Database} />
      </div>

      {/* Stats + Capacity Row */}
      <div className="flex items-start gap-2 flex-wrap">
        <div className="flex items-center gap-4 text-sm border border-border rounded px-2 py-1.5">
          <div><span className="font-semibold text-sm">{aggregates?.tenants.active || 0}</span> <span className="text-muted-foreground">tenants</span></div>
          <div><span className="font-semibold text-sm">{aggregates?.devices.online || 0}</span><span className="text-muted-foreground">/{aggregates?.devices.registered || 0} devices</span></div>
          <div><span className="font-semibold text-sm">{aggregates?.integrations.active || 0}</span><span className="text-muted-foreground">/{aggregates?.integrations.total || 0} integrations</span></div>
        </div>
        <div className="flex items-center gap-3 border border-border rounded px-2 py-1.5">
          <CapacityBar label="Disk" pct={diskPct} detail={capacity?.disk?.volumes?.root ? `${capacity.disk.volumes.root.used_gb.toFixed(0)}/${capacity.disk.volumes.root.total_gb.toFixed(0)}GB` : undefined} />
          <CapacityBar label="Conn" pct={connPct} detail={capacity?.postgres ? `${capacity.postgres.connections_used}/${capacity.postgres.connections_max}` : undefined} />
          {capacity?.postgres?.db_size_mb && (
            <div className="flex items-center gap-1 text-sm">
              <span className="text-muted-foreground">DB</span>
              <span className="font-medium">{capacity.postgres.db_size_mb.toFixed(0)}MB</span>
            </div>
          )}
        </div>
      </div>

      {/* Errors Section */}
      {errCount > 0 && (
        <div className="border border-border rounded px-2 py-1.5">
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm font-medium text-muted-foreground">Errors</span>
            <div className="flex gap-2 text-sm">
              <span className="text-red-600">{errors?.counts?.delivery_failures || 0} failed</span>
              <span className="text-yellow-600">{errors?.counts?.quarantined || 0} quarantined</span>
            </div>
          </div>
          <div className="space-y-0.5 max-h-24 overflow-y-auto">
            {errors?.errors?.slice(0, 6).map((err, i) => {
              const d = err.details as { device_id?: string; reason?: string } | null;
              return (
                <div key={i} className="flex items-center gap-2 text-sm">
                  <span className="text-muted-foreground tabular-nums">{new Date(err.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                  <span className="font-medium text-red-600">{err.error_type}</span>
                  <span className="text-muted-foreground truncate">{err.tenant_id && `[${err.tenant_id}]`} {d?.device_id} {d?.reason}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

    </div>
  );
}
