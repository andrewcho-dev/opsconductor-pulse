# 002 — Form Validation with react-hook-form + zod

## Context

Forms across the app use manual `useState` for each field, no schema validation, and inconsistent error display. This step installs `react-hook-form`, `@hookform/resolvers`, and `zod`, creates the Shadcn Form wrapper component, and retrofits the four highest-traffic form dialogs.

---

## 2a — Install dependencies

```bash
cd frontend && npm install react-hook-form @hookform/resolvers zod
```

---

## 2b — Create Shadcn Form component

**File**: `frontend/src/components/ui/form.tsx` (new file)

Create the standard Shadcn Form component. This wraps react-hook-form with accessible form field components.

```tsx
import * as React from "react";
import type * as LabelPrimitive from "@radix-ui/react-label";
import { Slot } from "@radix-ui/react-slot";
import {
  Controller,
  FormProvider,
  useFormContext,
  type ControllerProps,
  type FieldPath,
  type FieldValues,
} from "react-hook-form";

import { cn } from "@/lib/utils";
import { Label } from "@/components/ui/label";

const Form = FormProvider;

type FormFieldContextValue<
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>,
> = {
  name: TName;
};

const FormFieldContext = React.createContext<FormFieldContextValue>(
  {} as FormFieldContextValue
);

const FormField = <
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>,
>({
  ...props
}: ControllerProps<TFieldValues, TName>) => {
  return (
    <FormFieldContext.Provider value={{ name: props.name }}>
      <Controller {...props} />
    </FormFieldContext.Provider>
  );
};

const useFormField = () => {
  const fieldContext = React.useContext(FormFieldContext);
  const itemContext = React.useContext(FormItemContext);
  const { getFieldState, formState } = useFormContext();

  const fieldState = getFieldState(fieldContext.name, formState);

  if (!fieldContext) {
    throw new Error("useFormField should be used within <FormField>");
  }

  const { id } = itemContext;

  return {
    id,
    name: fieldContext.name,
    formItemId: `${id}-form-item`,
    formDescriptionId: `${id}-form-item-description`,
    formMessageId: `${id}-form-item-message`,
    ...fieldState,
  };
};

type FormItemContextValue = {
  id: string;
};

const FormItemContext = React.createContext<FormItemContextValue>(
  {} as FormItemContextValue
);

function FormItem({ className, ...props }: React.ComponentProps<"div">) {
  const id = React.useId();

  return (
    <FormItemContext.Provider value={{ id }}>
      <div
        data-slot="form-item"
        className={cn("space-y-2", className)}
        {...props}
      />
    </FormItemContext.Provider>
  );
}

function FormLabel({
  className,
  ...props
}: React.ComponentProps<typeof LabelPrimitive.Root>) {
  const { error, formItemId } = useFormField();

  return (
    <Label
      className={cn(error && "text-destructive", className)}
      htmlFor={formItemId}
      {...props}
    />
  );
}

function FormControl({ ...props }: React.ComponentProps<typeof Slot>) {
  const { error, formItemId, formDescriptionId, formMessageId } =
    useFormField();

  return (
    <Slot
      id={formItemId}
      aria-describedby={
        !error
          ? `${formDescriptionId}`
          : `${formDescriptionId} ${formMessageId}`
      }
      aria-invalid={!!error}
      {...props}
    />
  );
}

function FormDescription({
  className,
  ...props
}: React.ComponentProps<"p">) {
  const { formDescriptionId } = useFormField();

  return (
    <p
      id={formDescriptionId}
      className={cn("text-muted-foreground text-sm", className)}
      {...props}
    />
  );
}

function FormMessage({
  className,
  children,
  ...props
}: React.ComponentProps<"p">) {
  const { error, formMessageId } = useFormField();
  const body = error ? String(error?.message) : children;

  if (!body) {
    return null;
  }

  return (
    <p
      id={formMessageId}
      className={cn("text-destructive text-sm font-medium", className)}
      {...props}
    >
      {body}
    </p>
  );
}

export {
  useFormField,
  Form,
  FormItem,
  FormLabel,
  FormControl,
  FormDescription,
  FormMessage,
  FormField,
};
```

---

## 2c — Retrofit AddDeviceModal

**File**: `frontend/src/features/devices/AddDeviceModal.tsx`

### Changes:

1. Replace all `useState` field management with `useForm` + zod schema.
2. Add required field indicators (`*`) to labels.
3. Show field-level error messages via `FormMessage`.

### Zod schema:

```tsx
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
} from "@/components/ui/form";

const addDeviceSchema = z.object({
  name: z.string().min(1, "Device name is required").max(100),
  deviceType: z.string().min(1, "Device type is required").max(50),
  siteId: z.string().optional(),
  tags: z.string().optional(),
});

type AddDeviceFormValues = z.infer<typeof addDeviceSchema>;
```

### Hook setup (inside component):

```tsx
const form = useForm<AddDeviceFormValues>({
  resolver: zodResolver(addDeviceSchema),
  defaultValues: { name: "", deviceType: "", siteId: "", tags: "" },
});
```

### Reset function:

```tsx
const reset = () => {
  form.reset();
  setError(null);
};
```

### Submit handler:

```tsx
const submit = async (values: AddDeviceFormValues) => {
  setSaving(true);
  setError(null);
  try {
    const tags = (values.tags ?? "")
      .split(",")
      .map((tag) => tag.trim())
      .filter(Boolean);
    const result = await provisionDevice({
      name: values.name.trim(),
      device_type: values.deviceType.trim(),
      site_id: values.siteId?.trim() || undefined,
      tags: tags.length > 0 ? tags : undefined,
    });
    await onCreated();
    setCredentials(result);
  } catch (err) {
    setError((err as Error)?.message ?? "Failed to provision device");
  } finally {
    setSaving(false);
  }
};
```

### Form JSX:

Replace the `<form>` with:

```tsx
<Form {...form}>
  <form className="space-y-3" onSubmit={form.handleSubmit(submit)}>
    <FormField
      control={form.control}
      name="name"
      render={({ field }) => (
        <FormItem>
          <FormLabel>Device Name *</FormLabel>
          <FormControl>
            <Input placeholder="Device Name" {...field} />
          </FormControl>
          <FormMessage />
        </FormItem>
      )}
    />
    <FormField
      control={form.control}
      name="deviceType"
      render={({ field }) => (
        <FormItem>
          <FormLabel>Device Type *</FormLabel>
          <FormControl>
            <Input placeholder="Device Type" {...field} />
          </FormControl>
          <FormMessage />
        </FormItem>
      )}
    />
    <FormField
      control={form.control}
      name="siteId"
      render={({ field }) => (
        <FormItem>
          <FormLabel>Site</FormLabel>
          <FormControl>
            <Input placeholder="Site (optional)" {...field} />
          </FormControl>
          <FormMessage />
        </FormItem>
      )}
    />
    <FormField
      control={form.control}
      name="tags"
      render={({ field }) => (
        <FormItem>
          <FormLabel>Tags</FormLabel>
          <FormControl>
            <Input placeholder="Tags (comma separated)" {...field} />
          </FormControl>
          <FormMessage />
        </FormItem>
      )}
    />
    {error && <div className="text-xs text-destructive">{error}</div>}
    <div className="flex justify-end gap-2">
      <Button type="button" variant="outline" onClick={closeAll}>Cancel</Button>
      <Button type="submit" disabled={saving}>{saving ? "Creating..." : "Create"}</Button>
    </div>
  </form>
</Form>
```

Remove the old `useState` calls for `name`, `setName`, `deviceType`, `setDeviceType`, `siteId`, `setSiteId`, `tagsInput`, `setTagsInput`. Keep `error`/`setError`, `saving`/`setSaving`, and `credentials`/`setCredentials` as regular state.

---

## 2d — Retrofit InviteUserDialog

**File**: `frontend/src/features/users/InviteUserDialog.tsx`

### Zod schema:

```tsx
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
} from "@/components/ui/form";

const inviteUserSchema = z.object({
  email: z.string().email("Valid email is required"),
  firstName: z.string().optional(),
  lastName: z.string().optional(),
  role: z.string().min(1),
});

type InviteUserFormValues = z.infer<typeof inviteUserSchema>;
```

### Hook setup:

```tsx
const form = useForm<InviteUserFormValues>({
  resolver: zodResolver(inviteUserSchema),
  defaultValues: { email: "", firstName: "", lastName: "", role: "customer" },
});
```

### Submit:

```tsx
const handleSubmit = async (values: InviteUserFormValues) => {
  try {
    await inviteMutation.mutateAsync({
      email: values.email,
      first_name: values.firstName || undefined,
      last_name: values.lastName || undefined,
      role: values.role,
    });
    form.reset();
    onInvited();
  } catch {
    // mutation state shows error
  }
};
```

### Form JSX:

Wrap with `<Form {...form}>` and convert each field to use `FormField` / `FormItem` / `FormLabel` / `FormControl` / `FormMessage`. Add `*` to the Email label since it is required. Keep the `Mail` icon inside the email input's wrapper.

Remove the old `useState` calls for `email`, `firstName`, `lastName`, `role`.

---

## 2e — Retrofit CreateRoleDialog

**File**: `frontend/src/features/roles/CreateRoleDialog.tsx`

### Zod schema:

```tsx
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
} from "@/components/ui/form";

const createRoleSchema = z.object({
  name: z.string().min(1, "Role name is required").max(50),
  description: z.string().max(200).optional(),
});

type CreateRoleFormValues = z.infer<typeof createRoleSchema>;
```

### Hook setup:

```tsx
const form = useForm<CreateRoleFormValues>({
  resolver: zodResolver(createRoleSchema),
  defaultValues: { name: "", description: "" },
});
```

Sync `form.reset()` with `editRole` in the existing `useEffect`:

```tsx
useEffect(() => {
  if (!open) return;
  if (editRole) {
    form.reset({ name: editRole.name, description: editRole.description || "" });
    setSelectedPermissionIds(new Set(editRole.permissions.map((p) => p.id)));
  } else {
    form.reset({ name: "", description: "" });
    setSelectedPermissionIds(new Set());
  }
}, [open, editRole, form]);
```

### handleSave:

Update to read from form values:

```tsx
const handleSave = async () => {
  const valid = await form.trigger();
  if (!valid) return;
  const values = form.getValues();
  const payload = {
    name: values.name.trim(),
    description: values.description?.trim() || "",
    permission_ids: Array.from(selectedPermissionIds),
  };
  ...
};
```

### canSave:

Update to use `form.formState.isValid`:

```tsx
const canSave = useMemo(() => {
  if (!form.formState.isValid) return false;
  if (selectedPermissionIds.size === 0) return false;
  if (createMutation.isPending || updateMutation.isPending) return false;
  return true;
}, [form.formState.isValid, selectedPermissionIds, createMutation.isPending, updateMutation.isPending]);
```

### Form JSX:

Wrap the name/description inputs with `<Form {...form}>`, `FormField`, `FormItem`, `FormLabel`, `FormControl`, `FormMessage`. Add `*` to the Name label.

Remove old `useState` for `name` and `description`.

---

## 2f — Retrofit AlertRuleDialog (lightweight)

**File**: `frontend/src/features/alerts/AlertRuleDialog.tsx`

This dialog is very complex (847 lines, 20+ state variables, 4 rule modes). A full react-hook-form conversion is out of scope here. Instead, make these targeted improvements:

1. Add a simple `nameError` state that shows when the name field is empty on submit.
2. Add `*` to required field labels: "Name", "Metric Name", "Threshold".

### Before (in handleSubmit, line 261):

```tsx
  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (ruleMode === "simple" && !metricName.trim()) return;
```

### After:

Add state:
```tsx
const [nameError, setNameError] = useState("");
```

Update handleSubmit:
```tsx
  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim()) {
      setNameError("Rule name is required");
      return;
    }
    setNameError("");
    if (ruleMode === "simple" && !metricName.trim()) return;
```

### Update the Name field label (line 448):

**Before:**
```tsx
            <Label htmlFor="rule-name">Name</Label>
```

**After:**
```tsx
            <Label htmlFor="rule-name">Name *</Label>
```

Add error message below the Input:
```tsx
            {nameError && <p className="text-sm text-destructive">{nameError}</p>}
```

### Update the Threshold label (line 606):

**Before:**
```tsx
                <Label htmlFor="threshold">Threshold</Label>
```

**After:**
```tsx
                <Label htmlFor="threshold">Threshold *</Label>
```

---

## Commit

```bash
git add frontend/package.json frontend/package-lock.json \
  frontend/src/components/ui/form.tsx \
  frontend/src/features/devices/AddDeviceModal.tsx \
  frontend/src/features/users/InviteUserDialog.tsx \
  frontend/src/features/roles/CreateRoleDialog.tsx \
  frontend/src/features/alerts/AlertRuleDialog.tsx

git commit -m "feat: add react-hook-form + zod validation to core form dialogs"
```

## Verification

```bash
cd frontend && npm run build
# Expected: builds clean

cd frontend && npx tsc --noEmit
# Expected: zero type errors

grep "react-hook-form" frontend/package.json
# Expected: in dependencies

grep "zod" frontend/package.json
# Expected: in dependencies

grep "FormMessage" frontend/src/features/devices/AddDeviceModal.tsx
# Expected: shows FormMessage usage

grep "FormMessage" frontend/src/features/users/InviteUserDialog.tsx
# Expected: shows FormMessage usage
```
