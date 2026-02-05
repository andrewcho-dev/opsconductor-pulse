# Phase 22: SPA Cutover — Remove Legacy Jinja Templates

## Overview

The React SPA (Phases 18-21) is feature-complete with all 15 routes implemented. However, the backend still serves the old Jinja2 template pages at `/customer/*` and `/operator/*`, and the root `/` redirect sends users to the old templates instead of the SPA.

This phase removes the old template UI entirely, making the React SPA the only frontend.

## Current State

- **SPA location**: Served at `/app/*` from `frontend/dist` mounted at `/app/spa`
- **Old templates**: Served at `/customer/dashboard`, `/operator/dashboard`, etc.
- **Root `/`**: Redirects to old template routes based on role
- **OAuth callback**: Redirects to old template routes after login
- **Dual routes**: Some routes (`/customer/devices`, `/customer/alerts`, etc.) serve both HTML templates and JSON via a `format` query param
- **SPA auth**: Uses keycloak-js directly (does NOT use `/login`, `/callback`, or `pulse_session` cookies)

## Architecture After Cutover

```
GET /                  →  302 redirect to /app/
GET /app/*             →  React SPA (index.html + assets)
GET /api/v2/*          →  JSON API (devices, alerts, telemetry, WebSocket)
GET /customer/*        →  JSON API only (integrations, alert-rules CRUD)
GET /operator/*        →  JSON API only (devices, alerts, quarantine, audit-log, settings)
GET /login             →  (kept, unused by SPA but harmless)
GET /callback          →  (kept, unused by SPA but harmless)
GET /logout            →  (kept, unused by SPA but harmless)
```

## Key Points

- The SPA uses **keycloak-js** for auth, not the server-side OAuth flow. The `/login`, `/callback`, `/logout` routes are unused by the SPA but kept for backward compatibility.
- Routes like `/customer/devices` currently serve HTML by default and JSON when `?format=json` is passed. After cutover, they become JSON-only (remove the `format` param and always return JSON).
- The SPA calls `/api/v2/*` for device/alert reads and `/customer/*` for mutations (integrations, alert-rules CRUD). All these JSON routes stay.
- Template helper functions (`sparkline_points`, `to_float`, `to_int`, `redact_url`) are only used for HTML rendering and can be removed.
- Tests that assert `text/html` responses from template routes must be removed or updated.

## Task Order

Execute tasks 1-4 in order. Each task builds on the previous one.

| # | File | Description |
|---|------|-------------|
| 1 | `001-backend-spa-cutover.md` | Change root redirect, remove template routes, convert dual routes to JSON-only |
| 2 | `002-remove-legacy-files.md` | Delete template HTML files, static JS/CSS, update Dockerfile |
| 3 | `003-fix-tests.md` | Update conftest and test files for removed routes |
| 4 | `004-deploy-and-docs.md` | Update Vite proxy, rebuild frontend, rebuild Docker, add Phase 22 docs |
