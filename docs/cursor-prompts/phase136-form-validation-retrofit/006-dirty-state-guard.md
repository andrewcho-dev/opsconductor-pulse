# 136-006: Dirty-State Warning on All Dialogs

## Task
Create a reusable `useFormDirtyGuard` hook and apply it to all dialog-based forms (both newly converted and the 3 existing react-hook-form forms).

---

## 1. Create the Hook
**File**: `frontend/src/hooks/use-form-dirty-guard.ts`

```typescript
import { useState, useCallback } from "react";
import type { UseFormReturn } from "react-hook-form";

interface UseFormDirtyGuardOptions {
  form: UseFormReturn<any>;
  onClose: () => void;
}

interface UseFormDirtyGuardResult {
  /** Call this instead of directly calling onClose */
  handleClose: () => void;
  /** Whether the confirmation dialog is open */
  showConfirm: boolean;
  /** Confirm discard — closes the dialog */
  confirmDiscard: () => void;
  /** Cancel discard — keeps the dialog open */
  cancelDiscard: () => void;
}

export function useFormDirtyGuard({ form, onClose }: UseFormDirtyGuardOptions): UseFormDirtyGuardResult {
  const [showConfirm, setShowConfirm] = useState(false);

  const handleClose = useCallback(() => {
    if (form.formState.isDirty) {
      setShowConfirm(true);
    } else {
      onClose();
    }
  }, [form.formState.isDirty, onClose]);

  const confirmDiscard = useCallback(() => {
    setShowConfirm(false);
    form.reset();
    onClose();
  }, [form, onClose]);

  const cancelDiscard = useCallback(() => {
    setShowConfirm(false);
  }, []);

  return { handleClose, showConfirm, confirmDiscard, cancelDiscard };
}
```

---

## 2. Apply to Each Dialog

For each dialog component that uses react-hook-form, add the guard:

```typescript
import { useFormDirtyGuard } from "@/hooks/use-form-dirty-guard";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

// Inside the component:
const { handleClose, showConfirm, confirmDiscard, cancelDiscard } = useFormDirtyGuard({
  form,
  onClose: () => onOpenChange(false),
});

// Replace the dialog's onOpenChange to use the guard:
<Dialog open={open} onOpenChange={(isOpen) => {
  if (!isOpen) handleClose();
  else onOpenChange(true);
}}>

// Add the confirmation AlertDialog at the end of the component JSX:
<AlertDialog open={showConfirm} onOpenChange={cancelDiscard}>
  <AlertDialogContent>
    <AlertDialogHeader>
      <AlertDialogTitle>Discard changes?</AlertDialogTitle>
      <AlertDialogDescription>
        You have unsaved changes. Are you sure you want to close without saving?
      </AlertDialogDescription>
    </AlertDialogHeader>
    <AlertDialogFooter>
      <AlertDialogCancel onClick={cancelDiscard}>Keep Editing</AlertDialogCancel>
      <AlertDialogAction onClick={confirmDiscard} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
        Discard
      </AlertDialogAction>
    </AlertDialogFooter>
  </AlertDialogContent>
</AlertDialog>
```

Also update the Cancel button inside each dialog to use `handleClose` instead of directly calling `onOpenChange(false)`:
```typescript
<Button type="button" variant="outline" onClick={handleClose}>Cancel</Button>
```

---

## 3. Dialogs to Update

### Newly converted (from phases 136-001 through 136-005):
1. `features/alerts/AlertRuleDialog.tsx`
2. `features/devices/DeviceEditModal.tsx`
3. `features/devices/EditDeviceModal.tsx` (if not consolidated)
4. `features/operator/CreateUserDialog.tsx`
5. `features/operator/EditUserDialog.tsx`
6. `features/operator/CreateTenantDialog.tsx`
7. `features/operator/EditTenantDialog.tsx`
8. `features/operator/AssignRoleDialog.tsx`
9. `features/operator/AssignTenantDialog.tsx`
10. `features/users/ChangeRoleDialog.tsx`
11. `features/users/EditTenantUserDialog.tsx`

### Existing react-hook-form dialogs:
12. `features/devices/AddDeviceModal.tsx`
13. `features/roles/CreateRoleDialog.tsx`
14. `features/users/InviteUserDialog.tsx`

---

## 4. SettingsPage Exception
`features/operator/SettingsPage.tsx` is NOT a dialog — it's an inline page form. The dirty guard doesn't apply (no close action). Instead, the `isDirty` state should control the Save button's disabled state (already covered in 136-005).

---

## Verification
```bash
cd frontend && npm run build
npx tsc --noEmit
```
For each dialog:
1. Open dialog
2. Change a field value
3. Click Cancel or the X button → see "Discard changes?" confirmation
4. Click "Keep Editing" → stay in dialog, changes preserved
5. Click "Discard" → dialog closes, changes discarded
6. Open same dialog again → form is clean/reset
7. Open dialog, don't change anything, click Cancel → closes immediately (no confirmation)
