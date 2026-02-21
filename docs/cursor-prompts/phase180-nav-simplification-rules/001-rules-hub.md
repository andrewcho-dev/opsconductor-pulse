# Task 1: Rules Hub Page

## Objective

Create a Rules hub page that consolidates all rule/policy configuration into one place: Alert Rules, Escalation Policies, On-Call Schedules, and Maintenance Windows. These tabs are currently inside the Alerts hub and will be moved here.

## File to Create

`frontend/src/features/rules/RulesHubPage.tsx`

## Design

Follows the standard hub page pattern (Phase 176):
- `PageHeader` with title "Rules"
- `TabsList variant="line"` with 4 tabs
- URL-based tab state via `useSearchParams`
- Renders existing page components with `embedded` prop

Default tab: `alert-rules`

Tab values and labels:
| Tab value | Label | Component |
|-----------|-------|-----------|
| `alert-rules` | Alert Rules | `AlertRulesPage` |
| `escalation` | Escalation | `EscalationPoliciesPage` |
| `oncall` | On-Call | `OncallSchedulesPage` |
| `maintenance` | Maintenance | `MaintenanceWindowsPage` |

## Implementation

```tsx
import { useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/shared";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import AlertRulesPage from "@/features/alerts/AlertRulesPage";
import EscalationPoliciesPage from "@/features/escalation/EscalationPoliciesPage";
import OncallSchedulesPage from "@/features/oncall/OncallSchedulesPage";
import MaintenanceWindowsPage from "@/features/alerts/MaintenanceWindowsPage";

export default function RulesHubPage() {
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") ?? "alert-rules";

  return (
    <div className="space-y-4">
      <PageHeader
        title="Rules"
        description="Configure alert rules, escalation policies, and schedules"
      />
      <Tabs value={tab} onValueChange={(v) => setParams({ tab: v }, { replace: true })}>
        <TabsList variant="line">
          <TabsTrigger value="alert-rules">Alert Rules</TabsTrigger>
          <TabsTrigger value="escalation">Escalation</TabsTrigger>
          <TabsTrigger value="oncall">On-Call</TabsTrigger>
          <TabsTrigger value="maintenance">Maintenance</TabsTrigger>
        </TabsList>
        <TabsContent value="alert-rules" className="mt-4">
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

export const Component = RulesHubPage;
```

## Important Notes

- All four embedded components already support the `embedded` prop (from Phase 176)
- The `alert-rules` tab value uses a hyphen (not `rules`) to avoid confusion with the hub page's own route
- Deep links: `/rules?tab=alert-rules`, `/rules?tab=escalation`, `/rules?tab=oncall`, `/rules?tab=maintenance`
- This hub is designed to be extensible — future tabs (Routing Rules, Automation) can be added without restructuring

## Verification

- `npx tsc --noEmit` passes
- File created at correct path
- Hub page renders with 4 tabs
- Each tab renders its embedded component without its own PageHeader
- Tab switching updates the URL `?tab=` parameter
