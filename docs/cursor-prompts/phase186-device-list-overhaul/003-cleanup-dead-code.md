# Task 3: Delete DeviceDetailPane (Dead Code)

## File to Delete

`frontend/src/features/devices/DeviceDetailPane.tsx`

## Why

`DeviceDetailPane` was the right-side panel in the old master-detail split layout. With Task 1 replacing DeviceListPage with a full-width DataTable (row click → navigate to `/devices/:deviceId`), `DeviceDetailPane` is no longer imported or used anywhere.

## Pre-check

Before deleting, verify no remaining imports:

```bash
cd frontend && grep -r "DeviceDetailPane" src/ --include="*.tsx" --include="*.ts"
```

Expected output: only `DeviceDetailPane.tsx` itself (its own definition). If `DeviceListPage.tsx` still imports it, Task 1 was not fully applied — go back and fix.

## Action

Delete the file:

```bash
rm frontend/src/features/devices/DeviceDetailPane.tsx
```

## Sub-components are NOT orphaned

All sub-components that `DeviceDetailPane` imported are also used by `DeviceDetailPage`'s tabs:

| Component | Also used by |
|-----------|-------------|
| `DeviceApiTokensPanel` | `DeviceSecurityTab.tsx` |
| `DeviceUptimePanel` | `DeviceHealthTab.tsx` |
| `DeviceTwinPanel` | `DeviceTwinCommandsTab.tsx` |
| `TelemetryChartsSection` | `DeviceSensorsDataTab.tsx` |

**Do NOT delete any of these files.** Only delete `DeviceDetailPane.tsx`.

## Verification

```bash
cd frontend && npx tsc --noEmit
```

- No TypeScript errors
- No references to `DeviceDetailPane` in any file
- All sub-component files still exist and are used by DeviceDetailPage
