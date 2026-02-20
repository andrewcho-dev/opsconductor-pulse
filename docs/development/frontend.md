---
last-verified: 2026-02-20
sources:
  - frontend/package.json
  - frontend/vite.config.ts
  - frontend/src/app/
  - frontend/src/components/
  - frontend/src/features/
  - frontend/src/features/templates/
  - frontend/src/features/fleet/GettingStartedPage.tsx
  - frontend/src/index.css
  - frontend/src/components/shared/KpiCard.tsx
  - frontend/src/components/shared/illustrations.tsx
  - frontend/src/features/home/HomePage.tsx
  - frontend/src/features/alerts/AlertsHubPage.tsx
  - frontend/src/components/layout/SettingsLayout.tsx
  - frontend/src/features/fleet/ToolsHubPage.tsx
  - frontend/src/features/fleet/ConnectionGuidePage.tsx
  - frontend/src/features/fleet/MqttTestClientPage.tsx
  - frontend/src/features/devices/DeviceDetailPage.tsx
  - frontend/src/features/devices/DeviceSensorsDataTab.tsx
  - frontend/src/features/devices/DeviceTransportTab.tsx
  - frontend/src/features/devices/DeviceHealthTab.tsx
  - frontend/src/features/devices/DeviceTwinCommandsTab.tsx
  - frontend/src/features/devices/DeviceSecurityTab.tsx
  - frontend/src/hooks/
  - frontend/src/services/
  - frontend/src/services/api/templates.ts
  - frontend/src/services/api/types.ts
  - frontend/src/stores/
phases: [17, 18, 19, 20, 21, 22, 119, 124, 135, 136, 142, 143, 144, 145, 146, 147, 148, 170, 171, 173, 174, 175, 176, 177, 178, 179]
---

# Frontend

> React + TypeScript + Vite application architecture and conventions.

## Technology Stack

From `frontend/package.json`:

- React + TypeScript (Vite, ESM)
- TailwindCSS + shadcn/ui component conventions (Radix primitives)
- Charts: ECharts + uPlot
- Server state: TanStack Query
- Client state: Zustand (live data)
- Auth: keycloak-js (OIDC/PKCE)
- Forms: react-hook-form + zod
- Routing: react-router-dom
- Testing: Vitest + Testing Library

## Directory Structure

`frontend/src/`:

- `app/` — router, providers, shell/layout
- `components/` — shared components (dialogs, datatables, shadcn/ui wrappers)
- `features/` — feature modules (one directory per feature area)
- `hooks/` — query hooks and utilities
- `services/` — API client, auth, per-domain API modules
- `stores/` — Zustand stores (WebSocket and UI state)
- `lib/` — chart wrappers, tokens, helpers

## Feature Modules

Top-level feature areas under `frontend/src/features/` include (non-exhaustive):

- `dashboard/` — dashboards and widget builder
- `devices/` — device list/detail, provisioning wizard, import, tokens, twin, commands (Phase 171: tabbed device detail)
- `alerts/` — alert inbox and rule dialogs
- `escalation/` — escalation policies UI
- `fleet/` — fleet-level pages (Getting Started onboarding guide, Tools hub with Connection Guide + MQTT Test Client)
- `notifications/` — channels and routing rules UI
- `oncall/` — schedules, layers, overrides, timeline
- `reports/` — reports and export UI
- `metrics/` — metric catalog, mappings, normalized metrics
- `ota/` — firmware versions and OTA campaigns
- `sites/` — site pages
- `subscription/` — subscription pages and renewal flows
- `templates/` — device template management (list + detail tabs)
- `settings/` — profile/org/billing settings pages
- `operator/` — operator dashboards, tenants, users, subscriptions, NOC views
- `messaging/` — dead-letter/replay tooling
- `map/` — fleet map
- `roles/` — roles/permissions UI
- `users/` — tenant user management UI

## Component Patterns

### DataTable

List views use a standardized DataTable pattern (Phase 135) for:

- column definitions
- sorting/filtering/pagination
- consistent empty/loading states

### Form Validation

Forms use:

- `react-hook-form` for state and submission
- `zod` schemas (Phase 136) for validation

## Design System

Phases 143–144 establish a baseline visual system to keep the UI consistent and readable in a data-dense console.

- Spacing: AppShell `<main>` uses `px-6 py-4`; page wrappers use `space-y-4`; card grids use `gap-3`; cards default to `py-3 px-3` with `gap-2` (see `components/ui/card.tsx`); modal containers typically use `p-4 ... space-y-3`.
- Viewport/framing: AppShell is viewport-contained (`h-screen overflow-hidden`) so only `<main>` scrolls; footer (`AppFooter`, `h-7`) frames the bottom and shows version + year.
- Typography hierarchy:

| Role | Tailwind |
|------|----------|
| Page title | `text-lg font-semibold` |
| Section heading | `text-sm font-semibold uppercase tracking-wide text-muted-foreground` |
| Card title | `text-sm font-semibold` (default; no size overrides) |
| KPI number | `text-2xl font-semibold` (universal) |
| KPI label / caption | `text-xs text-muted-foreground` |
| Body | `text-sm` |
| Modal/dialog title | `text-base font-semibold` |

- Weight rule: use `font-semibold` for emphasis; avoid `font-bold` (exceptions: 404 and NOC label).
- Shapes: cards/modals use `rounded-lg`; buttons/inputs/badges use `rounded-md`; `rounded-full` only for semantically circular elements (status dots, switches, radio items, progress bars, stepper circles, avatars).
- Empty states: cap empty/loading padding at `py-8`; prefer the shared `EmptyState` component.
- Minimum readable size: `text-xs` is reserved for timestamps/badges/keyboard hints; do not use `text-[10px]` or smaller.
- Cards/backgrounds/status colors: border-based containment (no shadow); light mode uses a light gray page background with white cards (tokens in `src/index.css`); use semantic status token utilities (e.g. `text-status-online`, `bg-status-critical`), not Tailwind color literals.

## Color System (Phase 175)

The application uses a violet/purple primary color (`--primary: 262 83% 58%` in light mode, `262 83% 72%` in dark mode). All semantic tokens (ring, sidebar-primary, chart-1) derive from this primary.

Status colors remain independent of the primary: `--status-online` (green), `--status-stale` (amber), `--status-offline` (gray), `--status-critical` (red).

Color tokens are defined in `frontend/src/index.css` using CSS custom properties consumed by Tailwind v4's `@theme inline` block.

## Sidebar (Phase 175)

The sidebar uses shadcn/ui's `collapsible="icon"` mode:

- Expanded: full-width (16rem) with text labels
- Collapsed: icon-only strip (3rem) with hover tooltips
- Toggle: Cmd+B keyboard shortcut, SidebarTrigger button, or SidebarRail drag edge
- State persists via cookie (`sidebar_state`)

All `SidebarMenuButton` instances must include the `tooltip` prop for accessible icon-mode behavior.

## Header (Phase 175)

The AppHeader renders a compact (h-12) top bar:

- Left: SidebarTrigger + auto-derived breadcrumbs (from URL path)
- Right: Search (Cmd+K) + ConnectionStatus + Notification bell (alert count badge) + User avatar dropdown

The user avatar dropdown contains: Profile, Organization, Theme toggle, and Log out.

Breadcrumbs are no longer rendered by `PageHeader` — they are auto-derived in the header from the URL path.

## Shared Components (Phase 175)

New shared components:

- `components/ui/progress.tsx` — Radix Progress bar (used for quota/usage visualization)
- `components/ui/avatar.tsx` — Radix Avatar with fallback initials
- `components/shared/KpiCard.tsx` — KPI display card: label + big number + optional progress bar + optional description
- `components/shared/illustrations.tsx` — SVG illustration components (IllustrationEmpty, IllustrationSetup, IllustrationError, IllustrationNotFound)

The `EmptyState` component now renders an SVG illustration by default instead of a plain icon.

## Tab Conventions (Phase 175)

- `variant="line"` (underline with primary-colored active indicator): Use for hub page navigation tabs
- `variant="default"` (pill/muted background): Use for filter toggles and small control groups

Hub pages (Alerts, Analytics, Updates, etc.) should use `variant="line"` for their tab navigation.

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
| Tools | `/fleet/tools` | Connection Guide, MQTT Test Client |

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

## MQTT Test Client (Phase 178)

The MQTT Test Client (`/fleet/tools?tab=mqtt`) is a browser-based MQTT client using the `mqtt` npm package (mqtt.js). It connects via WebSocket to the EMQX broker.

Key implementation details:

- Connects to `ws://localhost:9001/mqtt` by default (EMQX WebSocket port)
- Manual credential entry: broker URL, client ID, password
- No auto-reconnect (`reconnectPeriod: 0`) — intentional for a debugging tool
- Message buffer capped at 200 messages
- Import: `import mqtt from "mqtt"` (Vite handles CJS → ESM)

## Navigation Structure (Phase 176 + 177)

The customer sidebar uses a flat layout with 3 section labels (no collapsible groups):

- **Home** — Landing page with fleet health KPIs, quick actions, recent alerts
- **Monitoring** — Dashboard, Alerts (hub), Analytics (hub)
- **Fleet** — Getting Started*, Devices, Sites, Templates, Fleet Map, Device Groups, Updates (hub), Tools (hub)
- **Settings** — Single link to `/settings` page with internal subcategory navigation

(\* conditional — hidden when dismissed)

Old standalone routes redirect to their hub page with the appropriate `?tab=` parameter.

## Settings Page (Phase 177)

The Settings page (`/settings`) uses a dedicated `SettingsLayout` component with a two-column layout:

- **Left nav** (200px): links organized under subcategory labels
- **Right content** (flex-1): active section rendered via `<Outlet />`

### Subcategories

| Category | Section | Route | Content |
|----------|---------|-------|---------|
| Account | General | `/settings/general` | Organization settings |
| Account | Billing | `/settings/billing` | Billing + subscription |
| Configuration | Notifications | `/settings/notifications` | Notifications hub (Channels/Delivery/Dead Letter tabs) |
| Configuration | Integrations | `/settings/integrations` | Carrier integrations |
| Access Control | Team | `/settings/access` | Team hub (Members/Roles tabs, requires `users.read`) |
| Personal | Profile | `/settings/profile` | Personal settings |

The SettingsLayout handles permission-based visibility: the "Team" nav item only appears for users with `users.read` permission.

Hub pages (Notifications, Team) render with `embedded` mode inside the Settings layout — they skip their own `PageHeader` but keep their tab navigation.

## UI Pattern Conventions

Phase 145 standardizes UI usage patterns across the app. These are conventions (how components are used), not a restyling.

## Device Detail Tabs (Phase 171)

The primary customer device detail page (`features/devices/DeviceDetailPage.tsx`) is structured as a 6-tab layout with tab-specific components:

- `DeviceSensorsDataTab.tsx` (modules + sensors + telemetry charts)
- `DeviceTransportTab.tsx` (protocol/connectivity + carrier linking)
- `DeviceHealthTab.tsx` (health + uptime)
- `DeviceTwinCommandsTab.tsx` (twin + commands)
- `DeviceSecurityTab.tsx` (API tokens + certificates)

Deprecated, duplicate, or reorganized components removed in Phase 171:

- `EditDeviceModal.tsx`
- `DeviceConnectionPanel.tsx`
- `DeviceCarrierPanel.tsx`
- `DeviceConnectivityPanel.tsx`

### Page Header Actions

- All pages MUST use the shared `<PageHeader>` component.
- Primary create action: `<Button>` with `Plus` icon + `"Add {Noun}"` label, placed in `PageHeader` `action`.
- Secondary page actions: `<Button variant="outline">` grouped next to the primary action.
- Settings/config actions: gear icon `DropdownMenu` (never a standalone page button).

### Table Row Actions

- 1–2 actions: `<Button variant="ghost" size="sm">` with icon + short label.
- 3+ actions: `MoreHorizontal` `DropdownMenu`, with destructive items after a separator.
- Navigation to detail: put a `<Link>` on the name/ID column text; do not add a separate View button.

### Breadcrumbs

- Breadcrumbs are derived from the URL path and rendered in the AppHeader (Phase 175).
- Pages may still pass `breadcrumbs` to `PageHeader` for backward compatibility, but they are not rendered.

### Modals & Dialogs

- All modals use Shadcn `<Dialog>`; no custom `<div className="fixed inset-0">` overlays.
- Dialog props: `open` + `onOpenChange` (avoid `onClose`, `isOpen`, etc).
- State naming:
  - `const [open, setOpen] = useState(false)` for simple boolean open state
  - `const [editing, setEditing] = useState<T | null>(null)` for compound edit state
- All form modals should use `useFormDirtyGuard` to protect against losing unsaved changes.
- Destructive confirms: use `<AlertDialog>`; never `window.confirm()`.

### Prohibited Patterns

- Raw `<button>` elements (use `<Button>`).
- Raw `<select>` elements (use shadcn `Select` + `SelectTrigger` + `SelectContent` + `SelectItem`).
- Raw `<input type="checkbox">` elements (use `Switch` for boolean toggles, `Checkbox` for multi-select lists).
- Custom div overlays for modals (use `<Dialog>`).
- `window.confirm()` / `confirm()` (use `<AlertDialog>`).
- Custom page header layouts (use `<PageHeader>`).
- Standalone "Back" buttons (use breadcrumbs).
- "New" / "Create" verbs in primary create actions (use `"Add {Noun}"`).
- Breadcrumbs in PageHeader (breadcrumbs are auto-derived in the AppHeader from URL).
- Standalone sidebar items for pages that belong in a hub (use the hub's tab instead).
- Rendering PageHeader when `embedded` prop is true (use conditional rendering).

## Form Primitives (Phase 179)

All form controls must use design system components instead of raw HTML elements:

| Need | Component | Import |
|------|-----------|--------|
| Dropdown / picker | `Select` + `SelectTrigger` + `SelectValue` + `SelectContent` + `SelectItem` | `@/components/ui/select` |
| Boolean toggle (on/off) | `Switch` | `@/components/ui/switch` |
| Multi-select list item | `Checkbox` | `@/components/ui/checkbox` |
| Action trigger | `Button` | `@/components/ui/button` |

### Select notes

- `SelectItem value` must be a non-empty string. Use `"all"` or `"none"` as sentinel values.
- For numeric values: `value={String(num)}` and `onValueChange={(v) => setNum(Number(v))}`.
- `SelectTrigger` renders a chevron automatically — do not add one manually.

### Switch vs Checkbox

- **Switch** — Single boolean setting (enabled/disabled, feature flags, retain flag, use TLS). Standard for all on/off controls.
- **Checkbox** — Item in a multi-select list (select devices, groups, metrics) or bulk-select header/row checkboxes.

## Mutation Feedback Conventions

Phase 146 standardizes mutation feedback and error formatting. The goal is zero silent operations: users should always see confirmation on success and a meaningful message on failure.

### Toast Feedback Rules

- Every `useMutation` MUST have both `onSuccess` and `onError` callbacks with toast feedback.
- Import: `import { toast } from "sonner";`
- Success: `toast.success("Noun verbed")` (past tense, concise).
- Error: `toast.error(getErrorMessage(err) || "Failed to verb noun")` (prefer API detail, with generic fallback).
- Import error utility: `import { getErrorMessage } from "@/lib/errors";`
- Keep existing `onSuccess` logic (invalidateQueries, dialog close, state reset) - toast is in addition, not replacement.
- No `console.error()` in feature files - use `toast.error()` instead.

### Error Formatting

- One centralized function: `getErrorMessage()` in `@/lib/errors`.
- Handles: `ApiError` (extracts `body.detail`), standard `Error`, plain objects, unknown.
- Never duplicate error formatting logic in components (no local `formatError()` helpers).

### Modal State Naming

- Simple boolean: `const [open, setOpen] = useState(false)`
- Multiple dialogs: `const [createOpen, setCreateOpen] = useState(false)`
- Compound edit state: `const [editing, setEditing] = useState<T | null>(null)`
- Avoid state names like `show*`, `isOpen`, `visible`, `openCreate`.

### Prohibited Patterns

- Silent mutations (no toast on success or error).
- `console.error()` in feature/page components.
- Duplicated `formatError()` functions - use `getErrorMessage` from `@/lib/errors`.
- `window.confirm()` - use `<AlertDialog>` (Phase 145).
- Inconsistent modal state names (`show`, `isOpen`, `visible`).

## Dashboard Widget System

Phase 147 overhauls the widget system to support responsive sizing, formatting controls, thresholds, visualization switching, and a categorized widget catalog.

### Widget Architecture

- Widgets are defined in `frontend/src/features/dashboard/widgets/widget-registry.ts` with type, label, description, category, default size, min/max size, default config, and a lazy-loaded renderer component.
- Widget config is stored as JSON - new config fields are optional and do not require backend schema migrations.
- `getWidgetRenderer()` resolves the renderer component loader, respecting `display_as` overrides.
- `getWidgetsByCategory()` groups widgets for the Add Widget catalog UI.

### Widget Categories

- Charts - time-series and comparison visualizations (line chart, area chart, bar chart, pie/donut, scatter plot, radar).
- Metrics - single-value displays (KPI tile, stat card with sparkline, gauge with 4 styles).
- Data - tabular/list views (device table, alert feed).
- Fleet Overview - consolidated fleet status (count, donut, health score).

### Widget Config Fields

- Data fields: `metric`, `time_range`, `devices`, `limit`, `max_items`, etc. (widget-type specific).
- Display: `display_as` (overrides visualization type), `display_mode` (fleet widget mode).
- Formatting: `decimal_precision`, `show_title`, `show_legend`, `show_x_axis`, `show_y_axis`, `y_axis_min`, `y_axis_max`.
- Thresholds: `thresholds: [{ value, color, label? }]` - rendered as markLines on charts, color zones on gauges, value coloring on KPI tiles.
- Display sub-types:
  - `gauge_style`: `"arc" | "speedometer" | "ring" | "grade"` - selects gauge visual style
  - `smooth`: boolean - smooth curve interpolation for line/area charts
  - `step`: boolean - step-line interpolation (overrides smooth)
  - `area_fill`: boolean - area fill under line chart
  - `stacked`: boolean - stacked series for bar/area charts
  - `horizontal`: boolean - horizontal bar orientation
- Pie chart fields:
  - `pie_data_source`: `"fleet_status" | "alert_severity"` - data source for pie chart
  - `doughnut`: boolean - donut vs filled pie style
  - `show_labels`: boolean - show percentage labels on slices
- Scatter chart fields:
  - `x_metric`: string - metric for X axis
  - `y_metric`: string - metric for Y axis
- Radar chart fields:
  - `radar_metrics`: string[] - 3-6 metrics for radar axes

### Renderer Rules

- All ECharts renderers MUST use `style={{ width: "100%", height: "100%" }}` (no fixed pixel heights).
- All renderers MUST handle missing config fields gracefully with defaults.
- All numeric displays MUST respect `decimal_precision` from config.
- Chart renderers MUST apply `show_legend`, `show_x_axis`, `show_y_axis` and `y_axis_min`/`y_axis_max` to ECharts options.
- New renderers MUST be wrapped in `min-h-[100px]` or `min-h-[120px]` to prevent collapse in small widgets.
- Gauge renderers MUST support `gauge_style` config and render all 4 styles via ECharts gauge options.
- Chart renderers that support sub-types (smooth, step, stacked, horizontal) MUST default to existing behavior when config fields are absent.
- Stat card renderers MUST show sparkline only when historical data is available.
- New visualization types for existing data shapes should use `display_as` switching, not new widget types.
- New visualization types with unique data needs (multi-metric, two-axis) should be standalone widget types.

### Prohibited Patterns

- Fixed pixel heights on ECharts containers (use percentage-based sizing).
- Hardcoded decimal places (use `config.decimal_precision`).
- Creating new widget types for variations of existing data (use `display_as` or `display_mode`).
- Skipping threshold support in new numeric renderers.
- Creating separate widget types for chart sub-types (use config toggles: smooth, step, stacked, horizontal).
- Hardcoding gauge style (use `config.gauge_style` to determine rendering).
- Separate renderers for pie vs donut (use `config.doughnut` toggle).

## State Management

### Server State (TanStack Query)

- API data fetching, caching, invalidation

### Client State (Zustand)

- Live telemetry/alerts and UI state that benefits from a lightweight store

## Development

```bash
cd frontend
npm install
npm run dev
npm run build
npx tsc --noEmit
```

Vite config notes:

- Base path: `/app/`
- Dev proxy forwards `/api`, `/customer`, and `/operator` paths to the backend.

## See Also

- [Getting Started](getting-started.md)
- [API Overview](../api/overview.md)
- [Conventions](conventions.md)

