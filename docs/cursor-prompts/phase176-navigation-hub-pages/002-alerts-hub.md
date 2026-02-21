# Task 2: Alerts Hub Page

## Objective

Create an Alerts hub page that consolidates 5 standalone alert-related pages into a single page with tabbed navigation. Modify each existing page to support an `embedded` prop.

## Files to Modify

1. `frontend/src/features/alerts/AlertListPage.tsx` — add `embedded` prop
2. `frontend/src/features/alerts/AlertRulesPage.tsx` — add `embedded` prop
3. `frontend/src/features/escalation/EscalationPoliciesPage.tsx` — add `embedded` prop
4. `frontend/src/features/oncall/OncallSchedulesPage.tsx` — add `embedded` prop
5. `frontend/src/features/alerts/MaintenanceWindowsPage.tsx` — add `embedded` prop

## File to Create

`frontend/src/features/alerts/AlertsHubPage.tsx`

---

## Step 1: Modify Existing Pages — Add `embedded` Prop

For **each** of the 5 pages listed above, apply this pattern:

### Change 1: Add `embedded` parameter to the function signature

**Before:**
```tsx
export default function AlertRulesPage() {
```

**After:**
```tsx
export default function AlertRulesPage({ embedded }: { embedded?: boolean }) {
```

### Change 2: Conditionally render PageHeader

Find the `<PageHeader ... />` JSX in each page. Wrap it in a conditional:

**Pattern for pages WITH action buttons in PageHeader:**
```tsx
// Extract the action JSX into a variable (if not already):
const actions = (
  <>
    {/* existing action buttons */}
  </>
);

// Replace the PageHeader with:
{!embedded ? (
  <PageHeader title="..." description="..." action={actions} />
) : (
  <div className="flex justify-end gap-2">{actions}</div>
)}
```

**Pattern for pages WITHOUT action buttons:**
```tsx
{!embedded && <PageHeader title="..." description="..." />}
```

### Specific Changes Per Page

#### AlertListPage.tsx
- Has PageHeader with `action` containing a Rules link button and Refresh button
- When `embedded`: skip PageHeader entirely (the hub page provides the title; Rules is now a tab; Refresh can stay as part of the content or be removed)
- Simplest approach: `{!embedded && <PageHeader ... />}`
- The internal severity tabs (ALL, CRITICAL, etc.) remain unchanged — they're filter controls, not navigation

#### AlertRulesPage.tsx
- Has PageHeader with `action` containing "Add All Defaults" and "Add Rule" buttons
- When `embedded`: render the action buttons in a `<div className="flex justify-end gap-2 mb-4">` without the PageHeader

#### EscalationPoliciesPage.tsx
- Has PageHeader with `action` containing "Add Policy" button
- When `embedded`: render the action button in a `<div className="flex justify-end gap-2 mb-4">`

#### OncallSchedulesPage.tsx
- Has PageHeader with `action` containing "New Schedule" button
- When `embedded`: render the action button in a `<div className="flex justify-end gap-2 mb-4">`

#### MaintenanceWindowsPage.tsx
- Has PageHeader with `action` containing "Add Window" button
- When `embedded`: render the action button in a `<div className="flex justify-end gap-2 mb-4">`

---

## Step 2: Create AlertsHubPage

**Create** `frontend/src/features/alerts/AlertsHubPage.tsx`:

```tsx
import { useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/shared";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import AlertListPage from "./AlertListPage";
import AlertRulesPage from "./AlertRulesPage";
import MaintenanceWindowsPage from "./MaintenanceWindowsPage";
import EscalationPoliciesPage from "@/features/escalation/EscalationPoliciesPage";
import OncallSchedulesPage from "@/features/oncall/OncallSchedulesPage";

const TABS = [
  { value: "inbox", label: "Inbox" },
  { value: "rules", label: "Rules" },
  { value: "escalation", label: "Escalation" },
  { value: "oncall", label: "On-Call" },
  { value: "maintenance", label: "Maintenance" },
] as const;

export default function AlertsHubPage() {
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") ?? "inbox";

  return (
    <div className="space-y-4">
      <PageHeader
        title="Alerts"
        description="Monitor, triage, and manage alert lifecycle"
      />
      <Tabs
        value={tab}
        onValueChange={(v) => setParams({ tab: v }, { replace: true })}
      >
        <TabsList variant="line">
          {TABS.map((t) => (
            <TabsTrigger key={t.value} value={t.value}>
              {t.label}
            </TabsTrigger>
          ))}
        </TabsList>
        <TabsContent value="inbox" className="mt-4">
          <AlertListPage embedded />
        </TabsContent>
        <TabsContent value="rules" className="mt-4">
          <AlertRulesPage embedded />
        </TabsContent>
        <TabsContent value="escalation" className="mt-4">
          <EscalationPoliciesPage embedded />
        </TabsContent>
        <TabsContent value="oncall" className="mt-4">
          <OncallSchedulesPage embedded />
        </TabsContent>
        <TabsContent value="maintenance" className="mt-4">
          <MaintenanceWindowsPage embedded />
        </TabsContent>
      </Tabs>
    </div>
  );
}

export const Component = AlertsHubPage;
```

**Important notes:**
- Verify the import paths match the actual file locations. `EscalationPoliciesPage` is in `features/escalation/` and `OncallSchedulesPage` is in `features/oncall/`
- The `variant="line"` on `TabsList` renders the primary-colored underline tabs (from Phase 175)
- `useSearchParams` stores tab state in the URL for deep linking
- `replace: true` prevents each tab click from creating a browser history entry

## Verification

- `npx tsc --noEmit` passes
- Each page still works standalone (without `embedded` prop — the default is `false`/`undefined`)
- AlertsHubPage renders with 5 tabs
- Clicking each tab shows the corresponding page content without a duplicate PageHeader
- Tab state is in the URL: `/alerts?tab=rules`, `/alerts?tab=escalation`, etc.
- Default tab (no `?tab` param) shows the Inbox
