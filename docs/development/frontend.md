---
last-verified: 2026-02-17
sources:
  - frontend/package.json
  - frontend/vite.config.ts
  - frontend/src/app/
  - frontend/src/components/
  - frontend/src/features/
  - frontend/src/hooks/
  - frontend/src/services/
  - frontend/src/stores/
phases: [17, 18, 19, 20, 21, 22, 119, 124, 135, 136, 142]
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

