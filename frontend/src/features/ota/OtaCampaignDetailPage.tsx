import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  useAbortCampaign,
  useCampaignDevices,
  useOtaCampaign,
  usePauseCampaign,
  useStartCampaign,
} from "@/hooks/use-ota";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/shared";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { DataTable } from "@/components/ui/data-table";
import { type ColumnDef, type PaginationState } from "@tanstack/react-table";
import type { OtaDeviceStatus } from "@/services/api/ota";

function statusVariant(status: string): "default" | "secondary" | "destructive" | "outline" {
  switch (status) {
    case "PENDING":
      return "secondary";
    case "DOWNLOADING":
    case "INSTALLING":
      return "default";
    case "SUCCESS":
      return "outline";
    case "FAILED":
      return "destructive";
    default:
      return "secondary";
  }
}

export default function OtaCampaignDetailPage() {
  const { campaignId } = useParams<{ campaignId: string }>();
  const id = Number(campaignId) || 0;
  const [page, setPage] = useState(0);
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [abortOpen, setAbortOpen] = useState(false);
  const PAGE_SIZE = 50;

  const { data: campaign, isLoading } = useOtaCampaign(id);
  const { data: devicesData } = useCampaignDevices(id, {
    status: statusFilter,
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
  });

  const startMut = useStartCampaign();
  const pauseMut = usePauseCampaign();
  const abortMut = useAbortCampaign();

  if (isLoading || !campaign) {
    return (
      <div className="text-sm text-muted-foreground">Loading campaign...</div>
    );
  }

  const breakdown = campaign.status_breakdown ?? {};
  const progressPct =
    campaign.total_devices > 0
      ? Math.round(((campaign.succeeded + campaign.failed) / campaign.total_devices) * 100)
      : 0;

  const devices: OtaDeviceStatus[] = devicesData?.devices ?? [];
  const totalDevices = devicesData?.total ?? 0;

  const description = `Firmware ${campaign.firmware_version} -> Group ${campaign.target_group_id}`;

  const columns: ColumnDef<OtaDeviceStatus>[] = [
    {
      accessorKey: "device_id",
      header: "Device ID",
      cell: ({ row }) => (
        <Link
          to={`/devices/${row.original.device_id}`}
          className="font-mono text-sm text-primary hover:underline"
        >
          {row.original.device_id}
        </Link>
      ),
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => (
        <Badge
          variant={statusVariant(row.original.status)}
          className={row.original.status === "SUCCESS" ? "text-status-online" : ""}
        >
          {row.original.status === "SUCCESS" ? "SUCCEEDED" : row.original.status}
        </Badge>
      ),
    },
    {
      accessorKey: "started_at",
      header: "Started",
      cell: ({ row }) => (
        <span className="text-xs text-muted-foreground">
          {row.original.started_at ? new Date(row.original.started_at).toLocaleString() : "—"}
        </span>
      ),
    },
    {
      accessorKey: "completed_at",
      header: "Completed",
      cell: ({ row }) => (
        <span className="text-xs text-muted-foreground">
          {row.original.completed_at ? new Date(row.original.completed_at).toLocaleString() : "—"}
        </span>
      ),
    },
    {
      accessorKey: "error_message",
      header: "Error",
      enableSorting: false,
      cell: ({ row }) => (
        <span className="max-w-[240px] truncate text-sm text-destructive">
          {row.original.error_message ?? "—"}
        </span>
      ),
    },
  ];

  const useServerPagination = totalDevices > PAGE_SIZE;

  return (
    <div className="space-y-4">
      <PageHeader
        title={campaign.name}
        description={description}
        breadcrumbs={[
          { label: "OTA Campaigns", href: "/ota/campaigns" },
          { label: campaign.name || "..." },
        ]}
        action={
          <div className="flex gap-2">
            {(campaign.status === "CREATED" || campaign.status === "PAUSED") && (
              <Button onClick={() => startMut.mutate(id)} disabled={startMut.isPending}>
                Start
              </Button>
            )}
            {campaign.status === "RUNNING" && (
              <>
                <Button
                  variant="outline"
                  onClick={() => pauseMut.mutate(id)}
                  disabled={pauseMut.isPending}
                >
                  Pause
                </Button>
                <Button
                  variant="destructive"
                  onClick={() => setAbortOpen(true)}
                  disabled={abortMut.isPending}
                >
                  Abort
                </Button>
              </>
            )}
          </div>
        }
      />

      <ConfirmDialog
        open={abortOpen}
        onOpenChange={setAbortOpen}
        title="Abort Campaign"
        description="Are you sure you want to abort this campaign? Devices that have already updated will not be rolled back."
        confirmText="Abort Campaign"
        variant="destructive"
        onConfirm={() => {
          abortMut.mutate(campaign.id);
          setAbortOpen(false);
        }}
        isPending={abortMut.isPending}
      />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="rounded border border-border p-3">
          <div className="text-sm text-muted-foreground">Status</div>
          <Badge className="mt-1">{campaign.status}</Badge>
        </div>
        <div className="rounded border border-border p-3">
          <div className="text-sm text-muted-foreground">Progress</div>
          <div className="mt-1 text-lg font-semibold">{progressPct}%</div>
          <div className="h-2 w-full rounded-full bg-muted mt-1 overflow-hidden">
            <div
              className="h-full bg-primary rounded-full transition-all"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>
        <div className="rounded border border-border p-3">
          <div className="text-sm text-muted-foreground">Succeeded / Total</div>
          <div className="mt-1 text-lg font-semibold text-status-online">
            {campaign.succeeded} / {campaign.total_devices}
          </div>
        </div>
        <div className="rounded border border-border p-3">
          <div className="text-sm text-muted-foreground">Failed</div>
          <div className="mt-1 text-lg font-semibold text-destructive">{campaign.failed}</div>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {Object.entries(breakdown).map(([status, count]) => (
          <Button
            key={status}
            type="button"
            onClick={() => {
              setPage(0);
              setStatusFilter(statusFilter === status ? undefined : status);
            }}
            size="sm"
            variant={statusFilter === status ? "default" : "outline"}
          >
            {status}: {count}
          </Button>
        ))}
        {statusFilter && (
          <Button
            type="button"
            onClick={() => {
              setPage(0);
              setStatusFilter(undefined);
            }}
            size="sm"
            variant="outline"
          >
            Clear filter
          </Button>
        )}
      </div>

      <DataTable
        columns={columns}
        data={devices}
        totalCount={useServerPagination ? totalDevices : undefined}
        pagination={
          useServerPagination ? { pageIndex: page, pageSize: PAGE_SIZE } : undefined
        }
        onPaginationChange={
          useServerPagination
            ? (updater) => {
                const next =
                  typeof updater === "function"
                    ? updater({ pageIndex: page, pageSize: PAGE_SIZE })
                    : (updater as PaginationState);
                setPage(next.pageIndex);
              }
            : undefined
        }
        isLoading={false}
        emptyState={
          <div className="rounded-lg border border-border py-8 text-center text-muted-foreground">
            No devices targeted in this campaign.
          </div>
        }
      />
    </div>
  );
}

