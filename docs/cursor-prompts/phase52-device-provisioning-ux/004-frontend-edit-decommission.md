# Prompt 004 — Frontend: Edit Device + Decommission

Read `frontend/src/features/devices/DeviceListPage.tsx` fully.

## Create `frontend/src/features/devices/EditDeviceModal.tsx`

A modal pre-populated with current device values:

Fields:
- **Device Name** (text input, pre-filled)
- **Site** (select or text, pre-filled)
- **Tags** (comma-separated, pre-filled from array)

On submit: calls `PATCH /customer/devices/{id}` with changed fields only.
On success: closes modal, refetches device list.

## Add Edit and Decommission Actions to DeviceListPage

In the device list table/card, add a row action menu (3-dot or kebab menu) with:
- **Edit** — opens EditDeviceModal
- **Decommission** — shows confirmation dialog ("Are you sure you want to decommission {name}?"), then calls `PATCH /customer/devices/{id}/decommission`

After decommission: device disappears from list (since API excludes decommissioned by default).

## Add API functions in `devices.ts`

```typescript
export async function updateDevice(deviceId: string, updates: Partial<{
  name: string;
  site_id: string;
  tags: string[];
}>): Promise<void> {
  await apiFetch(`/customer/devices/${deviceId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  });
}

export async function decommissionDevice(deviceId: string): Promise<void> {
  await apiFetch(`/customer/devices/${deviceId}/decommission`, { method: 'PATCH' });
}
```

## Acceptance Criteria

- [ ] EditDeviceModal.tsx exists, pre-filled with current values
- [ ] Row action menu with Edit and Decommission options
- [ ] Decommission requires confirmation dialog
- [ ] After decommission, device removed from list
- [ ] `npm run build` passes
