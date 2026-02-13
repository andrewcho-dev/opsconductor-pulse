import { useMemo, useState } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader, EmptyState } from "@/components/shared";
import { useDevices } from "@/hooks/use-devices";
import { Cpu, AlertTriangle } from "lucide-react";
import { getAllTags } from "@/services/api/devices";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/services/api/client";
import { Badge } from "@/components/ui/badge";
import { DeviceActions } from "./DeviceActions";
import { DeviceFilters } from "./DeviceFilters";
import { DeviceTable } from "./DeviceTable";

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
  const [offset, setOffset] = useState(0);
  const [limit, setLimit] = useState(100);
  const { data, isLoading, error } = useDevices(limit, offset);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [tagFilterOpen, setTagFilterOpen] = useState(false);

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
  const totalCount = data?.total ?? data?.count ?? 0;

  const filteredDevices = useMemo(() => {
    if (selectedTags.length === 0) return devices;
    return devices.filter((device) => {
      const tags = device.tags || [];
      return selectedTags.every((tag) => tags.includes(tag));
    });
  }, [devices, selectedTags]);

  const toggleTag = (tag: string) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
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
            : selectedTags.length > 0
            ? `${filteredDevices.length} devices match filters`
            : subscription
            ? `${totalCount} of ${subscription.device_limit} devices (${subscription.devices_available} available)`
            : `${totalCount} devices in your fleet`
        }
        action={<DeviceActions canCreate={canCreate} createDisabled={createDisabled} />}
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
            selectedTags={selectedTags}
            setSelectedTags={setSelectedTags}
            allTags={allTags}
            tagFilterOpen={tagFilterOpen}
            setTagFilterOpen={setTagFilterOpen}
            toggleTag={toggleTag}
            offset={offset}
            limit={limit}
            totalCount={totalCount}
            setOffset={setOffset}
            setLimit={setLimit}
          />

          <DeviceTable
            devices={filteredDevices}
            selectedTagsCount={selectedTags.length}
            onOpenTagFilter={() => setTagFilterOpen(true)}
          />
        </>
      )}
    </div>
  );
}
