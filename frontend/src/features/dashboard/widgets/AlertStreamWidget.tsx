import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { SeverityBadge } from "@/components/shared";
import { useAlertStore } from "@/stores/alert-store";
import { useUIStore } from "@/stores/ui-store";
import { useAlerts } from "@/hooks/use-alerts";
import { Bell } from "lucide-react";
import { Link } from "react-router-dom";
import { memo } from "react";

function AlertStreamWidgetInner() {
  // Live data from WebSocket (via Zustand store)
  const hasWsData = useAlertStore((s) => s.hasWsData);
  const liveAlerts = useAlertStore((s) => s.liveAlerts);
  const lastWsUpdate = useAlertStore((s) => s.lastWsUpdate);
  const wsStatus = useUIStore((s) => s.wsStatus);

  // Fallback: REST data via TanStack Query
  const { data: restData, isLoading: restLoading } = useAlerts("OPEN", 50, 0);

  // Prefer WS data if available
  const alerts = hasWsData ? liveAlerts : (restData?.alerts || []);
  const isLoading = !hasWsData && restLoading;

  // Format relative time for last update
  const lastUpdateText = lastWsUpdate
    ? `${Math.round((Date.now() - lastWsUpdate) / 1000)}s ago`
    : null;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div className="flex items-center gap-2">
          <CardTitle className="text-lg">Open Alerts</CardTitle>
          {wsStatus === "connected" && (
            <Badge
              variant="outline"
              className="text-[10px] text-green-700 border-green-200 dark:text-green-400 dark:border-green-700/50"
            >
              LIVE
            </Badge>
          )}
        </div>
        <div className="text-xs text-muted-foreground">
          {lastUpdateText && `Updated ${lastUpdateText}`}
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
        ) : alerts.length === 0 ? (
          <div className="flex flex-col items-center py-8 text-center">
            <Bell className="h-8 w-8 text-muted-foreground mb-2" />
            <p className="text-sm text-muted-foreground">No open alerts</p>
          </div>
        ) : (
          <div className="space-y-1">
            {alerts.slice(0, 20).map((a) => (
              <div
                key={a.alert_id}
                className="flex items-center gap-3 py-2 px-2 rounded-md hover:bg-accent/50 transition-colors text-sm"
              >
                <SeverityBadge severity={a.severity} className="shrink-0" />
                <Link
                  to={`/devices/${a.device_id}`}
                  className="font-mono text-xs text-primary hover:underline shrink-0"
                >
                  {a.device_id}
                </Link>
                <span className="truncate flex-1">{a.summary}</span>
                <span className="text-xs text-muted-foreground shrink-0 hidden md:inline">
                  {a.alert_type}
                </span>
              </div>
            ))}
            {alerts.length > 20 && (
              <div className="pt-2 text-center">
                <Link
                  to="/alerts"
                  className="text-xs text-primary hover:underline"
                >
                  View all {alerts.length} alerts
                </Link>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export const AlertStreamWidget = memo(AlertStreamWidgetInner);
