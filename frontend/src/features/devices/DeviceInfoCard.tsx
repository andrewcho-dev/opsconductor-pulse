import { Card, CardContent } from "@/components/ui/card";
import { StatusBadge } from "@/components/shared";
import { Skeleton } from "@/components/ui/skeleton";
import type { Device } from "@/services/api/types";
import { Cpu, MapPin, Clock } from "lucide-react";

interface DeviceInfoCardProps {
  device: Device | undefined;
  isLoading: boolean;
}

function formatTimestamp(ts: string | null): string {
  if (!ts) return "Never";
  try {
    return new Date(ts).toLocaleString();
  } catch {
    return ts;
  }
}

export function DeviceInfoCard({ device, isLoading }: DeviceInfoCardProps) {
  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="space-y-3">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-4 w-64" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!device) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-muted-foreground">Device not found.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <Cpu className="h-8 w-8 text-muted-foreground shrink-0" />
            <div>
              <h2 className="text-xl font-bold font-mono">{device.device_id}</h2>
              <div className="flex items-center gap-2 text-sm text-muted-foreground mt-1">
                <MapPin className="h-3.5 w-3.5" />
                <span>{device.site_id}</span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <StatusBadge status={device.status} />
          </div>
        </div>

        <div className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Clock className="h-3.5 w-3.5 shrink-0" />
            <span>Last seen: {formatTimestamp(device.last_seen_at)}</span>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground">
            <Clock className="h-3.5 w-3.5 shrink-0" />
            <span>Last heartbeat: {formatTimestamp(device.last_heartbeat_at)}</span>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground">
            <Clock className="h-3.5 w-3.5 shrink-0" />
            <span>Last telemetry: {formatTimestamp(device.last_telemetry_at)}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
