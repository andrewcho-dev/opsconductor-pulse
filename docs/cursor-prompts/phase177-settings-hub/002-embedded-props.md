# Task 2: Add `embedded` Prop to Settings Pages

## Objective

Add the `embedded?: boolean` prop to 6 page components that will be rendered inside the SettingsLayout. When `embedded` is true, each page skips its own `PageHeader` (the SettingsLayout provides the overall "Settings" header and left-nav context).

## Files to Modify

1. `frontend/src/features/settings/OrganizationPage.tsx`
2. `frontend/src/features/settings/BillingPage.tsx`
3. `frontend/src/features/settings/CarrierIntegrationsPage.tsx`
4. `frontend/src/features/settings/ProfilePage.tsx`
5. `frontend/src/features/notifications/NotificationsHubPage.tsx`
6. `frontend/src/features/users/TeamHubPage.tsx`

---

## Pattern

For each page, apply the same 2-step change used in Phase 176 for hub page embedding:

### Step 1: Add `embedded` parameter

```tsx
// Before:
export default function SomePage() {

// After:
export default function SomePage({ embedded }: { embedded?: boolean }) {
```

### Step 2: Conditionally render PageHeader

**For pages WITHOUT action buttons in PageHeader:**
```tsx
{!embedded && <PageHeader title="..." description="..." />}
```

**For pages WITH action buttons:**
```tsx
const actions = (/* existing action JSX */);

{!embedded ? (
  <PageHeader title="..." description="..." action={actions} />
) : actions ? (
  <div className="flex justify-end gap-2 mb-4">{actions}</div>
) : null}
```

---

## Specific Changes Per Page

### 1. OrganizationPage.tsx

- Has `<PageHeader>` with title "Organization" and icon
- **No action buttons** in PageHeader
- Change: `{!embedded && <PageHeader ... />}`

### 2. BillingPage.tsx

- Has `<PageHeader>` with title "Billing", description "Manage account tier and billing limits."
- **No action buttons** in PageHeader (Stripe portal/checkout buttons are in the content, not the header)
- Change: `{!embedded && <PageHeader ... />}`

### 3. CarrierIntegrationsPage.tsx

- Has `<PageHeader>` — check if it has action buttons
- If no actions: `{!embedded && <PageHeader ... />}`
- If has actions: extract and render conditionally

### 4. ProfilePage.tsx

- Has `<PageHeader>` with title "Profile" and icon
- **No action buttons** in PageHeader (save button is in the form content)
- Change: `{!embedded && <PageHeader ... />}`

### 5. NotificationsHubPage.tsx

This is a hub page from Phase 176. It has its own `<PageHeader>` and `<TabsList>`.

When `embedded` is true:
- **Skip the PageHeader** (the SettingsLayout provides context)
- **Keep the TabsList** (users still need to switch between Channels/Delivery/Dead Letter)

```tsx
export default function NotificationsHubPage({ embedded }: { embedded?: boolean }) {
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") ?? "channels";

  return (
    <div className="space-y-4">
      {!embedded && (
        <PageHeader title="Notifications" description="Channels, delivery tracking, and failed messages" />
      )}
      <Tabs value={tab} onValueChange={(v) => setParams({ tab: v }, { replace: true })}>
        <TabsList variant="line">
          {/* tabs stay — they're essential for navigating sub-sections */}
          <TabsTrigger value="channels">Channels</TabsTrigger>
          <TabsTrigger value="delivery">Delivery Log</TabsTrigger>
          <TabsTrigger value="dead-letter">Dead Letter</TabsTrigger>
        </TabsList>
        {/* TabsContent stays unchanged */}
      </Tabs>
    </div>
  );
}
```

### 6. TeamHubPage.tsx

Same pattern as NotificationsHubPage — skip PageHeader, keep TabsList:

```tsx
export default function TeamHubPage({ embedded }: { embedded?: boolean }) {
  // ... existing permission checks ...

  return (
    <div className="space-y-4">
      {!embedded && (
        <PageHeader title="Team" description="Manage users and roles in your organization" />
      )}
      <Tabs value={activeTab} onValueChange={(v) => setParams({ tab: v }, { replace: true })}>
        <TabsList variant="line">
          <TabsTrigger value="members">Members</TabsTrigger>
          {canManageRoles && <TabsTrigger value="roles">Roles</TabsTrigger>}
        </TabsList>
        {/* TabsContent stays unchanged */}
      </Tabs>
    </div>
  );
}
```

## Verification

- `npx tsc --noEmit` passes
- Each page still renders correctly when accessed directly (without `embedded` prop — backward compatible)
- When rendered with `embedded` prop, no PageHeader is shown
- NotificationsHubPage and TeamHubPage keep their TabsList even when embedded
- No broken imports or layout issues
