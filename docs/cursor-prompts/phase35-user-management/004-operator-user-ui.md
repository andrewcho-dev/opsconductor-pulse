# 004: Operator User Management UI

## Task

Build the operator UI for system-wide user management.

## Files to Create/Modify

### 1. User List Page

**File:** `frontend/src/features/operator/UsersPage.tsx` (NEW)

```typescript
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Search, MoreHorizontal, Edit, Trash2, Key, Shield } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatTimestamp } from '@/lib/format';
import { operatorApi, User } from '@/services/api/operator';
import { CreateUserDialog } from './CreateUserDialog';
import { EditUserDialog } from './EditUserDialog';
import { ResetPasswordDialog } from './ResetPasswordDialog';
import { ManageRolesDialog } from './ManageRolesDialog';
import { ConfirmDeleteDialog } from '@/components/shared/ConfirmDeleteDialog';

export function UsersPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [tenantFilter, setTenantFilter] = useState<string>('all');
  const [createOpen, setCreateOpen] = useState(false);
  const [editUser, setEditUser] = useState<User | null>(null);
  const [resetPasswordUser, setResetPasswordUser] = useState<User | null>(null);
  const [manageRolesUser, setManageRolesUser] = useState<User | null>(null);
  const [deleteUser, setDeleteUser] = useState<User | null>(null);

  const { data: users, isLoading } = useQuery({
    queryKey: ['operator', 'users', { search, tenantFilter }],
    queryFn: () => operatorApi.listUsers({
      search: search || undefined,
      tenant_id: tenantFilter !== 'all' ? tenantFilter : undefined,
    }),
  });

  const { data: tenants } = useQuery({
    queryKey: ['operator', 'tenants'],
    queryFn: () => operatorApi.listTenants(),
  });

  const deleteMutation = useMutation({
    mutationFn: (userId: string) => operatorApi.deleteUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['operator', 'users'] });
      setDeleteUser(null);
    },
  });

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'operator-admin': return 'bg-purple-100 text-purple-800';
      case 'operator': return 'bg-blue-100 text-blue-800';
      case 'tenant-admin': return 'bg-orange-100 text-orange-800';
      case 'customer': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">User Management</h1>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Create User
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>All Users</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4 mb-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search users..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
                aria-label="Search users"
              />
            </div>
            <Select value={tenantFilter} onValueChange={setTenantFilter}>
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="All tenants" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All tenants</SelectItem>
                <SelectItem value="none">No tenant (operators)</SelectItem>
                {tenants?.tenants?.map((t) => (
                  <SelectItem key={t.tenant_id} value={t.tenant_id}>
                    {t.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <Table aria-label="Users list">
            <TableHeader>
              <TableRow>
                <TableHead>Username</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Tenant</TableHead>
                <TableHead>Roles</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
                <TableHead className="w-[50px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-8">
                    Loading...
                  </TableCell>
                </TableRow>
              ) : users?.users?.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                    No users found
                  </TableCell>
                </TableRow>
              ) : (
                users?.users?.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell className="font-medium">{user.username}</TableCell>
                    <TableCell>{user.email || '-'}</TableCell>
                    <TableCell>
                      {user.first_name || user.last_name
                        ? `${user.first_name || ''} ${user.last_name || ''}`.trim()
                        : '-'}
                    </TableCell>
                    <TableCell>{user.tenant_name || '-'}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {user.roles.map((role) => (
                          <Badge key={role} className={getRoleBadgeColor(role)}>
                            {role}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge className={user.enabled ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                        {user.enabled ? 'Active' : 'Disabled'}
                      </Badge>
                    </TableCell>
                    <TableCell>{formatTimestamp(user.created_at)}</TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm" aria-label="User actions">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => setEditUser(user)}>
                            <Edit className="h-4 w-4 mr-2" />
                            Edit
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => setManageRolesUser(user)}>
                            <Shield className="h-4 w-4 mr-2" />
                            Manage Roles
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => setResetPasswordUser(user)}>
                            <Key className="h-4 w-4 mr-2" />
                            Reset Password
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={() => setDeleteUser(user)}
                            className="text-destructive"
                          >
                            <Trash2 className="h-4 w-4 mr-2" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <CreateUserDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        tenants={tenants?.tenants || []}
      />

      {editUser && (
        <EditUserDialog
          user={editUser}
          open={!!editUser}
          onOpenChange={(open) => !open && setEditUser(null)}
          tenants={tenants?.tenants || []}
        />
      )}

      {resetPasswordUser && (
        <ResetPasswordDialog
          user={resetPasswordUser}
          open={!!resetPasswordUser}
          onOpenChange={(open) => !open && setResetPasswordUser(null)}
        />
      )}

      {manageRolesUser && (
        <ManageRolesDialog
          user={manageRolesUser}
          open={!!manageRolesUser}
          onOpenChange={(open) => !open && setManageRolesUser(null)}
        />
      )}

      {deleteUser && (
        <ConfirmDeleteDialog
          open={!!deleteUser}
          onOpenChange={(open) => !open && setDeleteUser(null)}
          title="Delete User"
          description={`Are you sure you want to delete user "${deleteUser.username}"? This action cannot be undone.`}
          onConfirm={() => deleteMutation.mutate(deleteUser.id)}
          isLoading={deleteMutation.isPending}
        />
      )}
    </div>
  );
}
```

### 2. Create User Dialog

**File:** `frontend/src/features/operator/CreateUserDialog.tsx` (NEW)

```typescript
import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { operatorApi, Tenant } from '@/services/api/operator';
import { toast } from '@/components/ui/use-toast';

const createUserSchema = z.object({
  username: z.string().min(3, 'Username must be at least 3 characters'),
  email: z.string().email('Invalid email address'),
  first_name: z.string().optional(),
  last_name: z.string().optional(),
  tenant_id: z.string().optional(),
  password: z.string().min(8, 'Password must be at least 8 characters').optional(),
  temporary_password: z.boolean().default(true),
  roles: z.array(z.string()).default([]),
});

type CreateUserForm = z.infer<typeof createUserSchema>;

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tenants: Tenant[];
}

const AVAILABLE_ROLES = [
  { id: 'operator-admin', label: 'Operator Admin', description: 'Full system access' },
  { id: 'operator', label: 'Operator', description: 'System monitoring and management' },
  { id: 'tenant-admin', label: 'Tenant Admin', description: 'Tenant user management' },
  { id: 'customer', label: 'Customer', description: 'Standard tenant access' },
];

export function CreateUserDialog({ open, onOpenChange, tenants }: Props) {
  const queryClient = useQueryClient();
  const [selectedRoles, setSelectedRoles] = useState<string[]>([]);

  const form = useForm<CreateUserForm>({
    resolver: zodResolver(createUserSchema),
    defaultValues: {
      username: '',
      email: '',
      first_name: '',
      last_name: '',
      tenant_id: '',
      password: '',
      temporary_password: true,
      roles: [],
    },
  });

  const mutation = useMutation({
    mutationFn: (data: CreateUserForm) => operatorApi.createUser({
      ...data,
      roles: selectedRoles,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['operator', 'users'] });
      onOpenChange(false);
      form.reset();
      setSelectedRoles([]);
      toast({ title: 'User created successfully' });
    },
    onError: (error: Error) => {
      toast({ title: 'Failed to create user', description: error.message, variant: 'destructive' });
    },
  });

  const toggleRole = (roleId: string) => {
    setSelectedRoles((prev) =>
      prev.includes(roleId)
        ? prev.filter((r) => r !== roleId)
        : [...prev, roleId]
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Create User</DialogTitle>
        </DialogHeader>

        <form onSubmit={form.handleSubmit((data) => mutation.mutate(data))} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="username">Username *</Label>
              <Input id="username" {...form.register('username')} />
              {form.formState.errors.username && (
                <p className="text-sm text-destructive">{form.formState.errors.username.message}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email *</Label>
              <Input id="email" type="email" {...form.register('email')} />
              {form.formState.errors.email && (
                <p className="text-sm text-destructive">{form.formState.errors.email.message}</p>
              )}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="first_name">First Name</Label>
              <Input id="first_name" {...form.register('first_name')} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="last_name">Last Name</Label>
              <Input id="last_name" {...form.register('last_name')} />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="tenant">Tenant</Label>
            <Select
              value={form.watch('tenant_id') || ''}
              onValueChange={(value) => form.setValue('tenant_id', value === 'none' ? undefined : value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select tenant (optional)" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">No tenant (operator)</SelectItem>
                {tenants.map((t) => (
                  <SelectItem key={t.tenant_id} value={t.tenant_id}>
                    {t.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">Initial Password</Label>
            <Input id="password" type="password" {...form.register('password')} />
            {form.formState.errors.password && (
              <p className="text-sm text-destructive">{form.formState.errors.password.message}</p>
            )}
          </div>

          <div className="flex items-center gap-2">
            <Checkbox
              id="temporary_password"
              checked={form.watch('temporary_password')}
              onCheckedChange={(checked) => form.setValue('temporary_password', !!checked)}
            />
            <Label htmlFor="temporary_password" className="text-sm">
              Require password change on first login
            </Label>
          </div>

          <div className="space-y-2">
            <Label>Roles</Label>
            <div className="space-y-2">
              {AVAILABLE_ROLES.map((role) => (
                <div key={role.id} className="flex items-center gap-2">
                  <Checkbox
                    id={`role-${role.id}`}
                    checked={selectedRoles.includes(role.id)}
                    onCheckedChange={() => toggleRole(role.id)}
                  />
                  <Label htmlFor={`role-${role.id}`} className="text-sm">
                    {role.label}
                    <span className="text-muted-foreground ml-2">({role.description})</span>
                  </Label>
                </div>
              ))}
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? 'Creating...' : 'Create User'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
```

### 3. Edit User Dialog

**File:** `frontend/src/features/operator/EditUserDialog.tsx` (NEW)

```typescript
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { operatorApi, User, Tenant } from '@/services/api/operator';
import { toast } from '@/components/ui/use-toast';

const editUserSchema = z.object({
  email: z.string().email('Invalid email address').optional(),
  first_name: z.string().optional(),
  last_name: z.string().optional(),
  tenant_id: z.string().optional(),
  enabled: z.boolean().optional(),
});

type EditUserForm = z.infer<typeof editUserSchema>;

interface Props {
  user: User;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tenants: Tenant[];
}

export function EditUserDialog({ user, open, onOpenChange, tenants }: Props) {
  const queryClient = useQueryClient();

  const form = useForm<EditUserForm>({
    resolver: zodResolver(editUserSchema),
    defaultValues: {
      email: user.email || '',
      first_name: user.first_name || '',
      last_name: user.last_name || '',
      tenant_id: user.tenant_id || '',
      enabled: user.enabled,
    },
  });

  const mutation = useMutation({
    mutationFn: (data: EditUserForm) => operatorApi.updateUser(user.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['operator', 'users'] });
      onOpenChange(false);
      toast({ title: 'User updated successfully' });
    },
    onError: (error: Error) => {
      toast({ title: 'Failed to update user', description: error.message, variant: 'destructive' });
    },
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Edit User: {user.username}</DialogTitle>
        </DialogHeader>

        <form onSubmit={form.handleSubmit((data) => mutation.mutate(data))} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" {...form.register('email')} />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="first_name">First Name</Label>
              <Input id="first_name" {...form.register('first_name')} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="last_name">Last Name</Label>
              <Input id="last_name" {...form.register('last_name')} />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="tenant">Tenant</Label>
            <Select
              value={form.watch('tenant_id') || 'none'}
              onValueChange={(value) => form.setValue('tenant_id', value === 'none' ? undefined : value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select tenant" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">No tenant</SelectItem>
                {tenants.map((t) => (
                  <SelectItem key={t.tenant_id} value={t.tenant_id}>
                    {t.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center justify-between">
            <Label htmlFor="enabled">Account Enabled</Label>
            <Switch
              id="enabled"
              checked={form.watch('enabled')}
              onCheckedChange={(checked) => form.setValue('enabled', checked)}
            />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? 'Saving...' : 'Save Changes'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
```

### 4. Reset Password Dialog

**File:** `frontend/src/features/operator/ResetPasswordDialog.tsx` (NEW)

```typescript
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { operatorApi, User } from '@/services/api/operator';
import { toast } from '@/components/ui/use-toast';

const resetPasswordSchema = z.object({
  password: z.string().min(8, 'Password must be at least 8 characters'),
  temporary: z.boolean().default(false),
});

type ResetPasswordForm = z.infer<typeof resetPasswordSchema>;

interface Props {
  user: User;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ResetPasswordDialog({ user, open, onOpenChange }: Props) {
  const form = useForm<ResetPasswordForm>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: {
      password: '',
      temporary: false,
    },
  });

  const mutation = useMutation({
    mutationFn: (data: ResetPasswordForm) => operatorApi.resetPassword(user.id, data),
    onSuccess: () => {
      onOpenChange(false);
      form.reset();
      toast({ title: 'Password reset successfully' });
    },
    onError: (error: Error) => {
      toast({ title: 'Failed to reset password', description: error.message, variant: 'destructive' });
    },
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Reset Password: {user.username}</DialogTitle>
        </DialogHeader>

        <form onSubmit={form.handleSubmit((data) => mutation.mutate(data))} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="password">New Password</Label>
            <Input id="password" type="password" {...form.register('password')} />
            {form.formState.errors.password && (
              <p className="text-sm text-destructive">{form.formState.errors.password.message}</p>
            )}
          </div>

          <div className="flex items-center gap-2">
            <Checkbox
              id="temporary"
              checked={form.watch('temporary')}
              onCheckedChange={(checked) => form.setValue('temporary', !!checked)}
            />
            <Label htmlFor="temporary" className="text-sm">
              Require password change on next login
            </Label>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? 'Resetting...' : 'Reset Password'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
```

### 5. Manage Roles Dialog

**File:** `frontend/src/features/operator/ManageRolesDialog.tsx` (NEW)

```typescript
import { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { operatorApi, User } from '@/services/api/operator';
import { toast } from '@/components/ui/use-toast';

const AVAILABLE_ROLES = [
  { id: 'operator-admin', label: 'Operator Admin', description: 'Full system access', level: 'system' },
  { id: 'operator', label: 'Operator', description: 'System monitoring and management', level: 'system' },
  { id: 'tenant-admin', label: 'Tenant Admin', description: 'Tenant user management', level: 'tenant' },
  { id: 'customer', label: 'Customer', description: 'Standard tenant access', level: 'tenant' },
];

interface Props {
  user: User;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ManageRolesDialog({ user, open, onOpenChange }: Props) {
  const queryClient = useQueryClient();
  const [selectedRoles, setSelectedRoles] = useState<string[]>(user.roles);

  useEffect(() => {
    setSelectedRoles(user.roles);
  }, [user.roles]);

  const assignMutation = useMutation({
    mutationFn: (role: string) => operatorApi.assignRole(user.id, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['operator', 'users'] });
    },
  });

  const removeMutation = useMutation({
    mutationFn: (role: string) => operatorApi.removeRole(user.id, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['operator', 'users'] });
    },
  });

  const toggleRole = async (roleId: string) => {
    try {
      if (selectedRoles.includes(roleId)) {
        await removeMutation.mutateAsync(roleId);
        setSelectedRoles((prev) => prev.filter((r) => r !== roleId));
        toast({ title: `Role "${roleId}" removed` });
      } else {
        await assignMutation.mutateAsync(roleId);
        setSelectedRoles((prev) => [...prev, roleId]);
        toast({ title: `Role "${roleId}" assigned` });
      }
    } catch (error) {
      toast({
        title: 'Failed to update role',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      });
    }
  };

  const isLoading = assignMutation.isPending || removeMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Manage Roles: {user.username}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div>
            <Label className="text-sm text-muted-foreground">Current Roles</Label>
            <div className="flex flex-wrap gap-1 mt-1">
              {selectedRoles.length === 0 ? (
                <span className="text-muted-foreground">No roles assigned</span>
              ) : (
                selectedRoles.map((role) => (
                  <Badge key={role}>{role}</Badge>
                ))
              )}
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <Label className="text-sm font-medium">System Roles</Label>
              <div className="space-y-2 mt-2">
                {AVAILABLE_ROLES.filter((r) => r.level === 'system').map((role) => (
                  <div key={role.id} className="flex items-center gap-2">
                    <Checkbox
                      id={`role-${role.id}`}
                      checked={selectedRoles.includes(role.id)}
                      onCheckedChange={() => toggleRole(role.id)}
                      disabled={isLoading}
                    />
                    <Label htmlFor={`role-${role.id}`} className="text-sm">
                      {role.label}
                      <span className="text-muted-foreground ml-2">({role.description})</span>
                    </Label>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <Label className="text-sm font-medium">Tenant Roles</Label>
              <div className="space-y-2 mt-2">
                {AVAILABLE_ROLES.filter((r) => r.level === 'tenant').map((role) => (
                  <div key={role.id} className="flex items-center gap-2">
                    <Checkbox
                      id={`role-${role.id}`}
                      checked={selectedRoles.includes(role.id)}
                      onCheckedChange={() => toggleRole(role.id)}
                      disabled={isLoading}
                    />
                    <Label htmlFor={`role-${role.id}`} className="text-sm">
                      {role.label}
                      <span className="text-muted-foreground ml-2">({role.description})</span>
                    </Label>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button onClick={() => onOpenChange(false)}>
            Done
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

### 6. API Service Updates

**File:** `frontend/src/services/api/operator.ts`

Add the following to the existing operator API:

```typescript
export interface User {
  id: string;
  username: string;
  email: string | null;
  first_name: string | null;
  last_name: string | null;
  enabled: boolean;
  tenant_id: string | null;
  tenant_name: string | null;
  roles: string[];
  created_at: string | null;
}

export interface CreateUserRequest {
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
  tenant_id?: string;
  password?: string;
  temporary_password?: boolean;
  roles?: string[];
}

export interface UpdateUserRequest {
  email?: string;
  first_name?: string;
  last_name?: string;
  tenant_id?: string;
  enabled?: boolean;
}

export interface ResetPasswordRequest {
  password: string;
  temporary?: boolean;
}

export const operatorApi = {
  // ... existing methods ...

  // User management
  async listUsers(params?: { search?: string; tenant_id?: string; limit?: number; offset?: number }) {
    const query = new URLSearchParams();
    if (params?.search) query.set('search', params.search);
    if (params?.tenant_id) query.set('tenant_id', params.tenant_id);
    if (params?.limit) query.set('limit', String(params.limit));
    if (params?.offset) query.set('offset', String(params.offset));
    return apiGet<{ users: User[]; count: number }>(`/operator/users?${query}`);
  },

  async getUser(userId: string) {
    return apiGet<User>(`/operator/users/${userId}`);
  },

  async createUser(data: CreateUserRequest) {
    return apiPost<{ user_id: string; username: string }>('/operator/users', data);
  },

  async updateUser(userId: string, data: UpdateUserRequest) {
    return apiPatch<{ user_id: string; updated: boolean }>(`/operator/users/${userId}`, data);
  },

  async deleteUser(userId: string) {
    return apiDelete<{ user_id: string; deleted: boolean }>(`/operator/users/${userId}`);
  },

  async resetPassword(userId: string, data: ResetPasswordRequest) {
    return apiPost<{ user_id: string; password_reset: boolean }>(`/operator/users/${userId}/password`, data);
  },

  async assignRole(userId: string, role: string) {
    return apiPost<{ user_id: string; role: string; assigned: boolean }>(`/operator/users/${userId}/roles`, { role });
  },

  async removeRole(userId: string, role: string) {
    return apiDelete<{ user_id: string; role: string; removed: boolean }>(`/operator/users/${userId}/roles/${role}`);
  },

  async listRoles() {
    return apiGet<{ roles: Array<{ id: string; name: string; description?: string }> }>('/operator/roles');
  },
};
```

### 7. Router Update

**File:** `frontend/src/router.tsx`

Add route:

```typescript
import { UsersPage } from '@/features/operator/UsersPage';

// In operator routes:
{
  path: 'users',
  element: <UsersPage />,
},
```

### 8. Sidebar Update

**File:** `frontend/src/components/layout/AppSidebar.tsx`

Add Users link to operator section:

```typescript
import { Users } from 'lucide-react';

// In operator navigation items:
{
  title: 'Users',
  icon: Users,
  url: '/operator/users',
},
```

## Verification

```bash
cd frontend

# Type check
npm run type-check

# Lint
npm run lint

# Build
npm run build

# Manual test
# 1. Navigate to /operator/users
# 2. Create a new user
# 3. Edit user details
# 4. Reset password
# 5. Manage roles
# 6. Delete user
```
