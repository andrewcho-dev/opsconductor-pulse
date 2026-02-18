---
last-verified: 2026-02-18
sources:
  - frontend/package.json
  - frontend/vite.config.ts
  - frontend/src/app/
  - frontend/src/components/
  - frontend/src/features/
  - frontend/src/hooks/
  - frontend/src/services/
  - frontend/src/stores/
phases: [17, 18, 19, 20, 21, 22, 119, 124, 135, 136, 142, 143, 144, 145, 146]
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
- `devices/` — device list/detail, provisioning wizard, import, tokens, twin, commands
- `alerts/` — alert inbox and rule dialogs
- `escalation/` — escalation policies UI
- `notifications/` — channels and routing rules UI
- `oncall/` — schedules, layers, overrides, timeline
- `reports/` — reports and export UI
- `metrics/` — metric catalog, mappings, normalized metrics
- `ota/` — firmware versions and OTA campaigns
- `sites/` — site pages
- `subscription/` — subscription pages and renewal flows
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

- Spacing: AppShell `<main>` uses `p-4`; page wrappers use `space-y-4`; card grids use `gap-3`; cards default to `py-3 px-3` with `gap-2` (see `components/ui/card.tsx`); modal containers typically use `p-4 ... space-y-3`.
- Viewport/framing: AppShell is viewport-contained (`h-screen overflow-hidden`) so only `<main>` scrolls; footer (`AppFooter`, `h-8`) frames the bottom and shows version + year.
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

## UI Pattern Conventions

Phase 145 standardizes UI usage patterns across the app. These are conventions (how components are used), not a restyling.

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

- ALL detail pages MUST provide breadcrumbs via the `PageHeader` `breadcrumbs` prop.
- Format: `[{ label: "Parent", href: "/parent" }, { label: itemName }]`.
- No standalone "Back" buttons; breadcrumbs replace that navigation pattern.

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
- Custom div overlays for modals (use `<Dialog>`).
- `window.confirm()` / `confirm()` (use `<AlertDialog>`).
- Custom page header layouts (use `<PageHeader>`).
- Standalone "Back" buttons (use breadcrumbs).
- "New" / "Create" verbs in primary create actions (use `"Add {Noun}"`).

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

