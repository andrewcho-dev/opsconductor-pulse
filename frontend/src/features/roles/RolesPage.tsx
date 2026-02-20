import { useMemo, useState } from "react";
import { ChevronDown, ChevronRight, Lock, Pencil, Plus, Trash2 } from "lucide-react";

import { PageHeader } from "@/components/shared";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
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
import { useDeleteRole, useRoles } from "@/hooks/use-roles";
import { usePermissions } from "@/services/auth";
import type { Role } from "@/services/api/roles";
import { CreateRoleDialog } from "./CreateRoleDialog";

function RoleRow({
  role,
  expanded,
  onToggle,
  actions,
}: {
  role: Role;
  expanded: boolean;
  onToggle: () => void;
  actions?: React.ReactNode;
}) {
  const permCount = role.permissions?.length ?? 0;
  return (
    <div className="rounded-md border">
      <div className="flex items-center justify-between p-3">
        <Button type="button" variant="ghost" className="flex items-center gap-2 px-2 -ml-2" onClick={onToggle}>
          {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          {role.is_system && <Lock className="h-4 w-4 text-muted-foreground" />}
          <div className="text-sm font-medium">{role.name}</div>
          <Badge variant="secondary">{permCount} permissions</Badge>
        </Button>
        <div className="flex items-center gap-2">{actions}</div>
      </div>
      {expanded && (
        <div className="border-t p-3">
          <div className="flex flex-wrap gap-1">
            {role.permissions
              .slice()
              .sort((a, b) => a.category.localeCompare(b.category) || a.action.localeCompare(b.action))
              .map((p) => (
                <Badge key={p.action} variant="outline">
                  {p.action}
                </Badge>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function RolesPage({ embedded }: { embedded?: boolean }) {
  const { hasPermission } = usePermissions();
  const { data, isLoading, error, refetch } = useRoles();
  const deleteMutation = useDeleteRole();

  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editRole, setEditRole] = useState<Role | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [confirmDeleteRole, setConfirmDeleteRole] = useState<Role | null>(null);

  const systemRoles = useMemo(() => data?.roles?.filter((r) => r.is_system) ?? [], [data]);
  const customRoles = useMemo(() => data?.roles?.filter((r) => !r.is_system) ?? [], [data]);

  if (!hasPermission("users.roles")) {
    return <div className="text-muted-foreground">You don't have permission to manage roles.</div>;
  }

  const toggleExpanded = (roleId: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(roleId)) next.delete(roleId);
      else next.add(roleId);
      return next;
    });
  };

  const handleDelete = (role: Role) => {
    setConfirmDeleteRole(role);
  };

  const actions = (
    <Button onClick={() => setCreateDialogOpen(true)}>
      <Plus className="mr-1 h-4 w-4" />
      Add Role
    </Button>
  );

  return (
    <div className="space-y-4">
      {!embedded ? (
        <PageHeader
          title="Roles & Permissions"
          description="Manage role bundles for your organization"
          action={actions}
        />
      ) : (
        <div className="flex justify-end gap-2 mb-4">{actions}</div>
      )}

      {error ? (
        <div className="text-destructive">Failed to load roles: {(error as Error).message}</div>
      ) : isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Skeleton key={i} className="h-14 w-full" />
          ))}
        </div>
      ) : (
        <div className="space-y-6">
          <div className="space-y-2">
            <div className="text-sm font-medium">System Roles (read-only)</div>
            <div className="space-y-2">
              {systemRoles.map((role) => (
                <RoleRow
                  key={role.id}
                  role={role}
                  expanded={expanded.has(role.id)}
                  onToggle={() => toggleExpanded(role.id)}
                  actions={
                    <Button variant="outline" size="sm" onClick={() => toggleExpanded(role.id)}>
                      {expanded.has(role.id) ? "Hide" : "View"}
                    </Button>
                  }
                />
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <div className="text-sm font-medium">Custom Roles</div>
            {customRoles.length === 0 ? (
              <div className="rounded-md border p-4 text-sm text-muted-foreground">No custom roles yet.</div>
            ) : (
              <div className="space-y-2">
                {customRoles.map((role) => (
                  <RoleRow
                    key={role.id}
                    role={role}
                    expanded={expanded.has(role.id)}
                    onToggle={() => toggleExpanded(role.id)}
                    actions={
                      <>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            setEditRole(role);
                            setCreateDialogOpen(true);
                          }}
                        >
                          <Pencil className="mr-2 h-4 w-4" />
                          Edit
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="text-destructive"
                          onClick={() => handleDelete(role)}
                          disabled={deleteMutation.isPending}
                        >
                          <Trash2 className="mr-2 h-4 w-4" />
                          Delete
                        </Button>
                      </>
                    }
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      <CreateRoleDialog
        open={createDialogOpen}
        onOpenChange={(open) => {
          setCreateDialogOpen(open);
          if (!open) setEditRole(null);
        }}
        editRole={editRole ?? undefined}
        onSaved={() => {
          setCreateDialogOpen(false);
          setEditRole(null);
          refetch();
        }}
      />

      <AlertDialog open={!!confirmDeleteRole} onOpenChange={(open) => !open && setConfirmDeleteRole(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Role</AlertDialogTitle>
            <AlertDialogDescription>
              Delete role "{confirmDeleteRole?.name}"? This will remove it from all users.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={async () => {
                if (confirmDeleteRole) await deleteMutation.mutateAsync(confirmDeleteRole.id);
                setConfirmDeleteRole(null);
              }}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

