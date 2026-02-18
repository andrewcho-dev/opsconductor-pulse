import { useEffect } from "react";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { useAssignOperatorUserRole, useOperatorUser } from "@/hooks/use-users";
import { useFormDirtyGuard } from "@/hooks/use-form-dirty-guard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";

interface AssignRoleDialogProps {
  userId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAssigned: () => void;
}

const AVAILABLE_ROLES = [
  { value: "customer", label: "Customer", description: "Basic tenant access" },
  { value: "tenant-admin", label: "Tenant Admin", description: "Manage tenant users and settings" },
  { value: "operator", label: "Operator", description: "View all tenants" },
  { value: "operator-admin", label: "Operator Admin", description: "Full system administration" },
];

const assignRoleSchema = z.object({
  role_id: z.string().min(1, "Please select a role"),
});

type AssignRoleFormValues = z.infer<typeof assignRoleSchema>;

export function AssignRoleDialog({ userId, open, onOpenChange, onAssigned }: AssignRoleDialogProps) {
  const { data: user } = useOperatorUser(userId);
  const assignMutation = useAssignOperatorUserRole();
  const form = useForm<AssignRoleFormValues>({
    resolver: zodResolver(assignRoleSchema),
    defaultValues: { role_id: "" },
  });

  const { handleClose, showConfirm, confirmDiscard, cancelDiscard } = useFormDirtyGuard({
    form,
    onClose: () => onOpenChange(false),
  });

  const roleValue = form.watch("role_id");

  useEffect(() => {
    if (!open) return;
    form.reset({ role_id: "" });
  }, [form, open]);

  const onSubmit = async (values: AssignRoleFormValues) => {
    try {
      await assignMutation.mutateAsync({ userId, role: values.role_id });
      onAssigned();
    } catch {
      // mutation state shows error
    }
  };

  return (
    <>
      <Dialog
        open={open}
        onOpenChange={(openState) => {
          if (!openState) handleClose();
          else onOpenChange(true);
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Assign Role</DialogTitle>
          </DialogHeader>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <div className="text-sm text-muted-foreground">
              Assigning role for user: <strong>{user?.username}</strong>
            </div>
            {user?.roles && user.roles.length > 0 && (
              <div className="space-y-1">
                <div className="text-sm">Current roles:</div>
                <div className="flex flex-wrap gap-1">
                  {user.roles.map((r) => (
                    <Badge key={r} variant="secondary">
                      {r}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            <FormField
              control={form.control}
              name="role_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Add Role</FormLabel>
                  <Select value={field.value} onValueChange={field.onChange}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select role..." />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {AVAILABLE_ROLES.map((r) => (
                        <SelectItem key={r.value} value={r.value}>
                          {r.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <div className="text-xs text-muted-foreground">
                    {AVAILABLE_ROLES.find((r) => r.value === roleValue)?.description || ""}
                  </div>
                  <FormMessage />
                </FormItem>
              )}
            />

            {assignMutation.isError && (
              <div className="text-sm text-destructive">{(assignMutation.error as Error).message}</div>
            )}
            <DialogFooter>
              <Button type="button" variant="outline" onClick={handleClose}>
                Cancel
              </Button>
              <Button type="submit" disabled={!roleValue || assignMutation.isPending}>
                {assignMutation.isPending ? "Assigning..." : "Assign Role"}
              </Button>
            </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      <AlertDialog open={showConfirm} onOpenChange={cancelDiscard}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Discard changes?</AlertDialogTitle>
            <AlertDialogDescription>
              You have unsaved changes. Are you sure you want to close without saving?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={cancelDiscard}>Keep Editing</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDiscard}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Discard
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
