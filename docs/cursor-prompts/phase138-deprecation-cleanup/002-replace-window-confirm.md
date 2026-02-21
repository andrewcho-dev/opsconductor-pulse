# 138-002: Replace window.confirm() with AlertDialog

## Task
Replace all 3 `window.confirm()` calls with Shadcn AlertDialog components.

## Pattern: Reusable ConfirmDialog

First, check if a `ConfirmDialog` component already exists in `components/shared/` or `components/ui/`. If not, create one:

**File**: `frontend/src/components/shared/ConfirmDialog.tsx`

```typescript
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

interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmText?: string;
  cancelText?: string;
  variant?: "default" | "destructive";
  onConfirm: () => void;
  isPending?: boolean;
}

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmText = "Confirm",
  cancelText = "Cancel",
  variant = "default",
  onConfirm,
  isPending = false,
}: ConfirmDialogProps) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isPending}>{cancelText}</AlertDialogCancel>
          <AlertDialogAction
            onClick={onConfirm}
            disabled={isPending}
            className={variant === "destructive" ? "bg-destructive text-destructive-foreground hover:bg-destructive/90" : ""}
          >
            {isPending ? "Processing..." : confirmText}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
```

---

## Replacement 1: OtaCampaignsPage (line 138)

**File**: `frontend/src/features/ota/OtaCampaignsPage.tsx`

**Current**: `if (window.confirm(\`Abort campaign "${c.name}"?\`))`

**Replace with**:
```typescript
// Add state for confirm dialog
const [abortTarget, setAbortTarget] = useState<Campaign | null>(null);

// Replace the inline confirm with:
<Button variant="destructive" size="sm" onClick={() => setAbortTarget(c)}>
  Abort
</Button>

// Add ConfirmDialog at bottom of JSX:
<ConfirmDialog
  open={!!abortTarget}
  onOpenChange={(open) => { if (!open) setAbortTarget(null); }}
  title="Abort Campaign"
  description={`Are you sure you want to abort the campaign "${abortTarget?.name}"? This action cannot be undone. Devices that have already updated will not be rolled back.`}
  confirmText="Abort Campaign"
  variant="destructive"
  onConfirm={() => {
    if (abortTarget) {
      abortMutation.mutate(abortTarget.id);
      setAbortTarget(null);
    }
  }}
  isPending={abortMutation.isPending}
/>
```

Add import: `import { ConfirmDialog } from "@/components/shared/ConfirmDialog";`

---

## Replacement 2: OtaCampaignDetailPage (line 84)

**File**: `frontend/src/features/ota/OtaCampaignDetailPage.tsx`

**Current**: `if (window.confirm("Abort this campaign?"))`

**Replace with**:
```typescript
const [showAbortConfirm, setShowAbortConfirm] = useState(false);

// Replace the button onClick:
<Button variant="destructive" onClick={() => setShowAbortConfirm(true)}>
  Abort Campaign
</Button>

// Add ConfirmDialog:
<ConfirmDialog
  open={showAbortConfirm}
  onOpenChange={setShowAbortConfirm}
  title="Abort Campaign"
  description="Are you sure you want to abort this campaign? Devices that have already updated will not be rolled back."
  confirmText="Abort Campaign"
  variant="destructive"
  onConfirm={() => {
    abortMutation.mutate(campaign.id);
    setShowAbortConfirm(false);
  }}
  isPending={abortMutation.isPending}
/>
```

---

## Replacement 3: DeviceCertificatesTab (line 235)

**File**: `frontend/src/features/devices/DeviceCertificatesTab.tsx`

**Current**: `!window.confirm("Revoke this certificate? The device will no longer be able to authenticate with it.")`

**Replace with**:
```typescript
const [revokeTarget, setRevokeTarget] = useState<Certificate | null>(null);

// Replace the button onClick:
<Button variant="destructive" size="sm" onClick={() => setRevokeTarget(cert)}>
  Revoke
</Button>

// Add ConfirmDialog:
<ConfirmDialog
  open={!!revokeTarget}
  onOpenChange={(open) => { if (!open) setRevokeTarget(null); }}
  title="Revoke Certificate"
  description="Are you sure you want to revoke this certificate? The device will no longer be able to authenticate with it. This action cannot be undone."
  confirmText="Revoke Certificate"
  variant="destructive"
  onConfirm={() => {
    if (revokeTarget) {
      revokeMutation.mutate(revokeTarget.id);
      setRevokeTarget(null);
    }
  }}
  isPending={revokeMutation.isPending}
/>
```

---

## Verification
```bash
cd frontend && npm run build
npx tsc --noEmit
# Verify no window.confirm remains:
grep -r "window.confirm" frontend/src/
# Should return 0 results
```

Manual:
- OTA campaigns → click Abort → see AlertDialog → Cancel → nothing happens → Abort again → Confirm → campaign aborted
- OTA campaign detail → click Abort → see AlertDialog → works correctly
- Device certificates → click Revoke → see AlertDialog → Confirm → certificate revoked
