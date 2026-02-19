# Task 2: Module Assignment Endpoints

## Modify file: `services/ui_iot/routes/devices.py`

Add module CRUD endpoints to the existing devices router.

### Pydantic Models

```python
class ModuleCreate(BaseModel):
    slot_key: str = Field(..., min_length=1, max_length=100)
    bus_address: str | None = Field(default=None, max_length=100)
    module_template_id: int | None = None
    label: str = Field(..., min_length=1, max_length=200)
    serial_number: str | None = Field(default=None, max_length=100)
    metric_key_map: dict[str, str] = Field(default_factory=dict)

class ModuleUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=200)
    serial_number: str | None = Field(default=None, max_length=100)
    metric_key_map: dict[str, str] | None = None
    status: str | None = Field(default=None, pattern=r"^(active|inactive|removed)$")
```

### GET /devices/{device_id}/modules

```python
@router.get("/devices/{device_id}/modules")
async def list_device_modules(device_id: str, pool=Depends(get_db_pool)):
```
- Query `device_modules` for this device, JOIN with `device_templates` to get module template name
- Include: id, slot_key, bus_address, module_template (id+name), label, serial_number, metric_key_map, status, installed_at
- Order by slot_key, bus_address

### POST /devices/{device_id}/modules

```python
@router.post("/devices/{device_id}/modules", status_code=201)
async def create_device_module(device_id: str, body: ModuleCreate, pool=Depends(get_db_pool)):
```

**Validation steps:**
1. Verify device exists in `device_registry`
2. Get device's `template_id`; if set, verify `slot_key` exists in `template_slots`:
   ```sql
   SELECT * FROM template_slots
   WHERE template_id = $1 AND slot_key = $2
   ```
   If device has a template but slot_key is not in its template_slots, raise 400 "Slot key not found in device template"
3. If `compatible_templates` is set on the slot and `module_template_id` is provided, verify module_template_id is in the array:
   ```sql
   -- Check compatible_templates contains the module_template_id
   ```
   Raise 400 if not compatible
4. If `module_template_id` is provided, verify the template exists and has `category = 'expansion_module'`
5. **Max devices check**: Count existing active modules in this slot:
   ```sql
   SELECT count(*) FROM device_modules
   WHERE tenant_id = $1 AND device_id = $2 AND slot_key = $3 AND status = 'active'
   ```
   Compare against `template_slots.max_devices` (if set). Raise 409 "Slot full" if exceeded.
6. INSERT into `device_modules`
7. **Auto-create sensors from module template**: If `module_template_id` is set, create `device_sensors` for all `is_required=true` metrics on that module template:
   ```sql
   INSERT INTO device_sensors (tenant_id, device_id, metric_key, display_name, template_metric_id, device_module_id, unit, min_range, max_range, precision_digits, source)
   SELECT $1, $2, tm.metric_key, tm.display_name, tm.id, $3, tm.unit, tm.min_value, tm.max_value, tm.precision_digits, 'required'
   FROM template_metrics tm
   WHERE tm.template_id = $4 AND tm.is_required = true
   ON CONFLICT (tenant_id, device_id, metric_key) DO NOTHING
   ```
   Where `$3` is the newly created module ID and `$4` is `module_template_id`.

### PUT /devices/{device_id}/modules/{module_id}

```python
@router.put("/devices/{device_id}/modules/{module_id}")
async def update_device_module(device_id: str, module_id: int, body: ModuleUpdate, pool=Depends(get_db_pool)):
```
- Fetch module; 404 if not found or wrong device_id
- Use `model_dump(exclude_unset=True)` for partial update
- Return updated module

### DELETE /devices/{device_id}/modules/{module_id}

```python
@router.delete("/devices/{device_id}/modules/{module_id}", status_code=204)
async def delete_device_module(device_id: str, module_id: int, pool=Depends(get_db_pool)):
```
- Fetch module; 404 if not found
- Set `status = 'removed'` on the module (soft delete)
- Deactivate linked sensors:
  ```sql
  UPDATE device_sensors SET status = 'inactive' WHERE device_module_id = $1
  ```
- Return `Response(status_code=204)`

## Verification

Test the module assignment flow:
1. Create device with Lifeline Gateway template
2. Assign a temp probe module to `analog_1` slot
3. Verify module appears in GET /modules
4. Verify auto-created sensor for temperature
5. Try assigning a module to a non-existent slot → should get 400
6. Try exceeding max_devices on analog port → should get 409
