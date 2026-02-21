# Task 9: Update Documentation

## Context

Phase 146 established mutation feedback and error handling conventions. Document them so future development follows these rules.

## Files to Update

### 1. `docs/development/frontend.md`

Add a **"Mutation Feedback Conventions"** section after the UI Pattern Conventions section. Include:

#### Toast Feedback Rules
- Every `useMutation` MUST have both `onSuccess` and `onError` callbacks with toast feedback
- Import: `import { toast } from "sonner";`
- Success: `toast.success("Noun verbed")` — past tense, concise (e.g., "Tenant created", "Widget removed")
- Error: `toast.error(getErrorMessage(err) || "Failed to verb noun")` — show API detail with generic fallback
- Import error utility: `import { getErrorMessage } from "@/lib/errors";`
- Keep existing `onSuccess` logic (invalidateQueries, dialog close, state reset) — toast is in addition, not replacement
- No `console.error()` in feature files — always use `toast.error()` instead

#### Error Formatting
- One centralized function: `getErrorMessage()` in `@/lib/errors`
- Handles: `ApiError` (extracts `body.detail`), standard `Error`, plain objects, unknown
- Never duplicate error formatting logic in components

#### Modal State Naming
- Simple boolean: `const [open, setOpen] = useState(false)`
- Multiple dialogs: `const [createOpen, setCreateOpen] = useState(false)`
- Compound (edit item): `const [editing, setEditing] = useState<T | null>(null)`
- Never use: `show`, `isOpen`, `visible`, `showCreate`, `openCreate`

#### Prohibited Patterns
- Silent mutations (no toast on success or error)
- `console.error()` in feature/page components
- Duplicated `formatError()` functions — use `getErrorMessage` from `@/lib/errors`
- `window.confirm()` — use `<AlertDialog>` (established in Phase 145)
- Inconsistent modal state names (`show`, `isOpen`, `visible`)

Update YAML frontmatter:
- Set `last-verified` to today's date (2026-02-18)
- Add `146` to the `phases` array

### 2. `docs/index.md`

Update YAML frontmatter:
- Set `last-verified` to today's date (2026-02-18)
- Add `146` to the `phases` array

## Verify

```bash
grep "last-verified" docs/development/frontend.md
grep "146" docs/development/frontend.md
grep "146" docs/index.md
```
