# 136-003: Operator User & Tenant Forms

## Task
Convert 6 operator dialog forms from raw `useState` to react-hook-form + zod.

---

## 1. CreateUserDialog
**File**: `frontend/src/features/operator/CreateUserDialog.tsx`

**Current state**: 7 useState calls (username, email, firstName, lastName, password, tenantId, role), manual reset on success, no validation.

**Zod schema**:
```typescript
const createUserSchema = z.object({
  username: z.string().min(3, "Username must be at least 3 characters").max(50)
    .regex(/^[a-zA-Z0-9_-]+$/, "Only letters, numbers, hyphens, underscores"),
  email: z.string().email("Valid email is required"),
  first_name: z.string().max(50).optional(),
  last_name: z.string().max(50).optional(),
  temporary_password: z.string().min(8, "Password must be at least 8 characters").optional().or(z.literal("")),
  tenant_id: z.string().optional(),
  role: z.string().min(1, "Role is required"),
});
```

**Key changes**:
- Replace `useState("__none__")` for tenantId with `.optional()` zod field and transform in onSubmit
- Use `form.reset()` on success instead of manual state clearing
- Add `<FormMessage />` below each field for validation errors

---

## 2. EditUserDialog
**File**: `frontend/src/features/operator/EditUserDialog.tsx`

**Zod schema**:
```typescript
const editUserSchema = z.object({
  email: z.string().email("Valid email is required"),
  first_name: z.string().max(50).optional(),
  last_name: z.string().max(50).optional(),
  enabled: z.boolean(),
});
```

Initialize with `form.reset(user)` when dialog opens.

---

## 3. CreateTenantDialog
**File**: `frontend/src/features/operator/CreateTenantDialog.tsx`

**Current state**: 3 useState calls (tenantId, name, email). Has smart slug generation from name.

**Zod schema**:
```typescript
const createTenantSchema = z.object({
  tenant_id: z.string().min(2, "Tenant ID is required").max(64)
    .regex(/^[a-z0-9-]+$/, "Only lowercase letters, numbers, and hyphens"),
  name: z.string().min(2, "Tenant name is required").max(100),
  contact_email: z.string().email("Valid email required").optional().or(z.literal("")),
});
```

**Preserve slug generation**: Use `form.watch("name")` and `form.setValue("tenant_id", slug)` to auto-generate tenant ID from name:
```typescript
const name = form.watch("name");
useEffect(() => {
  const currentTenantId = form.getValues("tenant_id");
  const generatedSlug = generateSlug(name);
  // Only auto-update if user hasn't manually edited the tenant_id
  if (!currentTenantId || currentTenantId === generateSlug(previousName)) {
    form.setValue("tenant_id", generatedSlug);
  }
}, [name]);
```

---

## 4. EditTenantDialog
**File**: `frontend/src/features/operator/EditTenantDialog.tsx`

**Current state**: 18 useState calls — the second most complex form. Fields include: name, contactEmail, industry, address, billingEmail, billingAddress, deviceLimit, dataResidencyRegion, supportTier, slaLevel, stripeCustomerId, status, plus profile fields.

**Zod schema**:
```typescript
const editTenantSchema = z.object({
  name: z.string().min(2, "Tenant name required").max(100),
  contact_email: z.string().email("Valid email required").optional().or(z.literal("")),
  industry: z.string().max(100).optional(),
  address: z.string().max(500).optional(),
  billing_email: z.string().email("Valid email required").optional().or(z.literal("")),
  billing_address: z.string().max(500).optional(),
  device_limit: z.coerce.number().int().min(0, "Must be >= 0").optional(),
  data_residency_region: z.string().optional(),
  support_tier: z.string().optional(),
  sla_level: z.coerce.number().min(0).max(100).optional().or(z.literal("")),
  stripe_customer_id: z.string().max(100).optional(),
  status: z.enum(["ACTIVE", "SUSPENDED"]),
});
```

**Key changes**:
- Replace all 18 useState + large useEffect initialization with `form.reset(mapTenantToFormValues(tenant))` on dialog open
- Select components need controlled form fields — use `FormField` with `render` and pass `field.value` / `field.onChange` to the Select component:
```typescript
<FormField control={form.control} name="status" render={({ field }) => (
  <FormItem>
    <FormLabel>Status</FormLabel>
    <Select value={field.value} onValueChange={field.onChange}>
      <FormControl><SelectTrigger><SelectValue /></SelectTrigger></FormControl>
      <SelectContent>
        <SelectItem value="ACTIVE">Active</SelectItem>
        <SelectItem value="SUSPENDED">Suspended</SelectItem>
      </SelectContent>
    </Select>
    <FormMessage />
  </FormItem>
)} />
```

---

## 5. AssignRoleDialog
**File**: `frontend/src/features/operator/AssignRoleDialog.tsx`

**Zod schema**:
```typescript
const assignRoleSchema = z.object({
  role_id: z.string().min(1, "Please select a role"),
});
```

Simple single-select form.

---

## 6. AssignTenantDialog
**File**: `frontend/src/features/operator/AssignTenantDialog.tsx`

**Zod schema**:
```typescript
const assignTenantSchema = z.object({
  tenant_id: z.string().min(1, "Please select a tenant"),
});
```

Simple single-select form.

---

## Common Pattern for All
1. Add imports: `z, useForm, zodResolver, Form, FormField, FormItem, FormLabel, FormControl, FormMessage`
2. Define schema at module level (above component)
3. Initialize `useForm` with `zodResolver(schema)` and `defaultValues`
4. Wrap `<form>` in `<Form {...form}>`
5. Use `form.handleSubmit(onSubmit)` on the form element
6. Replace each input with `<FormField>` + `<FormMessage />`
7. Remove all individual `useState` calls for form fields
8. Remove manual reset code — use `form.reset()` on success

## Verification
```bash
cd frontend && npm run build
npx tsc --noEmit
```
For each dialog: open → submit empty → see field errors → fill valid data → submit → success.
