# Task 1: Add Embedded Props + Pill-Variant Nested Tabs

## Objective

Prepare pages for hub rendering by:
1. Adding the `embedded` prop to 5 pages that will be rendered as tabs inside DevicesHubPage
2. Updating 4 existing hub pages to use pill-variant tabs when rendered embedded (nested hub-in-hub)

---

## Part 1: Add `embedded` Prop to 5 Pages

For each page below, add `{ embedded }: { embedded?: boolean }` to the component props and conditionally skip the `PageHeader` when `embedded` is true. This follows the exact same pattern used by all other embedded pages (Phase 176).

### 1. `frontend/src/features/devices/DeviceListPage.tsx`

**Add `embedded` prop to the component signature:**
```tsx
export default function DeviceListPage({ embedded }: { embedded?: boolean }) {
```

**Conditionally render PageHeader:**
```tsx
{!embedded && (
  <PageHeader
    title="Devices"
    description={...}
    action={...}
  />
)}
```

When `embedded`, the action buttons (DeviceActions with Add Device, Guided Setup, Import) should still be accessible. Render them in a simple flex container:
```tsx
{embedded && (
  <div className="flex justify-end">
    <DeviceActions ... />
  </div>
)}
```

**Also remove the fleet quick-links row** — the `FLEET_LINKS` array and the `<div className="flex flex-wrap gap-1.5">` block that renders the outline button links. This row was added in Phase 180 and is being replaced by tabs in Task 2.

### 2. `frontend/src/features/sites/SitesPage.tsx`

Read the file first to see the current structure. Add `embedded` prop and conditionally skip PageHeader. Pattern:

```tsx
export default function SitesPage({ embedded }: { embedded?: boolean }) {
  // ...
  return (
    <div className="space-y-4">
      {!embedded && <PageHeader title="Sites" ... />}
      {/* rest of content */}
    </div>
  );
}
```

If the page has action buttons in the PageHeader, render them in a flex container when embedded (same pattern as other pages).

### 3. `frontend/src/features/templates/TemplateListPage.tsx`

Same pattern. Read the file, add `embedded` prop, conditionally skip PageHeader.

### 4. `frontend/src/features/devices/DeviceGroupsPage.tsx`

Same pattern. Read the file, add `embedded` prop, conditionally skip PageHeader.

### 5. `frontend/src/features/map/FleetMapPage.tsx`

Same pattern. Read the file, add `embedded` prop, conditionally skip PageHeader.

**Note for FleetMapPage:** If the map takes full height via `h-[calc(100vh-...)]`, it may need height adjustment when embedded (since the tab bar adds height above it). Adjust the calculation or use `flex-1` with a flex parent.

---

## Part 2: Pill-Variant Tabs for Nested Hubs

When a hub page is rendered inside another hub's tab, its internal tabs should use pill-style (`variant="default"`) instead of line-style (`variant="line"`) to create visual hierarchy. Update these 4 hub pages:

### 1. `frontend/src/features/ota/UpdatesHubPage.tsx`

**Current:**
```tsx
export default function UpdatesHubPage() {
```

**Change to:**
```tsx
export default function UpdatesHubPage({ embedded }: { embedded?: boolean }) {
```

Note: UpdatesHubPage may already have an `embedded` prop — if so, just update the TabsList line.

**Update TabsList:**
```tsx
<TabsList variant={embedded ? "default" : "line"}>
```

**Update PageHeader** (skip when embedded):
```tsx
{!embedded && <PageHeader title="Updates" description="Manage firmware and OTA rollouts" />}
```

### 2. `frontend/src/features/fleet/ToolsHubPage.tsx`

Same changes:
- Add/verify `embedded` prop
- `<TabsList variant={embedded ? "default" : "line"}>`
- Skip PageHeader when embedded

### 3. `frontend/src/features/notifications/NotificationsHubPage.tsx`

This page likely already has the `embedded` prop (from Phase 177). Verify and update:
- `<TabsList variant={embedded ? "default" : "line"}>`

If PageHeader is already conditionally rendered based on `embedded`, no change needed there.

### 4. `frontend/src/features/users/TeamHubPage.tsx`

Same as NotificationsHubPage — likely already has `embedded` prop. Update:
- `<TabsList variant={embedded ? "default" : "line"}>`

---

## Verification

```bash
cd frontend && npx tsc --noEmit
```

- All 9 files compile without errors
- DeviceListPage no longer renders fleet quick-links
- Each of the 5 new embedded pages skips PageHeader when `embedded={true}`
- Each of the 4 hub pages uses pill-variant tabs when `embedded={true}`
- When rendered standalone (not embedded), all pages look identical to before
