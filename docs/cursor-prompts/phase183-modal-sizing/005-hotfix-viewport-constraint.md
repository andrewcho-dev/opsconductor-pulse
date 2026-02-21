# Task 5: Hotfix — Restore Viewport Constraint to All Dialogs

## Problem

Tasks 2 and 3 removed `max-h-[85vh] overflow-y-auto` from AlertRuleDialog and EditTenantDialog on the assumption that wider dialogs + 2-column layouts would eliminate the need for scrolling. They don't — the forms are still taller than the viewport and now extend past the top and bottom of the screen with no scroll mechanism.

## Fix

Add `max-h-[85vh] overflow-y-auto` to the **default** `DialogContent` className in `dialog.tsx`. This gives every dialog a viewport safety net automatically. The wider widths and 2-column layouts still reduce how much scrolling is needed, but the constraint must always be present.

---

## File to Modify

`frontend/src/components/ui/dialog.tsx`

### Change

In the `DialogContent` function, add `max-h-[85vh] overflow-y-auto` to the `cn()` call on line 64:

```tsx
// OLD (line 64):
"bg-background data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 fixed top-[50%] left-[50%] z-50 grid w-full max-w-[calc(100%-2rem)] translate-x-[-50%] translate-y-[-50%] gap-4 rounded-lg border p-6 shadow-lg duration-200 outline-none sm:max-w-xl",

// NEW:
"bg-background data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 fixed top-[50%] left-[50%] z-50 grid w-full max-w-[calc(100%-2rem)] translate-x-[-50%] translate-y-[-50%] gap-4 rounded-lg border p-6 shadow-lg duration-200 outline-none sm:max-w-xl max-h-[85vh] overflow-y-auto",
```

That's it. Two classes added to one line.

---

## Why This Is Safe

- Small confirmation dialogs: content is short, never hits 85vh, no visible change.
- Medium forms: content is moderate, rarely hits 85vh, no visible change.
- AlertRuleDialog / EditTenantDialog: content is tall, gets a scrollbar when needed — exactly the behavior we need.
- Any dialog that previously had its own `max-h-[85vh] overflow-y-auto` in className: the duplicate is harmless (Tailwind dedupes).

## Verification

```bash
cd frontend && npx tsc --noEmit
```

- Open AlertRuleDialog — it should be contained within the viewport with a scrollbar if content is tall
- Open EditTenantDialog — same
- Open a small dialog (e.g., DeleteAlertRuleDialog) — should look identical to before, no unnecessary scrollbar
- No dialog extends past the viewport
