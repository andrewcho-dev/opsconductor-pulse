import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { DataTable } from "@/components/ui/data-table";
import { type ColumnDef, type PaginationState } from "@tanstack/react-table";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";
import { MoreHorizontal } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import {
  assignOperatorUserRole,
  assignOperatorUserTenant,
  createOperatorUser,
  deleteOperatorUser,
  disableOperatorUser,
  enableOperatorUser,
  fetchOperatorUsers,
  sendOperatorPasswordReset,
  type User,
} from "@/services/api/users";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/errors";

export default function UserListPage() {
  const qc = useQueryClient();
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [assignRoleOpen, setAssignRoleOpen] = useState(false);
  const [assignTenantOpen, setAssignTenantOpen] = useState(false);
  const [targetUser, setTargetUser] = useState<User | null>(null);
  const [roleInput, setRoleInput] = useState("");
  const [tenantInput, setTenantInput] = useState("");
  const [page, setPage] = useState(1);
  const limit = 50;
  const offset = (page - 1) * limit;
  const [form, setForm] = useState({
    username: "",
    email: "",
    first_name: "",
    last_name: "",
    temporary_password: "",
  });

  useEffect(() => {
    const timer = setTimeout(() => setSearch(searchInput), 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    setPage(1);
  }, [search]);

  const usersQ = useQuery({
    queryKey: ["operator-users", search, limit, offset],
    queryFn: () => fetchOperatorUsers(search, undefined, limit, offset),
  });

  const createMut = useMutation({
    mutationFn: createOperatorUser,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["operator-users"] });
      setCreateOpen(false);
      setForm({
        username: "",
        email: "",
        first_name: "",
        last_name: "",
        temporary_password: "",
      });
      toast.success("User created");
    },
    onError: (err: Error) => {
      toast.error(getErrorMessage(err) || "Failed to create user");
    },
  });
  const deleteMut = useMutation({
    mutationFn: deleteOperatorUser,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["operator-users"] });
      toast.success("User deleted");
    },
    onError: (err: Error) => {
      toast.error(getErrorMessage(err) || "Failed to delete user");
    },
  });
  const resetMut = useMutation({
    mutationFn: sendOperatorPasswordReset,
    onSuccess: () => {
      toast.success("Password reset email sent");
    },
    onError: (err: Error) => {
      toast.error(getErrorMessage(err) || "Failed to send password reset");
    },
  });
  const roleMut = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      assignOperatorUserRole(userId, role),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["operator-users"] });
      toast.success("Role assigned");
    },
    onError: (err: Error) => {
      toast.error(getErrorMessage(err) || "Failed to assign role");
    },
  });
  const tenantMut = useMutation({
    mutationFn: ({ userId, tenantId }: { userId: string; tenantId: string }) =>
      assignOperatorUserTenant(userId, tenantId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["operator-users"] });
      toast.success("Tenant assigned");
    },
    onError: (err: Error) => {
      toast.error(getErrorMessage(err) || "Failed to assign tenant");
    },
  });
  const enableMut = useMutation({
    mutationFn: (userId: string) => enableOperatorUser(userId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["operator-users"] });
      toast.success("User enabled");
    },
    onError: (err: Error) => {
      toast.error(getErrorMessage(err) || "Failed to enable user");
    },
  });
  const disableMut = useMutation({
    mutationFn: (userId: string) => disableOperatorUser(userId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["operator-users"] });
      toast.success("User disabled");
    },
    onError: (err: Error) => {
      toast.error(getErrorMessage(err) || "Failed to disable user");
    },
  });

  const users = useMemo(() => usersQ.data?.users || [], [usersQ.data?.users]);
  const total = usersQ.data?.total ?? 0;

  const columns: ColumnDef<User>[] = [
    {
      accessorKey: "username",
      header: "Username",
      cell: ({ row }) => (
        <div>
          <div className="font-medium">
            <Link className="underline" to={`/operator/users/${row.original.id}`}>
              {row.original.username}
            </Link>
          </div>
          <div className="text-sm text-muted-foreground">
            {`${row.original.first_name || ""} ${row.original.last_name || ""}`.trim() || "—"}
          </div>
        </div>
      ),
    },
    {
      accessorKey: "email",
      header: "Email",
      cell: ({ row }) => row.original.email || "—",
    },
    {
      accessorKey: "roles",
      header: "Role",
      cell: ({ row }) => {
        const role = row.original.roles?.[0] ?? "";
        return role ? (
          <Badge variant="outline" className="capitalize">
            {role}
          </Badge>
        ) : (
          <span className="text-muted-foreground">—</span>
        );
      },
    },
    {
      accessorKey: "enabled",
      header: "Status",
      cell: ({ row }) => (
        <Badge variant={row.original.enabled ? "default" : "secondary"}>
          {row.original.enabled ? "Active" : "Disabled"}
        </Badge>
      ),
    },
    {
      accessorKey: "created_at",
      header: "Created",
      cell: ({ row }) =>
        row.original.created_at != null ? (
          <span className="text-sm text-muted-foreground">
            {new Date(row.original.created_at).toLocaleDateString()}
          </span>
        ) : (
          <span className="text-sm text-muted-foreground">—</span>
        ),
    },
    {
      id: "actions",
      enableSorting: false,
      cell: ({ row }) => {
        const u = row.original;
        return (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="Open user actions">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem asChild>
                <Link to={`/operator/users/${u.id}`}>Edit</Link>
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => {
                  setTargetUser(u);
                  setRoleInput("");
                  setAssignRoleOpen(true);
                }}
              >
                Assign Role
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => {
                  setTargetUser(u);
                  setTenantInput(u.tenant_id ?? "");
                  setAssignTenantOpen(true);
                }}
              >
                Assign Tenant
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => resetMut.mutate(u.id)}>
                Send Password Reset
              </DropdownMenuItem>
              {u.enabled ? (
                <DropdownMenuItem variant="destructive" onClick={() => disableMut.mutate(u.id)}>
                  Disable
                </DropdownMenuItem>
              ) : (
                <DropdownMenuItem onClick={() => enableMut.mutate(u.id)}>Enable</DropdownMenuItem>
              )}
              <DropdownMenuItem variant="destructive" onClick={() => deleteMut.mutate(u.id)}>
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        );
      },
    },
  ];

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Users</CardTitle>
          <Button onClick={() => setCreateOpen(true)}>Create User</Button>
        </CardHeader>
        <CardContent className="space-y-3">
          <Input
            placeholder="Search users"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
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
            isLoading={usersQ.isLoading}
            emptyState={
              <div className="rounded-lg border border-border py-8 text-center text-muted-foreground">
                No users found.
              </div>
            }
          />
          {usersQ.error ? (
            <p className="text-sm text-destructive">{(usersQ.error as Error).message}</p>
          ) : null}
        </CardContent>
      </Card>

      <Dialog open={assignRoleOpen} onOpenChange={setAssignRoleOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Assign Role</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div className="text-sm text-muted-foreground">{targetUser?.username}</div>
            <div className="grid gap-2">
              <Label>Role</Label>
              <Input
                value={roleInput}
                onChange={(e) => setRoleInput(e.target.value)}
                placeholder="operator, operator-admin, customer, ..."
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAssignRoleOpen(false)}>
              Cancel
            </Button>
            <Button
              disabled={roleMut.isPending || !targetUser || !roleInput.trim()}
              onClick={() => {
                if (!targetUser) return;
                roleMut.mutate({ userId: targetUser.id, role: roleInput.trim() });
                setAssignRoleOpen(false);
              }}
            >
              Assign
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={assignTenantOpen} onOpenChange={setAssignTenantOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Assign Tenant</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div className="text-sm text-muted-foreground">{targetUser?.username}</div>
            <div className="grid gap-2">
              <Label>Tenant ID</Label>
              <Input
                value={tenantInput}
                onChange={(e) => setTenantInput(e.target.value)}
                placeholder="tenant-a"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAssignTenantOpen(false)}>
              Cancel
            </Button>
            <Button
              disabled={tenantMut.isPending || !targetUser || !tenantInput.trim()}
              onClick={() => {
                if (!targetUser) return;
                tenantMut.mutate({ userId: targetUser.id, tenantId: tenantInput.trim() });
                setAssignTenantOpen(false);
              }}
            >
              Assign
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create User</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div className="grid gap-2">
              <Label>Username</Label>
              <Input
                value={form.username}
                onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
              />
            </div>
            <div className="grid gap-2">
              <Label>Email</Label>
              <Input
                type="email"
                value={form.email}
                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
              />
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              <div className="grid gap-2">
                <Label>First Name</Label>
                <Input
                  value={form.first_name}
                  onChange={(e) => setForm((f) => ({ ...f, first_name: e.target.value }))}
                />
              </div>
              <div className="grid gap-2">
                <Label>Last Name</Label>
                <Input
                  value={form.last_name}
                  onChange={(e) => setForm((f) => ({ ...f, last_name: e.target.value }))}
                />
              </div>
            </div>
            <div className="grid gap-2">
              <Label>Temporary Password</Label>
              <Input
                type="password"
                value={form.temporary_password}
                onChange={(e) =>
                  setForm((f) => ({ ...f, temporary_password: e.target.value }))
                }
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>
              Cancel
            </Button>
            <Button
              disabled={createMut.isPending}
              onClick={() => createMut.mutate(form)}
            >
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
