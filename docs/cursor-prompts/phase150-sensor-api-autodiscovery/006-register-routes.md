# Task 006 — Register New Routes in app.py

## File

Modify `services/ui_iot/app.py`

## Changes

### 1. Import the sensors router

Find the section where routers are imported (near the top of the file, look for `from routes.xxx import router as xxx_router` pattern). Add:

```python
from routes.sensors import router as sensors_router
```

### 2. Register the router

Find where `app.include_router(...)` calls are made. Add:

```python
app.include_router(sensors_router)
```

Place it near the other customer-facing routers (devices, dashboards, alerts, etc.).

## Also: Add new device_registry columns to any response serializers

Search `app.py` and `routes/devices.py` for any response serialization that manually lists device_registry columns. If the device response is built by selecting specific columns (not `SELECT *`), ensure the new columns from migration 102 are included:

- `chipset`
- `modem_model`
- `board_revision`
- `meid`
- `bootloader_version`
- `modem_fw_version`
- `deployment_date`
- `batch_id`
- `installation_notes`
- `sensor_limit`

If the query uses `SELECT *` or `SELECT dr.*`, no changes needed — new columns will be included automatically.

If the query explicitly lists columns, add the new ones. Same for any Pydantic response models or TypedDict that enumerate device fields.

## Verification

```bash
cd services/ui_iot && python3 -c "from app import app; routes = [r.path for r in app.routes]; print([r for r in routes if 'sensor' in r or 'health' in r or 'connection' in r])"
```

Expected output should include:
- `/api/v1/customer/devices/{device_id}/sensors`
- `/api/v1/customer/sensors`
- `/api/v1/customer/sensors/{sensor_id}`
- `/api/v1/customer/devices/{device_id}/connection`
- `/api/v1/customer/devices/{device_id}/health`
- `/api/v1/customer/devices/{device_id}/health/latest`
