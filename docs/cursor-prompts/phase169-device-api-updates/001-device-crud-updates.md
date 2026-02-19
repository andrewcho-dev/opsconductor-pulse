# Task 1: Update Device CRUD for Template Support

## Modify file: `services/ui_iot/routes/devices.py`

### Changes to device provisioning (POST)

Find the existing `POST /devices` endpoint (the `provision_device` function). Update it to:

1. **Accept `template_id`** in the request body. Read the existing `ProvisionDeviceRequest` Pydantic model (likely defined in `devices.py` or imported from `types`) and add:
   ```python
   template_id: int | None = None
   parent_device_id: str | None = None
   ```

2. **Validate template_id**: If provided, verify the template exists and is visible to the tenant:
   ```sql
   SELECT id, category FROM device_templates
   WHERE id = $1 AND (tenant_id IS NULL OR tenant_id = $2)
   ```
   Raise 404 if not found.

3. **Set template_id on device_registry**: Add `template_id` to the INSERT statement for `device_registry`.

4. **Auto-create required sensors**: After device INSERT, if `template_id` is set, query for required metrics and create device_sensors:
   ```sql
   INSERT INTO device_sensors (tenant_id, device_id, metric_key, display_name, template_metric_id, unit, min_range, max_range, precision_digits, source)
   SELECT $1, $2, tm.metric_key, tm.display_name, tm.id, tm.unit, tm.min_value, tm.max_value, tm.precision_digits, 'required'
   FROM template_metrics tm
   WHERE tm.template_id = $3 AND tm.is_required = true
   ON CONFLICT (tenant_id, device_id, metric_key) DO NOTHING
   ```

5. **Set parent_device_id**: If provided, add to device_registry INSERT. The trigger from migration 113 will validate it exists in the same tenant.

### Changes to device read (GET)

Find the existing `GET /devices/{device_id}` endpoint. Update the response to include:

1. **Template summary**: Add a JOIN or subquery to include basic template info:
   ```sql
   LEFT JOIN device_templates dt ON dr.template_id = dt.id
   ```
   Add to response: `template: {id, name, slug, category}` or `null`.

2. **Module count**: Add a subquery for module count:
   ```sql
   (SELECT count(*) FROM device_modules dm WHERE dm.tenant_id = dr.tenant_id AND dm.device_id = dr.device_id) AS module_count
   ```

3. **Sensor count**: Add a subquery for active sensor count:
   ```sql
   (SELECT count(*) FROM device_sensors ds WHERE ds.tenant_id = dr.tenant_id AND ds.device_id = dr.device_id AND ds.status = 'active') AS sensor_count
   ```

4. **Parent device**: If `parent_device_id` is set, include it in the response.

### Changes to device list (GET /devices)

Add `template_id` as an optional query filter:
```python
template_id: int | None = Query(default=None)
```

If set, add `AND dr.template_id = $N` to the WHERE clause.

Also add template name to the list response:
```sql
LEFT JOIN device_templates dt ON dr.template_id = dt.id
```
Include `template_name: dt.name` in each device dict.

### Changes to device update (PUT)

Allow changing `template_id`:
```python
template_id: int | None = None  # Add to update model
```

**Important:** When template_id changes, do NOT auto-delete existing sensors. Just log a warning. The user must manually reconcile sensors. Only auto-create `is_required` sensors from the new template that don't already exist.

## Verification

Test the provisioning flow:
1. Create a device with `template_id` pointing to the Lifeline Gateway
2. Verify `device_sensors` rows were auto-created for battery_pct, signal_rssi, uptime_seconds
3. Verify GET response includes template summary and sensor count
