import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader, EmptyState } from "@/components/shared";
import { useDevices, useFleetSummary } from "@/hooks/use-devices";
import { Cpu, AlertTriangle } from "lucide-react";
import { getAllTags } from "@/services/api/devices";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/services/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DeviceActions } from "./DeviceActions";
import { DeviceFilters } from "./DeviceFilters";
import { DeviceTable } from "./DeviceTable";
import type { Device } from "@/services/api/types";
import { AddDeviceModal } from "./AddDeviceModal";
import { EditDeviceModal } from "./EditDeviceModal";
import { decommissionDevice } from "@/services/api/devices";
import { useQueryClient } from "@tanstack/react-query";

interface SubscriptionStatus {
  device_limit: number;
  active_device_count: number;
  devices_available: number;
  status: "TRIAL" | "ACTIVE" | "GRACE" | "SUSPENDED" | "EXPIRED";
}

interface SubscriptionsResponse {
  subscriptions: { status: SubscriptionStatus["status"] }[];
  summary: {
    total_device_limit: number;
    total_active_devices: number;
    total_available: number;
  };
}

function ProgressBar({ value }: { value: number }) {
  return (
    <div className="h-1.5 w-full rounded-full bg-muted">
      <div
        className="h-1.5 rounded-full bg-primary"
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  );
}

export default function DeviceListPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<{
    limit: number;
    offset: number;
    status?: string;
    tags: string[];
    q: string;
    site_id?: string;
  }>({
    limit: 100,
    offset: 0,
    status: undefined,
    tags: [],
    q: "",
    site_id: undefined,
  });
  const [viewMode, setViewMode] = useState<"list" | "grouped">("list");
  const [tagFilterOpen, setTagFilterOpen] = useState(false);
  const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>({});
  const [addOpen, setAddOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<Device | null>(null);
  const refreshDevices = async () => {
    await queryClient.invalidateQueries({ queryKey: ["devices"] });
    await queryClient.invalidateQueries({ queryKey: ["fleet-summary"] });
  };


  const {
    summary,
    isLoading: summaryLoading,
    error: summaryError,
    isConnected: summaryLiveConnected,
  } = useFleetSummary();
  const groupedCapExceeded = viewMode === "grouped" && (summary?.total ?? 0) > 500;
  const groupedModeActive = viewMode === "grouped" && !groupedCapExceeded;
  const deviceQueryParams = groupedModeActive
    ? {
        limit: 500,
        offset: 0,
        status: filters.status,
        tags: filters.tags,
        q: filters.q,
        site_id: filters.site_id,
      }
    : {
        limit: filters.limit,
        offset: filters.offset,
        status: filters.status,
        tags: filters.tags,
        q: filters.q,
        site_id: filters.site_id,
      };
  const { data, isLoading, error } = useDevices(deviceQueryParams);

  const { data: allTagsData } = useQuery({
    queryKey: ["tags"],
    queryFn: getAllTags,
  });
  const allTags = allTagsData?.tags ?? [];

  const { data: subscription } = useQuery({
    queryKey: ["subscription-status"],
    queryFn: async () => {
      const response = await apiGet<SubscriptionsResponse>("/customer/subscriptions");
      const statuses = response.subscriptions.map((sub) => sub.status);
      let status: SubscriptionStatus["status"] = "ACTIVE";
      if (statuses.includes("EXPIRED")) {
        status = "EXPIRED";
      } else if (statuses.includes("SUSPENDED")) {
        status = "SUSPENDED";
      } else if (statuses.includes("GRACE")) {
        status = "GRACE";
      } else if (statuses.includes("TRIAL") && !statuses.includes("ACTIVE")) {
        status = "TRIAL";
      }

      return {
        device_limit: response.summary.total_device_limit,
        active_device_count: response.summary.total_active_devices,
        devices_available: response.summary.total_available,
        status,
      };
    },
  });

  const devices = data?.devices || [];
  const totalCount = data?.total ?? 0;

  const toggleTag = (tag: string) => {
    setFilters((prev) => ({
      ...prev,
      tags: prev.tags.includes(tag)
        ? prev.tags.filter((t) => t !== tag)
        : [...prev.tags, tag],
      offset: 0,
    }));
  };

  const groupedDevices = useMemo(() => {
    const groups = new Map<string, Device[]>();
    const untagged: Device[] = [];
    for (const device of devices) {
      if (!device.tags || device.tags.length === 0) {
        untagged.push(device);
      } else {
        for (const tag of device.tags) {
          if (!groups.has(tag)) groups.set(tag, []);
          groups.get(tag)?.push(device);
        }
      }
    }
    const sorted = new Map([...groups.entries()].sort(([a], [b]) => a.localeCompare(b)));
    if (untagged.length > 0) sorted.set("(untagged)", untagged);
    return sorted;
  }, [devices]);

  useEffect(() => {
    if (!groupedModeActive) return;
    setCollapsedGroups((prev) => {
      const next: Record<string, boolean> = {};
      for (const [tag] of groupedDevices) {
        next[tag] = prev[tag] ?? false;
      }
      return next;
    });
  }, [groupedDevices, groupedModeActive]);

  const toggleGroup = (groupName: string) => {
    setCollapsedGroups((prev) => ({
      ...prev,
      [groupName]: !prev[groupName],
    }));
  };

  const toggleStatusFromWidget = (status: "ONLINE" | "STALE" | "OFFLINE") => {
    setFilters((prev) => ({
      ...prev,
      status: prev.status === status ? undefined : status,
      offset: 0,
    }));
  };

  const canCreate =
    subscription?.status !== "SUSPENDED" &&
    subscription?.status !== "EXPIRED";
  const createDisabled = subscription?.devices_available === 0;
  const usagePercent = subscription
    ? Math.round(
        (subscription.active_device_count / Math.max(subscription.device_limit, 1)) * 100
      )
    : 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Devices"
        description={
          isLoading
            ? "Loading..."
            : subscription
            ? `${totalCount} of ${subscription.device_limit} devices (${subscription.devices_available} available)`
            : `${totalCount} devices in your fleet`
        }
        action={
          <DeviceActions
            canCreate={canCreate}
            createDisabled={createDisabled}
            onCreate={() => setAddOpen(true)}
            onGuidedSetup={() => navigate("/devices/wizard")}
          />
        }
      />
      <AddDeviceModal
        open={addOpen}
        onClose={() => setAddOpen(false)}
        onCreated={refreshDevices}
      />
      <EditDeviceModal
        open={Boolean(editTarget)}
        device={editTarget}
        onClose={() => setEditTarget(null)}
        onSaved={refreshDevices}
      />

      {subscription && (
        <div className="flex items-center gap-4 py-2">
          <div className="flex-1 max-w-xs">
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="text-muted-foreground">Device Usage</span>
              <span>
                {subscription.active_device_count} / {subscription.device_limit}
              </span>
            </div>
            <ProgressBar value={usagePercent} />
          </div>

          {subscription.devices_available === 0 && (
            <Badge variant="outline" className="border-orange-500 text-orange-600">
              <AlertTriangle className="h-3 w-3 mr-1" />
              At Limit
            </Badge>
          )}

          {subscription.devices_available > 0 && subscription.devices_available <= 5 && (
            <Badge variant="outline" className="border-yellow-500 text-yellow-600">
              {subscription.devices_available} remaining
            </Badge>
          )}
        </div>
      )}

      {!summaryError &&
        (summaryLoading ? (
          <div className="space-y-2">
            <div className="flex justify-end">
              <Badge variant="outline" className="text-xs">
                ○ Polling
              </Badge>
            </div>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              {[1, 2, 3, 4].map((n) => (
                <Skeleton key={n} className="h-20" />
              ))}
            </div>
          </div>
        ) : summary ? (
          <div className="space-y-2">
            <div className="flex justify-end">
              <Badge
                variant="outline"
                className={`text-xs ${summaryLiveConnected ? "text-green-700 border-green-300 dark:text-green-400 dark:border-green-700" : ""}`}
              >
                {summaryLiveConnected ? "● Live" : "○ Polling"}
              </Badge>
            </div>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              {[
                { key: "ONLINE", label: "Online", color: "bg-green-500" },
                { key: "STALE", label: "Stale", color: "bg-yellow-500" },
                { key: "OFFLINE", label: "Offline", color: "bg-red-500" },
              ].map((card) => {
                const active = filters.status === card.key;
                const value = summary[card.key as "ONLINE" | "STALE" | "OFFLINE"] ?? 0;
                return (
                  <button
                    key={card.key}
                    type="button"
                    onClick={() => toggleStatusFromWidget(card.key as "ONLINE" | "STALE" | "OFFLINE")}
                    className={`rounded-md border p-3 text-left ${
                      active ? "border-primary bg-primary/5" : "border-border"
                    }`}
                  >
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <span className={`h-2 w-2 rounded-full ${card.color}`} />
                      {card.label}
                    </div>
                    <div className="mt-1 text-2xl font-semibold">{value}</div>
                  </button>
                );
              })}
              <div className="rounded-md border border-border p-3">
                <div className="text-sm text-muted-foreground">Total</div>
                <div className="mt-1 text-2xl font-semibold">{summary.total ?? 0}</div>
              </div>
            </div>
          </div>
        ) : null)}

      <div className="flex items-center gap-2">
        <Button
          type="button"
          size="sm"
          variant={viewMode === "list" ? "default" : "outline"}
          onClick={() => setViewMode("list")}
        >
          List view
        </Button>
        <Button
          type="button"
          size="sm"
          variant={viewMode === "grouped" ? "default" : "outline"}
          onClick={() => setViewMode("grouped")}
        >
          Group by tag
        </Button>
      </div>

      {groupedModeActive && (
        <p className="text-xs text-muted-foreground">
          Showing all devices grouped by tag. Use list view for pagination.
        </p>
      )}
      {groupedCapExceeded && (
        <p className="text-xs text-yellow-600">
          Grouped view is capped at 500 devices. Switch to list view for pagination.
        </p>
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
        <>
          <DeviceFilters
            selectedTags={filters.tags}
            setSelectedTags={(tags) =>
              setFilters((prev) => ({
                ...prev,
                tags,
                offset: 0,
              }))
            }
            allTags={allTags}
            tagFilterOpen={tagFilterOpen}
            setTagFilterOpen={setTagFilterOpen}
            toggleTag={toggleTag}
            offset={filters.offset}
            limit={filters.limit}
            totalCount={totalCount}
            setOffset={(n) => setFilters((prev) => ({ ...prev, offset: n }))}
            setLimit={(n) => setFilters((prev) => ({ ...prev, limit: n, offset: 0 }))}
            q={filters.q}
            onQChange={(q) => setFilters((prev) => ({ ...prev, q, offset: 0 }))}
            statusFilter={filters.status ?? ""}
            onStatusFilterChange={(s) =>
              setFilters((prev) => ({ ...prev, status: s || undefined, offset: 0 }))
            }
            showPagination={!groupedModeActive}
          />

          {groupedModeActive ? (
            <div className="space-y-3">
              {[...groupedDevices.entries()].map(([tag, group]) => {
                const collapsed = collapsedGroups[tag] ?? false;
                return (
                  <div key={tag} className="rounded-md border border-border">
                    <button
                      type="button"
                      className="flex w-full items-center justify-between px-3 py-2 text-left text-sm font-medium hover:bg-muted/40"
                      onClick={() => toggleGroup(tag)}
                    >
                      <span>
                        {collapsed ? "▶" : "▼"} {tag} ({group.length} devices)
                      </span>
                    </button>
                    {!collapsed && (
                      <div className="p-2">
                        <DeviceTable
                          devices={group}
                          selectedTagsCount={filters.tags.length}
                          onOpenTagFilter={() => setTagFilterOpen(true)}
                          onEdit={(device) => setEditTarget(device)}
                          onDecommission={async (device) => {
                            if (!window.confirm(`Are you sure you want to decommission ${device.device_id}?`)) return;
                            await decommissionDevice(device.device_id);
                            await refreshDevices();
                          }}
                        />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <DeviceTable
              devices={devices}
              selectedTagsCount={filters.tags.length}
              onOpenTagFilter={() => setTagFilterOpen(true)}
              onEdit={(device) => setEditTarget(device)}
              onDecommission={async (device) => {
                if (!window.confirm(`Are you sure you want to decommission ${device.device_id}?`)) return;
                await decommissionDevice(device.device_id);
                await refreshDevices();
              }}
            />
          )}
        </>
      )}
    </div>
  );
}
