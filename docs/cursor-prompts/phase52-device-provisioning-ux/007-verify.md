# Prompt 007 — Verify Phase 52

## Step 1: Unit Tests

```bash
pytest -m unit -v 2>&1 | tail -40
```

All must pass. Fix any failures before proceeding.

## Step 2: TypeScript Build

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Must complete with no errors.

## Step 3: Checklist

### Backend (001, 002)
- [ ] PATCH /customer/devices/{id} exists in customer.py
- [ ] PATCH /customer/devices/{id}/decommission exists in customer.py
- [ ] GET /devices excludes decommissioned by default (`decommissioned_at IS NULL`)
- [ ] `?include_decommissioned=true` param shows all
- [ ] Migration 058 exists if `decommissioned_at` column was added

### Frontend (003, 004, 005)
- [ ] `AddDeviceModal.tsx` exists with name/device_type/site/tags fields
- [ ] "Add Device" button in DeviceListPage opens modal
- [ ] `EditDeviceModal.tsx` exists, pre-filled with device values
- [ ] Row action menu (kebab) with Edit and Decommission
- [ ] Decommission shows confirmation dialog
- [ ] `CredentialModal.tsx` exists with copy + download buttons
- [ ] Warning banner present in CredentialModal
- [ ] Credential modal shown after successful provisioning

### API Client (003, 004)
- [ ] `provisionDevice()` in devices.ts
- [ ] `updateDevice()` in devices.ts
- [ ] `decommissionDevice()` in devices.ts

### Unit Tests (006)
- [ ] `tests/unit/test_device_management.py` exists with 7 tests

## Report

Output PASS / FAIL per criterion.
