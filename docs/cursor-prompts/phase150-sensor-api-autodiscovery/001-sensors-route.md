# Task 001 — Create `routes/sensors.py` with Full CRUD

## File

Create `services/ui_iot/routes/sensors.py`

## Endpoints

### 1. `GET /api/v1/customer/devices/{device_id}/sensors`

List all sensors on a device.

**Query params:**
- `sensor_type` (optional) — filter by type (e.g., "temperature")
- `status` (optional) — filter by status (e.g., "active")

**Response:**
```json
{
  "device_id": "GW-001",
  "sensors": [
    {
      "sensor_id": 1,
      "metric_name": "temperature",
      "sensor_type": "temperature",
      "label": "Server Room Temperature",
      "unit": "°C",
      "min_range": -10,
      "max_range": 60,
      "precision_digits": 1,
      "status": "active",
      "auto_discovered": true,
      "last_value": 22.4,
      "last_seen_at": "2026-02-18T10:30:00Z",
      "created_at": "2025-08-18T10:00:00Z"
    }
  ],
  "total": 5,
  "sensor_limit": 10
}
```

**Logic:**
1. Verify device exists: `SELECT 1 FROM device_registry WHERE tenant_id = $1 AND device_id = $2`
2. If not found → 404
3. Query `sensors` table with optional filters
4. Get effective sensor limit (from device_registry.sensor_limit or device_tiers.default_sensor_limit)
5. Return sensor list + total + limit

### 2. `GET /api/v1/customer/sensors`

List all sensors across all devices for the tenant.

**Query params:**
- `sensor_type` (optional)
- `status` (optional)
- `device_id` (optional)
- `limit` (default 50, max 200)
- `offset` (default 0)

**Response:**
```json
{
  "sensors": [...],
  "total": 16,
  "limit": 50,
  "offset": 0
}
```

### 3. `POST /api/v1/customer/devices/{device_id}/sensors`

Manually create a sensor on a device.

**Request body (Pydantic model `SensorCreate`):**
```json
{
  "metric_name": "ambient_temp",
  "sensor_type": "temperature",
  "label": "Ambient Temperature Sensor",
  "unit": "°C",
  "min_range": -40,
  "max_range": 80,
  "precision_digits": 1
}
```

**Logic:**
1. Verify device exists
2. Check sensor limit: count existing sensors vs effective limit. If at limit → 409 Conflict with message "Sensor limit reached for this device ({current}/{limit})"
3. Check uniqueness: metric_name must be unique for this device. If duplicate → 409 "Sensor with metric_name '{name}' already exists on this device"
4. Insert into `sensors` table with `auto_discovered = false`
5. Return the created sensor record with status 201

### 4. `PUT /api/v1/customer/sensors/{sensor_id}`

Update sensor metadata. Only label, unit, min_range, max_range, precision_digits, status, sensor_type can be updated. metric_name is immutable.

**Request body (Pydantic model `SensorUpdate`):**
```json
{
  "label": "Updated Label",
  "unit": "°F",
  "status": "disabled"
}
```

**Logic:**
1. Fetch sensor by sensor_id, verify tenant_id matches
2. If not found → 404
3. Build dynamic UPDATE with only provided fields (skip None values)
4. Return updated sensor record

### 5. `DELETE /api/v1/customer/sensors/{sensor_id}`

Delete a sensor record. Does NOT delete historical telemetry data (telemetry is stored by device_id + metric key, not sensor_id).

**Logic:**
1. Verify sensor exists and belongs to tenant
2. Delete from sensors table
3. Return 204 No Content

## Pydantic Models

```python
class SensorCreate(BaseModel):
    metric_name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z][a-zA-Z0-9_]*$")
    sensor_type: str = Field(..., min_length=1, max_length=50)
    label: str | None = Field(default=None, max_length=200)
    unit: str | None = Field(default=None, max_length=20)
    min_range: float | None = None
    max_range: float | None = None
    precision_digits: int = Field(default=1, ge=0, le=6)

class SensorUpdate(BaseModel):
    sensor_type: str | None = Field(default=None, min_length=1, max_length=50)
    label: str | None = Field(default=None, max_length=200)
    unit: str | None = Field(default=None, max_length=20)
    min_range: float | None = None
    max_range: float | None = None
    precision_digits: int | None = Field(default=None, ge=0, le=6)
    status: str | None = Field(default=None, pattern=r"^(active|disabled)$")
```

## Implementation Pattern

Follow the exact patterns from `routes/devices.py` and `routes/dashboards.py`:

```python
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional

from middleware.auth import JWTBearer
from middleware.tenant import inject_tenant_context, get_tenant_id, get_user, require_customer
from db.pool import tenant_connection
from dependencies import get_db_pool

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/customer",
    tags=["sensors"],
    dependencies=[
        Depends(JWTBearer()),
        Depends(inject_tenant_context),
        Depends(require_customer),
    ],
)
```

## Sensor Limit Check Helper

```python
async def _get_effective_sensor_limit(conn, tenant_id: str, device_id: str) -> int:
    """Get the effective sensor limit for a device (device override > tier default > 20)."""
    row = await conn.fetchrow(
        """
        SELECT dr.sensor_limit, dt.default_sensor_limit
        FROM device_registry dr
        LEFT JOIN device_tiers dt ON dt.tier_id = dr.tier_id
        WHERE dr.tenant_id = $1 AND dr.device_id = $2
        """,
        tenant_id, device_id,
    )
    if not row:
        return 20
    return row["sensor_limit"] or row["default_sensor_limit"] or 20
```

## Verification

```bash
cd services/ui_iot && python3 -c "from routes.sensors import router; print('OK:', len(router.routes), 'routes')"
```
