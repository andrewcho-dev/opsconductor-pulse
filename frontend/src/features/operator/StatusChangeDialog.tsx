import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { StatusBadge } from "@/components/shared";
import { apiPatch } from "@/services/api/client";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/errors";
import type { DeviceSubscriptionRow } from "@/services/api/operator";

interface StatusChangeDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  subscription: DeviceSubscriptionRow;
  onUpdated: () => void;
}

export function StatusChangeDialog({
  open,
  onOpenChange,
  subscription,
  onUpdated,
}: StatusChangeDialogProps) {
  const [newStatus, setNewStatus] = useState<string>(subscription.status);

  const mutation = useMutation({
    mutationFn: () =>
      apiPatch(
        `/api/v1/operator/device-subscriptions/${encodeURIComponent(subscription.subscription_id)}`,
        { status: newStatus }
      ),
    onSuccess: () => {
      onUpdated();
      toast.success("Status updated");
    },
    onError: (err: Error) => {
      toast.error(getErrorMessage(err) || "Failed to update status");
    },
  });

  const statusOptions = ["TRIAL", "ACTIVE", "GRACE", "SUSPENDED", "EXPIRED"];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Change Subscription Status</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="rounded-md bg-muted p-3">
            <p className="text-sm">
              Current status:{" "}
              <StatusBadge status={subscription.status} variant="subscription" />
            </p>
          </div>
          <div className="space-y-2">
            <Label>New Status</Label>
            <Select value={newStatus} onValueChange={setNewStatus}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {statusOptions.map((s) => (
                  <SelectItem key={s} value={s}>
                    {s}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {newStatus === "SUSPENDED" && (
            <div className="rounded-md bg-orange-50 p-3 text-sm dark:bg-orange-950">
              <p className="font-medium text-orange-800 dark:text-orange-200">
                Warning
              </p>
              <p className="text-orange-700 dark:text-orange-300">
                Suspending will block telemetry ingest for all devices on this
                subscription.
              </p>
            </div>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={() => mutation.mutate()}
            disabled={newStatus === subscription.status || mutation.isPending}
            variant={newStatus === "SUSPENDED" ? "destructive" : "default"}
          >
            {mutation.isPending ? "Updating..." : `Set to ${newStatus}`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
