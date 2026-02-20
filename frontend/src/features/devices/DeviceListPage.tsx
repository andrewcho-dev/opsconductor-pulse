import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader, EmptyState } from "@/components/shared";
import { useDevices } from "@/hooks/use-devices";
import {
  Building2,
  ChevronLeft,
  ChevronRight,
  Cpu,
  Layers,
  LayoutTemplate,
  MapPin,
  Radio,
  Wrench,
} from "lucide-react";
import { fetchSites } from "@/services/api/sites";
import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { DeviceActions } from "./DeviceActions";
import type { Device } from "@/services/api/types";
import { AddDeviceModal } from "./AddDeviceModal";
import { useAlerts } from "@/hooks/use-alerts";
import { DeviceDetailPane } from "./DeviceDetailPane";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";

interface DeviceListFilters {
  limit: number;
  offset: number;
  status?: string;
  q: string;
  site_id?: string;
}

const FLEET_LINKS = [
  { label: "Sites", href: "/sites", icon: Building2 },
  { label: "Templates", href: "/templates", icon: LayoutTemplate },
  { label: "Groups", href: "/device-groups", icon: Layers },
  { label: "Map", href: "/map", icon: MapPin },
  { label: "Updates", href: "/updates", icon: Radio },
  { label: "Tools", href: "/fleet/tools", icon: Wrench },
] as const;

function statusDot(status: string) {
  if (status === "ONLINE") return "bg-status-online";
  if (status === "STALE") return "bg-status-stale";
  return "bg-status-offline";
}

function formatTimeAgo(input?: string | null) {
  if (!input) return "never";
  const deltaMs = Date.now() - new Date(input).getTime();
  if (!Number.isFinite(deltaMs) || deltaMs < 0) return "just now";
  const mins = Math.floor(deltaMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export default function DeviceListPage() {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<DeviceListFilters>({
    limit: 25,
    offset: 0,
    status: undefined,
    q: "",
    site_id: undefined,
  });
  const [selectedDeviceId, setSelectedDeviceId] = useState<string | null>(null);
  const [addOpen, setAddOpen] = useState(false);
  const [searchInput, setSearchInput] = useState("");
  const debouncedSearch = useDebouncedValue(searchInput, 300);
  useEffect(() => {
    setFilters((prev) => ({ ...prev, q: debouncedSearch, offset: 0 }));
  }, [debouncedSearch]);
  const { data, isLoading, error } = useDevices({
    limit: filters.limit,
    offset: filters.offset,
    status: filters.status,
    search: debouncedSearch,
    q: debouncedSearch,
    site_id: filters.site_id,
  });
  const { data: sitesData } = useQuery({
    queryKey: ["sites"],
    queryFn: fetchSites,
  });
  const { data: openAlertsData } = useAlerts("OPEN", 200, 0);

  const devices = data?.devices || [];
  const totalCount = data?.total ?? 0;
  const selectedDevice = devices.find((d) => d.device_id === selectedDeviceId) ?? null;
  const alertCountByDevice = useMemo(() => {
    const counts = new Map<string, number>();
    for (const alert of openAlertsData?.alerts ?? []) {
      counts.set(alert.device_id, (counts.get(alert.device_id) ?? 0) + 1);
    }
    return counts;
  }, [openAlertsData?.alerts]);
  const statusCounts = useMemo(() => {
    const counts = { online: 0, stale: 0, offline: 0 };
    for (const d of devices) {
      if (d.status === "ONLINE") counts.online++;
      else if (d.status === "STALE") counts.stale++;
      else counts.offline++;
    }
    return counts;
  }, [devices]);

  const onDeviceClick = (device: Device) => {
    if (window.innerWidth < 1024) {
      navigate(`/devices/${device.device_id}`);
      return;
    }
    setSelectedDeviceId(device.device_id);
  };

  return (
    <div className="space-y-4">
      <PageHeader
        title="Devices"
        description={
          isLoading
            ? "Loading..."
            : `${totalCount} devices in your fleet`
        }
        action={
          <DeviceActions
            canCreate={true}
            createDisabled={false}
            onCreate={() => setAddOpen(true)}
            onGuidedSetup={() => navigate("/devices/wizard")}
            onImport={() => navigate("/devices/import")}
          />
        }
      />
      <AddDeviceModal
        open={addOpen}
        onClose={() => setAddOpen(false)}
        onCreated={async () => {}}
      />
      <div className="flex flex-wrap gap-1.5">
        {FLEET_LINKS.map((link) => {
          const Icon = link.icon;
          return (
            <Button key={link.href} variant="outline" size="sm" asChild className="h-7 text-xs">
              <Link to={link.href}>
                <Icon className="mr-1 h-3 w-3" />
                {link.label}
              </Link>
            </Button>
          );
        })}
      </div>

      {!isLoading && devices.length > 0 && (
        <div className="flex items-center gap-4 rounded-md border border-border px-3 py-2 text-sm">
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-status-online" />
            <span>{statusCounts.online} Online</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-status-stale" />
            <span>{statusCounts.stale} Stale</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-status-offline" />
            <span>{statusCounts.offline} Offline</span>
          </div>
          <span className="text-muted-foreground">|</span>
          <span className="text-muted-foreground">{totalCount} total devices</span>
        </div>
      )}

      {error ? (
        <div className="text-destructive">
          Failed to load devices: {(error as Error).message}
        </div>
      ) : isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : devices.length === 0 ? (
        <EmptyState
          title="No devices found"
          description="Devices will appear here once they connect and send data."
          icon={<Cpu className="h-12 w-12" />}
        />
      ) : (
        <div className="grid gap-4 lg:grid-cols-[380px_minmax(0,1fr)]">
          <div className="flex h-[calc(100vh-210px)] flex-col rounded-md border border-border">
            <div className="space-y-2 border-b border-border p-3">
              <input
                value={searchInput}
                onChange={(e) =>
                  setSearchInput(e.target.value)
                }
                placeholder="Search devices..."
                className="h-8 w-full rounded border border-border bg-background px-2 text-sm"
              />
              <div className="grid grid-cols-2 gap-2">
                <Select
                  value={filters.status ?? "all"}
                  onValueChange={(v) =>
                    setFilters((prev) => ({
                      ...prev,
                      status: v === "all" ? undefined : v,
                      offset: 0,
                    }))
                  }
                >
                  <SelectTrigger className="h-8">
                    <SelectValue placeholder="All Status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Status</SelectItem>
                    <SelectItem value="ONLINE">Online</SelectItem>
                    <SelectItem value="OFFLINE">Offline</SelectItem>
                    <SelectItem value="STALE">Stale</SelectItem>
                  </SelectContent>
                </Select>
                <Select
                  value={filters.site_id ?? "all"}
                  onValueChange={(v) =>
                    setFilters((prev) => ({
                      ...prev,
                      site_id: v === "all" ? undefined : v,
                      offset: 0,
                    }))
                  }
                >
                  <SelectTrigger className="h-8">
                    <SelectValue placeholder="All Sites" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Sites</SelectItem>
                    {(sitesData?.sites ?? []).map((site) => (
                      <SelectItem key={site.site_id} value={site.site_id}>
                        {site.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="flex-1 space-y-2 overflow-auto p-2">
              {devices.map((device) => {
                const isSelected = selectedDevice?.device_id === device.device_id;
                const openAlerts = alertCountByDevice.get(device.device_id) ?? 0;
                return (
                  <Button
                    key={device.device_id}
                    type="button"
                    onClick={() => onDeviceClick(device)}
                    variant="ghost"
                    className={`h-auto w-full rounded border p-2 text-left justify-start transition-colors ${
                      isSelected
                        ? "border-l-2 border-l-primary bg-primary/10 border-primary"
                        : "border-border hover:bg-accent"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className={`h-2.5 w-2.5 rounded-full ${statusDot(device.status)}`} />
                        <span className="font-semibold">{device.device_id}</span>
                      </div>
                      <span className="text-sm text-muted-foreground">
                        {formatTimeAgo(device.last_seen_at)}
                      </span>
                    </div>
                    <div className="mt-1 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-muted-foreground">
                          {(
                            device.template?.name ??
                            device.template_name ??
                            (device as any).device_type ??
                            device.model ??
                            "—"
                          )}
                        </span>
                        {device.plan_id ? (
                          <Badge variant="outline" className="h-5 text-xs">
                            {device.plan_id}
                          </Badge>
                        ) : (
                          <span className="text-xs text-muted-foreground">—</span>
                        )}
                      </div>
                      {openAlerts > 0 && (
                        <Badge variant="destructive" className="h-5 min-w-5 text-xs">
                          {openAlerts}
                        </Badge>
                      )}
                    </div>
                  </Button>
                );
              })}
            </div>

            <div className="flex items-center justify-between border-t border-border p-2">
              <Button
                type="button"
                onClick={() =>
                  setFilters((prev) => ({
                    ...prev,
                    offset: Math.max(0, prev.offset - prev.limit),
                  }))
                }
                disabled={filters.offset === 0}
                variant="outline"
                size="icon-sm"
                aria-label="Previous page"
              >
                <ChevronLeft className="h-3.5 w-3.5" />
              </Button>
              <Button
                type="button"
                onClick={() =>
                  setFilters((prev) => ({
                    ...prev,
                    offset: prev.offset + prev.limit,
                  }))
                }
                disabled={filters.offset + filters.limit >= totalCount}
                variant="outline"
                size="icon-sm"
                aria-label="Next page"
              >
                <ChevronRight className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>

          <div className="hidden h-[calc(100vh-210px)] overflow-hidden rounded-md border border-border lg:block">
            {selectedDeviceId ? (
              <DeviceDetailPane deviceId={selectedDeviceId} />
            ) : (
              <div className="flex h-full items-center justify-center text-muted-foreground">
                Select a device to view details →
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
