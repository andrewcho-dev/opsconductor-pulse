# Task 002 — Carrier Integration Settings Page

## File

Create `frontend/src/features/settings/CarrierIntegrationsPage.tsx`

Add to router and sidebar (under a "Settings" or "Integrations" section).

## Purpose

A settings page where users manage their carrier API integrations (Hologram, 1NCE, etc.). CRUD for integration records + sync status display.

## Layout

```
┌───────────────────────────────────────────────────────────────┐
│  Carrier Integrations                        [+ Add Carrier]  │
│  Connect your IoT carrier accounts for diagnostics and usage  │
│                                                               │
│  ┌───────────────────────────────────────────────────────────┐│
│  │ 🟢 Hologram Production                                   ││
│  │    Carrier: hologram  │  Account: HOL-ACME-2024-001      ││
│  │    API Key: ...xxxx   │  Sync: Every 60 min              ││
│  │    Last sync: Feb 18, 10:00 AM ✅                        ││
│  │                                        [Edit] [Delete]   ││
│  └───────────────────────────────────────────────────────────┘│
│                                                               │
│  ┌───────────────────────────────────────────────────────────┐│
│  │ 🟢 1NCE IoT                                              ││
│  │    Carrier: 1nce  │  Account: 1NCE-ACME-2025-001         ││
│  │    API Key: ...xxxx   │  Sync: Every 60 min              ││
│  │    Last sync: Never                                      ││
│  │                                        [Edit] [Delete]   ││
│  └───────────────────────────────────────────────────────────┘│
└───────────────────────────────────────────────────────────────┘
```

## Implementation

### Integration List

Each integration renders as a card with:
- Status indicator (green = enabled, gray = disabled)
- Display name + carrier name badge
- Account ID
- Masked API key (last 4 chars)
- Sync config (interval, last sync time, status)
- Edit / Delete buttons

### Add/Edit Dialog

A `Dialog` with form fields:
- **Carrier** (Select): hologram, 1nce (read-only on edit)
- **Display Name** (Input): User-friendly label
- **API Key** (Input, type=password): Full key on create, blank on edit means "keep existing"
- **API Secret** (Input, type=password, optional): For carriers that need it
- **Account ID** (Input, optional)
- **Custom API URL** (Input, optional): For sandbox/self-hosted
- **Sync Enabled** (Switch): Toggle periodic usage sync
- **Sync Interval** (Select): 15, 30, 60, 120, 360 minutes

### Delete Confirmation

`AlertDialog` with warning that deleting unlinks all devices from this carrier integration.

### Sync Status Display

For `last_sync_status`:
- `success` → green checkmark
- `error` → red X with `last_sync_error` in tooltip
- `partial` → orange warning
- `never` → gray "Never synced"

## Route & Sidebar

Add route at `/settings/carrier` or `/integrations/carrier`.

In sidebar, add under a "Settings" or "Integrations" collapsible group:
```tsx
{ label: "Carrier Integrations", href: "/settings/carrier", icon: Radio }
```

Use `Radio` or `Wifi` from lucide-react.

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```
