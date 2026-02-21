# Prompt 003 — Frontend: UptimeBar + DeviceUptimePanel

## Create `frontend/src/components/ui/UptimeBar.tsx`

Props: `{ uptimePct: number; label?: string }`

Renders: a colored progress bar (green >= 99%, yellow >= 95%, red < 95%) with percentage label.

## Create `frontend/src/features/devices/DeviceUptimePanel.tsx`

Props: `{ deviceId: string }`

Display:
- Range selector: 24h / 7d / 30d (tabs or buttons)
- UptimeBar showing current range uptime %
- Stats row: Uptime % | Offline duration | Current status badge (Online/Offline)
- Fetches GET /customer/devices/{id}/uptime?range={range}

## Add API client function in `frontend/src/services/api/devices.ts`

```typescript
export async function getDeviceUptime(deviceId: string, range: '24h' | '7d' | '30d'): Promise<DeviceUptimeStats>

interface DeviceUptimeStats {
  device_id: string;
  range: string;
  uptime_pct: number;
  offline_seconds: number;
  range_seconds: number;
  status: 'online' | 'offline';
}
```

## Wire DeviceUptimePanel into device detail

Add `<DeviceUptimePanel deviceId={device.id} />` in the device detail page/drawer.

## Acceptance Criteria
- [ ] UptimeBar.tsx with color thresholds
- [ ] DeviceUptimePanel.tsx with range selector
- [ ] API client function added
- [ ] `npm run build` passes
