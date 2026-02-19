"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import { toast } from "sonner";
import { CalendarPlus } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { getErrorMessage } from "@/lib/errors";
import {
  updateDeviceSubscription,
  type DeviceSubscriptionRow,
} from "@/services/api/operator";
import { fetchDevicePlans } from "@/services/api/device-tiers";

interface EditSubscriptionDialogProps {
  tenantId: string;
  subscription: DeviceSubscriptionRow | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
}

const STATUSES = [
  "TRIAL",
  "ACTIVE",
  "GRACE",
  "SUSPENDED",
  "EXPIRED",
  "CANCELLED",
] as const;

export function EditSubscriptionDialog({
  tenantId,
  subscription,
  open,
  onOpenChange,
  onSaved,
}: EditSubscriptionDialogProps) {
  const [termEnd, setTermEnd] = useState("");
  const [status, setStatus] = useState<string>("ACTIVE");
  const [planId, setPlanId] = useState<string>("");

  useEffect(() => {
    if (!open || !subscription) return;
    setStatus(subscription.status);
    setPlanId(subscription.plan_id);
    setTermEnd(
      subscription.term_end
        ? format(new Date(subscription.term_end), "yyyy-MM-dd")
        : ""
    );
  }, [open, subscription]);

  const { data: plansData } = useQuery({
    queryKey: ["operator-device-plans"],
    queryFn: fetchDevicePlans,
    enabled: open,
  });

  const plans = plansData?.plans ?? [];

  const mutation = useMutation({
    mutationFn: async () => {
      if (!subscription) return;
      return updateDeviceSubscription(subscription.subscription_id, {
        status,
        plan_id: planId,
        term_end: termEnd ? new Date(termEnd).toISOString() : undefined,
      });
    },
    onSuccess: () => {
      onSaved();
      toast.success("Subscription updated");
    },
    onError: (err: Error) => {
      toast.error(getErrorMessage(err) || "Failed to update subscription");
    },
  });

  const canSubmit = useMemo(() => {
    return Boolean(subscription && planId && status);
  }, [planId, status, subscription]);

  const extendTerm = (days: number) => {
    const base = subscription?.term_end ? new Date(subscription.term_end) : new Date();
    const newEnd = new Date(base.getTime() + days * 24 * 60 * 60 * 1000);
    setTermEnd(format(newEnd, "yyyy-MM-dd"));
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Edit Device Subscription</DialogTitle>
          <DialogDescription>
            Tenant: {tenantId}
            {subscription ? ` · Device: ${subscription.device_id}` : ""}
          </DialogDescription>
        </DialogHeader>

        {!subscription ? (
          <div className="py-4 text-sm text-muted-foreground">No subscription selected.</div>
        ) : (
          <div className="space-y-5 py-4">
            <div className="space-y-2">
              <div className="text-xs text-muted-foreground">Quick extend</div>
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" size="sm" onClick={() => extendTerm(30)}>
                  <CalendarPlus className="mr-1 h-3 w-3" />
                  +30 Days
                </Button>
                <Button variant="outline" size="sm" onClick={() => extendTerm(90)}>
                  <CalendarPlus className="mr-1 h-3 w-3" />
                  +90 Days
                </Button>
                <Button variant="outline" size="sm" onClick={() => extendTerm(365)}>
                  <CalendarPlus className="mr-1 h-3 w-3" />
                  +1 Year
                </Button>
              </div>
            </div>

            <div className="space-y-2">
              <div className="text-sm font-medium">Plan</div>
              <Select value={planId} onValueChange={setPlanId}>
                <SelectTrigger>
                  <SelectValue />
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
              <div className="text-sm font-medium">Status</div>
              <Select value={status} onValueChange={setStatus}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {STATUSES.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <div className="text-sm font-medium">Term End (optional)</div>
              <Input
                type="date"
                value={termEnd}
                onChange={(e) => setTermEnd(e.target.value)}
              />
            </div>
          </div>
        )}

        {mutation.isError && (
          <p className="text-sm text-destructive">
            Error: {(mutation.error as Error).message}
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

