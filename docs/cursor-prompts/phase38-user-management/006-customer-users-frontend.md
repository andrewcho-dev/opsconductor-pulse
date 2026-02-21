# Create Tenant Users Page

Create the tenant-level user management UI for tenant admins.

## Files to Create

### 1. `frontend/src/features/users/UsersPage.tsx`

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
  useTenantUsers,
  useRemoveTenantUser,
  useSendTenantPasswordReset,
} from "@/hooks/use-users";
import {
  Plus,
  MoreHorizontal,
  Search,
  Key,
  Pencil,
  UserMinus,
  Shield,
} from "lucide-react";
import { InviteUserDialog } from "./InviteUserDialog";
import { EditTenantUserDialog } from "./EditTenantUserDialog";
import { ChangeRoleDialog } from "./ChangeRoleDialog";

export default function UsersPage() {
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [page, setPage] = useState(1);
  const limit = 50;
  const offset = (page - 1) * limit;

  const { data, isLoading, error, refetch } = useTenantUsers(
    search || undefined,
    limit,
    offset
  );

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
    if (confirm(`Remove ${username} from this tenant? They will lose access to tenant resources.`)) {
      await removeMutation.mutateAsync(userId);
    }
  };

  const handleResetPassword = async (userId: string) => {
    await resetPasswordMutation.mutateAsync(userId);
    alert("Password reset email sent");
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
            <Plus className="h-4 w-4 mr-2" />
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
        <div className="text-center py-12">
          <div className="text-muted-foreground mb-4">No team members found.</div>
          <Button onClick={() => setInviteDialogOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
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
                  <TableHead className="w-[70px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell>
                      <div>
                        <div className="font-medium">
                          {[user.first_name, user.last_name].filter(Boolean).join(" ") ||
                            user.username}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          @{user.username}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="text-sm">{user.email}</TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          user.roles?.includes("tenant-admin") ? "default" : "secondary"
                        }
                      >
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
                            <Pencil className="h-4 w-4 mr-2" />
                            Edit
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => setChangeRoleUserId(user.id)}>
                            <Shield className="h-4 w-4 mr-2" />
                            Change Role
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem onClick={() => handleResetPassword(user.id)}>
                            <Key className="h-4 w-4 mr-2" />
                            Reset Password
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            onClick={() => handleRemove(user.id, user.username)}
                            className="text-destructive"
                          >
                            <UserMinus className="h-4 w-4 mr-2" />
                            Remove from Team
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))}
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
        <ChangeRoleDialog
          userId={changeRoleUserId}
          open={!!changeRoleUserId}
          onOpenChange={(open) => !open && setChangeRoleUserId(null)}
          onChanged={() => {
            setChangeRoleUserId(null);
            refetch();
          }}
        />
      )}
    </div>
  );
}
```

### 2. `frontend/src/features/users/InviteUserDialog.tsx`

```tsx
import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
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
import { useInviteTenantUser } from "@/hooks/use-users";
import { Mail } from "lucide-react";

interface InviteUserDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onInvited: () => void;
}

export function InviteUserDialog({ open, onOpenChange, onInvited }: InviteUserDialogProps) {
  const [email, setEmail] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [role, setRole] = useState("customer");

  const inviteMutation = useInviteTenantUser();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await inviteMutation.mutateAsync({
        email,
        first_name: firstName || undefined,
        last_name: lastName || undefined,
        role,
      });
      // Reset form
      setEmail("");
      setFirstName("");
      setLastName("");
      setRole("customer");
      onInvited();
    } catch (error) {
      // Error shown via mutation state
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Invite Team Member</DialogTitle>
          <DialogDescription>
            Send an invitation email to add someone to your team.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email Address *</Label>
            <div className="relative">
              <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="colleague@company.com"
                className="pl-9"
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
                placeholder="John"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="lastName">Last Name</Label>
              <Input
                id="lastName"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                placeholder="Doe"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="role">Role</Label>
            <Select value={role} onValueChange={setRole}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="customer">
                  <div>
                    <div>User</div>
                    <div className="text-xs text-muted-foreground">
                      Can view devices, alerts, and dashboards
                    </div>
                  </div>
                </SelectItem>
                <SelectItem value="tenant-admin">
                  <div>
                    <div>Admin</div>
                    <div className="text-xs text-muted-foreground">
                      Can manage team members and settings
                    </div>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {inviteMutation.isError && (
            <div className="text-sm text-destructive">
              {(inviteMutation.error as Error).message}
            </div>
          )}

          {inviteMutation.isSuccess && (
            <div className="text-sm text-green-600">
              Invitation sent! They'll receive an email with instructions to set up their account.
            </div>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={inviteMutation.isPending}>
              {inviteMutation.isPending ? "Sending..." : "Send Invitation"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
```

### 3. `frontend/src/features/users/EditTenantUserDialog.tsx`

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
import { useTenantUser, useUpdateTenantUser } from "@/hooks/use-users";

interface EditTenantUserDialogProps {
  userId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
}

export function EditTenantUserDialog({
  userId,
  open,
  onOpenChange,
  onSaved,
}: EditTenantUserDialogProps) {
  const { data: user, isLoading } = useTenantUser(userId);
  const updateMutation = useUpdateTenantUser();

  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");

  useEffect(() => {
    if (user) {
      setFirstName(user.first_name || "");
      setLastName(user.last_name || "");
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
          <DialogTitle>Edit Team Member</DialogTitle>
        </DialogHeader>
        {isLoading ? (
          <div className="space-y-4">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1">
              <Label className="text-muted-foreground">Email</Label>
              <div className="text-sm">{user?.email}</div>
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

### 4. `frontend/src/features/users/ChangeRoleDialog.tsx`

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
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { useTenantUser, useChangeTenantUserRole } from "@/hooks/use-users";

interface ChangeRoleDialogProps {
  userId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onChanged: () => void;
}

export function ChangeRoleDialog({
  userId,
  open,
  onOpenChange,
  onChanged,
}: ChangeRoleDialogProps) {
  const { data: user } = useTenantUser(userId);
  const changeMutation = useChangeTenantUserRole();

  const currentRole = user?.roles?.includes("tenant-admin") ? "tenant-admin" : "customer";
  const [role, setRole] = useState(currentRole);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (role === currentRole) {
      onChanged();
      return;
    }

    try {
      await changeMutation.mutateAsync({ userId, role });
      onChanged();
    } catch (error) {
      // Error shown via mutation state
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Change Role</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="text-sm text-muted-foreground">
            Changing role for:{" "}
            <strong>
              {[user?.first_name, user?.last_name].filter(Boolean).join(" ") ||
                user?.username}
            </strong>
          </div>

          <RadioGroup value={role} onValueChange={setRole} className="space-y-3">
            <div className="flex items-start space-x-3 p-3 border rounded-lg">
              <RadioGroupItem value="customer" id="customer" className="mt-1" />
              <Label htmlFor="customer" className="flex-1 cursor-pointer">
                <div className="font-medium">User</div>
                <div className="text-sm text-muted-foreground">
                  Can view devices, alerts, dashboards, and integrations.
                </div>
              </Label>
            </div>
            <div className="flex items-start space-x-3 p-3 border rounded-lg">
              <RadioGroupItem value="tenant-admin" id="tenant-admin" className="mt-1" />
              <Label htmlFor="tenant-admin" className="flex-1 cursor-pointer">
                <div className="font-medium">Admin</div>
                <div className="text-sm text-muted-foreground">
                  Can manage team members, alert rules, integrations, and all settings.
                </div>
              </Label>
            </div>
          </RadioGroup>

          {changeMutation.isError && (
            <div className="text-sm text-destructive">
              {(changeMutation.error as Error).message}
            </div>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={changeMutation.isPending}>
              {changeMutation.isPending ? "Saving..." : "Save Role"}
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

Add import and route (in customer section, wrapped by RequireCustomer):

```tsx
import UsersPage from "@/features/users/UsersPage";

// In RequireCustomer children array, add:
{ path: "users", element: <UsersPage /> },
```

### Update `frontend/src/components/layout/AppSidebar.tsx`

Add to customerNav array:

```tsx
import { Users } from "lucide-react";

// In customerNav array, add after "Subscription":
{ label: "Team", href: "/users", icon: Users },
```

## Notes

- Only tenant admins can see the Team page (backend enforces this)
- "Remove from Team" removes tenant assignment, doesn't delete the Keycloak account
- Invite sends a password reset email so user can set their own password
- Tenant admins can only assign "User" or "Admin" roles (not operator roles)
