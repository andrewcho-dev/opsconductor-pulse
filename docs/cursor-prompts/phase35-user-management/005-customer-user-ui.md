# 005: Customer User Management UI

## Task

Build the customer UI for tenant-level user management. Only users with tenant-admin role can access this page.

## Files to Create/Modify

### 1. Tenant Users Page

**File:** `frontend/src/features/settings/UsersPage.tsx` (NEW)

```typescript
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Search, MoreHorizontal, Edit, Trash2, Key, Shield, ShieldCheck } from 'lucide-react';
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
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { formatTimestamp } from '@/lib/format';
import { customerApi, TenantUser } from '@/services/api/customer';
import { useAuth } from '@/hooks/use-auth';
import { CreateTenantUserDialog } from './CreateTenantUserDialog';
import { EditTenantUserDialog } from './EditTenantUserDialog';
import { ResetTenantUserPasswordDialog } from './ResetTenantUserPasswordDialog';
import { ConfirmDeleteDialog } from '@/components/shared/ConfirmDeleteDialog';
import { toast } from '@/components/ui/use-toast';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertTriangle } from 'lucide-react';

export function UsersPage() {
  const queryClient = useQueryClient();
  const { user: currentUser } = useAuth();
  const [search, setSearch] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [editUser, setEditUser] = useState<TenantUser | null>(null);
  const [resetPasswordUser, setResetPasswordUser] = useState<TenantUser | null>(null);
  const [deleteUser, setDeleteUser] = useState<TenantUser | null>(null);
  const [toggleAdminUser, setToggleAdminUser] = useState<TenantUser | null>(null);

  const { data: users, isLoading, error } = useQuery({
    queryKey: ['customer', 'users', { search }],
    queryFn: () => customerApi.listUsers({ search: search || undefined }),
  });

  const deleteMutation = useMutation({
    mutationFn: (userId: string) => customerApi.deleteUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customer', 'users'] });
      setDeleteUser(null);
      toast({ title: 'User deleted successfully' });
    },
    onError: (error: Error) => {
      toast({ title: 'Failed to delete user', description: error.message, variant: 'destructive' });
    },
  });

  const toggleAdminMutation = useMutation({
    mutationFn: ({ userId, isAdmin }: { userId: string; isAdmin: boolean }) =>
      customerApi.toggleAdmin(userId, isAdmin),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['customer', 'users'] });
      setToggleAdminUser(null);
      toast({ title: variables.isAdmin ? 'Admin role granted' : 'Admin role removed' });
    },
    onError: (error: Error) => {
      toast({ title: 'Failed to update admin role', description: error.message, variant: 'destructive' });
    },
  });

  const isCurrentUser = (userId: string) => currentUser?.sub === userId;

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>
          Failed to load users. You may not have permission to manage users.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Team Members</h1>
          <p className="text-muted-foreground">Manage users in your organization</p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Invite User
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Users</CardTitle>
          <CardDescription>
            {users?.count || 0} users in your organization
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="mb-4">
            <div className="relative max-w-sm">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search users..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
                aria-label="Search users"
              />
            </div>
          </div>

          <Table aria-label="Team members list">
            <TableHeader>
              <TableRow>
                <TableHead>User</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Joined</TableHead>
                <TableHead className="w-[50px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8">
                    Loading...
                  </TableCell>
                </TableRow>
              ) : users?.users?.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                    No users found
                  </TableCell>
                </TableRow>
              ) : (
                users?.users?.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                          <span className="text-sm font-medium text-primary">
                            {(user.first_name?.[0] || user.username[0]).toUpperCase()}
                          </span>
                        </div>
                        <div>
                          <div className="font-medium">
                            {user.first_name || user.last_name
                              ? `${user.first_name || ''} ${user.last_name || ''}`.trim()
                              : user.username}
                            {isCurrentUser(user.id) && (
                              <Badge variant="outline" className="ml-2">You</Badge>
                            )}
                          </div>
                          <div className="text-sm text-muted-foreground">@{user.username}</div>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>{user.email || '-'}</TableCell>
                    <TableCell>
                      {user.roles.includes('tenant-admin') ? (
                        <Badge className="bg-orange-100 text-orange-800">
                          <ShieldCheck className="h-3 w-3 mr-1" />
                          Admin
                        </Badge>
                      ) : (
                        <Badge variant="secondary">Member</Badge>
                      )}
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
                            Edit Details
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => setResetPasswordUser(user)}>
                            <Key className="h-4 w-4 mr-2" />
                            Reset Password
                          </DropdownMenuItem>
                          {!isCurrentUser(user.id) && (
                            <>
                              <DropdownMenuItem
                                onClick={() => setToggleAdminUser(user)}
                              >
                                <Shield className="h-4 w-4 mr-2" />
                                {user.roles.includes('tenant-admin') ? 'Remove Admin' : 'Make Admin'}
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                onClick={() => setDeleteUser(user)}
                                className="text-destructive"
                              >
                                <Trash2 className="h-4 w-4 mr-2" />
                                Remove User
                              </DropdownMenuItem>
                            </>
                          )}
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

      <CreateTenantUserDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
      />

      {editUser && (
        <EditTenantUserDialog
          user={editUser}
          open={!!editUser}
          onOpenChange={(open) => !open && setEditUser(null)}
        />
      )}

      {resetPasswordUser && (
        <ResetTenantUserPasswordDialog
          user={resetPasswordUser}
          open={!!resetPasswordUser}
          onOpenChange={(open) => !open && setResetPasswordUser(null)}
        />
      )}

      {deleteUser && (
        <ConfirmDeleteDialog
          open={!!deleteUser}
          onOpenChange={(open) => !open && setDeleteUser(null)}
          title="Remove User"
          description={`Are you sure you want to remove "${deleteUser.username}" from your organization? They will lose access immediately.`}
          onConfirm={() => deleteMutation.mutate(deleteUser.id)}
          isLoading={deleteMutation.isPending}
        />
      )}

      {toggleAdminUser && (
        <ConfirmDeleteDialog
          open={!!toggleAdminUser}
          onOpenChange={(open) => !open && setToggleAdminUser(null)}
          title={toggleAdminUser.roles.includes('tenant-admin') ? 'Remove Admin Role' : 'Grant Admin Role'}
          description={
            toggleAdminUser.roles.includes('tenant-admin')
              ? `Remove admin privileges from "${toggleAdminUser.username}"? They will no longer be able to manage users.`
              : `Grant admin privileges to "${toggleAdminUser.username}"? They will be able to manage all users in your organization.`
          }
          confirmText={toggleAdminUser.roles.includes('tenant-admin') ? 'Remove Admin' : 'Grant Admin'}
          confirmVariant={toggleAdminUser.roles.includes('tenant-admin') ? 'destructive' : 'default'}
          onConfirm={() => toggleAdminMutation.mutate({
            userId: toggleAdminUser.id,
            isAdmin: !toggleAdminUser.roles.includes('tenant-admin'),
          })}
          isLoading={toggleAdminMutation.isPending}
        />
      )}
    </div>
  );
}
```

### 2. Create Tenant User Dialog

**File:** `frontend/src/features/settings/CreateTenantUserDialog.tsx` (NEW)

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
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { customerApi } from '@/services/api/customer';
import { toast } from '@/components/ui/use-toast';

const createUserSchema = z.object({
  username: z.string().min(3, 'Username must be at least 3 characters'),
  email: z.string().email('Invalid email address'),
  first_name: z.string().optional(),
  last_name: z.string().optional(),
  password: z.string().min(8, 'Password must be at least 8 characters').optional(),
  temporary_password: z.boolean().default(true),
  is_admin: z.boolean().default(false),
});

type CreateUserForm = z.infer<typeof createUserSchema>;

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CreateTenantUserDialog({ open, onOpenChange }: Props) {
  const queryClient = useQueryClient();

  const form = useForm<CreateUserForm>({
    resolver: zodResolver(createUserSchema),
    defaultValues: {
      username: '',
      email: '',
      first_name: '',
      last_name: '',
      password: '',
      temporary_password: true,
      is_admin: false,
    },
  });

  const mutation = useMutation({
    mutationFn: (data: CreateUserForm) => customerApi.createUser(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customer', 'users'] });
      onOpenChange(false);
      form.reset();
      toast({ title: 'User invited successfully' });
    },
    onError: (error: Error) => {
      toast({ title: 'Failed to create user', description: error.message, variant: 'destructive' });
    },
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Invite Team Member</DialogTitle>
          <DialogDescription>
            Add a new user to your organization. They will receive an email to set up their account.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={form.handleSubmit((data) => mutation.mutate(data))} className="space-y-4">
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

          <div className="space-y-2">
            <Label htmlFor="password">Initial Password</Label>
            <Input id="password" type="password" {...form.register('password')} placeholder="Leave blank to auto-generate" />
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

          <div className="flex items-center gap-2">
            <Checkbox
              id="is_admin"
              checked={form.watch('is_admin')}
              onCheckedChange={(checked) => form.setValue('is_admin', !!checked)}
            />
            <Label htmlFor="is_admin" className="text-sm">
              Grant admin privileges (can manage other users)
            </Label>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? 'Inviting...' : 'Invite User'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
```

### 3. Edit Tenant User Dialog

**File:** `frontend/src/features/settings/EditTenantUserDialog.tsx` (NEW)

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
import { customerApi, TenantUser } from '@/services/api/customer';
import { toast } from '@/components/ui/use-toast';

const editUserSchema = z.object({
  email: z.string().email('Invalid email address').optional(),
  first_name: z.string().optional(),
  last_name: z.string().optional(),
  enabled: z.boolean().optional(),
});

type EditUserForm = z.infer<typeof editUserSchema>;

interface Props {
  user: TenantUser;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function EditTenantUserDialog({ user, open, onOpenChange }: Props) {
  const queryClient = useQueryClient();

  const form = useForm<EditUserForm>({
    resolver: zodResolver(editUserSchema),
    defaultValues: {
      email: user.email || '',
      first_name: user.first_name || '',
      last_name: user.last_name || '',
      enabled: user.enabled,
    },
  });

  const mutation = useMutation({
    mutationFn: (data: EditUserForm) => customerApi.updateUser(user.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customer', 'users'] });
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
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" {...form.register('email')} />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <Label htmlFor="enabled">Account Active</Label>
              <p className="text-sm text-muted-foreground">
                Disabled users cannot log in
              </p>
            </div>
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

**File:** `frontend/src/features/settings/ResetTenantUserPasswordDialog.tsx` (NEW)

```typescript
import { useMutation } from '@tanstack/react-query';
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
import { customerApi, TenantUser } from '@/services/api/customer';
import { toast } from '@/components/ui/use-toast';

const resetPasswordSchema = z.object({
  password: z.string().min(8, 'Password must be at least 8 characters'),
  temporary: z.boolean().default(true),
});

type ResetPasswordForm = z.infer<typeof resetPasswordSchema>;

interface Props {
  user: TenantUser;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ResetTenantUserPasswordDialog({ user, open, onOpenChange }: Props) {
  const form = useForm<ResetPasswordForm>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: {
      password: '',
      temporary: true,
    },
  });

  const mutation = useMutation({
    mutationFn: (data: ResetPasswordForm) => customerApi.resetPassword(user.id, data),
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

### 5. Confirm Delete Dialog (Shared)

**File:** `frontend/src/components/shared/ConfirmDeleteDialog.tsx` (NEW if not exists)

```typescript
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { buttonVariants } from '@/components/ui/button';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmText?: string;
  confirmVariant?: 'default' | 'destructive';
  onConfirm: () => void;
  isLoading?: boolean;
}

export function ConfirmDeleteDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmText = 'Delete',
  confirmVariant = 'destructive',
  onConfirm,
  isLoading,
}: Props) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isLoading}>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={onConfirm}
            disabled={isLoading}
            className={buttonVariants({ variant: confirmVariant })}
          >
            {isLoading ? 'Processing...' : confirmText}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
```

### 6. Customer API Service Updates

**File:** `frontend/src/services/api/customer.ts`

Add the following:

```typescript
export interface TenantUser {
  id: string;
  username: string;
  email: string | null;
  first_name: string | null;
  last_name: string | null;
  enabled: boolean;
  roles: string[];
  created_at: string | null;
}

export interface CreateTenantUserRequest {
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
  password?: string;
  temporary_password?: boolean;
  is_admin?: boolean;
}

export interface UpdateTenantUserRequest {
  email?: string;
  first_name?: string;
  last_name?: string;
  enabled?: boolean;
}

export interface ResetPasswordRequest {
  password: string;
  temporary?: boolean;
}

export const customerApi = {
  // ... existing methods ...

  // User management
  async listUsers(params?: { search?: string; limit?: number; offset?: number }) {
    const query = new URLSearchParams();
    if (params?.search) query.set('search', params.search);
    if (params?.limit) query.set('limit', String(params.limit));
    if (params?.offset) query.set('offset', String(params.offset));
    return apiGet<{ users: TenantUser[]; count: number }>(`/customer/users?${query}`);
  },

  async getUser(userId: string) {
    return apiGet<TenantUser>(`/customer/users/${userId}`);
  },

  async createUser(data: CreateTenantUserRequest) {
    return apiPost<{ user_id: string; username: string }>('/customer/users', data);
  },

  async updateUser(userId: string, data: UpdateTenantUserRequest) {
    return apiPatch<{ user_id: string; updated: boolean }>(`/customer/users/${userId}`, data);
  },

  async deleteUser(userId: string) {
    return apiDelete<{ user_id: string; deleted: boolean }>(`/customer/users/${userId}`);
  },

  async resetPassword(userId: string, data: ResetPasswordRequest) {
    return apiPost<{ user_id: string; password_reset: boolean }>(`/customer/users/${userId}/password`, data);
  },

  async toggleAdmin(userId: string, isAdmin: boolean) {
    return apiPatch<{ user_id: string; is_admin: boolean }>(`/customer/users/${userId}/admin`, { is_admin: isAdmin });
  },
};
```

### 7. Router Update

**File:** `frontend/src/router.tsx`

Add route under customer/settings:

```typescript
import { UsersPage as TenantUsersPage } from '@/features/settings/UsersPage';

// In customer routes under settings:
{
  path: 'settings',
  children: [
    // ... existing routes
    {
      path: 'users',
      element: <TenantUsersPage />,
    },
  ],
},
```

### 8. Settings Page Navigation

**File:** `frontend/src/features/settings/SettingsPage.tsx` (or sidebar)

Add link to Users management:

```typescript
import { Users } from 'lucide-react';

// Add to settings navigation:
{
  title: 'Team Members',
  description: 'Manage users in your organization',
  icon: Users,
  href: '/app/settings/users',
  // Only show for tenant-admin
  requiresRole: 'tenant-admin',
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

# Manual test (as tenant-admin user)
# 1. Navigate to /app/settings/users
# 2. Invite a new user
# 3. Edit user details
# 4. Reset password
# 5. Toggle admin role
# 6. Remove user
```
