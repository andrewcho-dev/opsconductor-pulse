# Task 9: Update Documentation

## Objective

Update project documentation to reflect Phase 176's navigation restructure: new Home page, hub pages, flat sidebar, and route changes.

## Files to Update

1. `docs/development/frontend.md`
2. `docs/features/device-management.md`
3. `docs/index.md`
4. `docs/services/ui-iot.md`

---

## 1. `docs/development/frontend.md`

### Frontmatter

- Set `last-verified: 2026-02-19`
- Add `176` to the `phases` array
- Add to `sources`: `frontend/src/features/home/HomePage.tsx`, `frontend/src/features/alerts/AlertsHubPage.tsx`

### Content Changes

#### Add "Hub Page Pattern" section (after the Phase 175 sections)

```markdown
## Hub Pages (Phase 176)

Hub pages consolidate related standalone pages into a single page with tabbed navigation. Each hub:
- Renders a `PageHeader` with the hub title
- Uses `TabsList variant="line"` for primary-colored underline tabs
- Stores active tab in URL via `useSearchParams` (`?tab=value`) for deep linking
- Renders existing page components in `TabsContent` panels with the `embedded` prop

### Hub page inventory

| Hub | Route | Tabs |
|-----|-------|------|
| Alerts | `/alerts` | Inbox, Rules, Escalation, On-Call, Maintenance |
| Analytics | `/analytics` | Explorer, Reports |
| Updates | `/updates` | Campaigns, Firmware |
| Notifications | `/notifications` | Channels, Delivery Log, Dead Letter |
| Team | `/team` | Members, Roles |

### `embedded` prop convention

Page components that can be rendered inside a hub tab accept an optional `embedded?: boolean` prop. When `true`:
- The page skips its own `PageHeader`
- Action buttons render in a simple flex container instead
- All other content (queries, tables, modals) remains unchanged

### Creating a new hub page

```tsx
import { useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/shared";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";

export default function MyHubPage() {
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") ?? "default";

  return (
    <div className="space-y-4">
      <PageHeader title="Hub Title" description="Hub description" />
      <Tabs value={tab} onValueChange={(v) => setParams({ tab: v }, { replace: true })}>
        <TabsList variant="line">
          <TabsTrigger value="tab1">Tab 1</TabsTrigger>
          <TabsTrigger value="tab2">Tab 2</TabsTrigger>
        </TabsList>
        <TabsContent value="tab1" className="mt-4">
          <ExistingPage embedded />
        </TabsContent>
      </Tabs>
    </div>
  );
}
```

## Navigation Structure (Phase 176)

The customer sidebar uses a flat layout with 3 section labels (no collapsible groups):

- **Home** — Landing page with fleet health KPIs, quick actions, recent alerts
- **Monitoring** — Dashboard, Alerts (hub), Analytics (hub)
- **Fleet** — Getting Started*, Devices, Sites, Templates, Fleet Map, Device Groups, Updates (hub)
- **Settings** — Notifications (hub), Team (hub), Billing, Integrations

(\* conditional — hidden when dismissed)

Old standalone routes redirect to their hub page with the appropriate `?tab=` parameter.
```

#### Update "Prohibited Patterns" section

Add:
```markdown
- Standalone sidebar items for pages that belong in a hub (use the hub's tab instead)
- Rendering PageHeader when `embedded` prop is true (use conditional rendering)
```

---

## 2. `docs/features/device-management.md`

### Frontmatter

- Set `last-verified: 2026-02-19`
- Add `176` to the `phases` array

### Content Changes

No content changes needed — the device management features themselves are unchanged. The navigation restructure just moves where they appear in the sidebar.

---

## 3. `docs/index.md`

### Frontmatter

- Set `last-verified: 2026-02-19`
- Add `176` to the `phases` array

### Content Changes

Add to the feature list (if not already present):
- "Home landing page with fleet health overview"
- "Hub pages: Alerts, Analytics, Updates, Notifications, Team"
- "Flat sidebar navigation with section labels"

---

## 4. `docs/services/ui-iot.md`

### Frontmatter

- Set `last-verified: 2026-02-19`
- Add `176` to the `phases` array

### Content Changes

Note the new frontend routes:
- `/home` — Home landing page
- `/updates` — Updates hub (replaces `/ota/campaigns` and `/ota/firmware`)
- `/team` — Team hub (replaces `/users` and `/roles`)
- Redirects from old routes to hub pages

---

## Verification

- All four docs have `last-verified: 2026-02-19` and `176` in their `phases` array
- `docs/development/frontend.md` documents the hub page pattern, `embedded` prop convention, and new navigation structure
- No stale information in updated sections
