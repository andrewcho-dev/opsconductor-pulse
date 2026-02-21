# Task 8: Build Verification and Regression Fix

## Step 1: Type check

```bash
cd frontend && npx tsc --noEmit
```

Fix any TypeScript errors.

## Step 2: Production build

```bash
cd frontend && npm run build
```

Fix any build errors.

## Step 3: Verify zero silent mutations

```bash
# Find all files with useMutation that DON'T import toast
for f in $(grep -rn "useMutation" frontend/src/ --include="*.tsx" -l); do
  if ! grep -q 'from "sonner"' "$f"; then
    echo "MISSING TOAST: $f"
  fi
done
```

Any files listed here still need toast feedback added. Fix them following the same pattern from Tasks 2-6.

**Exception:** Hook files in `frontend/src/hooks/` that define reusable mutation hooks may not need toast directly — the consuming component should have it. But if the hook is the ONLY place the mutation is defined and consumed, it needs toast.

## Step 4: Verify zero duplicated formatError

```bash
grep -rn "function formatError" frontend/src/ --include="*.tsx" --include="*.ts"
```

Should return zero results. All error formatting should go through `getErrorMessage` from `@/lib/errors`.

## Step 5: Verify zero console.error in mutation handlers

```bash
grep -rn "console\.error" frontend/src/features/ --include="*.tsx"
```

Should return zero results in feature files. The only acceptable `console.error` is in `services/api/client.ts` for network-level logging.

## Step 6: Verify modal state naming

```bash
# Check for old patterns that should have been renamed
grep -rn "showCreate\|showEdit\|showDelete\|openCreate\|openEdit\|isOpen\b" frontend/src/features/ --include="*.tsx" | grep -v "onOpenChange\|showCloseButton\|showConfirm\|isOpenChange"
```

Review any matches. The following are acceptable:
- `showConfirm` / `showCloseButton` — these are from `useFormDirtyGuard` and UI components
- `onOpenChange` — this is a prop name, not state

Everything else should use the `xOpen` / `setXOpen` convention.

## Step 7: Functional checklist

- [ ] Dashboard: rename, share, set default show toast
- [ ] Dashboard: add/remove/configure widget show toast
- [ ] Devices: group CRUD shows toast
- [ ] Devices: certificate generate/rotate/revoke shows toast
- [ ] Devices: token revoke/rotate shows toast
- [ ] Operator: tenant create/edit/delete shows toast
- [ ] Operator: subscription create/edit shows toast
- [ ] Operator: user CRUD shows toast
- [ ] Alerts: delete rule shows toast
- [ ] Alerts: maintenance window CRUD shows toast
- [ ] Escalation: policy CRUD shows toast
- [ ] On-call: schedule CRUD shows toast
- [ ] Dead letters: replay/discard/purge shows toast
- [ ] Subscription: renewal shows toast
- [ ] Notifications: routing rule CRUD shows toast
- [ ] All error toasts show meaningful messages (not "API error: 500")
- [ ] No `console.error()` in feature files
- [ ] No duplicated `formatError()` functions

## Step 8: Final lint

```bash
cd frontend && npx tsc --noEmit
```

Zero errors before continuing.
