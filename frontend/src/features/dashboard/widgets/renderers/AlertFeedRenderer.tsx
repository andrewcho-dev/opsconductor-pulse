import { memo } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { SeverityBadge } from "@/components/shared";
import { useAlertStore } from "@/stores/alert-store";
import { useUIStore } from "@/stores/ui-store";
import { useAlerts } from "@/hooks/use-alerts";
import { Link } from "react-router-dom";
import type { WidgetRendererProps } from "../widget-registry";

function asNumber(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function asString(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function AlertFeedRendererInner({ config }: WidgetRendererProps) {
  const maxItems = asNumber(config.max_items, 20);
  const severityFilter = asString(config.severity_filter, "").trim();

  // Live data from WebSocket store
  const hasWsData = useAlertStore((s) => s.hasWsData);
  const liveAlerts = useAlertStore((s) => s.liveAlerts);
  const wsStatus = useUIStore((s) => s.wsStatus);

  // REST fallback
  const { data: restData, isLoading: restLoading } = useAlerts("OPEN", 50, 0);

  const allAlerts = hasWsData ? liveAlerts : (restData?.alerts || []);
  const isLoading = !hasWsData && restLoading;

  const filtered = severityFilter
    ? allAlerts.filter((a) => String(a.severity) === severityFilter)
    : allAlerts;

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3, 4, 5].map((i) => (
          <Skeleton key={i} className="h-8 w-full" />
        ))}
      </div>
    );
  }

  if (filtered.length === 0) {
    return (
      <div className="flex flex-col items-center py-8 text-center">
        <p className="text-sm text-muted-foreground">No open alerts</p>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {wsStatus === "connected" && (
        <div className="text-[10px] text-muted-foreground pb-1">LIVE</div>
      )}
      {filtered.slice(0, maxItems).map((a) => (
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
      {filtered.length > maxItems && (
        <div className="pt-2 text-center">
          <Link to="/alerts" className="text-xs text-primary hover:underline">
            View all {filtered.length} alerts
          </Link>
        </div>
      )}
    </div>
  );
}

export default memo(AlertFeedRendererInner);

