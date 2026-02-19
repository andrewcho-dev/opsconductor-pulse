import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { Pause, Play, Plus, Radio, RefreshCw, RotateCcw, XCircle } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { cn } from "@/lib/utils";
import {
  executeCarrierAction,
  getCarrierDiagnostics,
  getCarrierStatus,
  getCarrierUsage,
  listCarrierIntegrations,
  listCarrierPlans,
  provisionDeviceSim,
} from "@/services/api/carrier";
import type { CarrierDeviceStatus, CarrierDeviceUsage, CarrierPlansResponse } from "@/services/api/types";

interface DeviceCarrierPanelProps {
  deviceId: string;
}

function simStatusVariant(simStatus: string | null | undefined) {
  const s = (simStatus ?? "").toLowerCase();
  if (s === "active") return "active";
  if (s === "suspended") return "suspended";
  if (s === "inactive" || s === "deactivated") return "inactive";
  return "other";
}

function usageBarColor(pct: number) {
  if (!Number.isFinite(pct)) return "bg-primary";
  if (pct > 80) return "bg-status-critical";
  if (pct >= 50) return "bg-status-warning";
  return "bg-primary";
}

export function DeviceCarrierPanel({ deviceId }: DeviceCarrierPanelProps) {
  const queryClient = useQueryClient();
  const [confirmAction, setConfirmAction] = useState<(typeof CARRIER_ACTIONS)[number] | null>(null);
  const [provisionOpen, setProvisionOpen] = useState(false);
  const [selectedIntegrationId, setSelectedIntegrationId] = useState<number | null>(null);
  const [iccid, setIccid] = useState("");
  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null);

  const statusQuery = useQuery({
    queryKey: ["carrier-status", deviceId],
    queryFn: () => getCarrierStatus(deviceId),
    refetchInterval: 60_000,
    enabled: !!deviceId,
  });

  const integrationsQuery = useQuery({
    queryKey: ["carrier-integrations"],
    queryFn: listCarrierIntegrations,
    enabled: provisionOpen,
  });

  const plansQuery = useQuery({
    queryKey: ["carrier-plans", selectedIntegrationId],
    queryFn: () => listCarrierPlans(selectedIntegrationId!),
    enabled: provisionOpen && selectedIntegrationId != null,
  });

  const usageQuery = useQuery({
    queryKey: ["carrier-usage", deviceId],
    queryFn: () => getCarrierUsage(deviceId),
    refetchInterval: 300_000,
    enabled: !!deviceId,
  });

  const diagnosticsQuery = useQuery({
    queryKey: ["carrier-diagnostics", deviceId],
    queryFn: () => getCarrierDiagnostics(deviceId),
    refetchInterval: 300_000,
    enabled: !!deviceId,
  });

  const status = statusQuery.data as CarrierDeviceStatus | undefined;
  const usage = usageQuery.data as CarrierDeviceUsage | undefined;
  const info = status?.device_info;
  const linked = status?.linked === true;

  const usageInfo = usage?.usage;
  const usagePct = usageInfo?.usage_pct ?? 0;
  const usageBar = usageBarColor(usagePct);
  const simStatus = statusQuery.data?.device_info?.sim_status;

  const provisionMutation = useMutation({
    mutationFn: () =>
      provisionDeviceSim(deviceId, {
        carrier_integration_id: selectedIntegrationId!,
        iccid,
        plan_id: selectedPlanId ?? undefined,
      }),
    onSuccess: async () => {
      toast.success("SIM provisioned successfully");
      setProvisionOpen(false);
      setIccid("");
      setSelectedIntegrationId(null);
      setSelectedPlanId(null);
      await queryClient.invalidateQueries({ queryKey: ["carrier-status", deviceId] });
      await queryClient.invalidateQueries({ queryKey: ["carrier-usage", deviceId] });
      await queryClient.invalidateQueries({ queryKey: ["carrier-diagnostics", deviceId] });
    },
    onError: (err: any) => {
      toast.error(`Provisioning failed: ${err?.message ?? "Unknown error"}`);
    },
  });

  const actionMutation = useMutation({
    mutationFn: ({ action }: { action: "activate" | "suspend" | "deactivate" | "reboot" }) =>
      executeCarrierAction(deviceId, action),
    onSuccess: async (data) => {
      toast.success(`${data.action} completed successfully`);
      await queryClient.invalidateQueries({ queryKey: ["carrier-status", deviceId] });
      await queryClient.invalidateQueries({ queryKey: ["carrier-usage", deviceId] });
      await queryClient.invalidateQueries({ queryKey: ["carrier-diagnostics", deviceId] });
    },
    onError: (err: any) => {
      toast.error(`Action failed: ${err?.message ?? "Unknown error"}`);
    },
  });

  const isDisabled = (action: string) => {
    if (actionMutation.isPending) return true;
    if (simStatus === "active" && action === "activate") return true;
    if (simStatus === "suspended" && action === "suspend") return true;
    if (
      (simStatus === "deactivated" || simStatus === "inactive") &&
      (action === "suspend" || action === "deactivate")
    ) {
      return true;
    }
    return false;
  };

  const lastConnection = useMemo(() => {
    if (!info?.last_connection) return "—";
    try {
      return format(new Date(info.last_connection), "MMM d, h:mm a");
    } catch {
      return info.last_connection;
    }
  }, [info?.last_connection]);

  if (statusQuery.isLoading) {
    return (
      <div className="rounded-md border border-border p-3 space-y-3">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <div className="text-sm font-medium">Carrier Integration</div>
            <div className="text-xs text-muted-foreground">Loading…</div>
          </div>
          <Skeleton className="h-8 w-8" />
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-14 w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (statusQuery.isError) {
    return (
      <div className="rounded-md border border-border p-3 space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-medium">Carrier Integration</h3>
            <p className="text-xs text-muted-foreground">Carrier diagnostics and usage</p>
          </div>
          <Button variant="ghost" size="sm" onClick={() => statusQuery.refetch()}>
            Retry
          </Button>
        </div>
        <div className="text-sm text-destructive">Failed to load carrier data.</div>
      </div>
    );
  }

  if (status?.linked === false) {
    const integrations =
      (integrationsQuery.data as
        | {
            integrations: Array<{ id: number; display_name: string; carrier_name: string }>;
          }
        | undefined)?.integrations ?? [];
    const plans = (plansQuery.data as CarrierPlansResponse | undefined)?.plans ?? [];

    return (
      <div className="rounded-md border border-border p-3 space-y-3">
        <h3 className="text-sm font-medium">Carrier Integration</h3>
        <div className="text-center py-6 text-muted-foreground text-sm">
          <Radio className="h-8 w-8 mx-auto mb-2 opacity-40" />
          <p>No carrier integration linked to this device.</p>
          <Button
            variant="outline"
            size="sm"
            className="mt-3"
            onClick={() => setProvisionOpen(true)}
          >
            <Plus className="h-3.5 w-3.5 mr-1.5" />
            Provision SIM
          </Button>
        </div>

        <Dialog open={provisionOpen} onOpenChange={setProvisionOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Provision SIM Card</DialogTitle>
              <DialogDescription>
                Claim a new SIM from your carrier and link it to this device.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <Label htmlFor="prov-integration">Carrier Integration</Label>
                <Select
                  value={selectedIntegrationId?.toString() ?? ""}
                  onValueChange={(v) => {
                    setSelectedIntegrationId(Number(v));
                    setSelectedPlanId(null);
                  }}
                >
                  <SelectTrigger id="prov-integration">
                    <SelectValue placeholder="Select carrier..." />
                  </SelectTrigger>
                  <SelectContent>
                    {integrations.map((i) => (
                      <SelectItem key={i.id} value={i.id.toString()}>
                        {i.display_name} ({i.carrier_name})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="prov-iccid">ICCID</Label>
                <Input
                  id="prov-iccid"
                  placeholder="89014103211118510720"
                  value={iccid}
                  onChange={(e) => setIccid(e.target.value)}
                  maxLength={22}
                />
                <p className="text-xs text-muted-foreground">
                  The 15-22 digit number printed on the SIM card.
                </p>
              </div>

              {plans.length > 0 ? (
                <div className="space-y-2">
                  <Label htmlFor="prov-plan">Data Plan (optional)</Label>
                  <Select
                    value={selectedPlanId?.toString() ?? ""}
                    onValueChange={(v) => setSelectedPlanId(v ? Number(v) : null)}
                  >
                    <SelectTrigger id="prov-plan">
                      <SelectValue placeholder="Select plan..." />
                    </SelectTrigger>
                    <SelectContent>
                      {plans.map((p) => (
                        <SelectItem key={p.id} value={p.id.toString()}>
                          {p.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              ) : null}
            </div>
            <DialogFooter>
              <Button
                variant="ghost"
                onClick={() => setProvisionOpen(false)}
                disabled={provisionMutation.isPending}
              >
                Cancel
              </Button>
              <Button
                onClick={() => provisionMutation.mutate()}
                disabled={
                  !selectedIntegrationId ||
                  iccid.length < 15 ||
                  provisionMutation.isPending
                }
              >
                {provisionMutation.isPending ? "Provisioning..." : "Provision SIM"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    );
  }

  return (
    <div className="rounded-md border border-border p-3 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-medium">Carrier Integration</h3>
          {linked ? (
            <p className="text-xs text-muted-foreground">
              {status?.carrier_name} · {info?.carrier_device_id}
            </p>
          ) : null}
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            queryClient.invalidateQueries({ queryKey: ["carrier-status", deviceId] });
            queryClient.invalidateQueries({ queryKey: ["carrier-usage", deviceId] });
            queryClient.invalidateQueries({ queryKey: ["carrier-diagnostics", deviceId] });
          }}
          disabled={statusQuery.isFetching || usageQuery.isFetching}
        >
          <RefreshCw
            className={cn(
              "h-3.5 w-3.5",
              (statusQuery.isFetching || usageQuery.isFetching) && "animate-spin",
            )}
          />
        </Button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <StatCard label="SIM Status" value={info?.sim_status ?? "—"} variant={simStatusVariant(info?.sim_status)} />
        <StatCard label="Network" value={info?.network_type || "—"} />
        <StatCard label="IP Address" value={info?.ip_address || "—"} mono />
        <StatCard
          label="Signal"
          value={info?.signal_strength != null ? `${info.signal_strength}%` : "—"}
        />
      </div>

      {usageInfo ? (
        <div className="space-y-1.5">
          <h4 className="text-xs font-medium text-muted-foreground">Data Usage</h4>
          <div className="space-y-1">
            <div className="flex justify-between text-xs">
              <span>{usageInfo.data_used_mb.toFixed(1)} MB used</span>
              {usageInfo.data_limit_mb ? <span>{usageInfo.data_limit_mb} MB limit</span> : null}
            </div>
            <div className="h-2 rounded-full bg-muted overflow-hidden">
              <div
                className={`h-full ${usageBar}`}
                style={{ width: `${Math.min(100, Math.max(0, usagePct))}%` }}
              />
            </div>
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>{usagePct.toFixed(1)}% used</span>
              {usageInfo.billing_cycle_start && usageInfo.billing_cycle_end ? (
                <span>
                  {format(new Date(usageInfo.billing_cycle_start), "MMM d")} –{" "}
                  {format(new Date(usageInfo.billing_cycle_end), "MMM d")}
                </span>
              ) : null}
            </div>
            {usageInfo.sms_count > 0 ? (
              <div className="text-xs text-muted-foreground">SMS: {usageInfo.sms_count}</div>
            ) : null}
          </div>
        </div>
      ) : null}

      <div className="space-y-1.5">
        <h4 className="text-xs font-medium text-muted-foreground">Network Details</h4>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
          <DetailRow label="ICCID" value={info?.iccid} />
          <DetailRow label="Carrier Device ID" value={info?.carrier_device_id} />
          <DetailRow label="Network Status" value={info?.network_status} />
          <DetailRow label="Last Connection" value={lastConnection} />
        </div>
      </div>

      {linked ? (
        <div className="space-y-1.5">
          <h4 className="text-xs font-medium text-muted-foreground">Remote Actions</h4>
          <div className="flex flex-wrap gap-2">
            {CARRIER_ACTIONS.map((def) => {
              const Icon = def.icon;
              return (
                <Button
                  key={def.action}
                  variant={def.variant}
                  size="sm"
                  onClick={() => setConfirmAction(def)}
                  disabled={isDisabled(def.action)}
                >
                  <Icon className="h-3.5 w-3.5 mr-1.5" />
                  {def.label}
                </Button>
              );
            })}
          </div>
        </div>
      ) : null}

      <AlertDialog open={!!confirmAction} onOpenChange={(open) => !open && setConfirmAction(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {confirmAction?.destructive ? "⚠️ " : ""}
              {confirmAction?.label} Device?
            </AlertDialogTitle>
            <AlertDialogDescription>
              {confirmAction?.description}
              {confirmAction?.destructive ? (
                <span className="block mt-2 font-medium text-destructive">This action is irreversible.</span>
              ) : null}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={actionMutation.isPending}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (!confirmAction) return;
                actionMutation.mutate({ action: confirmAction.action });
                setConfirmAction(null);
              }}
              disabled={actionMutation.isPending}
              className={
                confirmAction?.destructive
                  ? "bg-destructive text-destructive-foreground hover:bg-destructive/90"
                  : ""
              }
            >
              {actionMutation.isPending ? "Processing..." : `Yes, ${confirmAction?.label}`}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {diagnosticsQuery.data ? (
        <details className="rounded-md border border-border p-2">
          <summary className="text-xs text-muted-foreground cursor-pointer">
            Raw diagnostics
          </summary>
          <pre className="text-xs overflow-auto mt-2">
            {JSON.stringify(diagnosticsQuery.data, null, 2)}
          </pre>
        </details>
      ) : null}
    </div>
  );
}

function StatCard({
  label,
  value,
  variant,
  mono,
}: {
  label: string;
  value: string;
  variant?: "active" | "suspended" | "inactive" | "other";
  mono?: boolean;
}) {
  const badge =
    variant === "active"
      ? { variant: "default" as const, className: "bg-status-online text-status-online-foreground" }
      : variant === "suspended"
        ? { variant: "destructive" as const, className: "" }
        : variant === "inactive"
          ? { variant: "secondary" as const, className: "" }
          : { variant: "outline" as const, className: "" };

  return (
    <div className="rounded border border-border p-2 text-center">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-sm font-medium mt-0.5 truncate">
        {variant ? (
          <Badge variant={badge.variant} className={badge.className}>
            {value}
          </Badge>
        ) : (
          <span className={mono ? "font-mono" : ""}>{value}</span>
        )}
      </div>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <>
      <span className="text-muted-foreground">{label}</span>
      <span className="font-mono">{value || "—"}</span>
    </>
  );
}

const CARRIER_ACTIONS = [
  {
    action: "activate" as const,
    label: "Activate",
    icon: Play,
    description: "Activate the SIM card on this device. This will enable cellular connectivity.",
    variant: "default" as const,
    destructive: false,
  },
  {
    action: "suspend" as const,
    label: "Suspend",
    icon: Pause,
    description:
      "Temporarily suspend the SIM card. The device will lose connectivity but can be reactivated later.",
    variant: "secondary" as const,
    destructive: false,
  },
  {
    action: "deactivate" as const,
    label: "Deactivate",
    icon: XCircle,
    description:
      "Permanently deactivate the SIM card. This action cannot be reversed — a new SIM will be required.",
    variant: "destructive" as const,
    destructive: true,
  },
  {
    action: "reboot" as const,
    label: "Reboot",
    icon: RotateCcw,
    description: "Send a remote reboot command to the device via the carrier network.",
    variant: "outline" as const,
    destructive: false,
  },
] as const;

