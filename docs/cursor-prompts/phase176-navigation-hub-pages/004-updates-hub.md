# Task 4: Updates Hub Page

## Objective

Create an Updates hub page that consolidates OTA Campaigns and Firmware pages into a single page with 2 tabs. Modify each existing page to support an `embedded` prop.

## Files to Modify

1. `frontend/src/features/ota/OtaCampaignsPage.tsx` — add `embedded` prop
2. `frontend/src/features/ota/FirmwareListPage.tsx` — add `embedded` prop

## File to Create

`frontend/src/features/ota/UpdatesHubPage.tsx`

---

## Step 1: Modify OtaCampaignsPage.tsx

Add `embedded` prop:

```tsx
export default function OtaCampaignsPage({ embedded }: { embedded?: boolean }) {
```

Extract the PageHeader action (the "Add Campaign" button) and conditionally render:

```tsx
const actions = (
  // ... existing "Add Campaign" button JSX ...
);

{!embedded ? (
  <PageHeader
    title="OTA Campaigns"
    description="Manage firmware rollouts to your device fleet."
    action={actions}
  />
) : (
  <div className="flex justify-end gap-2 mb-4">{actions}</div>
)}
```

## Step 2: Modify FirmwareListPage.tsx

Add `embedded` prop:

```tsx
export default function FirmwareListPage({ embedded }: { embedded?: boolean }) {
```

Extract the PageHeader action (the "Add Firmware" button) and conditionally render:

```tsx
const actions = (
  // ... existing "Add Firmware" button JSX ...
);

{!embedded ? (
  <PageHeader
    title="Firmware Versions"
    description="Registered firmware binaries available for OTA deployment."
    action={actions}
  />
) : (
  <div className="flex justify-end gap-2 mb-4">{actions}</div>
)}
```

## Step 3: Create UpdatesHubPage

**Create** `frontend/src/features/ota/UpdatesHubPage.tsx`:

```tsx
import { useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/shared";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import OtaCampaignsPage from "./OtaCampaignsPage";
import FirmwareListPage from "./FirmwareListPage";

export default function UpdatesHubPage() {
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") ?? "campaigns";

  return (
    <div className="space-y-4">
      <PageHeader
        title="Updates"
        description="Manage firmware and OTA rollouts"
      />
      <Tabs
        value={tab}
        onValueChange={(v) => setParams({ tab: v }, { replace: true })}
      >
        <TabsList variant="line">
          <TabsTrigger value="campaigns">Campaigns</TabsTrigger>
          <TabsTrigger value="firmware">Firmware</TabsTrigger>
        </TabsList>
        <TabsContent value="campaigns" className="mt-4">
          <OtaCampaignsPage embedded />
        </TabsContent>
        <TabsContent value="firmware" className="mt-4">
          <FirmwareListPage embedded />
        </TabsContent>
      </Tabs>
    </div>
  );
}

export const Component = UpdatesHubPage;
```

## Verification

- `npx tsc --noEmit` passes
- UpdatesHubPage renders with 2 tabs (Campaigns, Firmware)
- Campaigns tab shows the OTA campaigns list with progress bars
- Firmware tab shows firmware versions with "Add Firmware" button
- Tab state in URL: `/updates?tab=firmware`
- Campaign detail links (`/ota/campaigns/:campaignId`) still work from the campaigns table
