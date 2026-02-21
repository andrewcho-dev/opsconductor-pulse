# Task 004 — Carrier Remote Action Buttons

## File

Modify `frontend/src/features/devices/DeviceCarrierPanel.tsx` (created in Task 003)

## Purpose

Add remote SIM/device action buttons to the carrier panel: Activate, Suspend, Deactivate, and Reboot. Each action gets a confirmation dialog — `deactivate` gets a destructive-styled `AlertDialog` since it permanently kills the SIM.

## Layout

At the bottom of the carrier panel (only when device is linked):

```
┌──────────────────────────────────────────────────────────────────┐
│  Remote Actions                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐ ┌──────────┐       │
│  │▶ Activate │ │⏸ Suspend │ │⛔ Deactivate │ │↻ Reboot  │       │
│  └──────────┘ └──────────┘ └──────────────┘ └──────────┘       │
└──────────────────────────────────────────────────────────────────┘
```

## Implementation

### Action Definitions

```tsx
const CARRIER_ACTIONS = [
  {
    action: "activate" as const,
    label: "Activate",
    icon: Play,
    description: "Activate the SIM card on this device. This will enable cellular connectivity.",
    variant: "default" as const,
    destructive: false,
  },
  {
    action: "suspend" as const,
    label: "Suspend",
    icon: Pause,
    description: "Temporarily suspend the SIM card. The device will lose connectivity but can be reactivated later.",
    variant: "secondary" as const,
    destructive: false,
  },
  {
    action: "deactivate" as const,
    label: "Deactivate",
    icon: XCircle,
    description: "Permanently deactivate the SIM card. This action cannot be reversed — a new SIM will be required.",
    variant: "destructive" as const,
    destructive: true,
  },
  {
    action: "reboot" as const,
    label: "Reboot",
    icon: RotateCcw,
    description: "Send a remote reboot command to the device via the carrier network.",
    variant: "outline" as const,
    destructive: false,
  },
] as const;
```

Icons from `lucide-react`: `Play`, `Pause`, `XCircle`, `RotateCcw`.

### Mutation

```tsx
const actionMutation = useMutation({
  mutationFn: ({ action }: { action: "activate" | "suspend" | "deactivate" | "reboot" }) =>
    executeCarrierAction(deviceId, action),
  onSuccess: (data) => {
    toast.success(`${data.action} completed successfully`);
    // Refresh carrier status after action
    queryClient.invalidateQueries({ queryKey: ["carrier-status", deviceId] });
  },
  onError: (err: Error) => {
    toast.error(`Action failed: ${err.message}`);
  },
});
```

Import `executeCarrierAction` from `@/services/api/carrier`.

### Confirmation Dialog

Use a single `AlertDialog` controlled by state:

```tsx
const [confirmAction, setConfirmAction] = useState<typeof CARRIER_ACTIONS[number] | null>(null);
```

When a button is clicked, set `confirmAction` to that action definition. The dialog renders based on `confirmAction`:

```tsx
<AlertDialog open={!!confirmAction} onOpenChange={(open) => !open && setConfirmAction(null)}>
  <AlertDialogContent>
    <AlertDialogHeader>
      <AlertDialogTitle>
        {confirmAction?.destructive ? "⚠️ " : ""}
        {confirmAction?.label} Device?
      </AlertDialogTitle>
      <AlertDialogDescription>
        {confirmAction?.description}
        {confirmAction?.destructive && (
          <span className="block mt-2 font-medium text-destructive">
            This action is irreversible.
          </span>
        )}
      </AlertDialogDescription>
    </AlertDialogHeader>
    <AlertDialogFooter>
      <AlertDialogCancel disabled={actionMutation.isPending}>Cancel</AlertDialogCancel>
      <AlertDialogAction
        onClick={() => {
          if (confirmAction) {
            actionMutation.mutate({ action: confirmAction.action });
            setConfirmAction(null);
          }
        }}
        disabled={actionMutation.isPending}
        className={confirmAction?.destructive ? "bg-destructive text-destructive-foreground hover:bg-destructive/90" : ""}
      >
        {actionMutation.isPending ? "Processing..." : `Yes, ${confirmAction?.label}`}
      </AlertDialogAction>
    </AlertDialogFooter>
  </AlertDialogContent>
</AlertDialog>
```

### Action Buttons Row

Inside the carrier panel (at the bottom, only when linked):

```tsx
{statusQuery.data?.linked && (
  <div className="space-y-1.5">
    <h4 className="text-xs font-medium text-muted-foreground">Remote Actions</h4>
    <div className="flex flex-wrap gap-2">
      {CARRIER_ACTIONS.map((def) => {
        const Icon = def.icon;
        return (
          <Button
            key={def.action}
            variant={def.variant}
            size="sm"
            onClick={() => setConfirmAction(def)}
            disabled={actionMutation.isPending}
          >
            <Icon className="h-3.5 w-3.5 mr-1.5" />
            {def.label}
          </Button>
        );
      })}
    </div>
  </div>
)}
```

### Smart Button States

Optionally disable buttons based on current SIM status (from `statusQuery.data.device_info.sim_status`):

- If `sim_status === "active"` → disable "Activate" (already active)
- If `sim_status === "suspended"` → disable "Suspend" (already suspended)
- If `sim_status === "deactivated"` or `"inactive"` → disable "Suspend" and "Deactivate" (already off)

```tsx
const simStatus = statusQuery.data?.device_info?.sim_status;
const isDisabled = (action: string) => {
  if (actionMutation.isPending) return true;
  if (simStatus === "active" && action === "activate") return true;
  if (simStatus === "suspended" && action === "suspend") return true;
  if ((simStatus === "deactivated" || simStatus === "inactive") && (action === "suspend" || action === "deactivate")) return true;
  return false;
};
```

Use `isDisabled(def.action)` on each button's `disabled` prop.

### Imports Summary

Add these to the existing `DeviceCarrierPanel.tsx`:

```tsx
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Play, Pause, XCircle, RotateCcw } from "lucide-react";
import { executeCarrierAction } from "@/services/api/carrier";
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
import { toast } from "sonner";
```

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```
