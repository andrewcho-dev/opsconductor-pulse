import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { EChartsOption } from "echarts";
import { Cpu, Gauge, HardDrive, MapPin, Signal, Timer } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EChartWrapper } from "@/lib/charts/EChartWrapper";
import { getDeviceHealth } from "@/services/api/sensors";
import type { DeviceHealthPoint } from "@/services/api/types";

interface DeviceHealthPanelProps {
  deviceId: string;
}

type HealthRange = "1h" | "6h" | "24h" | "7d" | "30d";

function clamp(n: number, min: number, max: number) {
  return Math.max(min, Math.min(max, n));
}

function humanizeBytes(bytes: number | null): string {
  if (bytes == null || !Number.isFinite(bytes)) return "—";
  const abs = Math.abs(bytes);
  const units = ["B", "KB", "MB", "GB", "TB"];
  let idx = 0;
  let value = abs;
  while (value >= 1024 && idx < units.length - 1) {
    value /= 1024;
    idx += 1;
  }
  const sign = bytes < 0 ? "-" : "";
  const formatted = value >= 10 || idx === 0 ? value.toFixed(0) : value.toFixed(1);
  return `${sign}${formatted} ${units[idx]}`;
}

function humanizeUptime(seconds: number | null): string {
  if (seconds == null || !Number.isFinite(seconds) || seconds < 0) return "—";
  const s = Math.floor(seconds);
  const days = Math.floor(s / 86400);
  const hours = Math.floor((s % 86400) / 3600);
  const minutes = Math.floor((s % 3600) / 60);
  if (days > 0) return `${days}d`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

function signalColorClass(signalQuality: number | null): string {
  if (signalQuality == null || !Number.isFinite(signalQuality)) return "text-foreground";
  if (signalQuality >= 60) return "text-status-online";
  if (signalQuality >= 30) return "text-status-warning";
  return "text-status-critical";
}

function cpuTempColorClass(cpuTempC: number | null): string {
  if (cpuTempC == null || !Number.isFinite(cpuTempC)) return "text-foreground";
  if (cpuTempC < 60) return "text-status-online";
  if (cpuTempC < 80) return "text-status-warning";
  return "text-status-critical";
}

export function DeviceHealthPanel({ deviceId }: DeviceHealthPanelProps) {
  const [range, setRange] = useState<HealthRange>("24h");

  const { data, isLoading } = useQuery({
    queryKey: ["device-health", deviceId, range],
    queryFn: () => getDeviceHealth(deviceId, range, 200),
    enabled: !!deviceId,
    refetchInterval: 30_000,
  });

  const latest = data?.latest ?? null;
  const points = data?.data_points ?? [];

  const chartOption: EChartsOption | null = useMemo(() => {
    if (points.length < 2) return null;
    const seriesData = points
      .filter((p) => p.signal_quality != null)
      .map((p) => [p.time, p.signal_quality] as [string, number]);
    if (seriesData.length < 2) return null;

    return {
      tooltip: { trigger: "axis" },
      xAxis: { type: "time" },
      yAxis: { type: "value", min: 0, max: 100, name: "Signal %" },
      series: [
        {
          type: "line",
          data: seriesData,
          smooth: true,
          areaStyle: { opacity: 0.15 },
          lineStyle: { width: 2 },
          symbol: "none",
        },
      ],
      grid: { left: 40, right: 20, top: 10, bottom: 30 },
    };
  }, [points]);

  return (
    <div className="rounded-md border border-border p-3 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold">Device Health</h3>
          <p className="text-xs text-muted-foreground">Platform-collected device diagnostics</p>
        </div>
        <div className="flex gap-1">
          {(["1h", "6h", "24h", "7d", "30d"] as const).map((r) => (
            <Button
              key={r}
              size="sm"
              variant={range === r ? "secondary" : "ghost"}
              className="h-8 px-2"
              onClick={() => setRange(r)}
            >
              {r}
            </Button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          <div className="grid grid-cols-5 gap-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
          <Skeleton className="h-[150px] w-full" />
        </div>
      ) : !latest ? (
        <div className="text-sm text-muted-foreground py-2">
          No device health data available. Health telemetry is collected automatically when the device
          connects.
        </div>
      ) : (
        <>
          <div className="grid grid-cols-5 gap-2">
            <MiniStat
              icon={<Signal className="h-4 w-4 text-muted-foreground" />}
              label="Signal"
              value={
                latest.signal_quality != null ? (
                  <span className={signalColorClass(latest.signal_quality)}>
                    {clamp(latest.signal_quality, 0, 100)}%
                  </span>
                ) : (
                  "—"
                )
              }
              subValue={latest.rssi != null ? `${latest.rssi} dBm` : "—"}
            />
            <MiniStat
              icon={<Gauge className="h-4 w-4 text-muted-foreground" />}
              label="Battery"
              value={
                latest.battery_pct != null ? (
                  `${clamp(latest.battery_pct, 0, 100)}%`
                ) : latest.power_source === "line" ? (
                  "Line"
                ) : latest.power_source === "poe" ? (
                  "PoE"
                ) : (
                  "N/A"
                )
              }
              subValue={
                latest.battery_voltage != null
                  ? `${latest.battery_voltage.toFixed(2)} V`
                  : latest.power_source
                    ? `(${latest.power_source})`
                    : "—"
              }
            />
            <MiniStat
              icon={<Cpu className="h-4 w-4 text-muted-foreground" />}
              label="CPU Temp"
              value={
                latest.cpu_temp_c != null ? (
                  <span className={cpuTempColorClass(latest.cpu_temp_c)}>
                    {latest.cpu_temp_c.toFixed(1)}C
                  </span>
                ) : (
                  "—"
                )
              }
              subValue=" "
            />
            <MiniStat
              icon={<HardDrive className="h-4 w-4 text-muted-foreground" />}
              label="Memory"
              value={latest.memory_used_pct != null ? `${clamp(latest.memory_used_pct, 0, 100)}%` : "—"}
              subValue={
                latest.storage_used_pct != null ? `Storage ${clamp(latest.storage_used_pct, 0, 100)}%` : "—"
              }
            />
            <MiniStat
              icon={<Timer className="h-4 w-4 text-muted-foreground" />}
              label="Uptime"
              value={humanizeUptime(latest.uptime_seconds)}
              subValue={latest.reboot_count != null ? `${latest.reboot_count} reboots` : "—"}
            />
          </div>

          {chartOption && (
            <div className="space-y-2">
              <div className="text-xs text-muted-foreground">Signal Quality</div>
              <EChartWrapper option={chartOption} style={{ height: 150 }} />
            </div>
          )}

          <HealthDetails latest={latest} />
        </>
      )}
    </div>
  );
}

function MiniStat({
  icon,
  label,
  value,
  subValue,
}: {
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
  subValue: React.ReactNode;
}) {
  return (
    <div className="rounded-md border border-border p-2 space-y-1">
      <div className="flex items-center gap-2">
        {icon}
        <div className="text-xs text-muted-foreground">{label}</div>
      </div>
      <div className="text-lg font-semibold leading-none">{value}</div>
      <div className="text-xs text-muted-foreground truncate">{subValue}</div>
    </div>
  );
}

function HealthDetails({ latest }: { latest: DeviceHealthPoint }) {
  const tx = humanizeBytes(latest.data_tx_bytes);
  const rx = humanizeBytes(latest.data_rx_bytes);
  const gps =
    latest.gps_fix && latest.gps_lat != null && latest.gps_lon != null
      ? `${latest.gps_lat.toFixed(3)}, ${latest.gps_lon.toFixed(3)}`
      : "—";

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
      <span>Network: {latest.network_type ?? "—"}</span>
      <span>Cell: {latest.cell_id ?? "—"}</span>
      <span>TX: {tx}</span>
      <span>RX: {rx}</span>
      <span className="inline-flex items-center gap-1">
        <MapPin className="h-3.5 w-3.5" aria-hidden="true" /> GPS: {gps}
      </span>
    </div>
  );
}

