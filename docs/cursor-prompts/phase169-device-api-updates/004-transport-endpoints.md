# Task 4: Transport Endpoints

## Modify file: `services/ui_iot/routes/sensors.py` (or create new section in `devices.py`)

Add transport CRUD endpoints that query the new `device_transports` table, replacing the legacy `device_connections` endpoints.

### Pydantic Models

```python
class TransportCreate(BaseModel):
    ingestion_protocol: str = Field(
        ...,
        pattern=r"^(mqtt_direct|http_api|lorawan|gateway_proxy|modbus_rtu)$",
    )
    physical_connectivity: str | None = Field(
        default=None,
        pattern=r"^(cellular|ethernet|wifi|satellite|lora|other)$",
    )
    protocol_config: dict[str, Any] = Field(default_factory=dict)
    connectivity_config: dict[str, Any] = Field(default_factory=dict)
    carrier_integration_id: int | None = None
    is_primary: bool = True
    status: str = Field(default="active", pattern=r"^(active|inactive|failover)$")

class TransportUpdate(BaseModel):
    physical_connectivity: str | None = Field(
        default=None,
        pattern=r"^(cellular|ethernet|wifi|satellite|lora|other)$",
    )
    protocol_config: dict[str, Any] | None = None
    connectivity_config: dict[str, Any] | None = None
    carrier_integration_id: int | None = None
    is_primary: bool | None = None
    status: str | None = Field(default=None, pattern=r"^(active|inactive|failover)$")
```

### Endpoints

**GET /devices/{device_id}/transports** — List transports
```python
@router.get("/devices/{device_id}/transports")
async def list_device_transports(device_id: str, pool=Depends(get_db_pool)):
```
- Query `device_transports` for this device
- LEFT JOIN `carrier_integrations` for carrier display_name
- Return list of transport dicts including carrier info

**POST /devices/{device_id}/transports** — Add transport config
```python
@router.post("/devices/{device_id}/transports", status_code=201)
async def create_device_transport(device_id: str, body: TransportCreate, pool=Depends(get_db_pool)):
```
- Verify device exists
- If `carrier_integration_id` is provided, verify it exists and belongs to tenant
- INSERT into `device_transports`
- Return created transport

**PUT /devices/{device_id}/transports/{transport_id}** — Update transport
```python
@router.put("/devices/{device_id}/transports/{transport_id}")
async def update_device_transport(device_id: str, transport_id: int, body: TransportUpdate, pool=Depends(get_db_pool)):
```
- Fetch transport; 404 if not found or wrong device_id
- Dynamic UPDATE from `model_dump(exclude_unset=True)`
- Handle JSONB fields: if `protocol_config` or `connectivity_config` is provided, replace the whole JSONB (not merge)
- Return updated transport

**DELETE /devices/{device_id}/transports/{transport_id}** — Remove transport
```python
@router.delete("/devices/{device_id}/transports/{transport_id}", status_code=204)
async def delete_device_transport(device_id: str, transport_id: int, pool=Depends(get_db_pool)):
```
- Fetch; 404 if not found
- DELETE from `device_transports`
- Return `Response(status_code=204)`

### Populate from template defaults

When a device is created with a `template_id` (handled in Task 1), if the template has `transport_defaults` JSONB, auto-create a transport config:

```python
# In the device provisioning endpoint, after device INSERT:
if template_row and template_row["transport_defaults"]:
    defaults = template_row["transport_defaults"]
    await conn.execute("""
        INSERT INTO device_transports (tenant_id, device_id, ingestion_protocol, physical_connectivity, is_primary)
        VALUES ($1, $2, $3, $4, true)
        ON CONFLICT (tenant_id, device_id, ingestion_protocol) DO NOTHING
    """, tenant_id, device_id, defaults.get("ingestion_protocol", "mqtt_direct"), defaults.get("physical_connectivity"))
```

## Verification

1. Create device with Lifeline Gateway template → verify transport auto-created with mqtt_direct + cellular
2. GET /devices/{device_id}/transports → returns transport list
3. POST additional transport (http_api) → verify created
4. PUT update connectivity_config → verify updated
5. DELETE transport → verify removed
