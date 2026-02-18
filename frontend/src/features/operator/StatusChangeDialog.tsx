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
import { Textarea } from "@/components/ui/textarea";
import { StatusBadge } from "@/components/shared";
import { apiPatch } from "@/services/api/client";
import type { SubscriptionDetail } from "@/services/api/types";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/errors";

interface StatusChangeDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  subscription: SubscriptionDetail;
  onUpdated: () => void;
}

export function StatusChangeDialog({
  open,
  onOpenChange,
  subscription,
  onUpdated,
}: StatusChangeDialogProps) {
  const [newStatus, setNewStatus] = useState<string>(subscription.status);
  const [notes, setNotes] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      apiPatch(`/operator/subscriptions/${subscription.subscription_id}`, {
        status: newStatus,
        notes,
      }),
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
          <div className="space-y-2">
            <Label>Notes (required for audit)</Label>
            <Textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Reason for status change..."
              rows={2}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={() => mutation.mutate()}
            disabled={!notes || newStatus === subscription.status || mutation.isPending}
            variant={newStatus === "SUSPENDED" ? "destructive" : "default"}
          >
            {mutation.isPending ? "Updating..." : `Set to ${newStatus}`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
