import { Link } from "react-router-dom";
import { PageHeader } from "@/components/shared";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { useSites } from "@/hooks/use-sites";

export default function SitesPage({ embedded }: { embedded?: boolean }) {
  const { data, isLoading, error } = useSites();
  const sites = data?.sites ?? [];

  return (
    <div className="space-y-4">
      {!embedded && (
        <PageHeader title="Sites" description={isLoading ? "Loading..." : `${data?.total ?? 0} sites`} />
      )}

      {error ? (
        <div className="text-destructive">Failed to load sites: {(error as Error).message}</div>
      ) : isLoading ? (
        <div className="grid gap-3 md:grid-cols-2">
          {[1, 2, 3, 4].map((n) => (
            <Skeleton key={n} className="h-36" />
          ))}
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {sites.map((site) => (
            <Link
              key={site.site_id}
              to={`/sites/${site.site_id}`}
              className="block rounded-md border border-border p-4 text-left hover:bg-muted/40 transition-colors"
            >
              <div className="text-lg font-semibold">{site.name}</div>
              {site.location && <div className="text-sm text-muted-foreground">{site.location}</div>}
              <div className="mt-2 text-sm">
                <span className="text-status-online">{site.online_count} online</span>
                {" / "}
                <span className="text-status-stale">{site.stale_count} stale</span>
                {" / "}
                <span className="text-status-offline">{site.offline_count} offline</span>
              </div>
              <div className="mt-2 text-sm text-muted-foreground">{site.device_count} devices</div>
              <div className="mt-2">
                {site.active_alert_count > 0 ? (
                  <Badge variant="destructive">{site.active_alert_count} Active Alerts</Badge>
                ) : (
                  <Badge variant="secondary">No Active Alerts</Badge>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
