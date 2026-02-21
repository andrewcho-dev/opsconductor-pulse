# Fix Code Quality Issues

Remove debug logging and fix unsafe type assertions.

## 1. Remove console.log

**File:** `frontend/src/features/devices/DeviceEditModal.tsx`

Remove line 96:
```typescript
// DELETE THIS LINE:
console.log("Geocode response:", result);
```

## 2. Fix `any` Types

**File:** `frontend/src/features/operator/CreateTenantDialog.tsx`

### Issue 1: Line 49 - Error type in onError callback

Change:
```typescript
onError: (error: any) => {
```

To:
```typescript
onError: (error: Error) => {
```

### Issue 2: Lines 125-126 - Error display

The current code:
```typescript
{(mutation.error as any)?.body?.detail ||
  (mutation.error as any)?.response?.data?.detail ||
  (mutation.error as Error).message}
```

Create a proper error extraction helper and use it:

```typescript
// Add this helper function at top of file or in a shared utils file:
function getErrorMessage(error: unknown): string {
  if (!error) return "Unknown error";

  // Handle ApiError with body
  if (typeof error === "object" && error !== null) {
    const e = error as Record<string, unknown>;

    // Check for body.detail (our ApiError format)
    if (e.body && typeof e.body === "object") {
      const body = e.body as Record<string, unknown>;
      if (typeof body.detail === "string") return body.detail;
    }

    // Check for response.data.detail (axios-style)
    if (e.response && typeof e.response === "object") {
      const res = e.response as Record<string, unknown>;
      if (res.data && typeof res.data === "object") {
        const data = res.data as Record<string, unknown>;
        if (typeof data.detail === "string") return data.detail;
      }
    }

    // Check for message property
    if (typeof e.message === "string") return e.message;
  }

  // Fallback
  if (error instanceof Error) return error.message;
  return String(error);
}
```

Then update the error display:
```typescript
{mutation.error && (
  <div className="text-sm text-destructive">
    {getErrorMessage(mutation.error)}
  </div>
)}
```

## Alternative: Create Shared Error Utility

If this pattern is used elsewhere, create `frontend/src/lib/errors.ts`:

```typescript
/**
 * Extract user-friendly error message from various error formats.
 */
export function getErrorMessage(error: unknown): string {
  if (!error) return "Unknown error";

  if (typeof error === "object" && error !== null) {
    const e = error as Record<string, unknown>;

    // ApiError format: { body: { detail: string } }
    if (e.body && typeof e.body === "object") {
      const body = e.body as Record<string, unknown>;
      if (typeof body.detail === "string") return body.detail;
    }

    // Axios format: { response: { data: { detail: string } } }
    if (e.response && typeof e.response === "object") {
      const res = e.response as Record<string, unknown>;
      if (res.data && typeof res.data === "object") {
        const data = res.data as Record<string, unknown>;
        if (typeof data.detail === "string") return data.detail;
      }
    }

    // Standard Error
    if (typeof e.message === "string") return e.message;
  }

  if (error instanceof Error) return error.message;
  return String(error);
}
```

Then import and use in CreateTenantDialog:
```typescript
import { getErrorMessage } from "@/lib/errors";

// In JSX:
{mutation.error && (
  <div className="text-sm text-destructive">
    {getErrorMessage(mutation.error)}
  </div>
)}
```

## Verification

1. Build passes: `npm run build`
2. No TypeScript errors
3. No `any` types in modified files
4. No `console.log` in production code
