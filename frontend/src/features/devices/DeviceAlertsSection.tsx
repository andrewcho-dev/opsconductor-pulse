import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { SeverityBadge } from "@/components/shared";
import { useDeviceAlerts } from "@/hooks/use-device-alerts";
import { formatTimestamp } from "@/lib/format";
import { Bell } from "lucide-react";
import { memo } from "react";

interface DeviceAlertsSectionProps {
  deviceId: string;
}

function DeviceAlertsSectionInner({ deviceId }: DeviceAlertsSectionProps) {
  const { data, isLoading } = useDeviceAlerts(deviceId, "OPEN", 50);
  const alerts = data?.alerts || [];

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-lg">Device Alerts</CardTitle>
        <Link
          to="/alerts"
          className="text-xs text-primary hover:underline"
        >
          View all alerts
        </Link>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
        ) : alerts.length === 0 ? (
          <div className="flex flex-col items-center py-6 text-center">
            <Bell className="h-6 w-6 text-muted-foreground mb-2" />
            <p className="text-sm text-muted-foreground">
              No open alerts for this device
            </p>
          </div>
        ) : (
          <div className="space-y-1">
            {alerts.map((a) => (
              <div
                key={a.alert_id}
                className="flex items-center gap-3 py-2 px-2 rounded-md hover:bg-accent/50 transition-colors text-sm"
              >
                <SeverityBadge severity={a.severity} className="shrink-0" />
                <span className="truncate flex-1">{a.summary}</span>
                <span className="text-xs text-muted-foreground shrink-0">
                  {a.alert_type}
                </span>
                <span className="text-xs text-muted-foreground shrink-0 hidden md:inline">
                  {formatTimestamp(a.created_at)}
                </span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export const DeviceAlertsSection = memo(DeviceAlertsSectionInner);
