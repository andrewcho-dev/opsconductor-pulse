# Phase 119 — UI Foundation: Toast, Forms, DataTable, Navigation

You are executing Phase 119. This phase installs foundational frontend libraries and retrofits existing pages to use them: toast notifications (sonner), form validation (react-hook-form + zod), data tables (@tanstack/react-table), 404/breadcrumb navigation, and a TanStack Query refactor of JobsPage.

**Read and execute the following prompt files in this exact order.** Each file contains precise instructions — file paths, code blocks, shell commands, and verification steps. Follow them exactly.

## Execution Order

Execute these sequentially. Do NOT skip ahead. After each step, run its verification checks before proceeding to the next.

1. **`001-toast-notification-system.md`** — Install `sonner`, mount `<Toaster />` in AppShell, replace all `window.alert()` with `toast()` and all `window.confirm()` with Shadcn `AlertDialog`. Commit.
2. **`002-form-validation.md`** — Install `react-hook-form`, `@hookform/resolvers`, `zod`. Create Shadcn Form component. Retrofit AddDeviceModal, AlertRuleDialog, InviteUserDialog, CreateRoleDialog with validation. Commit.
3. **`003-standardize-tables.md`** — Install `@tanstack/react-table`. Create reusable `DataTable` component. Retrofit DeviceListPage (device list), AlertListPage, UsersPage, AlertRulesPage. Commit.
4. **`004-navigation-404-breadcrumbs.md`** — Add 404 route, create NotFoundPage, add breadcrumbs to detail pages, fix broken sidebar links and hardcoded version. Commit.
5. **`005-jobs-page-tanstack.md`** — Refactor JobsPage from raw useEffect/useState to useQuery/useMutation via new `use-jobs.ts` hook. Replace raw `<table>` with DataTable. Commit.

## Key Files

| File | Role |
|------|------|
| `frontend/package.json` | Dependency management |
| `frontend/src/components/layout/AppShell.tsx` | Main layout — Toaster mount |
| `frontend/src/components/layout/AppSidebar.tsx` | Sidebar navigation — version fix, link fixes |
| `frontend/src/app/router.tsx` | Routes — 404 catch-all |
| `frontend/src/components/ui/form.tsx` | New — Shadcn Form wrapper |
| `frontend/src/components/ui/data-table.tsx` | New — DataTable component |
| `frontend/src/features/jobs/JobsPage.tsx` | Jobs page — full refactor |
| `frontend/src/hooks/use-jobs.ts` | New — TanStack Query jobs hook |
| `frontend/src/features/NotFoundPage.tsx` | New — 404 page |
| `frontend/src/features/devices/AddDeviceModal.tsx` | Form validation retrofit |
| `frontend/src/features/alerts/AlertRuleDialog.tsx` | Form validation + toast retrofit |
| `frontend/src/features/alerts/AlertRulesPage.tsx` | Toast retrofit |
| `frontend/src/features/users/InviteUserDialog.tsx` | Form validation retrofit |
| `frontend/src/features/users/UsersPage.tsx` | Toast + confirm dialog retrofit |
| `frontend/src/features/roles/CreateRoleDialog.tsx` | Form validation retrofit |
| `frontend/src/features/notifications/NotificationChannelsPage.tsx` | Toast + confirm dialog retrofit |
| `frontend/src/features/alerts/AlertListPage.tsx` | DataTable retrofit |

## Rules

- Each step produces exactly one git commit. Do not squash or skip commits.
- If a verification check fails, fix the issue before moving on.
- Do not modify files beyond what each prompt specifies.
- Do not add comments, docstrings, or type annotations beyond what is specified.

## Final Verification

After all 5 steps are complete, run every one of these checks:

```bash
git status
# Expected: clean working tree (no unstaged changes)

git log --oneline -5
# Expected: 5 new commits matching the messages from each step

cd frontend && npm run build
# Expected: builds clean, zero errors

cd frontend && npx tsc --noEmit
# Expected: zero type errors

grep -r "window\.alert\(" frontend/src/
# Expected: no output (all replaced with toast)

grep -r "window\.confirm\(" frontend/src/
# Expected: no output (all replaced with AlertDialog)

grep 'v18' frontend/src/components/layout/AppSidebar.tsx
# Expected: no output (hardcoded version removed)
```

If all checks pass, Phase 119 is complete.
