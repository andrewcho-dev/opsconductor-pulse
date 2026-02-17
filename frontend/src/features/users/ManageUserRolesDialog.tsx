import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { usePermissions } from "@/services/auth/PermissionProvider";
import { useRoles, useUpdateUserAssignments, useUserAssignments } from "@/hooks/use-roles";
import { useTenantUser } from "@/hooks/use-users";

interface ManageUserRolesDialogProps {
  userId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
}

export function ManageUserRolesDialog({
  userId,
  open,
  onOpenChange,
  onSaved,
}: ManageUserRolesDialogProps) {
  const { data: user } = useTenantUser(userId);
  const { data: assignmentsData, isLoading: isLoadingAssignments } = useUserAssignments(userId);
  const { data: rolesData, isLoading: isLoadingRoles } = useRoles();
  const updateMutation = useUpdateUserAssignments();
  const { refetchPermissions } = usePermissions();

  const [selectedRoleIds, setSelectedRoleIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!open) return;
    const current = new Set((assignmentsData?.assignments ?? []).map((a) => a.role_id));
    setSelectedRoleIds(current);
  }, [open, assignmentsData]);

  const effectivePermissions = useMemo(() => {
    if (!rolesData?.roles) return [];
    const perms = new Map<string, { action: string; category: string }>();
    for (const role of rolesData.roles) {
      if (selectedRoleIds.has(role.id)) {
        for (const perm of role.permissions) {
          perms.set(perm.action, { action: perm.action, category: perm.category });
        }
      }
    }
    return Array.from(perms.values()).sort(
      (a, b) => a.category.localeCompare(b.category) || a.action.localeCompare(b.action),
    );
  }, [rolesData, selectedRoleIds]);

  const permsByCategory = useMemo(() => {
    const grouped: Record<string, string[]> = {};
    for (const p of effectivePermissions) {
      grouped[p.category] ||= [];
      grouped[p.category].push(p.action);
    }
    return grouped;
  }, [effectivePermissions]);

  const systemRoles = (rolesData?.roles ?? []).filter((r) => r.is_system);
  const customRoles = (rolesData?.roles ?? []).filter((r) => !r.is_system);

  const toggleRole = (roleId: string, checked: boolean) => {
    setSelectedRoleIds((prev) => {
      const next = new Set(prev);
      if (checked) next.add(roleId);
      else next.delete(roleId);
      return next;
    });
  };

  const handleSave = async () => {
    const roleIds = Array.from(selectedRoleIds);
    await updateMutation.mutateAsync({ userId, roleIds });
    refetchPermissions();
    onSaved();
  };

  const isLoading = isLoadingAssignments || isLoadingRoles;
  const canSave = selectedRoleIds.size > 0 && !updateMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>Manage Roles</DialogTitle>
        </DialogHeader>

        <div className="text-sm text-muted-foreground">
          Assigning roles for:{" "}
          <strong>
            {[user?.first_name, user?.last_name].filter(Boolean).join(" ") || user?.username || userId}
          </strong>
        </div>

        {isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-24 w-full" />
          </div>
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-4">
              <div className="rounded-lg border p-3">
                <div className="mb-2 text-sm font-medium">System Roles</div>
                <div className="space-y-2">
                  {systemRoles.map((role) => (
                    <div key={role.id} className="flex items-start gap-3 rounded-md border p-3">
                      <Checkbox
                        checked={selectedRoleIds.has(role.id)}
                        onCheckedChange={(checked) => toggleRole(role.id, checked)}
                        className="mt-1"
                      />
                      <Label className="flex-1 cursor-pointer">
                        <div className="font-medium">{role.name}</div>
                        <div className="text-sm text-muted-foreground">{role.description}</div>
                      </Label>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-lg border p-3">
                <div className="mb-2 text-sm font-medium">Custom Roles</div>
                {customRoles.length === 0 ? (
                  <div className="text-sm text-muted-foreground">No custom roles yet.</div>
                ) : (
                  <div className="space-y-2">
                    {customRoles.map((role) => (
                      <div key={role.id} className="flex items-start gap-3 rounded-md border p-3">
                        <Checkbox
                          checked={selectedRoleIds.has(role.id)}
                          onCheckedChange={(checked) => toggleRole(role.id, checked)}
                          className="mt-1"
                        />
                        <Label className="flex-1 cursor-pointer">
                          <div className="font-medium">{role.name}</div>
                          <div className="text-sm text-muted-foreground">{role.description}</div>
                        </Label>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="rounded-lg border p-3">
              <div className="mb-2 text-sm font-medium">Effective Permissions</div>
              {effectivePermissions.length === 0 ? (
                <div className="text-sm text-muted-foreground">Select at least one role to preview permissions.</div>
              ) : (
                <div className="space-y-3">
                  {Object.entries(permsByCategory).map(([category, actions]) => (
                    <div key={category}>
                      <div className="mb-1 text-xs font-medium text-muted-foreground">{category}</div>
                      <div className="flex flex-wrap gap-1">
                        {actions.map((action) => (
                          <Badge key={action} variant="secondary">
                            {action}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {updateMutation.isError && (
          <div className="text-sm text-destructive">{(updateMutation.error as Error).message}</div>
        )}

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="button" onClick={handleSave} disabled={!canSave}>
            {updateMutation.isPending ? "Saving..." : "Save Roles"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

