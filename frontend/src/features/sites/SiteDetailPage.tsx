import { useParams } from "react-router-dom";
import { PageHeader, SeverityBadge } from "@/components/shared";
import { Skeleton } from "@/components/ui/skeleton";
import { useSiteSummary } from "@/hooks/use-sites";

export default function SiteDetailPage() {
  const { siteId = "" } = useParams();
  const { data, isLoading, error } = useSiteSummary(siteId);

  return (
    <div className="space-y-4">
      <PageHeader
        title={data?.site?.name || "Site"}
        description={data?.site?.location || siteId}
        breadcrumbs={[
          { label: "Sites", href: "/sites" },
          { label: data?.site?.name || siteId },
        ]}
      />

      {error ? (
        <div className="text-destructive">Failed to load site: {(error as Error).message}</div>
      ) : isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          <div className="rounded-md border border-border p-4">
            <div className="mb-2 text-sm font-medium">Devices ({data?.device_count ?? 0})</div>
            <div className="space-y-2">
              {(data?.devices ?? []).map((device) => (
                <div key={device.device_id} className="flex items-center justify-between text-sm">
                  <span>{device.name || device.device_id}</span>
                  <span className="text-muted-foreground">{device.status}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-md border border-border p-4">
            <div className="mb-2 text-sm font-medium">
              Active Alerts ({data?.active_alert_count ?? 0})
            </div>
            <div className="space-y-2">
              {(data?.active_alerts ?? []).map((alert) => (
                <div key={alert.id} className="flex items-center justify-between text-sm">
                  <span className="truncate pr-2">{alert.summary}</span>
                  <SeverityBadge severity={alert.severity} />
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
