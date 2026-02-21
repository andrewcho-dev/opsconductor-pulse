# Task 3: Tools Hub Page

## Objective

Create a Tools hub page that combines the Connection Guide and MQTT Test Client into a single tabbed page, following the hub page pattern from Phase 176.

## File to Create

`frontend/src/features/fleet/ToolsHubPage.tsx`

## Design

The hub page uses the standard hub pattern:
- `PageHeader` with title "Tools"
- `TabsList variant="line"` with 2 tabs: Connection Guide, MQTT Test
- URL-based tab state via `useSearchParams` for deep linking
- Renders `ConnectionGuidePage` and `MqttTestClientPage` with `embedded` prop

## Implementation

```tsx
import { useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/shared";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import ConnectionGuidePage from "./ConnectionGuidePage";
import MqttTestClientPage from "./MqttTestClientPage";

export default function ToolsHubPage() {
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") ?? "guide";

  return (
    <div className="space-y-4">
      <PageHeader title="Tools" description="Connection guides and testing utilities" />
      <Tabs value={tab} onValueChange={(v) => setParams({ tab: v }, { replace: true })}>
        <TabsList variant="line">
          <TabsTrigger value="guide">Connection Guide</TabsTrigger>
          <TabsTrigger value="mqtt">MQTT Test Client</TabsTrigger>
        </TabsList>
        <TabsContent value="guide" className="mt-4">
          <ConnectionGuidePage embedded />
        </TabsContent>
        <TabsContent value="mqtt" className="mt-4">
          <MqttTestClientPage embedded />
        </TabsContent>
      </Tabs>
    </div>
  );
}

export const Component = ToolsHubPage;
```

## Important Notes

- This follows the exact same pattern as `UpdatesHubPage`, `AlertsHubPage`, etc.
- Default tab is `"guide"` (Connection Guide) since it's the most common entry point for new users
- Deep links: `/fleet/tools?tab=guide` and `/fleet/tools?tab=mqtt`
- Both child pages must have the `embedded` prop (created in Tasks 1 and 2)

## Verification

- `npx tsc --noEmit` passes
- File created at correct path
- Hub page renders with 2 tabs
- Switching tabs updates the URL `?tab=` parameter
- Both embedded pages render without their own PageHeader
