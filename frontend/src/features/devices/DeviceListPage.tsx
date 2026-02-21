import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { type ColumnDef, type PaginationState } from "@tanstack/react-table";
import { Cpu } from "lucide-react";
import { PageHeader, EmptyState } from "@/components/shared";
import { DataTable } from "@/components/ui/data-table";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { DeviceActions } from "./DeviceActions";
import { AddDeviceModal } from "./AddDeviceModal";
import { useDevices } from "@/hooks/use-devices";
import { useAlerts } from "@/hooks/use-alerts";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { fetchSites } from "@/services/api/sites";
import { listTemplates } from "@/services/api/templates";
import type { Device } from "@/services/api/types";

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

export default function DeviceListPage({ embedded }: { embedded?: boolean }) {
  const navigate = useNavigate();
  const [addOpen, setAddOpen] = useState(false);
  const [searchInput, setSearchInput] = useState("");
  const debouncedSearch = useDebouncedValue(searchInput, 300);
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [siteFilter, setSiteFilter] = useState<string | undefined>();
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 25,
  });

  // Reset to first page when filters change
  useEffect(() => {
    setPagination((prev) => ({ ...prev, pageIndex: 0 }));
  }, [debouncedSearch, statusFilter, siteFilter]);

  const { data, isLoading, error } = useDevices({
    limit: pagination.pageSize,
    offset: pagination.pageIndex * pagination.pageSize,
    status: statusFilter,
    q: debouncedSearch || undefined,
    site_id: siteFilter,
  });

  const { data: sitesData } = useQuery({
    queryKey: ["sites"],
    queryFn: fetchSites,
  });

  const { data: templatesData } = useQuery({
    queryKey: ["templates-list"],
    queryFn: () => listTemplates(),
    staleTime: 60_000,
  });

  const { data: openAlertsData } = useAlerts("OPEN", 200, 0);

  const devices = data?.devices ?? [];
  const totalCount = data?.total ?? 0;

  const alertCountByDevice = useMemo(() => {
    const counts = new Map<string, number>();
    for (const alert of openAlertsData?.alerts ?? []) {
      counts.set(alert.device_id, (counts.get(alert.device_id) ?? 0) + 1);
    }
    return counts;
  }, [openAlertsData?.alerts]);

  const templateNameById = useMemo(() => {
    const map = new Map<number, string>();
    for (const t of templatesData ?? []) {
      map.set(t.id, t.name);
    }
    return map;
  }, [templatesData]);

  // Compute status counts from the current page of devices
  // (This is approximate — ideally backend would return summary counts)
  const statusCounts = useMemo(() => {
    const counts = { online: 0, stale: 0, offline: 0 };
    for (const d of devices) {
      if (d.status === "ONLINE") counts.online++;
      else if (d.status === "STALE") counts.stale++;
      else counts.offline++;
    }
    return counts;
  }, [devices]);

  const columns = useMemo<ColumnDef<Device>[]>(
    () => [
      {
        id: "status",
        header: "Status",
        accessorKey: "status",
        cell: ({ row }) => (
          <div className="flex items-center gap-2">
            <span className={`h-2.5 w-2.5 rounded-full ${statusDot(row.original.status)}`} />
            <span className="text-sm">{row.original.status}</span>
          </div>
        ),
      },
      {
        accessorKey: "device_id",
        header: "Device ID",
        cell: ({ row }) => <span className="font-medium">{row.original.device_id}</span>,
      },
      {
        id: "template",
        header: "Template",
        cell: ({ row }) => (
          <span className="text-sm">
            {row.original.template?.name ??
              (row.original.template_id != null ? templateNameById.get(row.original.template_id) : undefined) ??
              row.original.template_name ??
              row.original.model ??
              "—"}
          </span>
        ),
      },
      {
        accessorKey: "site_id",
        header: "Site",
        cell: ({ row }) => {
          const site = (sitesData?.sites ?? []).find((s) => s.site_id === row.original.site_id);
          return <span className="text-sm">{site?.name ?? row.original.site_id ?? "—"}</span>;
        },
      },
      {
        id: "last_seen",
        header: "Last Seen",
        accessorKey: "last_seen_at",
        cell: ({ row }) => (
          <span className="text-sm text-muted-foreground">{formatTimeAgo(row.original.last_seen_at)}</span>
        ),
      },
      {
        id: "fw_version",
        header: "Firmware",
        accessorKey: "fw_version",
        cell: ({ row }) => (
          <span className="font-mono text-sm text-muted-foreground">{row.original.fw_version ?? "—"}</span>
        ),
      },
      {
        id: "alerts",
        header: "Alerts",
        enableSorting: false,
        cell: ({ row }) => {
          const count = alertCountByDevice.get(row.original.device_id) ?? 0;
          return count > 0 ? (
            <Badge variant="destructive" className="text-xs">
              {count}
            </Badge>
          ) : null;
        },
      },
    ],
    [alertCountByDevice, sitesData?.sites, templateNameById]
  );

  const emptyState = (
    <EmptyState
      title="No devices found"
      description="Devices will appear here once they connect and send data."
      icon={<Cpu className="h-12 w-12" />}
    />
  );

  return (
    <div className="space-y-4">
      {!embedded && (
        <PageHeader
          title="Devices"
          description={isLoading ? "Loading..." : `${totalCount} devices in your fleet`}
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
      )}
      {embedded && (
        <div className="flex justify-end">
          <DeviceActions
            canCreate={true}
            createDisabled={false}
            onCreate={() => setAddOpen(true)}
            onGuidedSetup={() => navigate("/devices/wizard")}
            onImport={() => navigate("/devices/import")}
          />
        </div>
      )}

      <AddDeviceModal open={addOpen} onClose={() => setAddOpen(false)} onCreated={async () => {}} />

      {/* Health strip */}
      {!isLoading && totalCount > 0 && (
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
        <div className="text-destructive">Failed to load devices: {(error as Error).message}</div>
      ) : (
        <>
          {/* Filter bar */}
          <div className="flex flex-col gap-2 md:flex-row md:items-center">
            <Input
              placeholder="Search devices..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="md:max-w-[280px]"
            />
            <div className="flex gap-2">
              <Select value={statusFilter ?? "all"} onValueChange={(v) => setStatusFilter(v === "all" ? undefined : v)}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="All Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="ONLINE">Online</SelectItem>
                  <SelectItem value="OFFLINE">Offline</SelectItem>
                  <SelectItem value="STALE">Stale</SelectItem>
                </SelectContent>
              </Select>
              <Select value={siteFilter ?? "all"} onValueChange={(v) => setSiteFilter(v === "all" ? undefined : v)}>
                <SelectTrigger className="w-[180px]">
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

          {/* DataTable */}
          <DataTable
            columns={columns}
            data={devices}
            totalCount={totalCount}
            pagination={pagination}
            onPaginationChange={setPagination}
            isLoading={isLoading}
            emptyState={emptyState}
            onRowClick={(device) => navigate(`/devices/${device.device_id}`)}
          />
        </>
      )}
    </div>
  );
}
