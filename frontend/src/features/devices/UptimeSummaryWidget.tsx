import { useQuery } from "@tanstack/react-query";
import { getFleetUptimeSummary } from "@/services/api/devices";
import { UptimeBar } from "@/components/ui/UptimeBar";

export function UptimeSummaryWidget() {
  const { data } = useQuery({
    queryKey: ["fleet-uptime-summary"],
    queryFn: getFleetUptimeSummary,
    refetchInterval: 60_000,
  });

  return (
    <div className="rounded-md border border-border p-3 space-y-2">
      <h3 className="text-sm font-semibold">Fleet Availability</h3>
      <div className="text-2xl font-semibold">{(data?.avg_uptime_pct ?? 0).toFixed(1)}%</div>
      <UptimeBar uptimePct={data?.avg_uptime_pct ?? 0} />
      <div className="text-xs text-muted-foreground">
        {data?.online ?? 0} Online | {data?.offline ?? 0} Offline | {data?.total_devices ?? 0} Total
      </div>
    </div>
  );
}
