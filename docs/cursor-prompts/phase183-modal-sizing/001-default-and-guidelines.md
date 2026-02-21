# Task 1: Bump Default Dialog Width + Explicit Sizes for Simple Dialogs

## Objective

Change the default `DialogContent` width from `sm:max-w-lg` (512px) to `sm:max-w-xl` (640px). Then add explicit `sm:max-w-md` to simple dialogs that should stay compact at the old smaller size.

---

## Part 1: Update Default in `dialog.tsx`

**Modify:** `frontend/src/components/ui/dialog.tsx`

In the `DialogContent` function, change the default class:

```tsx
// OLD:
"... sm:max-w-lg",

// NEW:
"... sm:max-w-xl",
```

This is a single string replacement in the `cn()` call on the DialogPrimitive.Content className. Change `sm:max-w-lg` to `sm:max-w-xl`.

---

## Part 2: Pin Simple Dialogs to `sm:max-w-md`

These dialogs are simple enough that 640px would look wastefully wide. Add explicit `sm:max-w-md` to their `DialogContent` (or keep it if already present):

### 1. `frontend/src/features/alerts/DeleteAlertRuleDialog.tsx`

Read the file. Find the `<DialogContent` tag. If it has no explicit width class, add `className="sm:max-w-md"`. If it uses `AlertDialogContent`, check if AlertDialog has its own default sizing — if so, no change needed.

### 2. Verify these already have `sm:max-w-md` (no change expected):

- `frontend/src/features/operator/AssignTenantDialog.tsx` — already `sm:max-w-md`
- `frontend/src/features/operator/AssignRoleDialog.tsx` — already `sm:max-w-md`
- `frontend/src/features/operator/EditUserDialog.tsx` — already `sm:max-w-md`
- `frontend/src/features/users/EditTenantUserDialog.tsx` — already `sm:max-w-md`
- `frontend/src/features/users/ChangeRoleDialog.tsx` — already `sm:max-w-md`
- `frontend/src/features/users/InviteUserDialog.tsx` — already `sm:max-w-md`

Just verify these are pinned. If any are missing the class, add it.

### 3. Dialogs that benefit from the new default (no change needed):

These currently have no explicit width and will auto-upgrade from 512→640px:

- `frontend/src/features/metrics/MapMetricDialog.tsx` — medium form, 640px is good
- `frontend/src/features/operator/StatusChangeDialog.tsx` — status select + warning, 640px is fine
- `frontend/src/features/operator/CreateTenantDialog.tsx` — 3-field form, 640px is fine

### 4. Dialogs with explicit `sm:max-w-lg` that should upgrade to new default:

If any dialogs have `className="sm:max-w-lg"` explicitly, **remove** that class so they pick up the new `sm:max-w-xl` default. Check:

- `frontend/src/features/operator/CreateSubscriptionDialog.tsx` — has `max-w-lg`, change to remove or leave (it's fine at either size)
- `frontend/src/features/operator/EditSubscriptionDialog.tsx` — same

---

## Verification

```bash
cd frontend && npx tsc --noEmit
```

- `dialog.tsx` default is now `sm:max-w-xl`
- Simple confirmation/assign dialogs are pinned at `sm:max-w-md` (448px)
- Medium forms auto-upgraded to 640px
- No TypeScript errors
