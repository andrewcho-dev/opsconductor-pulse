# Phase 52: Device Provisioning UX

## What Exists

- `provision_api` service handles device registration (issues MQTT credentials, writes device record)
- Devices are currently provisioned via direct API calls (no UI)
- Fleet list page shows devices read-only
- No "add device" or "edit device" UI workflow

## What This Phase Adds

1. **Add Device modal** — form to register a new device (name, site, tags, device_type). Calls `POST /provision/device`.
2. **Edit Device modal** — update device metadata (name, tags, site). Calls `PATCH /customer/devices/{id}`.
3. **Decommission Device** — soft-delete / mark device inactive. `PATCH /customer/devices/{id}/decommission`.
4. **Credential download** — after provisioning, show MQTT credentials (client_id, password, broker URL) in a one-time modal with a "Download .env" button.
5. **Backend PATCH endpoints** — update device metadata + decommission.

## Out of Scope (monitoring-first)

- Device twin / desired state
- Remote commands
- OTA firmware update

## Execution Order

| Prompt | Description |
|--------|-------------|
| 001 | Backend: PATCH /customer/devices/{id} (update metadata) |
| 002 | Backend: PATCH /customer/devices/{id}/decommission |
| 003 | Frontend: Add Device modal |
| 004 | Frontend: Edit Device + Decommission |
| 005 | Frontend: Credential download modal |
| 006 | Unit tests |
| 007 | Verify |

## Key Files

- `services/ui_iot/routes/customer.py` — prompts 001, 002
- `services/provision_api/app.py` — referenced for POST /provision/device signature
- `frontend/src/features/devices/DeviceListPage.tsx` — prompts 003, 004
- `frontend/src/features/devices/AddDeviceModal.tsx` — new, prompt 003
- `frontend/src/features/devices/EditDeviceModal.tsx` — new, prompt 004
- `frontend/src/features/devices/CredentialModal.tsx` — new, prompt 005
- `frontend/src/services/api/devices.ts` — prompts 003–005
