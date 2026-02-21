# 001 — Toast Notification System

## Context

The frontend uses `window.alert()` (4 locations) and `window.confirm()` (10 locations) for user feedback. These block the main thread, look unprofessional, and cannot be styled. This step installs `sonner` for toast notifications and replaces all `window.alert()` calls with `toast()`. All `window.confirm()` calls are replaced with Shadcn `AlertDialog` confirmation patterns.

---

## 1a — Install sonner

```bash
cd frontend && npm install sonner
```

---

## 1b — Mount Toaster in AppShell

**File**: `frontend/src/components/layout/AppShell.tsx`

Add the import at the top:

```tsx
import { Toaster } from "sonner";
```

Add `<Toaster />` after the closing `</main>` tag, inside the flex column div:

### Before:

```tsx
          <main className="flex-1 p-6 overflow-auto">
            <Outlet />
          </main>
        </div>
```

### After:

```tsx
          <main className="flex-1 p-6 overflow-auto">
            <Outlet />
          </main>
          <Toaster richColors position="bottom-right" />
        </div>
```

---

## 1c — Replace all window.alert() with toast()

### Location 1: `frontend/src/features/alerts/AlertRulesPage.tsx` (line 72)

Add import at top:
```tsx
import { toast } from "sonner";
```

**Before:**
```tsx
      window.alert(`Created ${result.created.length} rules, skipped ${result.skipped.length} (already exist)`);
```

**After:**
```tsx
      toast.success(`Created ${result.created.length} rules, skipped ${result.skipped.length} (already exist)`);
```

### Location 2: `frontend/src/features/notifications/NotificationChannelsPage.tsx` (line 114)

Add import at top:
```tsx
import { toast } from "sonner";
```

**Before:**
```tsx
                        window.alert(result.ok ? "Test sent" : `Test failed: ${result.error ?? "Unknown error"}`);
```

**After:**
```tsx
                        if (result.ok) {
                          toast.success("Test sent successfully");
                        } else {
                          toast.error(`Test failed: ${result.error ?? "Unknown error"}`);
                        }
```

### Location 3: `frontend/src/features/users/UsersPage.tsx` (line 63)

Add import at top:
```tsx
import { toast } from "sonner";
```

**Before:**
```tsx
    window.alert("Password reset email sent");
```

**After:**
```tsx
    toast.success("Password reset email sent");
```

### Location 4: `frontend/src/features/operator/OperatorUsersPage.tsx` (line 88)

Add import at top:
```tsx
import { toast } from "sonner";
```

**Before:**
```tsx
    window.alert("Password reset email sent");
```

**After:**
```tsx
    toast.success("Password reset email sent");
```

---

## 1d — Replace all window.confirm() with AlertDialog pattern

For each `window.confirm()` call, replace it with a state-driven Shadcn `AlertDialog`. The pattern is:

1. Add state: `const [confirmState, setConfirmState] = useState<{ ... } | null>(null);`
2. Replace the `if (!window.confirm(...)) return;` with `setConfirmState({ ... }); return;`
3. Add an `AlertDialog` component at the bottom of the JSX that reads from state and calls the action on confirm.

Import the AlertDialog primitives from Shadcn:
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

**NOTE**: If `frontend/src/components/ui/alert-dialog.tsx` does not exist yet, generate it using the standard Shadcn pattern. Create the file with these exports: `AlertDialog`, `AlertDialogTrigger`, `AlertDialogContent`, `AlertDialogHeader`, `AlertDialogFooter`, `AlertDialogTitle`, `AlertDialogDescription`, `AlertDialogAction`, `AlertDialogCancel`. Use `@radix-ui/react-alert-dialog` (already available via the `radix-ui` package).

### Location 1: `frontend/src/features/jobs/JobsPage.tsx` (line 37)

**Before:**
```tsx
  const handleCancel = async (jobId: string) => {
    if (!window.confirm(`Cancel job ${jobId}?`)) return;
    await cancelJob(jobId);
    await load();
    if (selectedJob?.job_id === jobId) {
      setSelectedJob(await getJob(jobId));
    }
  };
```

**After:**

Add state:
```tsx
const [confirmCancel, setConfirmCancel] = useState<string | null>(null);
```

Replace handler:
```tsx
  const handleCancel = (jobId: string) => {
    setConfirmCancel(jobId);
  };

  const confirmCancelJob = async () => {
    if (!confirmCancel) return;
    await cancelJob(confirmCancel);
    await load();
    if (selectedJob?.job_id === confirmCancel) {
      setSelectedJob(await getJob(confirmCancel));
    }
    setConfirmCancel(null);
  };
```

Add AlertDialog JSX before the closing `</div>` of the component return:
```tsx
      <AlertDialog open={!!confirmCancel} onOpenChange={(open) => !open && setConfirmCancel(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Cancel Job</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to cancel job {confirmCancel?.slice(0, 8)}...?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>No, keep it</AlertDialogCancel>
            <AlertDialogAction onClick={() => void confirmCancelJob()}>
              Yes, cancel job
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
```

### Location 2: `frontend/src/features/users/UsersPage.tsx` (line 56)

**Before:**
```tsx
  const handleRemove = async (userId: string, username: string) => {
    if (window.confirm(`Remove ${username} from this tenant?`)) {
      await removeMutation.mutateAsync(userId);
    }
  };
```

**After:**

Add state:
```tsx
const [confirmRemove, setConfirmRemove] = useState<{ userId: string; username: string } | null>(null);
```

Replace handler:
```tsx
  const handleRemove = (userId: string, username: string) => {
    setConfirmRemove({ userId, username });
  };

  const confirmRemoveUser = async () => {
    if (!confirmRemove) return;
    await removeMutation.mutateAsync(confirmRemove.userId);
    setConfirmRemove(null);
  };
```

Add AlertDialog JSX at the bottom of the component return, before the final `</div>`:
```tsx
      <AlertDialog open={!!confirmRemove} onOpenChange={(open) => !open && setConfirmRemove(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove Team Member</AlertDialogTitle>
            <AlertDialogDescription>
              Remove {confirmRemove?.username} from this tenant? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={() => void confirmRemoveUser()}>
              Remove
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
```

### Location 3: `frontend/src/features/notifications/NotificationChannelsPage.tsx` (line 140)

**Before:**
```tsx
                        if (!window.confirm("Delete this channel?")) return;
                        await deleteMutation.mutateAsync(channel.channel_id);
```

**After:**

Add state:
```tsx
const [confirmDelete, setConfirmDelete] = useState<number | null>(null);
```

Replace inline onClick:
```tsx
                      onClick={() => setConfirmDelete(channel.channel_id)}
```

Add AlertDialog at the bottom of the component return:
```tsx
      <AlertDialog open={!!confirmDelete} onOpenChange={(open) => !open && setConfirmDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Channel</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this notification channel? This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={async () => {
              if (confirmDelete) await deleteMutation.mutateAsync(confirmDelete);
              setConfirmDelete(null);
            }}>
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
```

### Location 4: `frontend/src/features/oncall/OncallSchedulesPage.tsx` (line 107)

Apply same pattern: add state `confirmDeleteSchedule`, replace `window.confirm("Delete schedule?")`, add AlertDialog.

### Location 5: `frontend/src/features/devices/wizard/SetupWizard.tsx` (line 336)

Apply same pattern: add state `confirmAbandon`, replace `window.confirm("Abandon setup?...")`, add AlertDialog.

### Location 6: `frontend/src/features/devices/DeviceApiTokensPanel.tsx` (line 138)

Apply same pattern: add state `confirmRevokeToken`, replace `window.confirm("Revoke this token?")`, add AlertDialog.

### Location 7: `frontend/src/features/devices/DeviceDetailPane.tsx` (line 121)

Apply same pattern: add state `confirmDecommission`, replace `window.confirm(...)`, add AlertDialog.

### Location 8: `frontend/src/features/operator/OperatorUsersPage.tsx` (line 81)

Apply same pattern: add state `confirmDeleteUser`, replace `window.confirm("Are you sure you want to delete this user?")`, add AlertDialog.

### Location 9: `frontend/src/features/escalation/EscalationPoliciesPage.tsx` (line 131)

Apply same pattern: add state `confirmDeletePolicy`, replace `window.confirm("Delete this escalation policy?")`, add AlertDialog.

### Location 10: `frontend/src/features/roles/RolesPage.tsx` (line 80)

Apply same pattern: add state `confirmDeleteRole` (storing the role object), replace `window.confirm(...)`, add AlertDialog with `Delete role "${confirmDeleteRole?.name}"?` message.

---

## Commit

```bash
git add frontend/package.json frontend/package-lock.json \
  frontend/src/components/layout/AppShell.tsx \
  frontend/src/components/ui/alert-dialog.tsx \
  frontend/src/features/alerts/AlertRulesPage.tsx \
  frontend/src/features/notifications/NotificationChannelsPage.tsx \
  frontend/src/features/users/UsersPage.tsx \
  frontend/src/features/operator/OperatorUsersPage.tsx \
  frontend/src/features/jobs/JobsPage.tsx \
  frontend/src/features/oncall/OncallSchedulesPage.tsx \
  frontend/src/features/devices/wizard/SetupWizard.tsx \
  frontend/src/features/devices/DeviceApiTokensPanel.tsx \
  frontend/src/features/devices/DeviceDetailPane.tsx \
  frontend/src/features/escalation/EscalationPoliciesPage.tsx \
  frontend/src/features/roles/RolesPage.tsx

git commit -m "feat: replace window.alert/confirm with sonner toasts and Shadcn AlertDialog"
```

## Verification

```bash
cd frontend && npm run build
# Expected: builds clean

grep -r "window\.alert\(" frontend/src/
# Expected: no output

grep -r "window\.confirm\(" frontend/src/
# Expected: no output

grep "sonner" frontend/package.json
# Expected: shows sonner in dependencies

grep "Toaster" frontend/src/components/layout/AppShell.tsx
# Expected: shows Toaster import and component
```
