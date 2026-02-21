# Task 7: Migrate CreateCampaignDialog to Shadcn Dialog

## Context

`CreateCampaignDialog.tsx` uses a custom `<div className="fixed inset-0 z-50">` overlay instead of the Shadcn `<Dialog>` component. This is the ONLY modal in the app that doesn't use the standard component.

## Step 1: Replace the custom overlay

**File:** `frontend/src/features/ota/CreateCampaignDialog.tsx`

Current structure (line 67-68):
```tsx
<div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
  <div className="w-full max-w-lg rounded-lg border border-border bg-background p-6 shadow-lg space-y-4">
```

Replace with Shadcn Dialog:
```tsx
<Dialog open={true} onOpenChange={(open) => { if (!open) onClose(); }}>
  <DialogContent className="sm:max-w-lg">
    <DialogHeader>
      <DialogTitle>Create OTA Campaign</DialogTitle>
    </DialogHeader>

    {/* Step indicator */}
    <div className="flex gap-2">
      {[1, 2, 3, 4].map((s) => (
        <div
          key={s}
          className={`flex-1 h-1 rounded-full ${s <= step ? "bg-primary" : "bg-muted"}`}
        />
      ))}
    </div>
    <div className="text-sm text-muted-foreground">
      Step {step} of 4: {stepLabel}
    </div>

    {/* Step content — keep existing step rendering logic */}
    <div className="space-y-3">
      {/* ... existing step content ... */}
    </div>

    <DialogFooter>
      {step > 1 && (
        <Button variant="outline" onClick={() => setStep(step - 1)}>
          Back
        </Button>
      )}
      {step < 4 ? (
        <Button onClick={() => setStep(step + 1)} disabled={!canProceed}>
          Next
        </Button>
      ) : (
        <Button onClick={handleCreate} disabled={creating}>
          {creating ? "Creating..." : "Create Campaign"}
        </Button>
      )}
    </DialogFooter>
  </DialogContent>
</Dialog>
```

Remove the custom "X" close button (line 71-73) — DialogContent already has a built-in close button.

## Step 2: Update props interface

Change the component to accept `open` + `onOpenChange` props instead of just `onClose`:
```tsx
interface CreateCampaignDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: () => void;
}
```

## Step 3: Update the parent (OtaCampaignsPage.tsx)

Change how the dialog is rendered:
```tsx
// BEFORE:
{showCreate && (
  <CreateCampaignDialog
    onClose={() => setShowCreate(false)}
    onCreated={() => { setShowCreate(false); /* refetch */ }}
  />
)}

// AFTER:
<CreateCampaignDialog
  open={showCreate}
  onOpenChange={setShowCreate}
  onCreated={() => { setShowCreate(false); /* refetch */ }}
/>
```

## Step 4: Add imports

```tsx
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
```

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
```
