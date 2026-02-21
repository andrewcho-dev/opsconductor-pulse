# Phase 157 — Hologram Carrier API Integration (Production-Ready)

## Problem

The `HologramProvider` in `services/ui_iot/services/carrier_service.py` (lines 101-164) was written against assumed API endpoints. After verifying the real Hologram REST API (`https://dashboard.hologram.io/api/1`), multiple methods use incorrect endpoints, wrong auth patterns, and missing response parsing. The provider compiles but will fail against the live API.

**Key issues:**
- Auth uses `headers={"apikey": key}` but Hologram requires query param `?apikey={key}`
- `get_usage` hits nonexistent endpoint `/devices/{id}/usage` — real is `GET /usage/data?deviceid={id}`
- `activate_sim` hits `/devices/{id}/activate` — real is `POST /devices/{id}/state` body `{"state":"live"}`
- `suspend_sim` hits `/devices/{id}/pause` — real is `POST /devices/{id}/state` body `{"state":"pause"}`
- `deactivate_sim` hits `/devices/{id}/deactivate` — real is `POST /devices/{id}/state` body `{"state":"deactivate"}`
- `send_sms` uses `fromNumber` (camelCase) — real API uses `fromnumber` (lowercase)
- No SIM claim/provisioning support
- No plan listing support

## Execution Order

| # | File | What |
|---|------|------|
| 1 | `001-fix-hologram-provider.md` | Fix HologramProvider auth + all 7 API methods, add `claim_sim()` + `list_plans()` to abstract base + both providers |
| 2 | `002-provision-plans-endpoints.md` | Add `POST /devices/{id}/carrier/provision` and `GET /carrier/integrations/{id}/plans` endpoints |
| 3 | `003-enhance-usage-sync.md` | Enhance sync worker: bulk usage, update sim_status/network_status, billing cycle |
| 4 | `004-frontend-provisioning.md` | SIM provisioning UI in DeviceCarrierPanel, new API functions + types |
| 5 | `005-update-docs.md` | Update affected documentation files |

## Files Modified

| File | Prompts |
|------|---------|
| `services/ui_iot/services/carrier_service.py` | 001 |
| `services/ui_iot/routes/carrier.py` | 002 |
| `services/ui_iot/services/carrier_sync.py` | 003 |
| `frontend/src/features/devices/DeviceCarrierPanel.tsx` | 004 |
| `frontend/src/services/api/carrier.ts` | 004 |
| `frontend/src/services/api/types.ts` | 004 |
| `docs/api/customer-endpoints.md` | 005 |
| `docs/services/ui-iot.md` | 005 |
| `docs/features/device-management.md` | 005 |

## Verification

```bash
# 1. Unit test: provider auth and method signatures
cd services/ui_iot && python -c "
from services.carrier_service import HologramProvider
p = HologramProvider('test-key', account_id='12345')
print('Auth params:', p.client._base_url, p.client.params)
# Should show params={'apikey': 'test-key'}, NOT headers
"

# 2. Live API smoke test (requires real credentials from .env):
curl "https://dashboard.hologram.io/api/1/devices?orgid=102605&apikey=\$HOLOGRAM_API_KEY"

# 3. Plan discovery test:
curl "https://dashboard.hologram.io/api/1/plans?orgid=102605&apikey=\$HOLOGRAM_API_KEY"

# 4. Frontend build:
cd frontend && npx tsc --noEmit && npm run build

# 5. Backend tests:
pytest tests/unit/ -m unit -q --tb=short -k carrier
```
