# Phase 146 — Mutation Feedback & Error Handling Standardization

## Problem

76 mutations across 27 files run silently — users get no confirmation when actions succeed or fail. Error formatting is duplicated. Modal state naming is inconsistent.

## Goals

1. Every mutation shows a toast on success and on error — no silent operations
2. One centralized `formatError()` function in `lib/errors.ts` — no duplication
3. Consistent modal state naming: `open`/`setOpen` for simple, `editing`/`setEditing` for compound
4. All `console.error()` in mutation handlers replaced with `toast.error()`

## Architecture

- **Toast library:** `sonner` (already installed, `<Toaster>` mounted in AppShell)
- **Import:** `import { toast } from "sonner";`
- **Error utility:** `@/lib/errors` — `getErrorMessage(error)` extracts user-facing message from ApiError, Error, or unknown
- **Success pattern:** `toast.success("Thing created")` — title only, no description (keep it concise)
- **Error pattern:** `toast.error(getErrorMessage(err) || "Failed to create thing")` — show API detail if available, fallback to generic

## Execution Order

| Task | File | Description |
|------|------|-------------|
| 001 | `lib/errors.ts` | Centralize formatError into getErrorMessage |
| 002 | Dashboard (6 files) | Add toast to 10 dashboard mutations |
| 003 | Devices (5 files) | Add toast to 12 device mutations |
| 004 | Operator (8 files) | Add toast to 19 operator mutations |
| 005 | Alerts/Escalation/Oncall (5 files) | Add toast to 12 alert mutations |
| 006 | Remaining (4 files) | Add toast to 8 remaining mutations |
| 007 | Modal state naming | Standardize open/setOpen across all dialogs |
| 008 | Verification | Type check + build + checklist |
| 009 | Documentation | Update frontend.md with feedback conventions |

## Rules

- Import `toast` from `"sonner"` (NOT from a custom wrapper)
- Import `getErrorMessage` from `"@/lib/errors"` for error formatting
- Success toast: `toast.success("Noun verbed")` — past tense, no description needed
- Error toast: `toast.error(getErrorMessage(err) || "Failed to verb noun")`
- Error callback type: `onError: (err: Error) =>` (not `any`)
- Keep existing `onSuccess` logic (invalidateQueries, close dialogs, etc.) — just ADD the toast call
- Do NOT create a wrapper hook — add toast directly in each mutation's callbacks
- Run `cd frontend && npx tsc --noEmit` after every task
