# Phase 151 — Frontend Sensor Management UI

## Overview

Phase 150 created the backend API for sensors, connections, and device health. This phase builds the frontend UI to manage sensors on devices, view connection info, and display platform health diagnostics.

## Architecture

The device detail page uses a **vertical panel stack** (NOT tabs). Each feature is a self-contained panel component added to `DeviceDetailPage.tsx`. We follow this same pattern.

## Execution Order

1. `001-sensor-api-types.md` — Frontend API functions + TypeScript types for sensors, connections, health
2. `002-sensors-panel.md` — `DeviceSensorsPanel.tsx` — sensor list, add, edit, delete on device detail page
3. `003-connection-panel.md` — `DeviceConnectionPanel.tsx` — cellular connection info and edit
4. `004-health-panel.md` — `DeviceHealthPanel.tsx` — platform diagnostics (signal, battery, CPU, GPS)
5. `005-sensor-list-page.md` — Cross-device sensor list page at `/sensors`
6. `006-sidebar-and-routes.md` — Add "Sensors" to sidebar nav + route registration

## Patterns to Match

- Panels: `<div className="rounded-md border border-border p-3 space-y-3">`
- Data: `useQuery` with `queryKey: ["resource", deviceId]`
- Mutations: `useMutation` → `invalidateQueries` → `toast.success/error`
- Tables: `DataTable` from `@/components/ui/data-table` with `ColumnDef`
- Dialogs: `AlertDialog` from shadcn/ui
- API: `apiGet`, `apiPost`, `apiPut`, `apiDelete` from `@/services/api/client`
- Errors: `toast.error(getErrorMessage(err))`
