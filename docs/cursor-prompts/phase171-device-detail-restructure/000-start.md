# Phase 171 — Device Detail Restructure

## Goal

Replace the current 12+ scattered panels on DeviceDetailPage with a clean 6-tab layout. Consolidate duplicate modals. Integrate the template/module/transport model into the device detail view.

## Prerequisites

- Phase 169-170 complete (backend endpoints + template frontend)
- Current DeviceDetailPage structure (see `frontend/src/features/devices/DeviceDetailPage.tsx`)
- Current panels: DeviceInfoCard, DeviceMapCard, DevicePlanPanel, DeviceSensorsPanel, DeviceConnectionPanel, DeviceCarrierPanel, DeviceHealthPanel, DeviceApiTokensPanel, DeviceCertificatesTab, DeviceUptimePanel, DeviceTwinPanel, DeviceConnectivityPanel, DeviceCommandPanel, TelemetryChartsSection, MetricGaugesSection

## Current State

The DeviceDetailPage currently renders all panels vertically with a 2-column grid at the top (DeviceInfoCard + DeviceMapCard), then a long list of panels below. This will be restructured into 6 tabs.

## New Tab Structure

| Tab | Contents | Replaces |
|-----|----------|----------|
| 1. Overview | Identity, map, status, quick stats | DeviceInfoCard, DeviceMapCard, DevicePlanPanel |
| 2. Sensors & Data | Module assignment, sensors table, telemetry charts | DeviceSensorsPanel, TelemetryChartsSection, MetricGaugesSection |
| 3. Transport | Transport cards (protocol + connectivity) | DeviceConnectionPanel, DeviceCarrierPanel, DeviceConnectivityPanel |
| 4. Health | Health telemetry charts | DeviceHealthPanel, DeviceUptimePanel |
| 5. Twin & Commands | Device twin + command dispatch | DeviceTwinPanel, DeviceCommandPanel |
| 6. Security | API tokens + certificates | DeviceApiTokensPanel, DeviceCertificatesTab |

## Execution Order

| Step | File | Description |
|------|------|-------------|
| 1 | `001-device-api-types.md` | Update TypeScript types for new response shapes |
| 2 | `002-overview-tab.md` | Overview tab components |
| 3 | `003-sensors-data-tab.md` | Sensors & Data tab (modules + sensors + charts) |
| 4 | `004-transport-tab.md` | Transport tab |
| 5 | `005-health-tab.md` | Health tab |
| 6 | `006-twin-commands-tab.md` | Twin & Commands tab |
| 7 | `007-security-tab.md` | Security tab |
| 8 | `008-cleanup-duplicates.md` | Remove deprecated components |
| 9 | `009-update-docs.md` | Update frontend docs |

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```

Manual:
1. Navigate to device detail page → 6 tabs visible
2. Each tab renders correct content
3. No broken imports or missing components
4. All device data is accessible (nothing lost from old layout)
