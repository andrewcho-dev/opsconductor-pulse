# Phase 154 — MVNO Carrier Integration: Frontend

## Overview

Phase 153 built the backend carrier service, routes, and sync worker. This phase adds the frontend UI for:

1. **Carrier integration setup** — Configure carrier API credentials (settings page)
2. **Device carrier diagnostics panel** — Live status, usage, network diagnostics on device detail
3. **Remote action buttons** — Activate, suspend, deactivate SIM; reboot device
4. **Carrier link management** — Link devices to carrier integrations

## Execution Order

1. `001-carrier-api-types.md` — Frontend API functions + types for carrier endpoints
2. `002-carrier-settings-page.md` — Settings page for managing carrier integrations
3. `003-carrier-diagnostics-panel.md` — Device detail panel for carrier status, usage, diagnostics
4. `004-carrier-actions.md` — Remote action buttons with confirmation dialogs
