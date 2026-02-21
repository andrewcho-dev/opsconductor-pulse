# Task 3: Remove `as any` Casts from AlertRuleDialog

## Context

`frontend/src/features/alerts/AlertRuleDialog.tsx` has multiple `as any` casts:
- Line ~387: `resolver: zodResolver(alertRuleSchema) as any`
- Lines ~448-450: `(form.formState.errors as any)?.conditions?.message` (and similar)

These casts bypass TypeScript's type checker and can mask runtime errors when the schema changes.

## Actions

1. Read `frontend/src/features/alerts/AlertRuleDialog.tsx` in full.

2. Read the `alertRuleSchema` Zod definition in the same file or wherever it is defined.

3. **Fix the resolver cast** (line ~387):
   The `resolver: zodResolver(schema) as any` pattern is usually needed when the schema's inferred type doesn't match `useForm`'s generic parameter. Fix by providing the schema type explicitly to `useForm`:
   ```typescript
   type AlertRuleFormValues = z.infer<typeof alertRuleSchema>;

   const form = useForm<AlertRuleFormValues>({
     resolver: zodResolver(alertRuleSchema),
     // No `as any` needed when the generic matches the schema
   });
   ```
   If the schema uses a discriminated union (different fields for different rule types), ensure the `useForm` generic is the union type.

4. **Fix the error object casts** (lines ~448-450):
   The `form.formState.errors` type is `DeepMap<AlertRuleFormValues, FieldError>`. Create a typed accessor instead of casting:
   ```typescript
   // Add near the top of the component (or in a separate file):
   function getConditionError(
     errors: typeof form.formState.errors,
     index?: number
   ): string | undefined {
     const condErrors = errors.conditions;
     if (!condErrors) return undefined;
     if (typeof condErrors.message === "string") return condErrors.message;
     if (index !== undefined && condErrors[index]?.message) {
       return condErrors[index].message as string;
     }
     return undefined;
   }
   ```
   Replace every `(form.formState.errors as any).conditions...` usage with calls to `getConditionError(form.formState.errors, index)`.

5. If there are other `as any` casts in the file, apply the same principle: find the correct type and use it, or create a typed helper.

6. Do not change any form logic or UI.

## Verification

```bash
grep -n 'as any' frontend/src/features/alerts/AlertRuleDialog.tsx
# Must return zero results
```
