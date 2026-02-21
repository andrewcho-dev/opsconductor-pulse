# Prompt 003 — Frontend: Add Device Modal

Read `frontend/src/features/devices/DeviceListPage.tsx` fully.
Read `frontend/src/services/api/devices.ts` and `frontend/src/services/api/` for API client patterns.
Read `services/provision_api/app.py` to understand the `POST /provision/device` request/response shape.

## Create `frontend/src/features/devices/AddDeviceModal.tsx`

A modal with a form:

Fields:
- **Device Name** (required, text input)
- **Device Type** (required, select — read existing device_type values or use free text)
- **Site** (optional, select from available sites or free text)
- **Tags** (optional, comma-separated text input parsed into array)

On submit:
1. Calls `POST /provision/device` with `{ name, device_type, site_id, tags }`
2. On success: closes form fields, shows CredentialModal (prompt 005) with returned credentials
3. On error: shows inline error message

Use existing modal/dialog UI patterns from the codebase.

## Wire into DeviceListPage

- Add "Add Device" button (top-right of page header)
- When clicked, opens AddDeviceModal
- After successful add: refetch device list

## Add API function in `devices.ts`

```typescript
export interface ProvisionDeviceRequest {
  name: string;
  device_type: string;
  site_id?: string;
  tags?: string[];
}

export interface ProvisionDeviceResponse {
  device_id: string;
  client_id: string;
  password: string;
  broker_url: string;
}

export async function provisionDevice(req: ProvisionDeviceRequest): Promise<ProvisionDeviceResponse> {
  return apiFetch('/provision/device', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
}
```

## Acceptance Criteria

- [ ] AddDeviceModal.tsx exists with name/device_type/site/tags fields
- [ ] "Add Device" button in DeviceListPage opens modal
- [ ] On success, credential modal shown
- [ ] On success, device list refetches
- [ ] `npm run build` passes
