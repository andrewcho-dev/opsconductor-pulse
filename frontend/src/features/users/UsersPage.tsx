import { useState } from "react";
import { Key, MoreHorizontal, Pencil, Plus, Search, Shield, UserMinus } from "lucide-react";

import { PageHeader } from "@/components/shared";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useRemoveTenantUser, useSendTenantPasswordReset, useTenantUsers } from "@/hooks/use-users";
import { useAuth } from "@/services/auth/AuthProvider";
import { ManageUserRolesDialog } from "./ManageUserRolesDialog";
import { EditTenantUserDialog } from "./EditTenantUserDialog";
import { InviteUserDialog } from "./InviteUserDialog";

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

  const users = data?.users || [];
  const total = data?.total ?? 0;

  const handleSearch = () => {
    setSearch(searchInput);
    setPage(1);
  };

  const handleRemove = async (userId: string, username: string) => {
    if (window.confirm(`Remove ${username} from this tenant?`)) {
      await removeMutation.mutateAsync(userId);
    }
  };

  const handleResetPassword = async (userId: string) => {
    await resetPasswordMutation.mutateAsync(userId);
    window.alert("Password reset email sent");
  };

  const getRoleLabel = (roles: string[]) => {
    if (roles.includes("tenant-admin")) return "Admin";
    if (roles.includes("customer")) return "User";
    return roles[0] || "User";
  };

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
      ) : isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : users.length === 0 ? (
        <div className="py-12 text-center">
          <div className="mb-4 text-muted-foreground">No team members found.</div>
          <Button onClick={() => setInviteDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Invite your first team member
          </Button>
        </div>
      ) : (
        <>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="w-[70px]" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.map((user) => {
                  const isSelf = user.id === currentUserId;
                  return (
                  <TableRow key={user.id}>
                    <TableCell>
                      <div>
                        <div className="font-medium">
                          {[user.first_name, user.last_name].filter(Boolean).join(" ") || user.username}
                        </div>
                        <div className="text-xs text-muted-foreground">@{user.username}</div>
                      </div>
                    </TableCell>
                    <TableCell className="text-sm">{user.email}</TableCell>
                    <TableCell>
                      <Badge variant={user.roles?.includes("tenant-admin") ? "default" : "secondary"}>
                        {getRoleLabel(user.roles || [])}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={user.enabled ? "outline" : "secondary"}>
                        {user.enabled ? "Active" : "Disabled"}
                      </Badge>
                    </TableCell>
                    <TableCell>
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
                    </TableCell>
                  </TableRow>
                )})}
              </TableBody>
            </Table>
          </div>

          {total > limit && (
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">
                Showing {offset + 1}–{offset + users.length} of {total}
              </span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => p + 1)}
                  disabled={offset + users.length >= total}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
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
    </div>
  );
}
