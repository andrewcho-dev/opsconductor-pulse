import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { Check, Loader2, X } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { apiPut } from "@/services/api/client";
import { fetchDevice } from "@/services/api/devices";
import { listDeviceSensors } from "@/services/api/sensors";
import { listDevicePlans } from "@/services/api/billing";
import type { DevicePlan } from "@/services/api/types";
import { getErrorMessage } from "@/lib/errors";

interface DevicePlanPanelProps {
  deviceId: string;
}

const FEATURE_LABELS: Record<string, string> = {
  ota_updates: "OTA Updates",
  advanced_analytics: "Analytics",
  streaming_export: "Streaming Export",
  x509_auth: "x509 Auth",
  message_routing: "Message Routing",
  device_commands: "Device Commands",
  device_twin: "Device Twin",
  carrier_diagnostics: "Carrier Diagnostics",
};

function formatUsd(cents: number | null | undefined) {
  const c = typeof cents === "number" ? cents : 0;
  return `$${(c / 100).toFixed(2)}`;
}

function safeFormatDate(value: unknown) {
  if (!value || typeof value !== "string") return "—";
  try {
    return format(new Date(value), "MMM d, yyyy");
  } catch {
    return value;
  }
}

export function DevicePlanPanel({ deviceId }: DevicePlanPanelProps) {
  const queryClient = useQueryClient();
  const [changeOpen, setChangeOpen] = useState(false);
  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null);

  const deviceQuery = useQuery({
    queryKey: ["device", deviceId],
    queryFn: () => fetchDevice(deviceId),
  });

  const plansQuery = useQuery({
    queryKey: ["device-plans"],
    queryFn: listDevicePlans,
  });

  const sensorsQuery = useQuery({
    queryKey: ["sensors", deviceId],
    queryFn: () => listDeviceSensors(deviceId),
  });

  const device: any = deviceQuery.data?.device;
  const planId: string | null = device?.plan_id ?? null;

  const plan: DevicePlan | undefined = useMemo(() => {
    if (!planId) return undefined;
    return plansQuery.data?.plans?.find((p) => p.plan_id === planId);
  }, [planId, plansQuery.data?.plans]);

  const sensorCount = sensorsQuery.data?.sensors?.length ?? 0;
  const sensorLimit = plan?.limits?.sensors ?? sensorsQuery.data?.sensor_limit ?? null;

  const changePlanMutation = useMutation({
    mutationFn: async (nextPlanId: string) => {
      return apiPut(`/api/v1/customer/devices/${encodeURIComponent(deviceId)}/plan`, {
        plan_id: nextPlanId,
      });
    },
    onSuccess: async () => {
      toast.success("Device plan updated");
      setChangeOpen(false);
      setSelectedPlanId(null);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["device", deviceId] }),
        queryClient.invalidateQueries({ queryKey: ["devices"] }),
        queryClient.invalidateQueries({ queryKey: ["sensors", deviceId] }),
      ]);
    },
    onError: (err: Error) => {
      toast.error(getErrorMessage(err) || "Failed to update device plan");
    },
  });

  const subscriptionStatus: string | null = device?.device_subscription_status ?? null;
  const termStart: string | null = device?.device_subscription_term_start ?? null;
  const termEnd: string | null = device?.device_subscription_term_end ?? null;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <div>
          <CardTitle className="text-sm font-medium">Device Plan</CardTitle>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-sm">
            <Badge variant="outline">{plan?.name ?? planId ?? "—"}</Badge>
            {plan ? (
              <span className="text-muted-foreground">
                {formatUsd(plan.monthly_price_cents)}/month
              </span>
            ) : null}
          </div>
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={() => {
            setSelectedPlanId(planId);
            setChangeOpen(true);
          }}
          disabled={plansQuery.isLoading || !plansQuery.data?.plans?.length}
        >
          Change Plan
        </Button>
      </CardHeader>

      <CardContent className="space-y-3">
        <div className="grid grid-cols-3 gap-2">
          <div className="rounded border p-2">
            <div className="text-xs text-muted-foreground">Sensors</div>
            <div className="text-sm font-medium">
              {sensorLimit != null ? `${sensorCount} / ${sensorLimit}` : `${sensorCount}`}
            </div>
          </div>
          <div className="rounded border p-2">
            <div className="text-xs text-muted-foreground">Retention</div>
            <div className="text-sm font-medium">
              {plan?.limits?.data_retention_days != null
                ? `${plan.limits.data_retention_days} days`
                : "—"}
            </div>
          </div>
          <div className="rounded border p-2">
            <div className="text-xs text-muted-foreground">Telemetry</div>
            <div className="text-sm font-medium">
              {plan?.limits?.telemetry_rate_per_minute != null
                ? `${plan.limits.telemetry_rate_per_minute} msg/min`
                : "—"}
            </div>
          </div>
        </div>

        <div>
          <div className="text-xs font-medium text-muted-foreground mb-1">Features</div>
          <div className="grid grid-cols-3 gap-1 text-xs">
            {Object.entries(FEATURE_LABELS).map(([key, label]) => {
              const enabled = Boolean((plan?.features as any)?.[key]);
              return (
                <div key={key} className="flex items-center gap-1">
                  {enabled ? (
                    <Check className="h-3 w-3 text-green-500" />
                  ) : (
                    <X className="h-3 w-3 text-muted-foreground" />
                  )}
                  <span className={enabled ? "" : "text-muted-foreground"}>{label}</span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <span>Subscription:</span>
          <Badge variant="outline">{subscriptionStatus ?? "—"}</Badge>
          {termStart ? (
            <span>
              {safeFormatDate(termStart)} – {termEnd ? safeFormatDate(termEnd) : "Open-ended"}
            </span>
          ) : null}
        </div>
      </CardContent>

      <Dialog open={changeOpen} onOpenChange={setChangeOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Change Plan</DialogTitle>
            <DialogDescription>Select a new plan for this device.</DialogDescription>
          </DialogHeader>

          <div className="grid gap-2 md:grid-cols-3">
            {(plansQuery.data?.plans ?? []).map((p) => {
              const isSelected = selectedPlanId === p.plan_id;
              return (
                <button
                  key={p.plan_id}
                  type="button"
                  className={`rounded border p-3 text-left hover:border-primary ${
                    isSelected ? "border-primary bg-primary/5" : "border-muted"
                  }`}
                  onClick={() => setSelectedPlanId(p.plan_id)}
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="font-medium">{p.name}</div>
                    <Badge variant="outline">{formatUsd(p.monthly_price_cents)}/mo</Badge>
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">{p.plan_id}</div>
                  <div className="mt-2 text-xs text-muted-foreground">
                    Sensors: {p.limits?.sensors ?? "—"} · Retention:{" "}
                    {p.limits?.data_retention_days ?? "—"}d · Telemetry:{" "}
                    {p.limits?.telemetry_rate_per_minute ?? "—"}/min
                  </div>
                </button>
              );
            })}
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setChangeOpen(false);
                setSelectedPlanId(null);
              }}
              disabled={changePlanMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              onClick={() => {
                if (!selectedPlanId) return;
                changePlanMutation.mutate(selectedPlanId);
              }}
              disabled={!selectedPlanId || changePlanMutation.isPending}
            >
              {changePlanMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Updating...
                </>
              ) : (
                "Confirm"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}

