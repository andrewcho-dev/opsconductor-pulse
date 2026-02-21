# Task 003 — Carrier API Endpoints

## File

Create `services/ui_iot/routes/carrier.py`

Register in `app.py` (same pattern as sensors_router).

## Endpoints

### 1. `GET /api/v1/customer/carrier/integrations`

List all carrier integrations for the tenant.

**Response:**
```json
{
  "integrations": [
    {
      "id": 1,
      "carrier_name": "hologram",
      "display_name": "Hologram Production",
      "enabled": true,
      "account_id": "HOL-ACME-2024-001",
      "sync_enabled": true,
      "sync_interval_minutes": 60,
      "last_sync_at": "2026-02-18T10:00:00Z",
      "last_sync_status": "success"
    }
  ]
}
```

**Note:** Do NOT include `api_key` or `api_secret` in the response. Mask them (e.g., show last 4 chars: `"...xxxx"`).

### 2. `POST /api/v1/customer/carrier/integrations`

Create a new carrier integration.

**Request body:**
```json
{
  "carrier_name": "hologram",
  "display_name": "Hologram Production",
  "api_key": "hlg_xxxxxxxxxxxx",
  "api_secret": null,
  "account_id": "HOL-ACME-2024-001",
  "api_base_url": null,
  "sync_enabled": true,
  "sync_interval_minutes": 60,
  "config": {}
}
```

**Logic:** Insert into `carrier_integrations`. Return the created record (without secrets).

### 3. `PUT /api/v1/customer/carrier/integrations/{id}`

Update integration settings (including rotating API keys).

### 4. `DELETE /api/v1/customer/carrier/integrations/{id}`

Remove a carrier integration. Sets `carrier_integration_id = NULL` on all linked device_connections.

### 5. `GET /api/v1/customer/devices/{device_id}/carrier/status`

Get live device status from the carrier API.

**Logic:**
1. Look up `device_connections` for the device → get `carrier_integration_id` and `carrier_device_id`
2. If no carrier link → return `{"linked": false}`
3. Load the carrier integration, create provider via `get_carrier_provider()`
4. Call `provider.get_device_info(carrier_device_id)`
5. Return standardized device info

**Response:**
```json
{
  "linked": true,
  "carrier_name": "hologram",
  "device_info": {
    "carrier_device_id": "123456",
    "iccid": "8901260012345678901",
    "sim_status": "active",
    "network_status": "connected",
    "ip_address": "10.176.42.101",
    "network_type": "LTE-M",
    "last_connection": "2026-02-18T10:30:00Z",
    "signal_strength": 78
  }
}
```

### 6. `GET /api/v1/customer/devices/{device_id}/carrier/usage`

Get data usage from the carrier API.

**Logic:** Same as status — look up carrier link, call `provider.get_usage()`.

**Response:**
```json
{
  "linked": true,
  "carrier_name": "hologram",
  "usage": {
    "data_used_bytes": 133693440,
    "data_limit_bytes": 524288000,
    "data_used_mb": 127.5,
    "data_limit_mb": 500,
    "usage_pct": 25.5,
    "billing_cycle_start": "2026-02-01",
    "billing_cycle_end": "2026-02-28",
    "sms_count": 3
  }
}
```

### 7. `POST /api/v1/customer/devices/{device_id}/carrier/actions/{action}`

Execute a remote action via the carrier API.

**Path param:** `action` — one of: `activate`, `suspend`, `deactivate`, `reboot`

**Logic:**
1. Validate action is allowed
2. Look up carrier link
3. Call appropriate provider method:
   - `activate` → `provider.activate_sim()`
   - `suspend` → `provider.suspend_sim()`
   - `deactivate` → `provider.deactivate_sim()`
   - `reboot` → `provider.send_sms(carrier_device_id, "REBOOT")` (carrier-specific reboot trigger)
4. Log the action in an audit trail
5. Return success/failure

**Response:**
```json
{
  "action": "suspend",
  "success": true,
  "carrier_name": "hologram"
}
```

**IMPORTANT:** `deactivate` is a destructive action. Require confirmation (the frontend will handle the confirmation dialog, but the backend should also log it prominently).

### 8. `GET /api/v1/customer/devices/{device_id}/carrier/diagnostics`

Get detailed network diagnostics from the carrier.

**Logic:** Call `provider.get_network_diagnostics()`. Return raw + standardized data.

### 9. `POST /api/v1/customer/devices/{device_id}/carrier/link`

Link a device to a carrier integration.

**Request:**
```json
{
  "carrier_integration_id": 1,
  "carrier_device_id": "123456"
}
```

**Logic:** Update `device_connections` to set `carrier_integration_id` and `carrier_device_id`.

## Error Handling

All carrier API calls should be wrapped in try/except:
```python
try:
    result = await provider.get_device_info(carrier_device_id)
except httpx.HTTPStatusError as e:
    raise HTTPException(502, f"Carrier API error: {e.response.status_code}")
except httpx.RequestError as e:
    raise HTTPException(502, f"Failed to reach carrier API: {str(e)}")
except Exception as e:
    logger.exception("Carrier API call failed")
    raise HTTPException(500, "Internal error during carrier API call")
```

Use HTTP 502 for carrier-side errors (bad gateway — we're proxying).

## Router Setup

```python
router = APIRouter(
    prefix="/api/v1/customer",
    tags=["carrier"],
    dependencies=[
        Depends(JWTBearer()),
        Depends(inject_tenant_context),
        Depends(require_customer),
    ],
)
```

## Verification

```bash
cd services/ui_iot && python3 -c "from routes.carrier import router; print('Routes:', len(router.routes))"
```
