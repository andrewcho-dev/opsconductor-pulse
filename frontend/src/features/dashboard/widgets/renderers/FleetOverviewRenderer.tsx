import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import type { WidgetRendererProps } from "../widget-registry";
import { fetchFleetSummary, fetchFleetHealth, getFleetUptimeSummary } from "@/services/api/devices";
import { Skeleton } from "@/components/ui/skeleton";
import { AlertTriangle, Battery, Bell, Zap } from "lucide-react";

export default function FleetOverviewRenderer({ config }: WidgetRendererProps) {
  const { data: summary, isLoading: l1 } = useQuery({
    queryKey: ["fleet-summary"],
    queryFn: fetchFleetSummary,
    refetchInterval: 30_000,
  });

  const { data: health, isLoading: l2 } = useQuery({
    queryKey: ["fleet-health"],
    queryFn: fetchFleetHealth,
    refetchInterval: 30_000,
  });

  const { data: uptime, isLoading: l3 } = useQuery({
    queryKey: ["fleet-uptime-summary"],
    queryFn: getFleetUptimeSummary,
    refetchInterval: 30_000,
  });

  if (l1 || l2 || l3) {
    return <Skeleton className="h-full w-full min-h-[100px]" />;
  }

  const online = summary?.online ?? summary?.ONLINE ?? 0;
  const stale = summary?.STALE ?? 0;
  const offline = summary?.offline ?? summary?.OFFLINE ?? 0;
  const total = (summary?.total ?? summary?.total_devices ?? online + stale + offline) as number;
  const summaryExtra = (summary as unknown as Record<string, unknown>) ?? {};
  const totalSensors = (summaryExtra.total_sensors as number | undefined) ?? 0;
  const devicesWithSensors = (summaryExtra.devices_with_sensors as number | undefined) ?? 0;

  return (
    <div className="h-full flex flex-col gap-2 px-2 py-1">
      <div className="flex-1 min-h-0 flex flex-col md:flex-row items-stretch gap-4">
        <HealthGauge
          score={health?.score ?? 0}
          thresholds={(config.thresholds as Array<{ value: number; color: string }>) ?? []}
        />
        <StatusBars
          online={online}
          stale={stale}
          offline={offline}
          total={total}
          totalSensors={totalSensors}
          devicesWithSensors={devicesWithSensors}
        />
        <UptimeDisplay pct={uptime?.avg_uptime_pct ?? 0} />
      </div>

      <div className="border-t border-border pt-2">
        <AlertStrip
          alertsOpen={summaryExtra.alerts_open as number | undefined}
          alertsNew={summaryExtra.alerts_new_1h as number | undefined}
          critical={health?.critical_alerts ?? 0}
          lowBattery={summaryExtra.low_battery_count as number | undefined}
        />
      </div>
    </div>
  );
}

function HealthGauge({
  score,
  thresholds,
}: {
  score: number;
  thresholds: Array<{ value: number; color: string }>;
}) {
  const clampedScore = Number.isFinite(score) ? Math.max(0, Math.min(100, score)) : 0;

  const thresholdColor = useMemo(() => {
    if (thresholds.length === 0) return undefined;
    const sorted = [...thresholds].sort((a, b) => b.value - a.value);
    return sorted.find((t) => clampedScore >= t.value)?.color;
  }, [thresholds, clampedScore]);

  const size = 120;
  const strokeWidth = 10;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = (clampedScore / 100) * circumference;
  const dashOffset = circumference - progress;

  return (
    <div className="flex flex-col items-center justify-center gap-1 shrink-0">
      <div className="relative">
        <svg viewBox="0 0 120 120" className="h-[96px] w-[96px] -rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            strokeWidth={strokeWidth}
            className="stroke-foreground/10"
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            stroke={thresholdColor}
            className="stroke-status-online transition-all duration-700"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-2xl font-semibold">{clampedScore.toFixed(0)}%</span>
        </div>
      </div>
      <div className="text-xs text-muted-foreground">Health</div>
    </div>
  );
}

function StatusBars({
  online,
  stale,
  offline,
  total,
  totalSensors,
  devicesWithSensors,
}: {
  online: number;
  stale: number;
  offline: number;
  total: number;
  totalSensors: number;
  devicesWithSensors: number;
}) {
  const safeTotal = Math.max(0, total);

  const rows = [
    { label: "Online", value: online, dot: "bg-status-online", bar: "bg-status-online" },
    { label: "Stale", value: stale, dot: "bg-status-warning", bar: "bg-status-warning" },
    { label: "Offline", value: offline, dot: "bg-status-critical", bar: "bg-status-critical" },
  ];

  return (
    <div className="flex-1 min-w-0 flex flex-col justify-center gap-2">
      <div className="text-xs text-muted-foreground">{safeTotal.toLocaleString()} devices</div>
      <div className="flex items-center gap-1 text-xs text-muted-foreground">
        <span className="font-medium text-foreground">{Math.max(0, totalSensors).toLocaleString()}</span>
        sensors across
        <span className="font-medium text-foreground">
          {Math.max(0, devicesWithSensors).toLocaleString()}
        </span>
        devices
      </div>
      <div className="space-y-2">
        {rows.map((r) => {
          const pct = safeTotal > 0 ? (r.value / safeTotal) * 100 : 0;
          return (
            <div key={r.label} className="flex items-center gap-2">
              <span className={`h-2 w-2 rounded-full ${r.dot}`} aria-hidden="true" />
              <span className="text-xs w-12 text-muted-foreground">{r.label}</span>
              <div className="flex-1 h-2 rounded bg-muted overflow-hidden">
                <div className={`h-full ${r.bar}`} style={{ width: `${pct}%` }} />
              </div>
              <span className="text-xs tabular-nums w-10 text-right">
                {Math.max(0, r.value).toLocaleString()}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function UptimeDisplay({ pct }: { pct: number }) {
  const clamped = Number.isFinite(pct) ? Math.max(0, Math.min(100, pct)) : 0;
  const color =
    clamped >= 99 ? "text-status-online" : clamped >= 95 ? "text-status-warning" : "text-status-critical";

  return (
    <div className="shrink-0 flex flex-col items-center justify-center gap-1">
      <div className={`text-2xl font-semibold tabular-nums ${color}`}>{clamped.toFixed(1)}%</div>
      <div className="text-xs text-muted-foreground">Avg Uptime</div>
    </div>
  );
}

function AlertStrip({
  alertsOpen,
  alertsNew,
  critical,
  lowBattery,
}: {
  alertsOpen?: number;
  alertsNew?: number;
  critical: number;
  lowBattery?: number;
}) {
  const items = [
    { key: "open", icon: Bell, label: "open", value: alertsOpen ?? 0, className: "text-muted-foreground" },
    { key: "new", icon: Zap, label: "new (1h)", value: alertsNew ?? 0, className: "text-muted-foreground" },
    { key: "critical", icon: AlertTriangle, label: "critical", value: critical ?? 0, className: "text-status-critical" },
    { key: "battery", icon: Battery, label: "low battery", value: lowBattery ?? 0, className: "text-muted-foreground" },
  ].filter((i) => i.value > 0);

  if (items.length === 0) {
    return <div className="text-xs text-status-online">All clear</div>;
  }

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
      {items.map((i) => {
        const Icon = i.icon;
        return (
          <div key={i.key} className={`flex items-center gap-1 ${i.className}`}>
            <Icon className="h-3.5 w-3.5" aria-hidden="true" />
            <span className="tabular-nums">{i.value}</span>
            <span>{i.label}</span>
          </div>
        );
      })}
    </div>
  );
}

