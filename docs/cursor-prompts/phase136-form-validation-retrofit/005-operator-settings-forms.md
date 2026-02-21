# 136-005: Operator Settings & Device Tiers Forms

## Task
Convert operator settings and device tier forms from raw `useState` to react-hook-form + zod.

---

## 1. SettingsPage
**File**: `frontend/src/features/operator/SettingsPage.tsx`

Read the file to understand what forms it contains (may have multiple form sections for different settings). For each form section:

**Define a schema per form section**, for example:
```typescript
const generalSettingsSchema = z.object({
  instance_name: z.string().min(1, "Instance name required").max(100),
  support_email: z.string().email("Valid email required").optional().or(z.literal("")),
  default_timezone: z.string().optional(),
  // ... other settings fields found in the file
});

// If there's a separate security/auth settings section:
const securitySettingsSchema = z.object({
  session_timeout_minutes: z.coerce.number().int().min(5).max(1440),
  max_login_attempts: z.coerce.number().int().min(1).max(20),
  // ... etc
});
```

If the page uses a single large form, create one combined schema. If it uses multiple Card sections each with their own save button, create separate schemas and separate `useForm` instances.

**Key pattern for settings pages** (different from dialogs):
- Settings forms are NOT in a dialog — they're inline on the page
- They may use a "Save" button per section
- Use `form.formState.isDirty` to enable/disable the Save button:
```typescript
<Button type="submit" disabled={!form.formState.isDirty || mutation.isPending}>
  {mutation.isPending ? "Saving..." : "Save Changes"}
</Button>
```

---

## 2. DeviceTiersPage
**File**: `frontend/src/features/operator/DeviceTiersPage.tsx`

This page likely has forms for creating/editing device tiers. Read the file to understand whether it uses:
- Inline editing (edit-in-place in a table)
- A dialog/modal for create/edit
- A separate form section

**Zod schema for device tier**:
```typescript
const deviceTierSchema = z.object({
  name: z.string().min(2, "Tier name required").max(50),
  display_name: z.string().min(2).max(100).optional(),
  description: z.string().max(500).optional(),
  rate_limit_messages_per_hour: z.coerce.number().int().min(0, "Must be non-negative").optional(),
  rate_limit_commands_per_hour: z.coerce.number().int().min(0, "Must be non-negative").optional(),
  max_payload_bytes: z.coerce.number().int().min(0).optional(),
  // Add other tier-specific fields found in the file
});
type DeviceTierFormValues = z.infer<typeof deviceTierSchema>;
```

If using a dialog:
```typescript
const form = useForm<DeviceTierFormValues>({
  resolver: zodResolver(deviceTierSchema),
  defaultValues: editingTier
    ? mapTierToFormValues(editingTier)
    : { name: "", rate_limit_messages_per_hour: 1000, ... },
});
```

If using inline editing, react-hook-form may not be the best fit. In that case, document why and keep the current approach with basic zod validation on save:
```typescript
// Inline editing: validate with zod before save
const result = deviceTierSchema.safeParse(rowData);
if (!result.success) {
  // Show errors
}
```

---

## Verification
```bash
cd frontend && npm run build
npx tsc --noEmit
```
- SettingsPage: change a setting → Save enabled → submit → saved. Don't change → Save disabled.
- DeviceTiersPage: create tier with empty name → error → fill in → submit → works
