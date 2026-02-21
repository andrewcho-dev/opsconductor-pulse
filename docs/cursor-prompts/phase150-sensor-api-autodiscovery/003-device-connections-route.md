# Task 003 — Device Connections Endpoints

## File

Add to `services/ui_iot/routes/sensors.py` (same file as task 001 — keeps connection/sensor routes together since they're device sub-resources)

## Endpoints

### 1. `GET /api/v1/customer/devices/{device_id}/connection`

Get the cellular/network connection info for a device.

**Response:**
```json
{
  "device_id": "GW-001",
  "connection_type": "cellular",
  "carrier_name": "Hologram",
  "carrier_account_id": "HOL-ACME-2024-001",
  "plan_name": "IoT Pro 500MB",
  "apn": "hologram",
  "sim_iccid": "8901260012345678901",
  "sim_status": "active",
  "data_limit_mb": 500,
  "data_used_mb": 127.4,
  "data_used_updated_at": "2026-02-18T08:30:00Z",
  "billing_cycle_start": 1,
  "ip_address": "10.176.42.101",
  "msisdn": null,
  "network_status": "connected",
  "last_network_attach": "2026-02-15T10:00:00Z"
}
```

**Logic:**
1. Verify device exists
2. Query `device_connections` by (tenant_id, device_id)
3. If no connection record → return `{"device_id": "...", "connection": null}`
4. Otherwise return the connection record

### 2. `PUT /api/v1/customer/devices/{device_id}/connection`

Create or update the connection record for a device (upsert).

**Request body (Pydantic model `ConnectionUpsert`):**
```json
{
  "connection_type": "cellular",
  "carrier_name": "Hologram",
  "plan_name": "IoT Pro 500MB",
  "apn": "hologram",
  "sim_iccid": "8901260012345678901",
  "sim_status": "active",
  "data_limit_mb": 500,
  "billing_cycle_start": 1,
  "msisdn": "+1234567890"
}
```

All fields are optional except `connection_type`.

**Logic:**
1. Verify device exists
2. Upsert into `device_connections`:
```sql
INSERT INTO device_connections (tenant_id, device_id, connection_type, carrier_name, ...)
VALUES ($1, $2, $3, $4, ...)
ON CONFLICT (tenant_id, device_id)
DO UPDATE SET connection_type = $3, carrier_name = $4, ..., updated_at = now()
```
3. Return updated record

### 3. `DELETE /api/v1/customer/devices/{device_id}/connection`

Remove the connection record.

**Logic:**
1. Delete from `device_connections` where tenant_id + device_id match
2. Return 204

## Pydantic Model

```python
class ConnectionUpsert(BaseModel):
    connection_type: str = Field(default="cellular", pattern=r"^(cellular|ethernet|wifi|lora|satellite|other)$")
    carrier_name: str | None = Field(default=None, max_length=100)
    carrier_account_id: str | None = Field(default=None, max_length=100)
    plan_name: str | None = Field(default=None, max_length=100)
    apn: str | None = Field(default=None, max_length=100)
    sim_iccid: str | None = Field(default=None, max_length=30)
    sim_status: str | None = Field(default=None, pattern=r"^(active|suspended|deactivated|ready|unknown)$")
    data_limit_mb: int | None = Field(default=None, ge=0)
    billing_cycle_start: int | None = Field(default=None, ge=1, le=28)
    ip_address: str | None = Field(default=None, max_length=45)
    msisdn: str | None = Field(default=None, max_length=20)
```

## Verification

```bash
cd services/ui_iot && python3 -c "from routes.sensors import router; print([r.path for r in router.routes])"
```
