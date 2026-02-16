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
import type { OtaDeviceStatus } from "@/services/api/ota";

const DEVICE_STATUS_COLOR: Record<string, string> = {
  PENDING: "text-muted-foreground",
  DOWNLOADING: "text-blue-500",
  INSTALLING: "text-amber-500",
  SUCCESS: "text-green-600",
  FAILED: "text-destructive",
  SKIPPED: "text-muted-foreground",
};

export default function OtaCampaignDetailPage() {
  const { campaignId } = useParams<{ campaignId: string }>();
  const id = Number(campaignId) || 0;
  const [page, setPage] = useState(0);
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
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
      <div className="p-4 text-sm text-muted-foreground">Loading campaign...</div>
    );
  }

  const breakdown = campaign.status_breakdown ?? {};
  const progressPct =
    campaign.total_devices > 0
      ? Math.round(((campaign.succeeded + campaign.failed) / campaign.total_devices) * 100)
      : 0;

  const devices: OtaDeviceStatus[] = devicesData?.devices ?? [];
  const totalDevices = devicesData?.total ?? 0;
  const totalPages = Math.ceil(totalDevices / PAGE_SIZE);

  const description = `Firmware ${campaign.firmware_version} -> Group ${campaign.target_group_id}`;

  return (
    <div className="p-4 space-y-6">
      <PageHeader
        title={campaign.name}
        description={description}
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
                  onClick={() => {
                    if (window.confirm("Abort this campaign?")) abortMut.mutate(id);
                  }}
                  disabled={abortMut.isPending}
                >
                  Abort
                </Button>
              </>
            )}
            <Link to="/ota/campaigns">
              <Button variant="outline">Back to Campaigns</Button>
            </Link>
          </div>
        }
      />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="rounded border border-border p-3">
          <div className="text-xs text-muted-foreground">Status</div>
          <Badge className="mt-1">{campaign.status}</Badge>
        </div>
        <div className="rounded border border-border p-3">
          <div className="text-xs text-muted-foreground">Progress</div>
          <div className="mt-1 text-lg font-semibold">{progressPct}%</div>
          <div className="h-2 w-full rounded-full bg-muted mt-1 overflow-hidden">
            <div
              className="h-full bg-primary rounded-full transition-all"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>
        <div className="rounded border border-border p-3">
          <div className="text-xs text-muted-foreground">Succeeded / Total</div>
          <div className="mt-1 text-lg font-semibold text-green-600">
            {campaign.succeeded} / {campaign.total_devices}
          </div>
        </div>
        <div className="rounded border border-border p-3">
          <div className="text-xs text-muted-foreground">Failed</div>
          <div className="mt-1 text-lg font-semibold text-destructive">{campaign.failed}</div>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {Object.entries(breakdown).map(([status, count]) => (
          <button
            key={status}
            onClick={() => {
              setPage(0);
              setStatusFilter(statusFilter === status ? undefined : status);
            }}
            className={`rounded border px-3 py-1 text-xs transition-colors ${
              statusFilter === status
                ? "border-primary bg-primary/10 text-primary"
                : "border-border hover:bg-muted"
            }`}
          >
            {status}: {count}
          </button>
        ))}
        {statusFilter && (
          <button
            onClick={() => {
              setPage(0);
              setStatusFilter(undefined);
            }}
            className="rounded border border-border px-3 py-1 text-xs hover:bg-muted"
          >
            Clear filter
          </button>
        )}
      </div>

      <div className="rounded border border-border overflow-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/40">
              {["Device ID", "Status", "Progress", "Error", "Started", "Completed"].map(
                (h) => (
                  <th key={h} className="px-3 py-2 text-left font-medium">
                    {h}
                  </th>
                )
              )}
            </tr>
          </thead>
          <tbody>
            {devices.map((d) => (
              <tr
                key={d.device_id}
                className="border-b border-border/40 hover:bg-muted/30"
              >
                <td className="px-3 py-2 font-mono text-xs">
                  <Link
                    to={`/devices/${d.device_id}`}
                    className="text-primary hover:underline"
                  >
                    {d.device_id}
                  </Link>
                </td>
                <td
                  className={`px-3 py-2 font-semibold text-xs ${
                    DEVICE_STATUS_COLOR[d.status] ?? ""
                  }`}
                >
                  {d.status}
                </td>
                <td className="px-3 py-2">
                  {d.status === "DOWNLOADING" || d.status === "INSTALLING" ? (
                    <div className="flex items-center gap-2">
                      <div className="h-1.5 w-16 rounded-full bg-muted overflow-hidden">
                        <div
                          className="h-full bg-primary rounded-full transition-all"
                          style={{ width: `${d.progress_pct}%` }}
                        />
                      </div>
                      <span className="text-xs">{d.progress_pct}%</span>
                    </div>
                  ) : d.status === "SUCCESS" ? (
                    <span className="text-xs text-green-600">100%</span>
                  ) : (
                    <span className="text-xs text-muted-foreground">-</span>
                  )}
                </td>
                <td className="px-3 py-2 text-xs text-destructive max-w-[200px] truncate">
                  {d.error_message ?? "-"}
                </td>
                <td className="px-3 py-2 text-xs">
                  {d.started_at ? new Date(d.started_at).toLocaleString() : "-"}
                </td>
                <td className="px-3 py-2 text-xs">
                  {d.completed_at ? new Date(d.completed_at).toLocaleString() : "-"}
                </td>
              </tr>
            ))}
            {devices.length === 0 && (
              <tr>
                <td colSpan={6} className="px-3 py-4 text-center text-sm text-muted-foreground">
                  No devices{statusFilter ? ` with status ${statusFilter}` : ""}.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
          >
            Previous
          </Button>
          <span className="text-sm text-muted-foreground">
            Page {page + 1} of {totalPages}
          </span>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setPage((p) => p + 1)}
            disabled={page >= totalPages - 1}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}

