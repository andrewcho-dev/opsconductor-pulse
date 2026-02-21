# Prompt 005 — Frontend: Device Groups Page

Read `frontend/src/features/devices/DeviceListPage.tsx` and `frontend/src/features/sites/SitesPage.tsx` for layout patterns.

## Create `frontend/src/features/devices/DeviceGroupsPage.tsx`

Route: `/device-groups`

Page layout:
- List of groups as cards or table rows:
  - Group name
  - Description
  - Member count
  - Actions: "View / Edit", "Delete"
- "Create Group" button (top right)

## Create Group Modal

Fields:
- Group Name (required)
- Description (optional)

## Group Detail View (inline or separate page `/device-groups/:groupId`)

Shows:
- Group name + description (editable inline)
- Member devices list (device_id, name, status)
- "Add Device" button → dropdown/search of tenant devices → PUT to add
- "Remove" button per device → DELETE to remove

## Add API Functions in `frontend/src/services/api/devices.ts`

```typescript
export interface DeviceGroup {
  group_id: string;
  name: string;
  description: string | null;
  member_count: number;
  created_at: string;
}

export async function fetchDeviceGroups(): Promise<{ groups: DeviceGroup[]; total: number }> {
  return apiFetch('/customer/device-groups');
}

export async function createDeviceGroup(data: { name: string; description?: string }): Promise<DeviceGroup> {
  return apiFetch('/customer/device-groups', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export async function deleteDeviceGroup(groupId: string): Promise<void> {
  await apiFetch(`/customer/device-groups/${groupId}`, { method: 'DELETE' });
}

export async function fetchGroupMembers(groupId: string) {
  return apiFetch(`/customer/device-groups/${groupId}/devices`);
}

export async function addGroupMember(groupId: string, deviceId: string): Promise<void> {
  await apiFetch(`/customer/device-groups/${groupId}/devices/${deviceId}`, { method: 'PUT' });
}

export async function removeGroupMember(groupId: string, deviceId: string): Promise<void> {
  await apiFetch(`/customer/device-groups/${groupId}/devices/${deviceId}`, { method: 'DELETE' });
}
```

## Navigation

Add "Device Groups" link to sidebar under Devices.
Add `/device-groups` and `/device-groups/:groupId` routes.

## Acceptance Criteria

- [ ] DeviceGroupsPage.tsx at /device-groups
- [ ] Create/delete group modals
- [ ] Member list with add/remove
- [ ] API functions in devices.ts
- [ ] Nav link + routes registered
- [ ] `npm run build` passes
