import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { getDeviceUptime } from "@/services/api/devices";
import { UptimeBar } from "@/components/ui/UptimeBar";

interface DeviceUptimePanelProps {
  deviceId: string;
}

type UptimeRange = "24h" | "7d" | "30d";

export function DeviceUptimePanel({ deviceId }: DeviceUptimePanelProps) {
  const [range, setRange] = useState<UptimeRange>("24h");
  const { data } = useQuery({
    queryKey: ["device-uptime", deviceId, range],
    queryFn: () => getDeviceUptime(deviceId, range),
    enabled: !!deviceId,
  });

  const offlineSeconds = data?.offline_seconds ?? 0;
  const offlineMinutes = Math.round(offlineSeconds / 60);

  return (
    <div className="rounded-md border border-border p-3 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Uptime</h3>
        <div className="flex gap-1">
          {(["24h", "7d", "30d"] as const).map((option) => (
            <button
              key={option}
              type="button"
              className={`px-2 py-1 text-xs rounded border ${
                range === option ? "bg-primary text-primary-foreground border-primary" : "border-border"
              }`}
              onClick={() => setRange(option)}
            >
              {option}
            </button>
          ))}
        </div>
      </div>
      <UptimeBar uptimePct={data?.uptime_pct ?? 0} label={`Availability (${range})`} />
      <div className="grid grid-cols-3 gap-2 text-xs">
        <div>
          <div className="text-muted-foreground">Uptime %</div>
          <div className="font-semibold">{(data?.uptime_pct ?? 0).toFixed(1)}%</div>
        </div>
        <div>
          <div className="text-muted-foreground">Offline Duration</div>
          <div className="font-semibold">{offlineMinutes} min</div>
        </div>
        <div>
          <div className="text-muted-foreground">Status</div>
          <Badge variant={(data?.status ?? "online") === "online" ? "default" : "destructive"}>
            {(data?.status ?? "online").toUpperCase()}
          </Badge>
        </div>
      </div>
    </div>
  );
}
