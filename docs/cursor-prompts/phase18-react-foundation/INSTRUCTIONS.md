# Phase 18: React Foundation + App Shell

## Overview

Transform OpsConductor-Pulse from server-rendered Jinja2 templates to a React SPA with Tailwind CSS, shadcn/ui, and modern state management. This phase establishes the project scaffold, authentication, app shell, API client, and Docker deployment.

The existing Jinja2 UI at `/customer/*` and `/operator/*` remains untouched. The new React app mounts at `/app/*`. Both coexist during migration.

## Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Framework | React 19 + TypeScript | Component model, render lifecycle |
| Build | Vite | Dev server, bundling, proxy |
| UI | Tailwind CSS + shadcn/ui | Styling, component library |
| Routing | React Router v6 | Client-side navigation |
| Server State | TanStack Query (React Query) | API data fetching, caching |
| Client State | Zustand | Device/alert stores (Phase 19) |
| Auth | keycloak-js | OIDC PKCE login, token management |
| Charts | ECharts + uPlot | Visualization (Phase 20) |

## Architecture

### Auth Flow
React SPA authenticates directly with Keycloak via `keycloak-js` (PKCE S256). JWT stored in memory (NOT localStorage). Sent as `Authorization: Bearer` header on all API calls. No dependency on `pulse_session` httpOnly cookie — that's for the legacy Jinja2 UI only.

### API Integration
All data fetched from existing `/api/v2/*` REST endpoints via TanStack Query. Vite dev server proxies `/api/*` to FastAPI at `localhost:8080`. In Docker, same-origin (FastAPI serves both API and React build).

### Directory Layout
New `frontend/` directory at project root, alongside existing `services/`. Not inside `services/` — this is a separate build artifact.

```
simcloud/
├── frontend/          ← NEW (React SPA)
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── vite.config.ts
├── services/          ← EXISTING (unchanged)
│   ├── ui_iot/
│   ├── ingest_iot/
│   └── ...
├── compose/
└── docs/
```

### Deployment Bridge
In Docker, a multi-stage build compiles the React app, then copies the `dist/` output into the UI service container. FastAPI serves the build at `/app/` with a catch-all route for client-side routing. Both `/customer/*` (legacy) and `/app/*` (new) are accessible simultaneously.

---

## Task Sequence

| # | File | Description | Dependencies |
|---|------|-------------|--------------|
| 1 | `001-vite-react-scaffold.md` | Vite + React + TypeScript + Tailwind + shadcn/ui project | None |
| 2 | `002-auth-integration.md` | Keycloak auth, AuthProvider, ProtectedRoute, API client | #1 |
| 3 | `003-app-shell.md` | AppShell, Sidebar, Header, React Router, page stubs, shared components | #2 |
| 4 | `004-api-client-queries.md` | TanStack Query, API services, Dashboard + Device List + Alert List pages | #3 |
| 5 | `005-docker-deployment.md` | Docker multi-stage build, FastAPI SPA mount, docker-compose update | #1-#4 |

---

## Backend Reference (existing, no changes needed)

### API v2 Endpoints

| Method | Path | Response Shape |
|--------|------|---------------|
| GET | `/api/v2/health` | `{ status }` |
| GET | `/api/v2/devices?limit=N&offset=N` | `{ tenant_id, devices[], count, limit, offset }` |
| GET | `/api/v2/devices/{device_id}` | `{ tenant_id, device }` |
| GET | `/api/v2/devices/{id}/telemetry?start=&end=&limit=N` | `{ tenant_id, device_id, telemetry[], count }` |
| GET | `/api/v2/devices/{id}/telemetry/latest?count=N` | `{ tenant_id, device_id, telemetry[], count }` |
| GET | `/api/v2/alerts?status=OPEN&alert_type=&limit=N&offset=N` | `{ tenant_id, alerts[], count, status, ... }` |
| GET | `/api/v2/alerts/{alert_id}` | `{ tenant_id, alert }` |
| GET | `/api/v2/alert-rules?limit=N` | `{ tenant_id, rules[], count }` |
| GET | `/api/v2/alert-rules/{rule_id}` | `{ tenant_id, rule }` |
| WS | `/api/v2/ws?token=JWT` | Live telemetry + alerts (JSON messages) |

### Keycloak Configuration

| Setting | Value |
|---------|-------|
| Realm | `pulse` |
| Client ID | `pulse-ui` |
| Client type | Public (PKCE S256 required) |
| Keycloak URL (browser) | `http://localhost:8180` |
| Access token lifespan | 900s (15 min) |
| JWT audience claim | `pulse-ui` |
| Custom JWT claims | `tenant_id`, `role` |
| Roles | `customer_viewer`, `customer_admin`, `operator`, `operator_admin` |
| Redirect URIs | `*` (wildcard, works for any dev port) |

### Current Navigation Links (to replicate in sidebar)

Customer pages:
- Dashboard → `/customer/dashboard`
- Devices → `/customer/devices`
- Alerts → `/customer/alerts`
- Alert Rules → `/customer/alert-rules`
- Webhooks → `/customer/webhooks`
- SNMP → `/customer/snmp-integrations`
- Email → `/customer/email-integrations`
- MQTT → `/customer/mqtt-integrations`

---

## Exit Criteria

- [ ] React app builds successfully (`npm run build`)
- [ ] Vite dev server starts (`npm run dev` on port 5173)
- [ ] Keycloak PKCE login/logout works from React app
- [ ] Sidebar navigation between all page stubs
- [ ] Device list page loads real data from API v2
- [ ] Dashboard page shows stat cards with real device counts
- [ ] Alert list page loads real alerts from API v2
- [ ] Docker compose builds and serves React app at `/app/`
- [ ] Legacy Jinja2 UI still works at `/customer/` and `/operator/`
- [ ] All existing Python unit tests pass (395 tests)

---

## Dark Theme Color Reference

Carry forward the existing OpsConductor dark theme:

| Token | Hex | Usage |
|-------|-----|-------|
| Background | `#0a0a1a` | Page background (slightly darker than current) |
| Card | `#1a1a2e` | Cards, sidebar, elevated surfaces |
| Card hover | `#2a2a4e` | Hover states, secondary surfaces |
| Border | `#333333` | All borders |
| Text primary | `#eeeeee` | Primary text |
| Text muted | `#888888` | Secondary/muted text |
| Accent/Primary | `#8ab4f8` | Links, active states, primary buttons |
| Online/Success | `#4caf50` | Online status, success states |
| Stale/Warning | `#ff9800` | Stale status, warnings |
| Critical/Error | `#f44336` | Critical alerts, errors |
| Info | `#64b5f6` | Info badges |
