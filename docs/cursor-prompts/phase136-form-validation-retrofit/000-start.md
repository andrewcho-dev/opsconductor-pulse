# Phase 136 — Form Validation Retrofit

## Goal
Convert all remaining raw `useState` forms to react-hook-form + zod with field-level validation, required indicators, and dirty-state warnings.

## Current State
- 3 of 16 forms already use react-hook-form + zod: AddDeviceModal, CreateRoleDialog, InviteUserDialog
- The remaining 13 use raw `useState` with no field validation, no error messages, and no dirty-state tracking

## Dependencies Already Installed
```json
"@hookform/resolvers": "^5.2.2",
"react-hook-form": "^7.71.1",
"zod": "^4.3.6"
```

## Shadcn Form Components Available
`frontend/src/components/ui/form.tsx` exports: `Form, FormField, FormItem, FormLabel, FormControl, FormMessage, FormDescription`

## Reference Pattern (from AddDeviceModal)
```typescript
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Form, FormField, FormItem, FormLabel, FormControl, FormMessage } from "@/components/ui/form";

const schema = z.object({
  name: z.string().min(1, "Name is required").max(100),
  email: z.string().email("Valid email is required"),
});
type FormValues = z.infer<typeof schema>;

const form = useForm<FormValues>({
  resolver: zodResolver(schema),
  defaultValues: { name: "", email: "" },
});

<Form {...form}>
  <form onSubmit={form.handleSubmit(onSubmit)}>
    <FormField control={form.control} name="name" render={({ field }) => (
      <FormItem>
        <FormLabel>Name *</FormLabel>
        <FormControl><Input {...field} /></FormControl>
        <FormMessage />
      </FormItem>
    )} />
  </form>
</Form>
```

## Execution Order
1. `001-alert-monitoring-forms.md` — AlertRuleDialog
2. `002-device-forms.md` — DeviceEditModal, EditDeviceModal
3. `003-operator-forms.md` — CreateUserDialog, EditUserDialog, CreateTenantDialog, EditTenantDialog, AssignRoleDialog, AssignTenantDialog
4. `004-customer-user-forms.md` — ChangeRoleDialog, EditTenantUserDialog
5. `005-operator-settings-forms.md` — SettingsPage, DeviceTiersPage
6. `006-dirty-state-guard.md` — useFormDirtyGuard hook + apply to all dialogs

## Verification (after all tasks)
```bash
cd frontend && npm run build
npx tsc --noEmit
```
Manual: for each form, submit with empty required fields → see field-level errors. Fill in valid data → submit succeeds.
