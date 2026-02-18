import { useEffect } from "react";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { useAssignOperatorUserTenant, useOperatorUser, useOrganizations } from "@/hooks/use-users";
import { useFormDirtyGuard } from "@/hooks/use-form-dirty-guard";
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

interface AssignTenantDialogProps {
  userId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAssigned: () => void;
}

const assignTenantSchema = z.object({
  tenant_id: z.string().min(1, "Please select a tenant"),
});

type AssignTenantFormValues = z.infer<typeof assignTenantSchema>;

export function AssignTenantDialog({
  userId,
  open,
  onOpenChange,
  onAssigned,
}: AssignTenantDialogProps) {
  const { data: user } = useOperatorUser(userId);
  const { data: orgsData } = useOrganizations();
  const assignMutation = useAssignOperatorUserTenant();

  const form = useForm<AssignTenantFormValues>({
    resolver: zodResolver(assignTenantSchema),
    defaultValues: { tenant_id: "" },
  });

  const { handleClose, showConfirm, confirmDiscard, cancelDiscard } = useFormDirtyGuard({
    form,
    onClose: () => onOpenChange(false),
  });

  const tenantValue = form.watch("tenant_id");

  useEffect(() => {
    if (!open) return;
    form.reset({ tenant_id: "" });
  }, [form, open]);

  const onSubmit = async (values: AssignTenantFormValues) => {
    try {
      await assignMutation.mutateAsync({ userId, tenantId: values.tenant_id });
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
            <DialogTitle>Assign Tenant</DialogTitle>
          </DialogHeader>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <div className="text-sm text-muted-foreground">
              Assigning tenant for user: <strong>{user?.username}</strong>
            </div>
            {user?.tenant_id && (
              <div className="text-sm">
                Current tenant: <code className="rounded bg-muted px-1">{user.tenant_id}</code>
              </div>
            )}

            <FormField
              control={form.control}
              name="tenant_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>New Tenant</FormLabel>
                  <Select value={field.value} onValueChange={field.onChange}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select tenant..." />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {orgsData?.organizations?.map((org) => (
                        <SelectItem key={org.id} value={org.alias || org.name}>
                          {org.alias || org.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
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
              <Button type="submit" disabled={!tenantValue || assignMutation.isPending}>
                {assignMutation.isPending ? "Assigning..." : "Assign Tenant"}
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
