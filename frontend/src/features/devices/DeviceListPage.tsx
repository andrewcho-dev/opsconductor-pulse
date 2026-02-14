import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader, EmptyState } from "@/components/shared";
import { useDevices } from "@/hooks/use-devices";
import { Cpu } from "lucide-react";
import { fetchSites } from "@/services/api/sites";
import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { DeviceActions } from "./DeviceActions";
import type { Device } from "@/services/api/types";
import { AddDeviceModal } from "./AddDeviceModal";
import { useAlerts } from "@/hooks/use-alerts";
import { DeviceDetailPane } from "./DeviceDetailPane";

interface DeviceListFilters {
  limit: number;
  offset: number;
  status?: string;
  q: string;
  site_id?: string;
}

function statusDot(status: string) {
  if (status === "ONLINE") return "bg-green-500";
  if (status === "STALE") return "bg-yellow-500";
  return "bg-red-500";
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
  const { data, isLoading, error } = useDevices({
    limit: filters.limit,
    offset: filters.offset,
    status: filters.status,
    q: filters.q,
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
                value={filters.q}
                onChange={(e) =>
                  setFilters((prev) => ({ ...prev, q: e.target.value, offset: 0 }))
                }
                placeholder="Search devices..."
                className="h-8 w-full rounded border border-border bg-background px-2 text-sm"
              />
              <div className="grid grid-cols-2 gap-2">
                <select
                  value={filters.status ?? ""}
                  onChange={(e) =>
                    setFilters((prev) => ({
                      ...prev,
                      status: e.target.value || undefined,
                      offset: 0,
                    }))
                  }
                  className="h-8 rounded border border-border bg-background px-2 text-sm"
                >
                  <option value="">All Status</option>
                  <option value="ONLINE">Online</option>
                  <option value="OFFLINE">Offline</option>
                  <option value="STALE">Stale</option>
                </select>
                <select
                  value={filters.site_id ?? ""}
                  onChange={(e) =>
                    setFilters((prev) => ({
                      ...prev,
                      site_id: e.target.value || undefined,
                      offset: 0,
                    }))
                  }
                  className="h-8 rounded border border-border bg-background px-2 text-sm"
                >
                  <option value="">All Sites</option>
                  {(sitesData?.sites ?? []).map((site) => (
                    <option key={site.site_id} value={site.site_id}>
                      {site.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex-1 space-y-2 overflow-auto p-2">
              {devices.map((device) => {
                const isSelected = selectedDevice?.device_id === device.device_id;
                const openAlerts = alertCountByDevice.get(device.device_id) ?? 0;
                return (
                  <button
                    key={device.device_id}
                    onClick={() => onDeviceClick(device)}
                    className={`w-full rounded border p-2 text-left transition-colors ${
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
                      <span className="text-xs text-muted-foreground">
                        {formatTimeAgo(device.last_seen_at)}
                      </span>
                    </div>
                    <div className="mt-1 flex items-center justify-between">
                      <span className="text-xs text-muted-foreground">
                        {device.model || "unknown-type"}
                      </span>
                      {openAlerts > 0 && (
                        <Badge variant="destructive" className="h-5 min-w-5 text-xs">
                          {openAlerts}
                        </Badge>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>

            <div className="flex items-center justify-between border-t border-border p-2">
              <button
                onClick={() =>
                  setFilters((prev) => ({
                    ...prev,
                    offset: Math.max(0, prev.offset - prev.limit),
                  }))
                }
                disabled={filters.offset === 0}
                className="rounded border border-border px-2 py-1 text-xs disabled:opacity-50"
              >
                {"< Prev"}
              </button>
              <button
                onClick={() =>
                  setFilters((prev) => ({
                    ...prev,
                    offset: prev.offset + prev.limit,
                  }))
                }
                disabled={filters.offset + filters.limit >= totalCount}
                className="rounded border border-border px-2 py-1 text-xs disabled:opacity-50"
              >
                {"Next >"}
              </button>
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
