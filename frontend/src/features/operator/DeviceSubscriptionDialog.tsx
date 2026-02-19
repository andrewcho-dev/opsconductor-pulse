"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/errors";
import {
  createDeviceSubscription,
  updateDeviceSubscription,
} from "@/services/api/operator";
import { fetchDevicePlans } from "@/services/api/device-tiers";

interface DeviceSubscriptionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  deviceId: string;
  tenantId: string;
  currentSubscriptionId?: string | null;
  onAssigned: () => void;
}

export function DeviceSubscriptionDialog({
  open,
  onOpenChange,
  deviceId,
  tenantId,
  currentSubscriptionId,
  onAssigned,
}: DeviceSubscriptionDialogProps) {
  const [planId, setPlanId] = useState("");
  const [termEnd, setTermEnd] = useState("");

  useEffect(() => {
    if (!open) return;
    setPlanId("");
    setTermEnd("");
  }, [open]);

  const { data: planData, isLoading: plansLoading } = useQuery({
    queryKey: ["operator-device-plans"],
    queryFn: fetchDevicePlans,
    enabled: open,
  });

  const plans = planData?.plans ?? [];

  const canSubmit = useMemo(() => {
    return Boolean(planId);
  }, [planId]);

  const mutation = useMutation({
    mutationFn: async () => {
      if (currentSubscriptionId) {
        return updateDeviceSubscription(currentSubscriptionId, {
          plan_id: planId,
          term_end: termEnd ? new Date(termEnd).toISOString() : undefined,
        });
      }
      return createDeviceSubscription({
        tenant_id: tenantId,
        device_id: deviceId,
        plan_id: planId,
        status: "ACTIVE",
        term_end: termEnd ? new Date(termEnd).toISOString() : undefined,
      });
    },
    onSuccess: () => {
      onAssigned();
      toast.success(currentSubscriptionId ? "Subscription updated" : "Subscription created");
    },
    onError: (err: Error) => {
      toast.error(getErrorMessage(err) || "Failed to save subscription");
    },
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {currentSubscriptionId ? "Update Device Subscription" : "Create Device Subscription"}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="text-sm text-muted-foreground">
            Device: <span className="font-mono">{deviceId}</span>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Current Subscription</span>
              {currentSubscriptionId ? (
                <Badge variant="outline">{currentSubscriptionId}</Badge>
              ) : (
                <Badge variant="secondary">None</Badge>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <span className="text-sm font-medium">Plan</span>
            <Select value={planId} onValueChange={setPlanId} disabled={plansLoading}>
              <SelectTrigger>
                <SelectValue placeholder={plansLoading ? "Loading plans..." : "Select plan"} />
              </SelectTrigger>
              <SelectContent>
                {plans.map((p) => (
                  <SelectItem key={p.plan_id} value={p.plan_id}>
                    {p.name} ({p.plan_id})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <span className="text-sm font-medium">Term End (optional)</span>
            <Input
              type="date"
              value={termEnd}
              onChange={(e) => setTermEnd(e.target.value)}
            />
          </div>
        </div>

        {mutation.isError && (
          <p className="text-sm text-destructive">
            {(mutation.error as Error).message}
          </p>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={() => mutation.mutate()}
            disabled={!canSubmit || mutation.isPending}
          >
            {mutation.isPending ? "Saving..." : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

