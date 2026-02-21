# Task 8: Replace confirm() with AlertDialog

## Context

Some places use `window.confirm()` for destructive actions. The rule: always use `<AlertDialog>`.

## Step 1: Find all confirm() usage

```bash
grep -rn "confirm(" frontend/src/ --include="*.tsx" | grep -v node_modules | grep -v "confirmDiscard\|confirmDelete\|showConfirm\|setConfirm"
```

## Step 2: Fix DashboardBuilder.tsx

**File:** `frontend/src/features/dashboard/DashboardBuilder.tsx`

Line 106:
```tsx
// BEFORE:
if (confirm("Remove this widget from the dashboard?")) {
  removeMutation.mutate(widgetId);
}
```

Replace with AlertDialog:

Add state:
```tsx
const [removeTargetId, setRemoveTargetId] = useState<number | null>(null);
```

Change the handler:
```tsx
const handleRemoveWidget = useCallback((widgetId: number) => {
  setRemoveTargetId(widgetId);
}, []);

const confirmRemoveWidget = useCallback(() => {
  if (removeTargetId !== null) {
    removeMutation.mutate(removeTargetId);
    setRemoveTargetId(null);
  }
}, [removeTargetId, removeMutation]);
```

Add the AlertDialog at the end of the component return:
```tsx
<AlertDialog open={removeTargetId !== null} onOpenChange={(open) => { if (!open) setRemoveTargetId(null); }}>
  <AlertDialogContent>
    <AlertDialogHeader>
      <AlertDialogTitle>Remove Widget</AlertDialogTitle>
      <AlertDialogDescription>
        Remove this widget from the dashboard? This action cannot be undone.
      </AlertDialogDescription>
    </AlertDialogHeader>
    <AlertDialogFooter>
      <AlertDialogCancel>Cancel</AlertDialogCancel>
      <AlertDialogAction onClick={confirmRemoveWidget}>Remove</AlertDialogAction>
    </AlertDialogFooter>
  </AlertDialogContent>
</AlertDialog>
```

Import AlertDialog components:
```tsx
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
```

## Step 3: Fix any other confirm() usage

Check the grep results from Step 1 and apply the same pattern to each:
1. Replace `confirm()` call with a state setter
2. Add `AlertDialog` with confirm/cancel actions
3. Move the mutation call to the confirm handler

## Step 4: Verify zero confirm() remaining

```bash
# Should return 0 results (excluding variable names like confirmDelete)
grep -rn "window\.confirm\|[^a-zA-Z]confirm(" frontend/src/ --include="*.tsx" | grep -v "confirmDiscard\|confirmDelete\|showConfirm\|setConfirm\|confirmRemove\|ConfirmDialog\|onConfirm"
```

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
```
