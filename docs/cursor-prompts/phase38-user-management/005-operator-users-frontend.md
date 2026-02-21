# Create Operator Users Page and Dialogs

Create the operator-level user management UI.

## Files to Create

### 1. `frontend/src/features/operator/OperatorUsersPage.tsx`

```tsx
import { useState } from "react";
import { PageHeader } from "@/components/shared";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useOperatorUsers,
  useEnableOperatorUser,
  useDisableOperatorUser,
  useDeleteOperatorUser,
  useSendOperatorPasswordReset,
} from "@/hooks/use-users";
import {
  Plus,
  MoreHorizontal,
  Search,
  UserCheck,
  UserX,
  Key,
  Pencil,
  Trash2,
  Building2,
  Shield,
} from "lucide-react";
import { CreateUserDialog } from "./CreateUserDialog";
import { EditUserDialog } from "./EditUserDialog";
import { AssignTenantDialog } from "./AssignTenantDialog";
import { AssignRoleDialog } from "./AssignRoleDialog";

export default function OperatorUsersPage() {
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

  const handleDelete = async (userId: string) => {
    if (confirm("Are you sure you want to delete this user?")) {
      await deleteMutation.mutateAsync(userId);
    }
  };

  const handleResetPassword = async (userId: string) => {
    await resetPasswordMutation.mutateAsync(userId);
    alert("Password reset email sent");
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
            <Plus className="h-4 w-4 mr-2" />
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
        <div className="text-destructive">
          Failed to load users: {(error as Error).message}
        </div>
      ) : isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : users.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          No users found.
        </div>
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
                  <TableHead className="w-[70px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell className="font-mono text-sm">
                      {user.username}
                    </TableCell>
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
                        <span className="text-muted-foreground text-xs">—</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {user.roles?.map((role) => (
                          <Badge
                            key={role}
                            variant={getRoleBadgeVariant(role)}
                            className="text-xs"
                          >
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
                            <Pencil className="h-4 w-4 mr-2" />
                            Edit
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => setAssignRoleUserId(user.id)}>
                            <Shield className="h-4 w-4 mr-2" />
                            Assign Role
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => setAssignTenantUserId(user.id)}>
                            <Building2 className="h-4 w-4 mr-2" />
                            Assign Tenant
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem onClick={() => handleResetPassword(user.id)}>
                            <Key className="h-4 w-4 mr-2" />
                            Reset Password
                          </DropdownMenuItem>
                          {user.enabled ? (
                            <DropdownMenuItem onClick={() => handleDisable(user.id)}>
                              <UserX className="h-4 w-4 mr-2" />
                              Disable
                            </DropdownMenuItem>
                          ) : (
                            <DropdownMenuItem onClick={() => handleEnable(user.id)}>
                              <UserCheck className="h-4 w-4 mr-2" />
                              Enable
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            onClick={() => handleDelete(user.id)}
                            className="text-destructive"
                          >
                            <Trash2 className="h-4 w-4 mr-2" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))}
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
    </div>
  );
}
```

### 2. `frontend/src/features/operator/CreateUserDialog.tsx`

```tsx
import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useCreateOperatorUser, useOrganizations } from "@/hooks/use-users";

interface CreateUserDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: () => void;
}

export function CreateUserDialog({ open, onOpenChange, onCreated }: CreateUserDialogProps) {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [password, setPassword] = useState("");
  const [tenantId, setTenantId] = useState<string>("");
  const [role, setRole] = useState("customer");

  const createMutation = useCreateOperatorUser();
  const { data: orgsData } = useOrganizations();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createMutation.mutateAsync({
        username,
        email,
        first_name: firstName,
        last_name: lastName,
        temporary_password: password || undefined,
        tenant_id: tenantId || undefined,
        role,
      });
      // Reset form
      setUsername("");
      setEmail("");
      setFirstName("");
      setLastName("");
      setPassword("");
      setTenantId("");
      setRole("customer");
      onCreated();
    } catch (error) {
      // Error shown via mutation state
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Create User</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="username">Username *</Label>
              <Input
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email *</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="firstName">First Name</Label>
              <Input
                id="firstName"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="lastName">Last Name</Label>
              <Input
                id="lastName"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">Temporary Password</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Leave empty to send password reset email"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="tenant">Tenant</Label>
              <Select value={tenantId} onValueChange={setTenantId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select tenant..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">No tenant (operator)</SelectItem>
                  {orgsData?.organizations?.map((org) => (
                    <SelectItem key={org.id} value={org.name}>
                      {org.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="role">Role</Label>
              <Select value={role} onValueChange={setRole}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="customer">Customer</SelectItem>
                  <SelectItem value="tenant-admin">Tenant Admin</SelectItem>
                  <SelectItem value="operator">Operator</SelectItem>
                  <SelectItem value="operator-admin">Operator Admin</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {createMutation.isError && (
            <div className="text-sm text-destructive">
              {(createMutation.error as Error).message}
            </div>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? "Creating..." : "Create User"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
```

### 3. `frontend/src/features/operator/EditUserDialog.tsx`

```tsx
import { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { useOperatorUser, useUpdateOperatorUser } from "@/hooks/use-users";

interface EditUserDialogProps {
  userId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
}

export function EditUserDialog({ userId, open, onOpenChange, onSaved }: EditUserDialogProps) {
  const { data: user, isLoading } = useOperatorUser(userId);
  const updateMutation = useUpdateOperatorUser();

  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");

  useEffect(() => {
    if (user) {
      setFirstName(user.first_name || "");
      setLastName(user.last_name || "");
      setEmail(user.email || "");
    }
  }, [user]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await updateMutation.mutateAsync({
        userId,
        data: {
          first_name: firstName,
          last_name: lastName,
          email,
        },
      });
      onSaved();
    } catch (error) {
      // Error shown via mutation state
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Edit User</DialogTitle>
        </DialogHeader>
        {isLoading ? (
          <div className="space-y-4">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label>Username</Label>
              <Input value={user?.username || ""} disabled className="bg-muted" />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="firstName">First Name</Label>
                <Input
                  id="firstName"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="lastName">Last Name</Label>
                <Input
                  id="lastName"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>

            {updateMutation.isError && (
              <div className="text-sm text-destructive">
                {(updateMutation.error as Error).message}
              </div>
            )}

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={updateMutation.isPending}>
                {updateMutation.isPending ? "Saving..." : "Save Changes"}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
```

### 4. `frontend/src/features/operator/AssignTenantDialog.tsx`

```tsx
import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAssignOperatorUserTenant, useOrganizations, useOperatorUser } from "@/hooks/use-users";

interface AssignTenantDialogProps {
  userId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAssigned: () => void;
}

export function AssignTenantDialog({ userId, open, onOpenChange, onAssigned }: AssignTenantDialogProps) {
  const { data: user } = useOperatorUser(userId);
  const { data: orgsData } = useOrganizations();
  const assignMutation = useAssignOperatorUserTenant();

  const [tenantId, setTenantId] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tenantId) return;

    try {
      await assignMutation.mutateAsync({ userId, tenantId });
      onAssigned();
    } catch (error) {
      // Error shown via mutation state
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Assign Tenant</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="text-sm text-muted-foreground">
            Assigning tenant for user: <strong>{user?.username}</strong>
          </div>

          {user?.tenant_id && (
            <div className="text-sm">
              Current tenant: <code className="bg-muted px-1 rounded">{user.tenant_id}</code>
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="tenant">New Tenant</Label>
            <Select value={tenantId} onValueChange={setTenantId}>
              <SelectTrigger>
                <SelectValue placeholder="Select tenant..." />
              </SelectTrigger>
              <SelectContent>
                {orgsData?.organizations?.map((org) => (
                  <SelectItem key={org.id} value={org.name}>
                    {org.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {assignMutation.isError && (
            <div className="text-sm text-destructive">
              {(assignMutation.error as Error).message}
            </div>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={!tenantId || assignMutation.isPending}>
              {assignMutation.isPending ? "Assigning..." : "Assign Tenant"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
```

### 5. `frontend/src/features/operator/AssignRoleDialog.tsx`

```tsx
import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAssignOperatorUserRole, useOperatorUser } from "@/hooks/use-users";

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

export function AssignRoleDialog({ userId, open, onOpenChange, onAssigned }: AssignRoleDialogProps) {
  const { data: user } = useOperatorUser(userId);
  const assignMutation = useAssignOperatorUserRole();

  const [role, setRole] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!role) return;

    try {
      await assignMutation.mutateAsync({ userId, role });
      onAssigned();
    } catch (error) {
      // Error shown via mutation state
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Assign Role</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
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

          <div className="space-y-2">
            <Label htmlFor="role">Add Role</Label>
            <Select value={role} onValueChange={setRole}>
              <SelectTrigger>
                <SelectValue placeholder="Select role..." />
              </SelectTrigger>
              <SelectContent>
                {AVAILABLE_ROLES.map((r) => (
                  <SelectItem key={r.value} value={r.value}>
                    <div>
                      <div>{r.label}</div>
                      <div className="text-xs text-muted-foreground">{r.description}</div>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {assignMutation.isError && (
            <div className="text-sm text-destructive">
              {(assignMutation.error as Error).message}
            </div>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={!role || assignMutation.isPending}>
              {assignMutation.isPending ? "Assigning..." : "Assign Role"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
```

## Update Router and Sidebar

### Update `frontend/src/app/router.tsx`

Add import and route:

```tsx
import OperatorUsersPage from "@/features/operator/OperatorUsersPage";

// In operator children array, add:
{ path: "users", element: <OperatorUsersPage /> },
```

### Update `frontend/src/components/layout/AppSidebar.tsx`

Add to operatorNav array:

```tsx
import { Users } from "lucide-react";

// In operatorNav array, add after "Tenants":
{ label: "Users", href: "/operator/users", icon: Users },
```
