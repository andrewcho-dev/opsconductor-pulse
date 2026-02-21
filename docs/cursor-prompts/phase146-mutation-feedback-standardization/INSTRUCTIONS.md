# Phase 146 — Cursor Execution Instructions

Execute these 9 tasks **in order**. Each task depends on the previous one completing successfully. After each task, run `cd frontend && npx tsc --noEmit` to catch errors before moving on.

**Important:** This phase adds user feedback (toasts) to existing mutations and standardizes naming. It does NOT change any business logic or visual styling.

---

## Task 1: Centralize error formatting

Open and read `docs/cursor-prompts/phase146-mutation-feedback-standardization/001-centralize-error-formatting.md` for full details.

Merge the duplicated `formatError()` function into `lib/errors.ts` as an improved `getErrorMessage()`. Remove the local copies from AlertRuleDialog.tsx and DeleteAlertRuleDialog.tsx.

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 2: Dashboard mutation toasts

Open and read `docs/cursor-prompts/phase146-mutation-feedback-standardization/002-dashboard-toasts.md` for full details.

Add toast feedback to 10 mutations across 6 dashboard files: DashboardBuilder, DashboardSettings, DashboardSelector, DashboardPage, WidgetConfigDialog, AddWidgetDrawer.

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 3: Device mutation toasts

Open and read `docs/cursor-prompts/phase146-mutation-feedback-standardization/003-device-toasts.md` for full details.

Add toast feedback to 12 mutations across 5 device files: DeviceGroupsPage, DeviceCertificatesTab, DeviceApiTokensPanel, DeviceCommandPanel, Step3Provision.

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 4: Operator mutation toasts

Open and read `docs/cursor-prompts/phase146-mutation-feedback-standardization/004-operator-toasts.md` for full details.

Add toast feedback to 19 mutations across 9 operator files. Replace `console.error()` with `toast.error()` in CreateTenantDialog.

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 5: Alert/Escalation/Oncall mutation toasts

Open and read `docs/cursor-prompts/phase146-mutation-feedback-standardization/005-alert-escalation-oncall-toasts.md` for full details.

Add toast feedback to 12 mutations across 5 files: MaintenanceWindowsPage, DeleteAlertRuleDialog, AlertRulesPage, EscalationPoliciesPage, OncallSchedulesPage.

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 6: Remaining mutation toasts

Open and read `docs/cursor-prompts/phase146-mutation-feedback-standardization/006-remaining-toasts.md` for full details.

Add toast feedback to 8 mutations across 3 files: DeadLetterPage, RenewalPage, RoutingRulesPanel. Then sweep for any remaining silent mutations.

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 7: Standardize modal state naming

Open and read `docs/cursor-prompts/phase146-mutation-feedback-standardization/007-standardize-modal-state.md` for full details.

Rename `showCreate`/`showEdit`/`openCreate`/`showForm` etc. to the standard `xOpen`/`setXOpen` convention across ~12 files.

**Checkpoint:** `cd frontend && npx tsc --noEmit`

---

## Task 8: Build verification

Open and read `docs/cursor-prompts/phase146-mutation-feedback-standardization/008-verify-and-fix.md` for the complete checklist.

1. `cd frontend && npx tsc --noEmit` — must be zero errors
2. `cd frontend && npm run build` — must succeed
3. Verify zero silent mutations (grep check)
4. Verify zero duplicated formatError (grep check)
5. Verify zero console.error in features (grep check)
6. Verify modal state naming consistency (grep check)

---

## Task 9: Update documentation

Open and read `docs/cursor-prompts/phase146-mutation-feedback-standardization/009-update-documentation.md` for full details.

Add **"Mutation Feedback Conventions"** section to `docs/development/frontend.md` covering toast rules, error formatting, modal state naming, and prohibited patterns. Update YAML frontmatter in both `docs/development/frontend.md` and `docs/index.md`.
