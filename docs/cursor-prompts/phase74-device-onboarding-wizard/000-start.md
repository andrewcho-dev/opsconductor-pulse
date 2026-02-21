# Phase 74: Device Onboarding Wizard

## What Exists

- `AddDeviceModal.tsx` — single-step modal: name/device_type/site/tags → POST /customer/devices → CredentialModal
- `CredentialModal.tsx` — displays MQTT credentials with copy + download buttons
- `POST /customer/devices` → returns `{ device_id, client_id, password, broker_url }`
- No multi-step wizard or Stepper component exists
- Device groups (Phase 68) — can assign device to group
- Alert rules with group_ids (Phase 68)
- Sites (Phase 54) — can assign device to site

## What This Phase Adds

A guided **multi-step onboarding wizard** as a dedicated page at `/devices/wizard`, replacing the single-step modal for new users. The wizard walks through:

1. **Step 1 — Device Details**: name, device_type, site (required fields)
2. **Step 2 — Tags & Groups**: optional tags + assign to device groups
3. **Step 3 — Provision**: calls POST /customer/devices, shows progress
4. **Step 4 — Credentials**: displays credentials (same as CredentialModal but in-page)
5. **Step 5 — Add Alert Rules**: optional — "Add a threshold rule for this device now?" with quick-add form

The existing `AddDeviceModal` stays for quick add. The wizard is for guided first-time setup.

## Execution Order

| Prompt | Description |
|--------|-------------|
| 001 | Wizard step components + Stepper UI |
| 002 | Wizard page + orchestration |
| 003 | Step 5: quick alert rule creation |
| 004 | Nav + route wiring |
| 005 | Unit tests |
| 006 | Verify |

## Key Files

- `frontend/src/components/ui/stepper.tsx` — new Stepper component (prompt 001)
- `frontend/src/features/devices/wizard/` — new directory (prompts 001–003)
- `frontend/src/features/devices/AddDeviceModal.tsx` — unchanged (keep as-is)
- `frontend/src/app/router.tsx` — prompt 004
