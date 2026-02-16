import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { PermissionGrid } from "./PermissionGrid";
import { useCreateRole, usePermissionsList, useUpdateRole } from "@/hooks/use-roles";
import type { Role } from "@/services/api/roles";

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

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [selectedPermissionIds, setSelectedPermissionIds] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (!open) return;
    if (editRole) {
      setName(editRole.name);
      setDescription(editRole.description || "");
      setSelectedPermissionIds(new Set(editRole.permissions.map((p) => p.id)));
    } else {
      setName("");
      setDescription("");
      setSelectedPermissionIds(new Set());
    }
  }, [open, editRole]);

  const selectedCount = selectedPermissionIds.size;
  const totalCount = allPermissions.length;

  const canSave = useMemo(() => {
    if (!name.trim()) return false;
    if (selectedPermissionIds.size === 0) return false;
    if (createMutation.isPending || updateMutation.isPending) return false;
    return true;
  }, [name, selectedPermissionIds, createMutation.isPending, updateMutation.isPending]);

  const handleSave = async () => {
    const payload = {
      name: name.trim(),
      description: description.trim(),
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
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="role-name">Name</Label>
              <Input
                id="role-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Device Operator"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="role-description">Description</Label>
              <Input
                id="role-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Optional"
              />
            </div>

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

