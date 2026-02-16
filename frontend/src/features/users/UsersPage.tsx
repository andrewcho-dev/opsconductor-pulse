import { useState } from "react";
import { Key, MoreHorizontal, Pencil, Plus, Search, Shield, UserMinus } from "lucide-react";
import { type ColumnDef, type PaginationState } from "@tanstack/react-table";

import { PageHeader } from "@/components/shared";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { DataTable } from "@/components/ui/data-table";
import { useRemoveTenantUser, useSendTenantPasswordReset, useTenantUsers } from "@/hooks/use-users";
import { useAuth } from "@/services/auth/AuthProvider";
import { ManageUserRolesDialog } from "./ManageUserRolesDialog";
import { EditTenantUserDialog } from "./EditTenantUserDialog";
import { InviteUserDialog } from "./InviteUserDialog";

type TenantUser = {
  id: string;
  username: string;
  email: string;
  first_name?: string | null;
  last_name?: string | null;
  enabled: boolean;
  roles?: string[] | null;
};

export default function UsersPage() {
  const { user: currentUser } = useAuth();
  const currentUserId = currentUser?.sub;
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [page, setPage] = useState(1);
  const limit = 50;
  const offset = (page - 1) * limit;

  const { data, isLoading, error, refetch } = useTenantUsers(search || undefined, limit, offset);
  const removeMutation = useRemoveTenantUser();
  const resetPasswordMutation = useSendTenantPasswordReset();

  const [inviteDialogOpen, setInviteDialogOpen] = useState(false);
  const [editUserId, setEditUserId] = useState<string | null>(null);
  const [changeRoleUserId, setChangeRoleUserId] = useState<string | null>(null);
  const [confirmRemove, setConfirmRemove] = useState<{ userId: string; username: string } | null>(null);

  const users = data?.users || [];
  const total = data?.total ?? 0;

  const columns: ColumnDef<TenantUser>[] = [
    {
      accessorKey: "username",
      header: "Name",
      cell: ({ row }) => (
        <div>
          <div className="font-medium">
            {[row.original.first_name, row.original.last_name].filter(Boolean).join(" ") ||
              row.original.username}
          </div>
          <div className="text-xs text-muted-foreground">@{row.original.username}</div>
        </div>
      ),
    },
    {
      accessorKey: "email",
      header: "Email",
      cell: ({ row }) => <span className="text-sm">{row.original.email}</span>,
    },
    {
      id: "role",
      header: "Role",
      cell: ({ row }) => (
        <Badge variant={row.original.roles?.includes("tenant-admin") ? "default" : "secondary"}>
          {getRoleLabel(row.original.roles || [])}
        </Badge>
      ),
    },
    {
      id: "status",
      header: "Status",
      cell: ({ row }) => (
        <Badge variant={row.original.enabled ? "outline" : "secondary"}>
          {row.original.enabled ? "Active" : "Disabled"}
        </Badge>
      ),
    },
    {
      id: "actions",
      enableSorting: false,
      cell: ({ row }) => {
        const user = row.original;
        const isSelf = user.id === currentUserId;
        return (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => setEditUserId(user.id)}>
                <Pencil className="mr-2 h-4 w-4" />
                Edit
              </DropdownMenuItem>
              {!isSelf && (
                <DropdownMenuItem onClick={() => setChangeRoleUserId(user.id)}>
                  <Shield className="mr-2 h-4 w-4" />
                  Manage Roles
                </DropdownMenuItem>
              )}
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => handleResetPassword(user.id)}>
                <Key className="mr-2 h-4 w-4" />
                Reset Password
              </DropdownMenuItem>
              {!isSelf && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    onClick={() => handleRemove(user.id, user.username)}
                    className="text-destructive"
                  >
                    <UserMinus className="mr-2 h-4 w-4" />
                    Remove from Team
                  </DropdownMenuItem>
                </>
              )}
              {isSelf && (
                <>
                  <DropdownMenuSeparator />
                  <div className="px-2 py-1.5 text-xs text-muted-foreground">
                    This is your account
                  </div>
                </>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        );
      },
    },
  ];

  const handleSearch = () => {
    setSearch(searchInput);
    setPage(1);
  };

  function handleRemove(userId: string, username: string) {
    setConfirmRemove({ userId, username });
  }

  async function handleResetPassword(userId: string) {
    await resetPasswordMutation.mutateAsync(userId);
    toast.success("Password reset email sent");
  }

  const confirmRemoveUser = async () => {
    if (!confirmRemove) return;
    await removeMutation.mutateAsync(confirmRemove.userId);
    setConfirmRemove(null);
  };

  function getRoleLabel(roles: string[]) {
    if (roles.includes("tenant-admin")) return "Admin";
    if (roles.includes("customer")) return "User";
    return roles[0] || "User";
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Team Members"
        description="Manage users in your organization"
        action={
          <Button onClick={() => setInviteDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Invite User
          </Button>
        }
      />

      <div className="flex gap-2">
        <Input
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder="Search users..."
          className="max-w-xs"
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
        />
        <Button variant="outline" onClick={handleSearch}>
          <Search className="h-4 w-4" />
        </Button>
        {search && (
          <Button
            variant="ghost"
            onClick={() => {
              setSearch("");
              setSearchInput("");
              setPage(1);
            }}
          >
            Clear
          </Button>
        )}
      </div>

      {error ? (
        <div className="text-destructive">Failed to load users: {(error as Error).message}</div>
      ) : (
        <DataTable
          columns={columns}
          data={users}
          totalCount={total}
          pagination={{ pageIndex: page - 1, pageSize: limit }}
          onPaginationChange={(updater) => {
            const next =
              typeof updater === "function"
                ? updater({ pageIndex: page - 1, pageSize: limit })
                : (updater as PaginationState);
            setPage(next.pageIndex + 1);
          }}
          isLoading={isLoading}
          emptyState={
            <div className="py-12 text-center">
              <div className="mb-4 text-muted-foreground">No team members found.</div>
              <Button onClick={() => setInviteDialogOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Invite your first team member
              </Button>
            </div>
          }
        />
      )}

      <InviteUserDialog
        open={inviteDialogOpen}
        onOpenChange={setInviteDialogOpen}
        onInvited={() => {
          setInviteDialogOpen(false);
          refetch();
        }}
      />

      {editUserId && (
        <EditTenantUserDialog
          userId={editUserId}
          open={!!editUserId}
          onOpenChange={(open) => !open && setEditUserId(null)}
          onSaved={() => {
            setEditUserId(null);
            refetch();
          }}
        />
      )}

      {changeRoleUserId && (
        <ManageUserRolesDialog
          userId={changeRoleUserId}
          open={!!changeRoleUserId}
          onOpenChange={(open) => !open && setChangeRoleUserId(null)}
          onSaved={() => {
            setChangeRoleUserId(null);
            refetch();
          }}
        />
      )}

      <AlertDialog open={!!confirmRemove} onOpenChange={(open) => !open && setConfirmRemove(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove Team Member</AlertDialogTitle>
            <AlertDialogDescription>
              Remove {confirmRemove?.username} from this tenant? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={() => void confirmRemoveUser()}>
              Remove
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
