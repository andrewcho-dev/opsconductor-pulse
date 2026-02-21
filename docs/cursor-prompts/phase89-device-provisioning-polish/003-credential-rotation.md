# Phase 89 — Credential Rotation Flow

## Context

Phase 75 added:
- `GET /customer/devices/{id}/api-tokens` — list tokens
- `POST /customer/devices/{id}/api-tokens` — create/rotate
- `DELETE /customer/devices/{id}/api-tokens/{token_id}` — revoke
- `DeviceApiTokensPanel.tsx` in the device detail pane (Credentials tab)

## New shared component

### `frontend/src/components/shared/OneTimeSecretDisplay.tsx`

```typescript
interface Props {
  label: string;
  value: string;
  filename?: string; // if provided, show "Download .env" button
}
```

Behavior:
- Value is masked by default: `••••••••••••••••`
- "Reveal" button toggles between masked and plain text
- "Copy" button copies `value` to clipboard, shows "Copied!" for 2s
- If `filename` provided: "Download .env" button creates a Blob download
  containing `{LABEL_UPPER}={value}\n` (e.g. `API_TOKEN=abc123`)

Style: small card with monospace font for the value area.

## Modify: DeviceApiTokensPanel.tsx

### 1. Token age indicator

For each token row, compute age from `created_at`:
- < 30 days → green dot + "X days old"
- 30–90 days → yellow dot + "X days old"
- > 90 days → red dot + "X days old" + tooltip "Consider rotating"

Use a `TokenAgeChip` inline component (just a `<span>` with conditional color class).

### 2. Rotate / Create confirmation modal

Replace the current "Create Token" button behavior with a confirmation flow:

When user clicks "Create Token" (or "Rotate" if a token already exists):
1. Show a shadcn AlertDialog:
   - Title: "Rotate API Credentials"
   - Description: "Creating a new token will not automatically revoke existing
     tokens. Revoke old tokens after updating your device configuration."
   - Buttons: Cancel | Generate Token
2. On confirm: call `POST /customer/devices/{id}/api-tokens`
3. On success: show the new token using `<OneTimeSecretDisplay>` inside the
   same AlertDialog (or a follow-up dialog):
   - label: "API Token"
   - value: the returned token string
   - filename: `device-{deviceId}.env`

### Files to modify
- `frontend/src/features/devices/DeviceApiTokensPanel.tsx`

### New file
- `frontend/src/components/shared/OneTimeSecretDisplay.tsx`
