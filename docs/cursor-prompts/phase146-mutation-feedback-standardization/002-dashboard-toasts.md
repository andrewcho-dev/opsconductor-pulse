# Task 2: Add Toast Feedback to Dashboard Mutations

## Context

6 dashboard files contain 10 mutations with zero user feedback. Add `toast.success()` on success and `toast.error()` on error to every mutation.

## Pattern

For each mutation, add `import { toast } from "sonner"` and `import { getErrorMessage } from "@/lib/errors"` at the top of the file, then add toast calls inside the existing `onSuccess` and a new `onError` callback:

```typescript
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: ["..."] }); // keep existing
  toast.success("Message here");
},
onError: (err: Error) => {
  toast.error(getErrorMessage(err) || "Failed to ...");
},
```

## File 1: `frontend/src/features/dashboard/DashboardBuilder.tsx`

Add imports: `toast` from `"sonner"`, `getErrorMessage` from `"@/lib/errors"`

| Mutation | Success toast | Error toast |
|----------|--------------|-------------|
| `layoutMutation` (batchUpdateLayout) | `"Layout saved"` | `"Failed to save layout"` |
| `removeMutation` (removeWidget) | `"Widget removed"` | `"Failed to remove widget"` |

## File 2: `frontend/src/features/dashboard/DashboardSettings.tsx`

Add imports: `toast` from `"sonner"`, `getErrorMessage` from `"@/lib/errors"`

| Mutation | Success toast | Error toast |
|----------|--------------|-------------|
| `renameMutation` (updateDashboard) | `"Dashboard renamed"` | `"Failed to rename dashboard"` |
| `shareMutation` (toggleDashboardShare) | `"Sharing updated"` | `"Failed to update sharing"` |
| `defaultMutation` (updateDashboard) | `"Default dashboard updated"` | `"Failed to set default"` |

## File 3: `frontend/src/features/dashboard/DashboardSelector.tsx`

Add imports: `toast` from `"sonner"`, `getErrorMessage` from `"@/lib/errors"`

| Mutation | Success toast | Error toast |
|----------|--------------|-------------|
| `createMutation` | `"Dashboard created"` | `"Failed to create dashboard"` |
| `deleteMutation` | `"Dashboard deleted"` | `"Failed to delete dashboard"` |
| `setDefaultMutation` | `"Default dashboard updated"` | `"Failed to set default"` |

## File 4: `frontend/src/features/dashboard/DashboardPage.tsx`

Add imports: `toast` from `"sonner"`, `getErrorMessage` from `"@/lib/errors"`

| Mutation | Success toast | Error toast |
|----------|--------------|-------------|
| `bootstrapMutation` | No success toast needed (bootstrapping is invisible to user) | `"Failed to initialize dashboard"` |

Note: bootstrapMutation is a behind-the-scenes first-time setup. Only add `onError` — no success toast.

## File 5: `frontend/src/features/dashboard/WidgetConfigDialog.tsx`

Add imports: `toast` from `"sonner"`, `getErrorMessage` from `"@/lib/errors"`

| Mutation | Success toast | Error toast |
|----------|--------------|-------------|
| `mutation` (updateWidget) | `"Widget updated"` | `"Failed to update widget"` |

## File 6: `frontend/src/features/dashboard/AddWidgetDrawer.tsx`

Add imports: `toast` from `"sonner"`, `getErrorMessage` from `"@/lib/errors"`

| Mutation | Success toast | Error toast |
|----------|--------------|-------------|
| `addMutation` (addWidget) | `"Widget added"` | `"Failed to add widget"` |

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
```
