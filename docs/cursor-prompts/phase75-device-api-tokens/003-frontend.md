# Prompt 003 — Frontend: DeviceApiTokensPanel

Read `frontend/src/features/devices/DeviceDetailPage.tsx` (or similar device detail component) to understand the layout pattern.

## Create `frontend/src/features/devices/DeviceApiTokensPanel.tsx`

Props: `{ deviceId: string }`

Display:
- Table of tokens: Client ID | Label | Created | Status (Active/Revoked) | Actions
- "Revoke" button per active token → confirm dialog → DELETE call → refresh
- "Rotate Credentials" button → confirm dialog → POST /rotate → shows CredentialModal (reuse from Phase 52) with new credentials
- Show warning: "Revoking a token will immediately disconnect any device using it."

## Add API client functions in `frontend/src/services/api/devices.ts`

```typescript
export async function listDeviceTokens(deviceId: string): Promise<DeviceToken[]>
export async function revokeDeviceToken(deviceId: string, tokenId: string): Promise<void>
export async function rotateDeviceToken(deviceId: string, label?: string): Promise<ProvisionedCredentials>
```

## Wire into Device Detail

Import and render `<DeviceApiTokensPanel deviceId={device.id} />` in the device detail page/drawer.

## Acceptance Criteria
- [ ] DeviceApiTokensPanel.tsx exists
- [ ] Revoke with confirmation works
- [ ] Rotate shows CredentialModal with new password
- [ ] API client functions added
- [ ] `npm run build` passes
