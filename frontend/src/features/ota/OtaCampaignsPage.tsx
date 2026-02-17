import { useState } from "react";
import { Link } from "react-router-dom";
import {
  useAbortCampaign,
  useOtaCampaigns,
  usePauseCampaign,
  useStartCampaign,
} from "@/hooks/use-ota";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/shared";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
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
  const [showCreate, setShowCreate] = useState(false);
  const [abortTarget, setAbortTarget] = useState<OtaCampaign | null>(null);
  const { data, isLoading } = useOtaCampaigns();
  const startMut = useStartCampaign();
  const pauseMut = usePauseCampaign();
  const abortMut = useAbortCampaign();

  const campaigns = data?.campaigns ?? [];

  function progressPct(c: (typeof campaigns)[0]): number {
    if (c.total_devices === 0) return 0;
    return Math.round(((c.succeeded + c.failed) / c.total_devices) * 100);
  }

  return (
    <div className="p-4 space-y-4">
      <PageHeader
        title="OTA Campaigns"
        description="Manage firmware rollouts to your device fleet."
        action={<Button onClick={() => setShowCreate(true)}>+ New Campaign</Button>}
      />

      {isLoading && (
        <div className="text-sm text-muted-foreground">Loading campaigns...</div>
      )}

      <div className="rounded border border-border overflow-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/40">
              {[
                "Name",
                "Firmware",
                "Group",
                "Status",
                "Progress",
                "Strategy",
                "Created",
                "Actions",
              ].map((h) => (
                <th key={h} className="px-3 py-2 text-left font-medium">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {campaigns.map((c) => (
              <tr
                key={c.id}
                className="border-b border-border/40 hover:bg-muted/30"
              >
                <td className="px-3 py-2">
                  <Link
                    to={`/ota/campaigns/${c.id}`}
                    className="text-primary hover:underline font-medium"
                  >
                    {c.name}
                  </Link>
                </td>
                <td className="px-3 py-2 text-xs font-mono">{c.firmware_version}</td>
                <td className="px-3 py-2 text-xs">{c.target_group_id}</td>
                <td className="px-3 py-2">
                  <Badge variant={STATUS_VARIANT[c.status] ?? "outline"}>
                    {c.status}
                  </Badge>
                </td>
                <td className="px-3 py-2">
                  <div className="flex items-center gap-2">
                    <div className="h-2 w-24 rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full bg-primary rounded-full transition-all"
                        style={{ width: `${progressPct(c)}%` }}
                      />
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {c.succeeded}/{c.total_devices}
                      {c.failed > 0 && (
                        <span className="text-destructive"> ({c.failed} failed)</span>
                      )}
                    </span>
                  </div>
                </td>
                <td className="px-3 py-2 text-xs capitalize">{c.rollout_strategy}</td>
                <td className="px-3 py-2 text-xs">
                  {new Date(c.created_at).toLocaleDateString()}
                </td>
                <td className="px-3 py-2 space-x-1">
                  {(c.status === "CREATED" || c.status === "PAUSED") && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => startMut.mutate(c.id)}
                      disabled={startMut.isPending}
                    >
                      Start
                    </Button>
                  )}
                  {c.status === "RUNNING" && (
                    <>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => pauseMut.mutate(c.id)}
                        disabled={pauseMut.isPending}
                      >
                        Pause
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => setAbortTarget(c)}
                        disabled={abortMut.isPending}
                      >
                        Abort
                      </Button>
                    </>
                  )}
                </td>
              </tr>
            ))}
            {campaigns.length === 0 && !isLoading && (
              <tr>
                <td
                  colSpan={8}
                  className="px-3 py-6 text-center text-sm text-muted-foreground"
                >
                  No OTA campaigns yet. Create one to get started.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {showCreate && (
        <CreateCampaignDialog
          onClose={() => setShowCreate(false)}
          onCreated={() => setShowCreate(false)}
        />
      )}

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

