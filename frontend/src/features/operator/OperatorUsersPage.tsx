import { useState } from "react";
import { Building2, Key, MoreHorizontal, Pencil, Plus, Search, Shield, Trash2, UserCheck, UserX } from "lucide-react";
import { toast } from "sonner";

import { PageHeader } from "@/components/shared";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  useDeleteOperatorUser,
  useDisableOperatorUser,
  useEnableOperatorUser,
  useOperatorUsers,
  useSendOperatorPasswordReset,
} from "@/hooks/use-users";
import { useAuth } from "@/services/auth/AuthProvider";
import { AssignRoleDialog } from "./AssignRoleDialog";
import { AssignTenantDialog } from "./AssignTenantDialog";
import { CreateUserDialog } from "./CreateUserDialog";
import { EditUserDialog } from "./EditUserDialog";

export default function OperatorUsersPage() {
  const { user: currentUser } = useAuth();
  const currentUserId = currentUser?.sub;
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [tenantFilter, setTenantFilter] = useState<string | undefined>();
  const [page, setPage] = useState(1);
  const limit = 50;
  const offset = (page - 1) * limit;

  const { data, isLoading, error, refetch } = useOperatorUsers(
    search || undefined,
    tenantFilter,
    limit,
    offset
  );

  const enableMutation = useEnableOperatorUser();
  const disableMutation = useDisableOperatorUser();
  const deleteMutation = useDeleteOperatorUser();
  const resetPasswordMutation = useSendOperatorPasswordReset();

  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editUserId, setEditUserId] = useState<string | null>(null);
  const [assignTenantUserId, setAssignTenantUserId] = useState<string | null>(null);
  const [assignRoleUserId, setAssignRoleUserId] = useState<string | null>(null);
  const [confirmDeleteUser, setConfirmDeleteUser] = useState<string | null>(null);

  const users = data?.users || [];
  const total = data?.total ?? 0;

  const handleSearch = () => {
    setSearch(searchInput);
    setPage(1);
  };

  const handleEnable = async (userId: string) => {
    await enableMutation.mutateAsync(userId);
  };

  const handleDisable = async (userId: string) => {
    await disableMutation.mutateAsync(userId);
  };

  const handleDelete = (userId: string) => {
    setConfirmDeleteUser(userId);
  };

  const handleResetPassword = async (userId: string) => {
    await resetPasswordMutation.mutateAsync(userId);
    toast.success("Password reset email sent");
  };

  const confirmDeleteOperatorUser = async () => {
    if (!confirmDeleteUser) return;
    await deleteMutation.mutateAsync(confirmDeleteUser);
    setConfirmDeleteUser(null);
  };

  const getRoleBadgeVariant = (role: string) => {
    if (role.includes("operator")) return "destructive";
    if (role.includes("admin")) return "default";
    return "secondary";
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="User Management"
        description="Manage users across all tenants"
        action={
          <Button onClick={() => setCreateDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Create User
          </Button>
        }
      />

      <div className="flex flex-wrap gap-2">
        <div className="flex gap-2">
          <Input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search users..."
            className="w-64"
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          />
          <Button variant="outline" onClick={handleSearch}>
            <Search className="h-4 w-4" />
          </Button>
        </div>
        <Input
          value={tenantFilter || ""}
          onChange={(e) => {
            setTenantFilter(e.target.value || undefined);
            setPage(1);
          }}
          placeholder="Filter by tenant..."
          className="w-48"
        />
        {(search || tenantFilter) && (
          <Button
            variant="ghost"
            onClick={() => {
              setSearch("");
              setSearchInput("");
              setTenantFilter(undefined);
              setPage(1);
            }}
          >
            Clear filters
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
        <div className="py-12 text-center text-muted-foreground">No users found.</div>
      ) : (
        <>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Username</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Tenant</TableHead>
                  <TableHead>Roles</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="w-[70px]" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.map((user) => {
                  const isSelf = user.id === currentUserId;
                  return (
                  <TableRow key={user.id}>
                    <TableCell className="font-mono text-sm">{user.username}</TableCell>
                    <TableCell className="text-sm">{user.email}</TableCell>
                    <TableCell className="text-sm">
                      {[user.first_name, user.last_name].filter(Boolean).join(" ") || "—"}
                    </TableCell>
                    <TableCell>
                      {user.tenant_id ? (
                        <Badge variant="outline" className="font-mono text-xs">
                          {user.tenant_id}
                        </Badge>
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {user.roles?.map((role) => (
                          <Badge key={role} variant={getRoleBadgeVariant(role)} className="text-xs">
                            {role}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={user.enabled ? "default" : "secondary"}>
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
                            <DropdownMenuItem onClick={() => setAssignRoleUserId(user.id)}>
                              <Shield className="mr-2 h-4 w-4" />
                              Assign Role
                            </DropdownMenuItem>
                          )}
                          {!isSelf && (
                            <DropdownMenuItem onClick={() => setAssignTenantUserId(user.id)}>
                              <Building2 className="mr-2 h-4 w-4" />
                              Assign Tenant
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuSeparator />
                          <DropdownMenuItem onClick={() => handleResetPassword(user.id)}>
                            <Key className="mr-2 h-4 w-4" />
                            Reset Password
                          </DropdownMenuItem>
                          {!isSelf && (user.enabled ? (
                            <DropdownMenuItem onClick={() => handleDisable(user.id)}>
                              <UserX className="mr-2 h-4 w-4" />
                              Disable
                            </DropdownMenuItem>
                          ) : (
                            <DropdownMenuItem onClick={() => handleEnable(user.id)}>
                              <UserCheck className="mr-2 h-4 w-4" />
                              Enable
                            </DropdownMenuItem>
                          ))}
                          {!isSelf && (
                            <>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem
                                onClick={() => handleDelete(user.id)}
                                className="text-destructive"
                              >
                                <Trash2 className="mr-2 h-4 w-4" />
                                Delete
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
        </>
      )}

      <CreateUserDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onCreated={() => {
          setCreateDialogOpen(false);
          refetch();
        }}
      />

      {editUserId && (
        <EditUserDialog
          userId={editUserId}
          open={!!editUserId}
          onOpenChange={(open) => !open && setEditUserId(null)}
          onSaved={() => {
            setEditUserId(null);
            refetch();
          }}
        />
      )}

      {assignTenantUserId && (
        <AssignTenantDialog
          userId={assignTenantUserId}
          open={!!assignTenantUserId}
          onOpenChange={(open) => !open && setAssignTenantUserId(null)}
          onAssigned={() => {
            setAssignTenantUserId(null);
            refetch();
          }}
        />
      )}

      {assignRoleUserId && (
        <AssignRoleDialog
          userId={assignRoleUserId}
          open={!!assignRoleUserId}
          onOpenChange={(open) => !open && setAssignRoleUserId(null)}
          onAssigned={() => {
            setAssignRoleUserId(null);
            refetch();
          }}
        />
      )}

      <AlertDialog open={!!confirmDeleteUser} onOpenChange={(open) => !open && setConfirmDeleteUser(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete User</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this user? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={() => void confirmDeleteOperatorUser()}>
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
