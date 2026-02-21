import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { Cpu, Gauge, HardDrive, Signal, Timer } from "lucide-react";

import { Skeleton } from "@/components/ui/skeleton";
import { getDeviceHealth } from "@/services/api/sensors";

interface DeviceHealthStripProps {
  deviceId: string;
}

function clamp(n: number, min: number, max: number) {
  return Math.max(min, Math.min(max, n));
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

export function DeviceHealthStrip({ deviceId }: DeviceHealthStripProps) {
  const { data, isLoading } = useQuery({
    queryKey: ["device-health", deviceId, "24h"],
    queryFn: () => getDeviceHealth(deviceId, "24h", 1),
    enabled: !!deviceId,
    staleTime: 30_000,
    refetchInterval: 30_000,
  });

  const latest = data?.latest ?? null;

  if (isLoading) {
    return (
      <div className="grid grid-cols-5 gap-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-16 w-full" />
        ))}
      </div>
    );
  }

  if (!latest) return null;

  return (
    <div className="grid grid-cols-5 gap-2">
      <MiniStat
        icon={<Signal className="h-4 w-4 text-muted-foreground" />}
        label="Signal"
        value={
          latest.signal_quality != null ? (
            <span className={signalColorClass(latest.signal_quality)}>{clamp(latest.signal_quality, 0, 100)}%</span>
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
            <span className={cpuTempColorClass(latest.cpu_temp_c)}>{latest.cpu_temp_c.toFixed(1)}&deg;C</span>
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
        subValue={latest.storage_used_pct != null ? `Storage ${clamp(latest.storage_used_pct, 0, 100)}%` : "—"}
      />
      <MiniStat
        icon={<Timer className="h-4 w-4 text-muted-foreground" />}
        label="Uptime"
        value={humanizeUptime(latest.uptime_seconds)}
        subValue={latest.reboot_count != null ? `${latest.reboot_count} reboots` : "—"}
      />
    </div>
  );
}

function MiniStat({
  icon,
  label,
  value,
  subValue,
}: {
  icon: ReactNode;
  label: string;
  value: ReactNode;
  subValue: ReactNode;
}) {
  return (
    <div className="space-y-1 rounded-md border border-border p-2">
      <div className="flex items-center gap-2">
        {icon}
        <div className="text-xs text-muted-foreground">{label}</div>
      </div>
      <div className="text-lg font-semibold leading-none">{value}</div>
      <div className="truncate text-xs text-muted-foreground">{subValue}</div>
    </div>
  );
}
