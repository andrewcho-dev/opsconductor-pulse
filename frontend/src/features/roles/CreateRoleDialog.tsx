import { useEffect, useMemo, useState } from "react";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { PermissionGrid } from "./PermissionGrid";
import { useCreateRole, usePermissionsList, useUpdateRole } from "@/hooks/use-roles";
import type { Role } from "@/services/api/roles";
import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
} from "@/components/ui/form";

const createRoleSchema = z.object({
  name: z.string().min(1, "Role name is required").max(50),
  description: z.string().max(200).optional(),
});

type CreateRoleFormValues = z.infer<typeof createRoleSchema>;

interface CreateRoleDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
  editRole?: Role;
}

export function CreateRoleDialog({ open, onOpenChange, onSaved, editRole }: CreateRoleDialogProps) {
  const { data: permissionsData, isLoading: isLoadingPermissions, error } = usePermissionsList();
  const createMutation = useCreateRole();
  const updateMutation = useUpdateRole();

  const allPermissions = permissionsData?.permissions ?? [];

  const [selectedPermissionIds, setSelectedPermissionIds] = useState<Set<number>>(new Set());

  const form = useForm<CreateRoleFormValues>({
    resolver: zodResolver(createRoleSchema),
    defaultValues: { name: "", description: "" },
    mode: "onChange",
  });

  useEffect(() => {
    if (!open) return;
    if (editRole) {
      form.reset({ name: editRole.name, description: editRole.description || "" });
      setSelectedPermissionIds(new Set(editRole.permissions.map((p) => p.id)));
    } else {
      form.reset({ name: "", description: "" });
      setSelectedPermissionIds(new Set());
    }
  }, [open, editRole, form]);

  const selectedCount = selectedPermissionIds.size;
  const totalCount = allPermissions.length;

  const canSave = useMemo(() => {
    if (!form.formState.isValid) return false;
    if (selectedPermissionIds.size === 0) return false;
    if (createMutation.isPending || updateMutation.isPending) return false;
    return true;
  }, [form.formState.isValid, selectedPermissionIds, createMutation.isPending, updateMutation.isPending]);

  const handleSave = async () => {
    const valid = await form.trigger();
    if (!valid) return;
    const values = form.getValues();
    const payload = {
      name: values.name.trim(),
      description: values.description?.trim() || "",
      permission_ids: Array.from(selectedPermissionIds),
    };
    if (editRole) {
      await updateMutation.mutateAsync({ roleId: editRole.id, data: payload });
    } else {
      await createMutation.mutateAsync(payload);
    }
    onSaved();
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{editRole ? "Edit Role" : "Create Custom Role"}</DialogTitle>
        </DialogHeader>

        {error ? (
          <div className="text-sm text-destructive">Failed to load permissions: {(error as Error).message}</div>
        ) : isLoadingPermissions ? (
          <div className="space-y-3">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-64 w-full" />
          </div>
        ) : (
          <Form {...form}>
            <div className="space-y-4">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Name *</FormLabel>
                    <FormControl>
                      <Input id="role-name" placeholder="e.g. Device Operator" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="description"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Description</FormLabel>
                    <FormControl>
                      <Input id="role-description" placeholder="Optional" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="space-y-2">
                <div className="text-sm font-medium">Permissions</div>
                <PermissionGrid
                  permissions={allPermissions}
                  selectedIds={selectedPermissionIds}
                  onChange={setSelectedPermissionIds}
                />
                <div className="text-sm text-muted-foreground">
                  Selected: {selectedCount} of {totalCount} permissions
                </div>
              </div>

              {(createMutation.isError || updateMutation.isError) && (
                <div className="text-sm text-destructive">
                  {((createMutation.error || updateMutation.error) as Error).message}
                </div>
              )}
            </div>
          </Form>
        )}

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="button" onClick={handleSave} disabled={!canSave}>
            {createMutation.isPending || updateMutation.isPending
              ? "Saving..."
              : editRole
                ? "Save Changes"
                : "Create Role"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

