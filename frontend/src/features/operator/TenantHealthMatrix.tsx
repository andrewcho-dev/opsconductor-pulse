import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { RefreshCw, AlertTriangle, CheckCircle2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { fetchTenantsSummary, type TenantSummary } from "@/services/api/tenants";
import { fetchSubscriptions } from "@/services/api/operator";
import TenantActivitySparkline from "./TenantActivitySparkline";

// DataTable not used: TenantHealthMatrix uses a custom grid layout with
// color-coded cells and visual indicators that don't map to standard table columns.

type SortKey = "alerts" | "devices" | "lastActive" | "name";

function formatRelativeTime(value: string | null): string {
  if (!value) return "Never";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown";
  const diffSeconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
  if (diffSeconds < 60) return `${diffSeconds}s ago`;
  const minutes = Math.floor(diffSeconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function TenantHealthBar({ onlinePct }: { onlinePct: number }) {
  const color = onlinePct >= 90 ? "#22c55e" : onlinePct >= 70 ? "#f59e0b" : "#ef4444";
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-24 overflow-hidden rounded bg-gray-200 dark:bg-gray-700">
        <div
          className="h-full rounded transition-all"
          style={{ width: `${Math.max(0, Math.min(100, onlinePct))}%`, backgroundColor: color }}
        />
      </div>
      <span className="text-sm tabular-nums" style={{ color }}>
        {onlinePct.toFixed(0)}%
      </span>
    </div>
  );
}

export default function TenantHealthMatrix() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState<SortKey>("alerts");

  const { data: tenantsData, isFetching } = useQuery({
    queryKey: ["operator-tenants-health"],
    queryFn: fetchTenantsSummary,
    refetchInterval: 30000,
  });

  const { data: subscriptionData } = useQuery({
    queryKey: ["operator-subscriptions-health-matrix"],
    queryFn: () => fetchSubscriptions({ limit: 500 }),
    refetchInterval: 60000,
  });

  const subscriptionByTenant = useMemo(() => {
    const map = new Map<string, { type: string; status: string }>();
    for (const sub of subscriptionData?.subscriptions ?? []) {
      if (!map.has(sub.tenant_id)) {
        map.set(sub.tenant_id, {
          type: sub.subscription_type,
          status: sub.status,
        });
      }
    }
    return map;
  }, [subscriptionData?.subscriptions]);

  const rows = useMemo(() => {
    const tenants = tenantsData?.tenants ?? [];
    const needle = search.trim().toLowerCase();
    const filtered = tenants.filter((tenant) => {
      if (!needle) return true;
      return (
        tenant.tenant_id.toLowerCase().includes(needle) ||
        tenant.name.toLowerCase().includes(needle)
      );
    });

    return filtered.sort((a, b) => {
      if (sortBy === "name") {
        return a.name.localeCompare(b.name);
      }
      if (sortBy === "devices") {
        return b.device_count - a.device_count;
      }
      if (sortBy === "lastActive") {
        const aTime = a.last_activity ? new Date(a.last_activity).getTime() : 0;
        const bTime = b.last_activity ? new Date(b.last_activity).getTime() : 0;
        return bTime - aTime;
      }
      return b.open_alerts - a.open_alerts;
    });
  }, [search, sortBy, tenantsData?.tenants]);

  const getRowClass = (tenant: TenantSummary) => {
    const onlinePct = tenant.device_count > 0 ? (tenant.online_count / tenant.device_count) * 100 : 0;
    if (tenant.open_alerts > 5) return "bg-red-950/20";
    if (onlinePct < 70) return "bg-yellow-950/20";
    return "";
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="text-xl font-semibold">Tenant Health Matrix</div>
        <div className="flex items-center gap-2">
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search tenants..."
            className="h-8 w-56"
          />
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortKey)}
            className="h-8 rounded border border-border bg-background px-2 text-sm"
          >
            <option value="alerts">Sort: Alerts</option>
            <option value="devices">Sort: Devices</option>
            <option value="lastActive">Sort: Last Active</option>
            <option value="name">Sort: Tenant Name</option>
          </select>
          <div className="flex items-center gap-1 text-sm text-muted-foreground">
            <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? "animate-spin" : ""}`} />
            <span>↻ 30s</span>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full min-w-[980px] text-sm">
          <thead className="bg-muted/40 text-sm uppercase tracking-wide text-muted-foreground">
            <tr>
              <th className="px-3 py-2 text-left">Tenant</th>
              <th className="px-3 py-2 text-left">Devices</th>
              <th className="px-3 py-2 text-left">Activity</th>
              <th className="px-3 py-2 text-left">Device Health</th>
              <th className="px-3 py-2 text-left">Alerts</th>
              <th className="px-3 py-2 text-left">Last Active</th>
              <th className="px-3 py-2 text-left">Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((tenant) => {
              const onlinePct = tenant.device_count > 0 ? (tenant.online_count / tenant.device_count) * 100 : 0;
              const sub = subscriptionByTenant.get(tenant.tenant_id);
              return (
                <tr
                  key={tenant.tenant_id}
                  className={`cursor-pointer border-t transition-colors hover:bg-muted/50 ${getRowClass(tenant)}`}
                  onClick={() => navigate(`/operator/tenants/${tenant.tenant_id}`)}
                >
                  <td className="px-3 py-2">
                    <div className="font-semibold">{tenant.tenant_id}</div>
                    <div className="text-sm text-muted-foreground">{tenant.name}</div>
                    <Badge variant="outline" className="mt-1">
                      {sub?.type ?? "STANDARD"}
                    </Badge>
                  </td>
                  <td className="px-3 py-2 tabular-nums">
                    {tenant.online_count}/{tenant.device_count}
                  </td>
                  <td className="px-3 py-2">
                    <TenantActivitySparkline tenantId={tenant.tenant_id} />
                  </td>
                  <td className="px-3 py-2">
                    <TenantHealthBar onlinePct={onlinePct} />
                  </td>
                  <td className="px-3 py-2">
                    {tenant.open_alerts === 0 ? (
                      <div className="flex items-center gap-1 text-gray-500">
                        <CheckCircle2 className="h-4 w-4" />
                        <span>none</span>
                      </div>
                    ) : tenant.open_alerts <= 5 ? (
                      <div className="flex items-center gap-1 text-status-warning">
                        <AlertTriangle className="h-4 w-4" />
                        <span>{tenant.open_alerts} open</span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-1 text-status-critical">
                        <span className="inline-block h-2.5 w-2.5 rounded-full bg-status-critical" />
                        <span>{tenant.open_alerts} open</span>
                      </div>
                    )}
                  </td>
                  <td className="px-3 py-2 text-sm text-muted-foreground">
                    {formatRelativeTime(tenant.last_activity)}
                  </td>
                  <td className="px-3 py-2">
                    <Badge variant={tenant.status === "ACTIVE" ? "default" : "destructive"}>
                      {sub?.status ?? tenant.status}
                    </Badge>
                  </td>
                </tr>
              );
            })}
            {rows.length === 0 && (
              <tr>
                <td className="px-3 py-6 text-center text-sm text-muted-foreground" colSpan={7}>
                  No tenants match your filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
