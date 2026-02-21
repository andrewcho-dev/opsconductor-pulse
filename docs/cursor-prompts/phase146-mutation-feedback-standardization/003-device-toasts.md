# Task 3: Add Toast Feedback to Device Mutations

## Context

5 device files contain 12 mutations with zero user feedback. These include security-sensitive operations (certificate revocation, token rotation) where confirmation is critical.

## Pattern

Same as Task 2 — add `import { toast } from "sonner"` and `import { getErrorMessage } from "@/lib/errors"` then add `toast.success()` in `onSuccess` and `toast.error()` in new `onError` callback.

## File 1: `frontend/src/features/devices/DeviceGroupsPage.tsx`

Add imports: `toast` from `"sonner"`, `getErrorMessage` from `"@/lib/errors"`

| Mutation | Success toast | Error toast |
|----------|--------------|-------------|
| `createMutation` (createDeviceGroup) | `"Device group created"` | `"Failed to create device group"` |
| `createDynamicMutation` (createDynamicGroup) | `"Dynamic group created"` | `"Failed to create dynamic group"` |
| `updateMutation` | `"Device group updated"` | `"Failed to update device group"` |
| `deleteMutation` | `"Device group deleted"` | `"Failed to delete device group"` |
| `addMemberMutation` (addGroupMember) | `"Device added to group"` | `"Failed to add device to group"` |
| `removeMemberMutation` (removeGroupMember) | `"Device removed from group"` | `"Failed to remove device from group"` |

## File 2: `frontend/src/features/devices/DeviceCertificatesTab.tsx`

Add imports: `toast` from `"sonner"`, `getErrorMessage` from `"@/lib/errors"`

| Mutation | Success toast | Error toast |
|----------|--------------|-------------|
| `generateMutation` | `"Certificate generated"` | `"Failed to generate certificate"` |
| `rotateMutation` | `"Certificate rotated"` | `"Failed to rotate certificate"` |
| `revokeMutation` | `"Certificate revoked"` | `"Failed to revoke certificate"` |

## File 3: `frontend/src/features/devices/DeviceApiTokensPanel.tsx`

Add imports: `toast` from `"sonner"`, `getErrorMessage` from `"@/lib/errors"`

| Mutation | Success toast | Error toast |
|----------|--------------|-------------|
| `revokeMutation` | `"API token revoked"` | `"Failed to revoke token"` |
| `rotateMutation` | `"API token rotated"` | `"Failed to rotate token"` |

## File 4: `frontend/src/features/devices/DeviceCommandPanel.tsx`

Add imports: `toast` from `"sonner"`, `getErrorMessage` from `"@/lib/errors"`

| Mutation | Success toast | Error toast |
|----------|--------------|-------------|
| `sendMutation` (sendCommand) | `"Command sent"` | `"Failed to send command"` |

Note: This file already sets `lastResult` state on success. Keep that — just add the toast alongside it.

## File 5: `frontend/src/features/devices/wizard/Step3Provision.tsx`

This file uses `async/await` directly, not `useMutation`. Find the try/catch block and add toast:

```typescript
try {
  // ... existing provision logic
  toast.success("Device provisioned");
} catch (err) {
  toast.error(getErrorMessage(err) || "Failed to provision device");
  // keep existing setError() call
}
```

Add imports: `toast` from `"sonner"`, `getErrorMessage` from `"@/lib/errors"`

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
```
