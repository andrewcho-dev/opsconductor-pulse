# Task 1: Centralize Error Formatting

## Context

`formatError()` is duplicated identically in `AlertRuleDialog.tsx` (line 83) and `DeleteAlertRuleDialog.tsx` (line 21). Meanwhile `lib/errors.ts` already has `getErrorMessage()` which does similar work but doesn't handle `ApiError.body.detail` extraction as well.

## Step 1: Update `lib/errors.ts`

**File:** `frontend/src/lib/errors.ts`

Replace the entire file with a merged version that handles all cases:

```typescript
import { ApiError } from "@/services/api/client";

/**
 * Extract a user-facing error message from common API error shapes.
 */
export function getErrorMessage(error: unknown): string {
  if (!error) return "Unknown error";

  // Handle our custom ApiError (has status + body from backend)
  if (error instanceof ApiError) {
    if (typeof error.body === "string") return error.body;
    if (error.body && typeof error.body === "object") {
      const body = error.body as Record<string, unknown>;
      if (typeof body.detail === "string") return body.detail;
    }
    return error.message;
  }

  // Handle standard Error objects
  if (error instanceof Error) return error.message;

  // Handle plain objects with common error shapes
  if (typeof error === "object" && error !== null) {
    const err = error as Record<string, unknown>;

    if (err.body && typeof err.body === "object") {
      const body = err.body as Record<string, unknown>;
      if (typeof body.detail === "string") return body.detail;
    }

    if (err.response && typeof err.response === "object") {
      const response = err.response as Record<string, unknown>;
      if (response.data && typeof response.data === "object") {
        const data = response.data as Record<string, unknown>;
        if (typeof data.detail === "string") return data.detail;
      }
    }

    if (typeof err.message === "string") return err.message;
  }

  return String(error);
}
```

## Step 2: Update AlertRuleDialog.tsx

**File:** `frontend/src/features/alerts/AlertRuleDialog.tsx`

1. Remove the local `formatError()` function definition (lines ~83-95)
2. Add import: `import { getErrorMessage } from "@/lib/errors";`
3. Find all uses of `formatError(` and replace with `getErrorMessage(`

## Step 3: Update DeleteAlertRuleDialog.tsx

**File:** `frontend/src/features/alerts/DeleteAlertRuleDialog.tsx`

1. Remove the local `formatError()` function definition (lines ~21-33)
2. Remove the `import { ApiError }` line (no longer needed locally)
3. Add import: `import { getErrorMessage } from "@/lib/errors";`
4. Find all uses of `formatError(` and replace with `getErrorMessage(`

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
```
