# Prompt 005 — Verify Phase 75

## Step 1
```bash
pytest -m unit -v 2>&1 | tail -30
```
All must pass.

## Step 2
```bash
cd frontend && npm run build 2>&1 | tail -20
```
Must complete with no errors.

## Checklist
- [ ] Migration 064 exists
- [ ] GET /customer/devices/{id}/tokens in customer.py
- [ ] DELETE /customer/devices/{id}/tokens/{token_id} in customer.py
- [ ] POST /customer/devices/{id}/tokens/rotate in customer.py
- [ ] DeviceApiTokensPanel.tsx exists
- [ ] CredentialModal reused for rotate result
- [ ] API client: listDeviceTokens, revokeDeviceToken, rotateDeviceToken
- [ ] tests/unit/test_device_api_tokens.py with 5 tests

## Report
Output PASS / FAIL per criterion.
