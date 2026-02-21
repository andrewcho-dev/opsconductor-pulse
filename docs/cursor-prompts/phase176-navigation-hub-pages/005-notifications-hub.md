# Task 5: Notifications Hub Page

## Objective

Create a Notifications hub page that consolidates Notification Channels, Delivery Log, and Dead Letter Queue into a single page with 3 tabs. Modify each existing page to support an `embedded` prop.

## Files to Modify

1. `frontend/src/features/notifications/NotificationChannelsPage.tsx` — add `embedded` prop
2. `frontend/src/features/delivery/DeliveryLogPage.tsx` — add `embedded` prop
3. `frontend/src/features/messaging/DeadLetterPage.tsx` — add `embedded` prop

## File to Create

`frontend/src/features/notifications/NotificationsHubPage.tsx`

---

## Step 1: Modify NotificationChannelsPage.tsx

Add `embedded` prop:

```tsx
export default function NotificationChannelsPage({ embedded }: { embedded?: boolean }) {
```

Extract the PageHeader action ("Add Channel" button) and conditionally render:

```tsx
const actions = (
  // ... existing "Add Channel" button JSX ...
);

{!embedded ? (
  <PageHeader
    title="Notification Channels"
    description="Configure channels and alert routing rules."
    action={actions}
  />
) : (
  <div className="flex justify-end gap-2 mb-4">{actions}</div>
)}
```

## Step 2: Modify DeliveryLogPage.tsx

Add `embedded` prop:

```tsx
export default function DeliveryLogPage({ embedded }: { embedded?: boolean }) {
```

This page has a PageHeader with a dynamic description (job count). Wrap it:

```tsx
{!embedded && <PageHeader title="Delivery Log" description={`${total} jobs`} />}
```

## Step 3: Modify DeadLetterPage.tsx

Add `embedded` prop:

```tsx
export default function DeadLetterPage({ embedded }: { embedded?: boolean }) {
```

This page has a PageHeader with a dynamic description (message count). Wrap it:

```tsx
{!embedded && <PageHeader title="Dead Letter Queue" description={`${total} messages`} />}
```

## Step 4: Create NotificationsHubPage

**Create** `frontend/src/features/notifications/NotificationsHubPage.tsx`:

```tsx
import { useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/shared";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import NotificationChannelsPage from "./NotificationChannelsPage";
import DeliveryLogPage from "@/features/delivery/DeliveryLogPage";
import DeadLetterPage from "@/features/messaging/DeadLetterPage";

export default function NotificationsHubPage() {
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") ?? "channels";

  return (
    <div className="space-y-4">
      <PageHeader
        title="Notifications"
        description="Channels, delivery tracking, and failed messages"
      />
      <Tabs
        value={tab}
        onValueChange={(v) => setParams({ tab: v }, { replace: true })}
      >
        <TabsList variant="line">
          <TabsTrigger value="channels">Channels</TabsTrigger>
          <TabsTrigger value="delivery">Delivery Log</TabsTrigger>
          <TabsTrigger value="dead-letter">Dead Letter</TabsTrigger>
        </TabsList>
        <TabsContent value="channels" className="mt-4">
          <NotificationChannelsPage embedded />
        </TabsContent>
        <TabsContent value="delivery" className="mt-4">
          <DeliveryLogPage embedded />
        </TabsContent>
        <TabsContent value="dead-letter" className="mt-4">
          <DeadLetterPage embedded />
        </TabsContent>
      </Tabs>
    </div>
  );
}

export const Component = NotificationsHubPage;
```

## Verification

- `npx tsc --noEmit` passes
- NotificationsHubPage renders with 3 tabs
- Channels tab shows notification channels with Add/Test/Edit/Delete
- Delivery Log tab shows job history with status filter
- Dead Letter tab shows failed messages with replay/discard actions
- Tab state in URL: `/notifications?tab=delivery`, `/notifications?tab=dead-letter`
