The shadcn/ui Dialog component handles focus trapping automatically via Radix UI — confirm this is being used correctly and not being worked around.

Search for all dialog/modal usage:

```bash
grep -rn 'Dialog\|Modal\|Sheet' frontend/src/ --include="*.tsx" | grep 'import' | grep -v 'shadcn\|radix\|ui/'
```

For each modal/dialog component that uses shadcn `<Dialog>`:
1. Confirm it uses `<DialogContent>` which provides focus trapping automatically.
2. Confirm `<DialogTitle>` is present — this is required for screen readers. If the title is visually hidden, use `<DialogTitle className="sr-only">`.
3. Confirm `<DialogDescription>` is present or add one (can be `sr-only` if not needed visually).

For any custom modal implementations (not using shadcn Dialog): ensure they use `role="dialog"`, `aria-modal="true"`, `aria-labelledby` pointing to the title, and that focus is moved to the dialog on open and returned to the trigger on close.

Check specifically:
- `frontend/src/features/alerts/AlertRuleDialog.tsx`
- `frontend/src/features/devices/` — any device detail modals
- Any confirmation dialogs

If a `<Dialog>` is missing `<DialogTitle>`, add one. This is both a WCAG requirement and a Radix UI warning.
