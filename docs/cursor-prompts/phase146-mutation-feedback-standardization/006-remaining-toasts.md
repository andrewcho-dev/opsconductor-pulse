# Task 6: Add Toast Feedback to Remaining Mutations

## Context

4 remaining files with 8 mutations that need toast feedback: dead letter queue, subscription renewal, and notification routing rules.

## Pattern

Same as previous tasks. Add `import { toast } from "sonner"` and `import { getErrorMessage } from "@/lib/errors"`.

## File 1: `frontend/src/features/messaging/DeadLetterPage.tsx`

Add imports: `toast` from `"sonner"`, `getErrorMessage` from `"@/lib/errors"`

| Mutation | Success toast | Error toast |
|----------|--------------|-------------|
| `replayMutation` (replayDeadLetter) | `"Message replayed"` | `"Failed to replay message"` |
| `batchReplayMutation` (replayDeadLetterBatch) | `"Messages replayed"` | `"Failed to replay messages"` |
| `discardMutation` (discardDeadLetter) | `"Message discarded"` | `"Failed to discard message"` |
| `purgeMutation` (purgeDeadLetter) | `"Old messages purged"` | `"Failed to purge messages"` |

## File 2: `frontend/src/features/subscription/RenewalPage.tsx`

Add imports: `toast` from `"sonner"`, `getErrorMessage` from `"@/lib/errors"`

| Mutation | Success toast | Error toast |
|----------|--------------|-------------|
| `renewMutation` (apiPost) | `"Subscription renewed"` | `"Failed to renew subscription"` |

## File 3: `frontend/src/features/notifications/RoutingRulesPanel.tsx`

Add imports: `toast` from `"sonner"`, `getErrorMessage` from `"@/lib/errors"`

| Mutation | Success toast | Error toast |
|----------|--------------|-------------|
| `createMutation` (createRoutingRule) | `"Routing rule created"` | `"Failed to create routing rule"` |
| `updateMutation` (updateRoutingRule) | `"Routing rule updated"` | `"Failed to update routing rule"` |
| `deleteMutation` (deleteRoutingRule) | `"Routing rule deleted"` | `"Failed to delete routing rule"` |

## File 4: Sweep for any remaining silent mutations

Run this grep to find any mutations still missing toast:

```bash
# Find all files with useMutation
grep -rn "useMutation" frontend/src/ --include="*.tsx" -l | sort

# For each file, check if it imports toast
for f in $(grep -rn "useMutation" frontend/src/ --include="*.tsx" -l); do
  if ! grep -q 'from "sonner"' "$f"; then
    echo "MISSING TOAST: $f"
  fi
done
```

If any files are found that have `useMutation` but no `toast` import, add toast feedback following the same pattern.

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
```
