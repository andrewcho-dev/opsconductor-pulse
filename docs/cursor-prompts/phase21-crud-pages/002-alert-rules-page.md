# Task 002: Alert Rules CRUD Page

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Create/modify only the files listed in "Files to Create/Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

Task 1 created the API client layer with types, functions, and hooks for alert rules. This task replaces the AlertRulesPage stub with a full CRUD implementation: a table of existing rules, a create/edit dialog, delete confirmation, and enable/disable toggle.

Alert rules let customers define threshold conditions on device metrics (e.g., "battery_pct < 20" or "temp_c > 85"). When the evaluator detects a violation, it generates a THRESHOLD alert that flows through the existing dispatcher pipeline.

**Read first**:
- `frontend/src/features/alerts/AlertRulesPage.tsx` — current stub
- `frontend/src/hooks/use-alert-rules.ts` — hooks from Task 1
- `frontend/src/services/api/types.ts` — AlertRule, AlertRuleCreate, AlertRuleUpdate
- `frontend/src/features/alerts/AlertListPage.tsx` — existing table pattern for reference
- `frontend/src/components/shared/PageHeader.tsx` — action slot for "Add" button
- `frontend/src/services/auth/AuthProvider.tsx` — useAuth() for role checks

---

## Task

### 2.1 Create AlertRuleDialog component

**File**: `frontend/src/features/alerts/AlertRuleDialog.tsx` (NEW)

A dialog for creating or editing an alert rule. Uses shadcn Dialog, Input, Select, and Label components.

The dialog should contain a form with these fields:
- **Name** — text input (required, 1-100 chars)
- **Metric Name** — text input (required, e.g., `battery_pct`, `temp_c`)
- **Operator** — select dropdown: GT (>), LT (<), GTE (>=), LTE (<=)
- **Threshold** — number input (required)
- **Severity** — select dropdown: 1 (Info), 2 (Low), 3 (Medium), 4 (High), 5 (Critical)
- **Description** — textarea (optional)
- **Enabled** — switch toggle (default: true)

When editing, prefill all fields with the existing rule data.

On submit:
- If creating: call `useCreateAlertRule` mutation
- If editing: call `useUpdateAlertRule` mutation with only changed fields
- Close dialog on success
- Show error message from API on failure

Key implementation details:
- Use controlled form state with `useState`
- Disable the submit button while mutation is pending
- Show `mutation.error` message if the API returns an error
- The dialog's `open` prop is controlled by the parent
- Pass `onClose` callback that fires on success or cancel

### 2.2 Create DeleteAlertRuleDialog component

**File**: `frontend/src/features/alerts/DeleteAlertRuleDialog.tsx` (NEW)

A confirmation dialog for deleting an alert rule. Shows the rule name and asks for confirmation.

- Uses shadcn Dialog
- Shows "Delete alert rule '{rule.name}'?"
- "Delete" button (destructive variant) triggers `useDeleteAlertRule` mutation
- "Cancel" button closes the dialog
- Calls `onClose` on success or cancel

### 2.3 Implement AlertRulesPage

**File**: `frontend/src/features/alerts/AlertRulesPage.tsx` (REPLACE)

Replace the stub with a full implementation:

1. **PageHeader** with title "Alert Rules", description showing count, and an "Add Rule" button (only for `customer_admin` role)
2. **Table** listing all rules with columns:
   - Name
   - Condition (formatted as "metric_name operator threshold", e.g., "battery_pct < 20")
   - Severity (using SeverityBadge)
   - Enabled (Switch toggle, only interactive for `customer_admin`)
   - Actions (Edit, Delete buttons — only for `customer_admin`)
3. **Loading** state with Skeleton components
4. **Empty** state with EmptyState component
5. **Error** state showing error message

The page state manages:
- `dialogOpen` — whether the create/edit dialog is visible
- `editingRule` — the rule being edited (null = creating new)
- `deletingRule` — the rule being deleted (null = no delete dialog)

When the user toggles the Enabled switch, call `useUpdateAlertRule` with `{ enabled: newValue }`.

Key patterns:
- Use `useAuth()` to check `user?.role === "customer_admin"` for showing CRUD buttons
- Use `useAlertRules()` hook from Task 1
- Use `PageHeader` with action slot for the "Add Rule" button
- Format operator display: GT→">", LT→"<", GTE→"≥", LTE→"≤"
- Button component from shadcn for all buttons

---

## Files to Create/Modify

| Action | Path | What |
|--------|------|------|
| CREATE | `frontend/src/features/alerts/AlertRuleDialog.tsx` | Create/edit dialog |
| CREATE | `frontend/src/features/alerts/DeleteAlertRuleDialog.tsx` | Delete confirmation dialog |
| MODIFY | `frontend/src/features/alerts/AlertRulesPage.tsx` | Full CRUD page (replace stub) |

---

## Test

### Step 1: Verify build

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
```

### Step 2: Verify TypeScript

```bash
cd /home/opsconductor/simcloud/frontend && npx tsc --noEmit
```

### Step 3: Verify implementation

Read the files and confirm:
- [ ] AlertRulesPage lists rules in a table with name, condition, severity, enabled, actions
- [ ] Condition column formats as "metric_name > threshold"
- [ ] "Add Rule" button only shown for customer_admin role
- [ ] Edit and Delete buttons only shown for customer_admin
- [ ] Enabled switch toggles call updateAlertRule
- [ ] AlertRuleDialog has form with all 7 fields
- [ ] Dialog prefills when editing existing rule
- [ ] Dialog submits create or update mutation
- [ ] Error messages displayed from API response
- [ ] DeleteAlertRuleDialog shows confirmation with rule name
- [ ] Loading and empty states handled
- [ ] SeverityBadge used for severity column

### Step 4: Verify backend tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

---

## Acceptance Criteria

- [ ] Alert rules page shows table of all rules
- [ ] Create dialog with name, metric, operator, threshold, severity, description, enabled
- [ ] Edit dialog prefilled with existing rule data
- [ ] Delete confirmation dialog
- [ ] Enable/disable toggle directly in table
- [ ] CRUD operations only available for customer_admin role
- [ ] Error handling with API error messages
- [ ] Loading and empty states
- [ ] `npm run build` succeeds
- [ ] All Python tests pass

---

## Commit

```
Implement alert rules CRUD page with create/edit dialog

Table listing all rules with condition formatting, severity
badges, and enabled toggles. Create/edit dialog with form
validation. Delete confirmation. Role-based access control.

Phase 21 Task 2: Alert Rules Page
```
