import { useState } from "react";
import { Link } from "react-router-dom";
import {
  useAbortCampaign,
  useOtaCampaigns,
} from "@/hooks/use-ota";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/shared";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { DataTable } from "@/components/ui/data-table";
import { type ColumnDef } from "@tanstack/react-table";
import { Plus, XCircle } from "lucide-react";
import { CreateCampaignDialog } from "./CreateCampaignDialog";
import type { CampaignStatus, OtaCampaign } from "@/services/api/ota";

const STATUS_VARIANT: Record<
  CampaignStatus,
  "default" | "secondary" | "destructive" | "outline"
> = {
  CREATED: "outline",
  RUNNING: "default",
  PAUSED: "secondary",
  COMPLETED: "default",
  ABORTED: "destructive",
};

export default function OtaCampaignsPage() {
  const [createOpen, setCreateOpen] = useState(false);
  const [abortTarget, setAbortTarget] = useState<OtaCampaign | null>(null);
  const { data, isLoading } = useOtaCampaigns();
  const abortMut = useAbortCampaign();

  const campaigns = data?.campaigns ?? [];

  function progressPct(c: (typeof campaigns)[0]): number {
    if (c.total_devices === 0) return 0;
    return Math.round(((c.succeeded + c.failed) / c.total_devices) * 100);
  }

  const statusClass = (status: CampaignStatus) => {
    if (status === "COMPLETED") return "text-status-online";
    return "";
  };

  const columns: ColumnDef<OtaCampaign>[] = [
    {
      accessorKey: "name",
      header: "Name",
      cell: ({ row }) => (
        <Link
          to={`/ota/campaigns/${row.original.id}`}
          className="text-primary hover:underline font-medium"
        >
          {row.original.name}
        </Link>
      ),
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => (
        <Badge
          variant={STATUS_VARIANT[row.original.status] ?? "outline"}
          className={statusClass(row.original.status)}
        >
          {row.original.status}
        </Badge>
      ),
    },
    {
      accessorKey: "firmware_version",
      header: "Firmware",
      cell: ({ row }) => <span className="text-sm font-mono">{row.original.firmware_version}</span>,
    },
    {
      accessorKey: "total_devices",
      header: "Total Devices",
    },
    {
      id: "progress",
      header: "Progress",
      enableSorting: false,
      accessorFn: (c) => `${c.succeeded}/${c.total_devices}`,
      cell: ({ row }) => {
        const c = row.original;
        const pct = progressPct(c);
        return (
          <div className="flex items-center gap-2">
            <div className="h-2 w-24 rounded-full bg-muted overflow-hidden">
              <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${pct}%` }} />
            </div>
            <span className="text-sm text-muted-foreground">
              {c.succeeded}/{c.total_devices}
              {c.failed > 0 && <span className="text-destructive"> ({c.failed} failed)</span>}
            </span>
          </div>
        );
      },
    },
    {
      accessorKey: "created_at",
      header: "Created",
      cell: ({ row }) => (
        <span className="text-xs text-muted-foreground">
          {new Date(row.original.created_at).toLocaleDateString()}
        </span>
      ),
    },
    {
      id: "actions",
      enableSorting: false,
      header: "Actions",
      cell: ({ row }) => {
        const c = row.original;
        const canAbort = c.status === "RUNNING" || c.status === "CREATED";
        if (!canAbort) return null;
        return (
          <Button
            variant="ghost"
            size="sm"
            className="text-destructive"
            onClick={() => setAbortTarget(c)}
          >
            <XCircle className="mr-1 h-3.5 w-3.5" />
            Abort
          </Button>
        );
      },
    },
  ];

  return (
    <div className="space-y-4">
      <PageHeader
        title="OTA Campaigns"
        description="Manage firmware rollouts to your device fleet."
        action={
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="mr-1 h-4 w-4" />
            Add Campaign
          </Button>
        }
      />

      <DataTable
        columns={columns}
        data={campaigns}
        isLoading={isLoading}
        emptyState={
          <div className="rounded-lg border border-border py-8 text-center text-muted-foreground">
            No OTA campaigns created yet.
          </div>
        }
        manualPagination={false}
      />

      <CreateCampaignDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreated={() => setCreateOpen(false)}
      />

      <ConfirmDialog
        open={!!abortTarget}
        onOpenChange={(open) => {
          if (!open) setAbortTarget(null);
        }}
        title="Abort Campaign"
        description={`Are you sure you want to abort the campaign "${abortTarget?.name}"? This action cannot be undone. Devices that have already updated will not be rolled back.`}
        confirmText="Abort Campaign"
        variant="destructive"
        onConfirm={() => {
          if (abortTarget) {
            abortMut.mutate(abortTarget.id);
            setAbortTarget(null);
          }
        }}
        isPending={abortMut.isPending}
      />
    </div>
  );
}

