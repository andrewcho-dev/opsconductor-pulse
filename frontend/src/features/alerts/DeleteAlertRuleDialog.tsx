import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useDeleteAlertRule } from "@/hooks/use-alert-rules";
import type { AlertRule } from "@/services/api/types";
import { getErrorMessage } from "@/lib/errors";
import { toast } from "sonner";
import { useMemo } from "react";

interface DeleteAlertRuleDialogProps {
  open: boolean;
  rule: AlertRule | null;
  onClose: () => void;
}

export function DeleteAlertRuleDialog({
  open,
  rule,
  onClose,
}: DeleteAlertRuleDialogProps) {
  const deleteMutation = useDeleteAlertRule();
  const errorMessage = useMemo(
    () => (deleteMutation.error ? getErrorMessage(deleteMutation.error) : null),
    [deleteMutation.error]
  );

  async function handleDelete() {
    if (!rule) return;
    await deleteMutation.mutateAsync(String(rule.rule_id));
    toast.success("Alert rule deleted");
    onClose();
  }

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => !nextOpen && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Delete Alert Rule</DialogTitle>
          <DialogDescription>
            Delete alert rule &quot;{rule?.name}&quot;? This cannot be undone.
          </DialogDescription>
        </DialogHeader>

        {errorMessage && (
          <div className="text-sm text-destructive">{errorMessage}</div>
        )}

        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="button"
            variant="destructive"
            onClick={handleDelete}
            disabled={!rule || deleteMutation.isPending}
          >
            {deleteMutation.isPending ? "Deleting..." : "Delete"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
