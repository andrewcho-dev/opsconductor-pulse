"use client"

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { format } from "date-fns";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
import { apiPost } from "@/services/api/client";
import { CalendarPlus, AlertTriangle, CheckCircle, XCircle } from "lucide-react";

interface Subscription {
  tenant_id: string;
  device_limit: number;
  active_device_count: number;
  term_start: string | null;
  term_end: string | null;
  plan_id: string | null;
  status: string;
  grace_end: string | null;
}

interface EditSubscriptionDialogProps {
  tenantId: string;
  subscription: Subscription | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
}

const STATUSES = ["TRIAL", "ACTIVE", "GRACE", "SUSPENDED", "EXPIRED"];

export function EditSubscriptionDialog({
  tenantId,
  subscription,
  open,
  onOpenChange,
  onSaved,
}: EditSubscriptionDialogProps) {
  const [deviceLimit, setDeviceLimit] = useState(
    subscription?.device_limit?.toString() || "100"
  );
  const [termEnd, setTermEnd] = useState(
    subscription?.term_end
      ? format(new Date(subscription.term_end), "yyyy-MM-dd")
      : format(new Date(Date.now() + 365 * 24 * 60 * 60 * 1000), "yyyy-MM-dd")
  );
  const [status, setStatus] = useState(subscription?.status || "ACTIVE");
  const [notes, setNotes] = useState("");
  const [transactionRef, setTransactionRef] = useState("");

  const [showConfirm, setShowConfirm] = useState(false);
  const [pendingAction, setPendingAction] = useState<{
    type: string;
    data: Record<string, unknown>;
  } | null>(null);

  const handleOpenChange = (isOpen: boolean) => {
    if (isOpen && subscription) {
      setDeviceLimit(subscription.device_limit?.toString() || "100");
      setTermEnd(
        subscription.term_end
          ? format(new Date(subscription.term_end), "yyyy-MM-dd")
          : format(new Date(Date.now() + 365 * 24 * 60 * 60 * 1000), "yyyy-MM-dd")
      );
      setStatus(subscription.status || "ACTIVE");
      setNotes("");
      setTransactionRef("");
    }
    onOpenChange(isOpen);
  };

  const mutation = useMutation({
    mutationFn: async (data: Record<string, unknown>) => {
      return apiPost(`/operator/tenants/${tenantId}/subscription`, data);
    },
    onSuccess: () => {
      onSaved();
    },
  });

  const handleSave = () => {
    const data = {
      device_limit: parseInt(deviceLimit, 10),
      term_end: new Date(termEnd).toISOString(),
      status,
      notes: notes || undefined,
      transaction_ref: transactionRef || undefined,
    };

    if (status === "SUSPENDED" || status === "EXPIRED") {
      setPendingAction({ type: "status_change", data });
      setShowConfirm(true);
      return;
    }

    if (
      subscription &&
      parseInt(deviceLimit, 10) < subscription.active_device_count
    ) {
      setPendingAction({ type: "limit_reduction", data });
      setShowConfirm(true);
      return;
    }

    mutation.mutate(data);
  };

  const confirmAction = () => {
    if (pendingAction) {
      mutation.mutate(pendingAction.data);
      setPendingAction(null);
      setShowConfirm(false);
    }
  };

  const extendTerm = (days: number) => {
    const currentEnd = subscription?.term_end
      ? new Date(subscription.term_end)
      : new Date();
    const newEnd = new Date(currentEnd.getTime() + days * 24 * 60 * 60 * 1000);
    setTermEnd(format(newEnd, "yyyy-MM-dd"));
  };

  const quickActivate = () => {
    setStatus("ACTIVE");
    setNotes("Manually activated by operator");
  };

  const quickSuspend = () => {
    setStatus("SUSPENDED");
    setNotes("Manually suspended by operator");
  };

  return (
    <>
      <Dialog open={open} onOpenChange={handleOpenChange}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {subscription ? "Edit Subscription" : "Create Subscription"}
            </DialogTitle>
            <DialogDescription>
              Manage subscription for tenant: {tenantId}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-6 py-4">
            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground">Quick Actions</Label>
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
                {subscription?.status !== "ACTIVE" && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="border-green-500 text-green-600 hover:bg-green-50"
                    onClick={quickActivate}
                  >
                    <CheckCircle className="mr-1 h-3 w-3" />
                    Activate
                  </Button>
                )}
                {subscription?.status === "ACTIVE" && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="border-red-500 text-red-600 hover:bg-red-50"
                    onClick={quickSuspend}
                  >
                    <XCircle className="mr-1 h-3 w-3" />
                    Suspend
                  </Button>
                )}
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="deviceLimit">Device Limit</Label>
              <Input
                id="deviceLimit"
                type="number"
                min="0"
                value={deviceLimit}
                onChange={(e) => setDeviceLimit(e.target.value)}
              />
              {subscription && parseInt(deviceLimit, 10) < subscription.active_device_count && (
                <p className="text-xs text-orange-600">
                  Warning: Current usage ({subscription.active_device_count}) exceeds this
                  limit. Tenant will need to remove devices.
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="termEnd">Term End Date</Label>
              <Input
                id="termEnd"
                type="date"
                value={termEnd}
                onChange={(e) => setTermEnd(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="status">Status</Label>
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
              <Label htmlFor="transactionRef">
                Transaction/Approval Reference
                <span className="text-muted-foreground font-normal"> (optional)</span>
              </Label>
              <Input
                id="transactionRef"
                placeholder="e.g., INV-2024-001, PO-12345"
                value={transactionRef}
                onChange={(e) => setTransactionRef(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="notes">
                Notes / Reason
                <span className="text-destructive"> *</span>
              </Label>
              <Textarea
                id="notes"
                placeholder="Reason for this change (required for audit log)"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={!notes.trim() || mutation.isPending}>
              {mutation.isPending ? "Saving..." : "Save Changes"}
            </Button>
          </DialogFooter>

          {mutation.isError && (
            <p className="text-sm text-destructive">
              Error: {(mutation.error as Error).message}
            </p>
          )}
        </DialogContent>
      </Dialog>

      <AlertDialog open={showConfirm} onOpenChange={setShowConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-orange-500" />
              Confirm Action
            </AlertDialogTitle>
            <AlertDialogDescription>
              {pendingAction?.type === "status_change" && (
                <>
                  You are about to set the subscription status to <strong>{status}</strong>.
                  This will:
                  <ul className="mt-2 list-disc pl-6">
                    {status === "SUSPENDED" && (
                      <>
                        <li>Block all UI access for this tenant</li>
                        <li>Reject all incoming telemetry</li>
                      </>
                    )}
                    {status === "EXPIRED" && (
                      <>
                        <li>Block all access for this tenant</li>
                        <li>Mark subscription for data retention review</li>
                      </>
                    )}
                  </ul>
                </>
              )}
              {pendingAction?.type === "limit_reduction" && (
                <>
                  The new device limit ({deviceLimit}) is below the current usage (
                  {subscription?.active_device_count}). The tenant will need to remove
                  devices to comply.
                </>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={confirmAction}>Confirm</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
