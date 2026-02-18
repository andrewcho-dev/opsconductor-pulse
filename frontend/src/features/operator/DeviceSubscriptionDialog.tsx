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
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { apiGet, apiPost } from "@/services/api/client";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/errors";

interface SubscriptionRow {
  subscription_id: string;
  subscription_type: string;
  device_limit: number;
  active_device_count: number;
  status: string;
}

interface SubscriptionListResponse {
  subscriptions: SubscriptionRow[];
}

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
  const [targetSubscriptionId, setTargetSubscriptionId] = useState("");
  const [notes, setNotes] = useState("");

  useEffect(() => {
    if (open) {
      setTargetSubscriptionId("");
      setNotes("");
    }
  }, [open]);

  const queryString = useMemo(() => {
    const params = new URLSearchParams();
    params.set("tenant_id", tenantId);
    params.set("status", "ACTIVE");
    params.set("limit", "200");
    return params.toString();
  }, [tenantId]);

  const { data } = useQuery({
    queryKey: ["operator-device-subscriptions", queryString],
    queryFn: () =>
      apiGet<SubscriptionListResponse>(`/operator/subscriptions?${queryString}`),
    enabled: open,
  });

  const subscriptions = data?.subscriptions ?? [];
  const selected = subscriptions.find(
    (sub) => sub.subscription_id === targetSubscriptionId
  );

  const mutation = useMutation({
    mutationFn: async () =>
      apiPost(`/operator/devices/${deviceId}/subscription`, {
        subscription_id: targetSubscriptionId,
        notes,
      }),
    onSuccess: () => {
      onAssigned();
      toast.success("Subscription assigned");
    },
    onError: (err: Error) => {
      toast.error(getErrorMessage(err) || "Failed to assign subscription");
    },
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Assign Subscription</DialogTitle>
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
                <Badge variant="secondary">Unassigned</Badge>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <span className="text-sm font-medium">Target Subscription</span>
            <Select value={targetSubscriptionId} onValueChange={setTargetSubscriptionId}>
              <SelectTrigger>
                <SelectValue placeholder="Select subscription" />
              </SelectTrigger>
              <SelectContent>
                {subscriptions.map((sub) => {
                  const isFull = sub.active_device_count >= sub.device_limit;
                  const isCurrent = sub.subscription_id === currentSubscriptionId;
                  return (
                    <SelectItem
                      key={sub.subscription_id}
                      value={sub.subscription_id}
                      disabled={isFull || isCurrent}
                    >
                      {sub.subscription_id} ({sub.active_device_count}/{sub.device_limit})
                    </SelectItem>
                  );
                })}
              </SelectContent>
            </Select>
            {selected && selected.active_device_count >= selected.device_limit && (
              <p className="text-xs text-destructive">
                Subscription is at device limit.
              </p>
            )}
          </div>

          <div className="space-y-2">
            <span className="text-sm font-medium">Notes</span>
            <Textarea
              placeholder="Reason for assignment (required)"
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              rows={3}
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
            disabled={!targetSubscriptionId || !notes.trim() || mutation.isPending}
          >
            {mutation.isPending ? "Assigning..." : "Assign"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
