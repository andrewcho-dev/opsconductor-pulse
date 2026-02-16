import { useQuery } from "@tanstack/react-query";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchFleetSummary } from "@/services/api/devices";
import type { WidgetRendererProps } from "../widget-registry";

export default function DeviceCountRenderer(_props: WidgetRendererProps) {
  const { data, isLoading } = useQuery({
    queryKey: ["widget-device-count"],
    queryFn: fetchFleetSummary,
    refetchInterval: 30000,
  });

  const total =
    data?.total ??
    data?.total_devices ??
    ((data?.ONLINE ?? 0) + (data?.STALE ?? 0) + (data?.OFFLINE ?? 0));
  const online = data?.online ?? data?.ONLINE ?? 0;
  const offline = data?.offline ?? data?.OFFLINE ?? 0;

  if (isLoading) return <Skeleton className="h-16 w-full" />;

  return (
    <div className="h-full flex items-center justify-between px-2">
      <div>
        <div className="text-3xl font-bold">{(total ?? 0).toLocaleString()}</div>
        <div className="text-xs text-muted-foreground">Total devices</div>
      </div>
      <div className="text-right text-xs text-muted-foreground">
        <div>{online.toLocaleString()} online</div>
        <div>{offline.toLocaleString()} offline</div>
      </div>
    </div>
  );
}

