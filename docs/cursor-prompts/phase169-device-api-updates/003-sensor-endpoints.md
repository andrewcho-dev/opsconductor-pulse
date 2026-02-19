# Task 3: Restructured Sensor Endpoints

## Modify file: `services/ui_iot/routes/sensors.py`

Restructure the sensor endpoints to use the new `device_sensors` table while maintaining backward compatibility for the fleet-wide sensor list.

### Updated Pydantic Models

Replace the existing `SensorCreate` and `SensorUpdate` models with versions that match the new schema:

```python
class DeviceSensorCreate(BaseModel):
    metric_key: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z][a-zA-Z0-9_]*$")
    display_name: str = Field(..., min_length=1, max_length=200)
    template_metric_id: int | None = None
    device_module_id: int | None = None
    unit: str | None = Field(default=None, max_length=20)
    min_range: float | None = None
    max_range: float | None = None
    precision_digits: int = Field(default=2, ge=0, le=6)

class DeviceSensorUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    unit: str | None = Field(default=None, max_length=20)
    min_range: float | None = None
    max_range: float | None = None
    precision_digits: int | None = Field(default=None, ge=0, le=6)
    status: str | None = Field(default=None, pattern=r"^(active|inactive)$")
```

### Device-Scoped Sensor Endpoints (NEW — primary)

These are the new per-device sensor endpoints that query `device_sensors`:

**GET /devices/{device_id}/sensors** — List sensors for a device
```python
@router.get("/devices/{device_id}/sensors")
async def list_device_sensors_v2(
    device_id: str,
    status: str | None = Query(default=None),
    source: str | None = Query(default=None),
    pool=Depends(get_db_pool),
):
```
- Query `device_sensors` table (NOT the old `sensors` table)
- JOIN with `template_metrics` for template info, `device_modules` for module info
- Return: id, metric_key, display_name, source, template_metric (id+name), module (id+label), unit, min_range, max_range, precision_digits, status, last_value, last_value_text, last_seen_at

**POST /devices/{device_id}/sensors** — Manually add sensor
```python
@router.post("/devices/{device_id}/sensors", status_code=201)
async def create_device_sensor(device_id: str, body: DeviceSensorCreate, pool=Depends(get_db_pool)):
```
- If `template_metric_id` is provided, verify it belongs to the device's template
- If `device_module_id` is provided, verify it belongs to this device
- Determine `source`: 'optional' if template_metric_id is set, 'unmodeled' otherwise
- INSERT into `device_sensors`
- Return created sensor

**PUT /devices/{device_id}/sensors/{sensor_id}** — Update sensor
```python
@router.put("/devices/{device_id}/sensors/{sensor_id}")
async def update_device_sensor(device_id: str, sensor_id: int, body: DeviceSensorUpdate, pool=Depends(get_db_pool)):
```
- Fetch sensor; 404 if not found or wrong device_id
- Dynamic UPDATE from `model_dump(exclude_unset=True)`
- Return updated sensor

**DELETE /devices/{device_id}/sensors/{sensor_id}** — Remove sensor
```python
@router.delete("/devices/{device_id}/sensors/{sensor_id}", status_code=204)
async def delete_device_sensor(device_id: str, sensor_id: int, pool=Depends(get_db_pool)):
```
- Fetch sensor; 404 if not found
- If `source = 'required'`, raise 400 "Cannot delete a required sensor. Deactivate it instead."
- DELETE from `device_sensors`
- Return `Response(status_code=204)`

### Fleet-Wide Sensor Endpoint (UPDATED — backward compat)

Update the existing `GET /sensors` endpoint to query from `device_sensors` instead of `sensors`:

```python
@router.get("/sensors")
async def list_all_sensors(
    sensor_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    device_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    pool=Depends(get_db_pool),
):
```
- Query `device_sensors` table with filters
- Map response fields to maintain backward compatibility where possible:
  - `sensor_id` → `id`
  - `metric_name` → `metric_key`
  - `sensor_type` → derived from template or 'unknown'
  - `label` → `display_name`
  - `auto_discovered` → `source != 'required'`
- Include `total` count for pagination

### Legacy endpoint redirect

Keep the existing per-device sensor endpoints (`GET /devices/{device_id}/sensors`) working. The old implementation queries `sensors` table — update it to query `device_sensors` instead. If both old and new endpoints exist on the same path, consolidate to the new implementation.

### Update the connection endpoints

The existing connection endpoints in `sensors.py` (GET/PUT/DELETE `/devices/{device_id}/connection`) should remain working for now but add a deprecation header:

```python
response.headers["Deprecation"] = "true"
response.headers["Sunset"] = "2026-06-01"
response.headers["Link"] = '</api/v1/customer/devices/{device_id}/transports>; rel="successor-version"'
```

## Verification

1. GET /devices/{device_id}/sensors returns data from device_sensors table
2. POST a new sensor with template_metric_id → source should be 'optional'
3. POST a new sensor without template_metric_id → source should be 'unmodeled'
4. DELETE a required sensor → should get 400
5. GET /sensors (fleet-wide) still works with backward-compatible response shape
