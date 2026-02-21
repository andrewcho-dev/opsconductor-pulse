# 136-004: Customer User Management Forms

## Task
Convert 2 customer-facing user management dialogs from raw `useState` to react-hook-form + zod.

---

## 1. ChangeRoleDialog
**File**: `frontend/src/features/users/ChangeRoleDialog.tsx`

**Zod schema**:
```typescript
const changeRoleSchema = z.object({
  role: z.string().min(1, "Please select a role"),
});
type ChangeRoleFormValues = z.infer<typeof changeRoleSchema>;
```

**Migration**:
```typescript
const form = useForm<ChangeRoleFormValues>({
  resolver: zodResolver(changeRoleSchema),
  defaultValues: { role: currentRole || "" },
});

// Reset when dialog opens with current user's role
useEffect(() => {
  if (open && user) {
    form.reset({ role: user.role || user.roles?.[0] || "" });
  }
}, [open, user]);

const onSubmit = async (values: ChangeRoleFormValues) => {
  await changeMutation.mutateAsync({ user_id: user.user_id, role: values.role });
  onRoleChanged();
};
```

Use `FormField` with a Select component for role selection:
```typescript
<FormField control={form.control} name="role" render={({ field }) => (
  <FormItem>
    <FormLabel>New Role *</FormLabel>
    <Select value={field.value} onValueChange={field.onChange}>
      <FormControl><SelectTrigger><SelectValue placeholder="Select role" /></SelectTrigger></FormControl>
      <SelectContent>
        {availableRoles.map(r => <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>)}
      </SelectContent>
    </Select>
    <FormMessage />
  </FormItem>
)} />
```

---

## 2. EditTenantUserDialog
**File**: `frontend/src/features/users/EditTenantUserDialog.tsx`

**Zod schema**:
```typescript
const editTenantUserSchema = z.object({
  first_name: z.string().max(50).optional(),
  last_name: z.string().max(50).optional(),
  email: z.string().email("Valid email is required"),
  enabled: z.boolean(),
});
type EditTenantUserFormValues = z.infer<typeof editTenantUserSchema>;
```

**Migration**:
```typescript
const form = useForm<EditTenantUserFormValues>({
  resolver: zodResolver(editTenantUserSchema),
  defaultValues: {
    first_name: user?.first_name || "",
    last_name: user?.last_name || "",
    email: user?.email || "",
    enabled: user?.enabled ?? true,
  },
});

useEffect(() => {
  if (open && user) {
    form.reset({
      first_name: user.first_name || "",
      last_name: user.last_name || "",
      email: user.email || "",
      enabled: user.enabled ?? true,
    });
  }
}, [open, user]);
```

For the `enabled` boolean toggle, use FormField with a Switch:
```typescript
<FormField control={form.control} name="enabled" render={({ field }) => (
  <FormItem className="flex items-center justify-between">
    <FormLabel>Account Active</FormLabel>
    <FormControl>
      <Switch checked={field.value} onCheckedChange={field.onChange} />
    </FormControl>
  </FormItem>
)} />
```

---

## Common Import Changes
Add to each file:
```typescript
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Form, FormField, FormItem, FormLabel, FormControl, FormMessage } from "@/components/ui/form";
```

Remove no-longer-needed `useState` imports for form fields.

## Verification
```bash
cd frontend && npm run build
npx tsc --noEmit
```
- ChangeRoleDialog: open → submit without selecting → see error → select role → submit → works
- EditTenantUserDialog: open → clear email → submit → see email error → fix → submit → works
