# Prompt 002 — Device Detail Pane with Tabs

Read `frontend/src/features/devices/DeviceDetailPage.tsx` and all components it uses
(DeviceApiTokensPanel, DeviceUptimePanel, etc.) before making changes.

## Create `frontend/src/features/devices/DeviceDetailPane.tsx`

Props: `{ deviceId: string }`

A tabbed panel that shows device information without requiring full-page navigation.

### Pane header (always visible):
```
┌────────────────────────────────────────────────┐
│ ● pump-alpha              [Edit] [⋮ more]      │
│   temperature | Site: Building A               │
│   Tags: floor1, zone2                          │
└────────────────────────────────────────────────┘
```
- Large status dot + device name
- Device type + site name
- Tags as small badges
- Edit button → opens EditDeviceModal (existing)
- ⋮ menu → Decommission, View Full Page (links to /devices/:id)

### Tabs:

**Tab 1: Overview**
- Key metrics: last seen time, provision date, device_id (copyable)
- Current telemetry snapshot (latest values from /api/v2/devices/:id)
- Active alerts count with link to Alerts tab

**Tab 2: Telemetry**
- Reuse `TelemetryChartsSection` or equivalent telemetry chart component
  (already built in Phase 57, used in DeviceDetailPage)

**Tab 3: Alerts**
- Compact alert list for this device (filter /customer/alerts by device_id if supported,
  otherwise filter client-side from useAlerts)
- Same ack/close/silence actions as AlertListPage

**Tab 4: Tokens**
- Reuse `DeviceApiTokensPanel` (already built in Phase 75)
  Import from `frontend/src/features/devices/DeviceApiTokensPanel.tsx`

**Tab 5: Uptime**
- Reuse `DeviceUptimePanel` (already built in Phase 78)
  Import from `frontend/src/features/devices/DeviceUptimePanel.tsx`

### Data fetching:
Use the existing `useDevice(deviceId)` hook or fetch from `/api/v2/devices/:id`.
Refetch when `deviceId` prop changes.

## Acceptance Criteria
- [ ] DeviceDetailPane.tsx with pane header + 5 tabs
- [ ] Overview tab shows key device fields
- [ ] Telemetry tab reuses existing chart component
- [ ] Tokens tab reuses DeviceApiTokensPanel
- [ ] Uptime tab reuses DeviceUptimePanel
- [ ] Edit button opens EditDeviceModal
- [ ] `npm run build` passes
