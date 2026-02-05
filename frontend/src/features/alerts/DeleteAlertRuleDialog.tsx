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
import { ApiError } from "@/services/api/client";
import { useMemo } from "react";

interface DeleteAlertRuleDialogProps {
  open: boolean;
  rule: AlertRule | null;
  onClose: () => void;
}

function formatError(error: unknown): string {
  if (!error) return "";
  if (error instanceof ApiError) {
    if (typeof error.body === "string") return error.body;
    if (error.body && typeof error.body === "object") {
      const detail = (error.body as { detail?: string }).detail;
      if (detail) return detail;
    }
    return error.message;
  }
  if (error instanceof Error) return error.message;
  return "Unknown error";
}

export function DeleteAlertRuleDialog({
  open,
  rule,
  onClose,
}: DeleteAlertRuleDialogProps) {
  const deleteMutation = useDeleteAlertRule();
  const errorMessage = useMemo(
    () => formatError(deleteMutation.error),
    [deleteMutation.error]
  );

  async function handleDelete() {
    if (!rule) return;
    await deleteMutation.mutateAsync(String(rule.rule_id));
    onClose();
  }

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => !nextOpen && onClose()}>
      <DialogContent>
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
