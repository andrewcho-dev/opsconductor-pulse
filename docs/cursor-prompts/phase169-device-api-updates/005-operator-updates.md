# Task 5: Operator Device Endpoint Updates

## Modify file: `services/ui_iot/routes/operator.py`

Update the operator device endpoints to include template information.

### Update operator device list

Find the existing operator device listing endpoint (likely `GET /operator/devices` or similar). Update the query to:

1. JOIN `device_templates` to include template name in the response:
   ```sql
   LEFT JOIN device_templates dt ON dr.template_id = dt.id
   ```
2. Add `template_id` and `template_name` to each device dict in the response.
3. Add `template_id` filter parameter:
   ```python
   template_id: int | None = Query(default=None)
   ```

### Update operator device detail

If there's an operator device detail endpoint, update it to include:
- Template summary (id, name, category, source)
- Module count
- Sensor count (from device_sensors)
- Transport list (from device_transports)

### Operator module/sensor/transport read access

Add read-only endpoints for operators to view module, sensor, and transport data for any device:

```python
@router.get("/devices/{device_id}/modules")
async def operator_list_device_modules(request: Request, device_id: str, pool=Depends(get_db_pool)):
    # Use operator_connection to bypass RLS
    # Same query as customer version
    # Log access

@router.get("/devices/{device_id}/sensors")
async def operator_list_device_sensors(request: Request, device_id: str, pool=Depends(get_db_pool)):

@router.get("/devices/{device_id}/transports")
async def operator_list_device_transports(request: Request, device_id: str, pool=Depends(get_db_pool)):
```

All use `operator_connection(pool)` and include `log_operator_access()` calls.

## Verification

Test that operator can:
1. List all devices with template_name included
2. Filter devices by template_id
3. View modules, sensors, transports for any device
