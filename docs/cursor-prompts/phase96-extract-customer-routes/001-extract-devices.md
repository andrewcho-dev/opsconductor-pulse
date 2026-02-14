# Phase 96 — Extract devices domain to routes/devices.py

## File to create
`services/ui_iot/routes/devices.py`

## Endpoints to move from customer.py

Move ALL of the following functions out of `customer.py` and into the new `devices.py` file.
Look these up by function name in customer.py to get the exact line content.

### Device CRUD
- `create_device()` — POST /devices (line ~554)
- `list_devices()` — GET /devices (line ~1037)
- `device_summary()` — GET /devices/summary (line ~1193)
- `delete_device()` — DELETE /devices/{device_id} (line ~1206)
- `get_device()` — GET /devices/{device_id} (line ~1258)
- `update_device()` — PATCH /devices/{device_id} (line ~1741)
- `decommission_device()` — PATCH /devices/{device_id}/decommission (line ~1843)

### Device tokens
- `list_device_tokens()` — GET /devices/{device_id}/tokens (line ~601)
- `delete_device_token()` — DELETE /devices/{device_id}/tokens/{token_id} (line ~639)
- `rotate_device_token()` — POST /devices/{device_id}/tokens/rotate (line ~666)

### Bulk import
- `bulk_import_devices()` — POST /devices/import (line ~717)

### Uptime
- `device_uptime()` — GET /devices/{device_id}/uptime (line ~901)
- `fleet_uptime_summary()` — GET /fleet/uptime-summary (line ~968)

### Telemetry
- `get_telemetry_history()` — GET /devices/{device_id}/telemetry/history (line ~1284)
- `export_telemetry()` — GET /devices/{device_id}/telemetry/export (line ~1342)

### Tags
- `list_all_tags()` — GET /tags (line ~2026)
- `list_device_tags()` — GET /devices/{device_id}/tags (line ~1882)
- `set_device_tags()` — PUT /devices/{device_id}/tags (line ~1915)
- `add_device_tag()` — POST /devices/{device_id}/tags/{tag} (line ~1953)
- `delete_device_tag()` — DELETE /devices/{device_id}/tags/{tag} (line ~1990)

### Device groups
- `list_device_groups()` — GET /device-groups (line ~2048)
- `create_device_group()` — POST /device-groups (line ~2073)
- `update_device_group()` — PATCH /device-groups/{group_id} (line ~2102)
- `delete_device_group()` — DELETE /device-groups/{group_id} (line ~2136)
- `list_group_devices()` — GET /device-groups/{group_id}/devices (line ~2159)
- `add_device_to_group()` — PUT /device-groups/{group_id}/devices/{device_id} (line ~2190)
- `remove_device_from_group()` — DELETE /device-groups/{group_id}/devices/{device_id} (line ~2228)

### Maintenance windows
- `list_maintenance_windows()` — GET /maintenance-windows (line ~2252)
- `create_maintenance_window()` — POST /maintenance-windows (line ~2273)
- `update_maintenance_window()` — PATCH /maintenance-windows/{window_id} (line ~2303)
- `delete_maintenance_window()` — DELETE /maintenance-windows/{window_id} (line ~2351)

## Structure of devices.py

```python
"""Device management routes — CRUD, tokens, uptime, tags, groups, maintenance windows."""

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from typing import Optional, Any
# ... copy all imports needed by the moved functions from customer.py top-of-file

from dependencies import get_db_pool, require_customer, require_customer_admin
# ... other shared imports

router = APIRouter(prefix="/customer", tags=["devices"])

# ── paste all device functions here ──────────────────────────────────────────
```

The `prefix="/customer"` ensures all paths stay exactly the same as before.

## After creating devices.py

1. **Delete** all moved functions from `customer.py`
2. **Remove** any imports in `customer.py` that are now only used by devices.py
3. **Do NOT** register devices.py in app.py yet — that happens in `005-register-routers.md`

## Smoke test command (run after registering in step 005)

```bash
curl -s http://localhost:8000/customer/devices \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | head -20
# Expected: list of devices (no 404, no 500)
```
