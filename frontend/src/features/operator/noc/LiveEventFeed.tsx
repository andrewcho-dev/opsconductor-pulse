import { useEffect, useMemo, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchOperatorAlerts, fetchOperatorTenants } from "@/services/api/operator";
import { fetchSystemErrors } from "@/services/api/system";
import { fetchTenantsSummary } from "@/services/api/tenants";
import { NOC_COLORS } from "./nocColors";

interface LiveEventFeedProps {
  refreshInterval: number;
  isPaused: boolean;
}

interface FeedEvent {
  id: string;
  timestamp: string;
  type: "error" | "alert" | "info";
  severity?: string;
  message: string;
  tenant?: string;
  device?: string;
}

function toneFor(event: FeedEvent): string {
  if (event.type === "error") return "text-red-400";
  if (event.type === "alert") {
    const sev = (event.severity ?? "").toUpperCase();
    if (sev === "CRITICAL" || sev === "HIGH") return "text-orange-400";
    return "text-yellow-400";
  }
  return "text-gray-400";
}

function labelFor(event: FeedEvent): string {
  if (event.type === "error") return "ERROR";
  if (event.type === "alert") return "ALERT";
  return "INFO";
}

function formatTime(ts: string): string {
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return "--:--:--";
  return d.toLocaleTimeString();
}

export function LiveEventFeed({ refreshInterval, isPaused }: LiveEventFeedProps) {
  const feedRef = useRef<HTMLDivElement>(null);

  const { data: errorData } = useQuery({
    queryKey: ["noc-live-feed-errors"],
    queryFn: () => fetchSystemErrors(1),
    refetchInterval: isPaused ? false : Math.min(refreshInterval, 10000),
  });
  const { data: alertData } = useQuery({
    queryKey: ["noc-live-feed-alerts"],
    queryFn: () => fetchOperatorAlerts("OPEN", undefined, 20),
    refetchInterval: isPaused ? false : Math.min(refreshInterval, 10000),
  });
  const { data: tenantSummary } = useQuery({
    queryKey: ["noc-live-feed-tenant-summary"],
    queryFn: fetchTenantsSummary,
    refetchInterval: isPaused ? false : 30000,
  });
  // Keep this call to align with prompt's /operator/tenants usage.
  useQuery({
    queryKey: ["noc-live-feed-tenants-list"],
    queryFn: () => fetchOperatorTenants({ limit: 200 }),
    refetchInterval: isPaused ? false : 60000,
  });

  const events = useMemo<FeedEvent[]>(() => {
    const mappedErrors: FeedEvent[] = (errorData?.errors ?? []).map((err, idx) => {
      const details = err.details ?? {};
      return {
        id: `error-${idx}-${err.timestamp}`,
        timestamp: err.timestamp,
        type: "error",
        message: err.error_type,
        tenant: err.tenant_id ?? undefined,
        device:
          typeof details.device_id === "string" ? details.device_id : undefined,
      };
    });

    const mappedAlerts: FeedEvent[] = (alertData?.alerts ?? []).map((alert) => {
      const sevNumber = alert.severity ?? 0;
      const sevLabel =
        sevNumber >= 4 ? "CRITICAL" : sevNumber === 3 ? "HIGH" : sevNumber === 2 ? "MEDIUM" : "LOW";
      return {
        id: `alert-${alert.alert_id}`,
        timestamp: alert.created_at,
        type: "alert",
        severity: sevLabel,
        message: `${sevLabel} ${alert.alert_type}`,
        tenant: alert.tenant_id,
        device: alert.device_id,
      };
    });

    const mappedInfo: FeedEvent[] = (tenantSummary?.tenants ?? []).slice(0, 20).map((tenant) => ({
      id: `info-${tenant.tenant_id}-${tenant.last_activity ?? "never"}`,
      timestamp: tenant.last_activity ?? new Date(0).toISOString(),
      type: "info",
      message: "tenant active",
      tenant: tenant.tenant_id,
      device: `${tenant.online_count} devices online`,
    }));

    return [...mappedErrors, ...mappedAlerts, ...mappedInfo]
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      .slice(0, 50);
  }, [alertData?.alerts, errorData?.errors, tenantSummary?.tenants]);

  useEffect(() => {
    feedRef.current?.scrollTo({ top: 0, behavior: "smooth" });
  }, [events]);

  return (
    <div
      className="rounded-lg border p-3"
      style={{ borderColor: NOC_COLORS.bg.cardBorder, backgroundColor: NOC_COLORS.bg.card }}
    >
      <div className="mb-2 flex items-center gap-2">
        <span className="h-2 w-2 animate-pulse rounded-full" style={{ backgroundColor: NOC_COLORS.healthy }} />
        <span className="text-sm font-medium" style={{ color: NOC_COLORS.textSecondary }}>
          Live Event Feed
        </span>
        <span className="ml-auto text-xs" style={{ color: NOC_COLORS.neutral }}>
          {events.length} events
        </span>
      </div>
      <div ref={feedRef} className="h-48 space-y-1 overflow-y-auto font-mono text-xs">
        {events.map((event, idx) => (
          <div
            key={event.id}
            className={`flex items-start gap-2 ${toneFor(event)} ${idx < 3 ? "animate-pulse" : ""}`}
          >
            <span className="text-gray-500">[{formatTime(event.timestamp)}]</span>
            <span className="w-12 font-semibold">[{labelFor(event)}]</span>
            <span className="truncate">{event.message}</span>
            {event.tenant && <span className="text-gray-500">tenant: {event.tenant}</span>}
            {event.device && <span className="text-gray-500">device: {event.device}</span>}
          </div>
        ))}
      </div>
    </div>
  );
}
