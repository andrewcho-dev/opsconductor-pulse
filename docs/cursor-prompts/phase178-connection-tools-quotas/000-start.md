# Phase 178: Connection Tools + Quota Visualization

## Overview

This phase adds three EMQX-inspired features:

1. **Connection Guide** — A page with language-specific code snippets showing how to connect devices and send telemetry (Python, Node.js, curl, Arduino)
2. **MQTT Test Client** — A browser-based MQTT client for publishing/subscribing to topics to verify device connectivity
3. **Usage/Quota KPIs** — Resource usage visualization on the Home page and Billing settings page using KpiCard + Progress components

Connection Guide and MQTT Test Client are combined into a **Tools hub page** in the Fleet sidebar section (1 new sidebar item with 2 tabs), following the hub page pattern from Phase 176.

## Execution Order

1. `001-connection-guide.md` — Create Connection Guide page component
2. `002-mqtt-test-client.md` — Install mqtt.js + Create MQTT Test Client page component
3. `003-tools-hub.md` — Create Tools hub page with 2 tabs
4. `004-quota-kpis.md` — Add quota/usage KPIs to Home page + refactor Billing page
5. `005-sidebar-routes.md` — Add Tools to sidebar + routes + CommandPalette
6. `006-update-docs.md` — Documentation updates

## Key Design Decisions

- **Tools hub** — Rather than adding 2 sidebar items (Connection Guide + MQTT Test), a single "Tools" link opens a hub page with tabs. This keeps the Fleet section from growing too large.
- **mqtt.js** — The standard browser-compatible MQTT client library. Connects via WebSocket to the EMQX broker (port 9001, path `/mqtt`). Installed as a frontend dependency.
- **Manual credentials** — The MQTT Test Client accepts broker URL, client ID, and password as manual input. Auto-fill from device credentials is a future enhancement (would require a non-rotating read endpoint for device tokens).
- **Entitlements API** — The existing `GET /api/v1/customer/billing/entitlements` returns `usage: Record<string, { current, limit }>` which provides all data needed for quota visualization.
- **KpiCard reuse** — Phase 175's KpiCard component (with built-in Progress bar) is used for quota display, replacing BillingPage's custom progress bar.

## Files Modified/Created Summary

| File | Change |
|------|--------|
| `frontend/src/features/fleet/ConnectionGuidePage.tsx` | **NEW** — Code snippets for device connection |
| `frontend/src/features/fleet/MqttTestClientPage.tsx` | **NEW** — Browser-based MQTT test client |
| `frontend/src/features/fleet/ToolsHubPage.tsx` | **NEW** — Tools hub (2 tabs) |
| `frontend/src/features/home/HomePage.tsx` | Add resource usage KPI section |
| `frontend/src/features/settings/BillingPage.tsx` | Refactor to use KpiCard for usage display |
| `frontend/src/components/layout/AppSidebar.tsx` | Add "Tools" to Fleet section |
| `frontend/src/app/router.tsx` | Add `/fleet/tools` route |
| `frontend/src/components/shared/CommandPalette.tsx` | Add Tools entries |
| `frontend/src/components/layout/AppHeader.tsx` | Add breadcrumb labels |
| `frontend/package.json` | Add `mqtt` dependency |
| `docs/development/frontend.md` | Document MQTT client, tools hub |
| `docs/index.md` | Add features to list |
| `docs/services/ui-iot.md` | Note new routes |

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```

- Connection Guide page renders with 4 language tabs and copy buttons
- MQTT Test Client connects to EMQX broker via WebSocket
- Tools hub page renders with 2 tabs
- Home page shows resource usage KPIs with progress bars
- Billing page uses KpiCard for usage display
- Tools link appears in Fleet sidebar section
