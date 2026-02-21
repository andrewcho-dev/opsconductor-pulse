# Task 5: Add Toast Feedback to Alert/Escalation/Oncall Mutations

## Context

5 files covering alerts, escalation policies, and on-call schedules have 12 mutations with no user feedback.

## Pattern

Same as previous tasks. Add `import { toast } from "sonner"` and `import { getErrorMessage } from "@/lib/errors"`.

## File 1: `frontend/src/features/alerts/MaintenanceWindowsPage.tsx`

Add imports: `toast` from `"sonner"`, `getErrorMessage` from `"@/lib/errors"`

| Mutation | Success toast | Error toast |
|----------|--------------|-------------|
| `createMutation` (createMaintenanceWindow) | `"Maintenance window created"` | `"Failed to create maintenance window"` |
| `updateMutation` (updateMaintenanceWindow) | `"Maintenance window updated"` | `"Failed to update maintenance window"` |
| `deleteMutation` (deleteMaintenanceWindow) | `"Maintenance window deleted"` | `"Failed to delete maintenance window"` |

## File 2: `frontend/src/features/alerts/DeleteAlertRuleDialog.tsx`

This file already shows inline error via `formatError()` (now `getErrorMessage()` after Task 1). Add a success toast after the mutation completes:

Add import: `toast` from `"sonner"` (if not already present)

Find the mutation's `onSuccess` or the `mutateAsync` call and add:
```typescript
toast.success("Alert rule deleted");
```

If there's no `onSuccess` handler (it uses `mutateAsync` in a handler), add the toast after the `await`:
```typescript
await deleteMutation.mutateAsync(String(rule.rule_id));
toast.success("Alert rule deleted");
onClose();
```

## File 3: `frontend/src/features/alerts/AlertRulesPage.tsx`

This file already has `toast.success()` for the default rules template feature. Check if the individual rule create/update/delete mutations also have toast feedback. If any mutations lack it, add:

| Mutation (if present) | Success toast | Error toast |
|----------|--------------|-------------|
| Any create/update/delete rule mutations | Follow same pattern | Follow same pattern |

Note: Most CRUD for alert rules goes through AlertRuleDialog, not this page directly. Just verify — if no additional mutations exist here beyond the template one, skip.

## File 4: `frontend/src/features/escalation/EscalationPoliciesPage.tsx`

Add imports: `toast` from `"sonner"`, `getErrorMessage` from `"@/lib/errors"`

| Mutation | Success toast | Error toast |
|----------|--------------|-------------|
| `createMutation` (createEscalationPolicy) | `"Escalation policy created"` | `"Failed to create escalation policy"` |
| `updateMutation` (updateEscalationPolicy) | `"Escalation policy updated"` | `"Failed to update escalation policy"` |
| `deleteMutation` (deleteEscalationPolicy) | `"Escalation policy deleted"` | `"Failed to delete escalation policy"` |

## File 5: `frontend/src/features/oncall/OncallSchedulesPage.tsx`

Add imports: `toast` from `"sonner"`, `getErrorMessage` from `"@/lib/errors"`

| Mutation | Success toast | Error toast |
|----------|--------------|-------------|
| `createMutation` (createSchedule) | `"On-call schedule created"` | `"Failed to create schedule"` |
| `updateMutation` (updateSchedule) | `"On-call schedule updated"` | `"Failed to update schedule"` |
| `deleteMutation` (deleteSchedule) | `"On-call schedule deleted"` | `"Failed to delete schedule"` |

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
```
