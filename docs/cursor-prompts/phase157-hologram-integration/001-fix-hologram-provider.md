# Task 1: Fix HologramProvider Auth + All API Methods, Add claim_sim/list_plans

## File
`services/ui_iot/services/carrier_service.py`

## Context

The `HologramProvider` class (lines 101-164) has the wrong auth mechanism and incorrect endpoints for most methods. The `CarrierProvider` abstract base class (lines 62-98) needs two new abstract methods. The `OneNCEProvider` (lines 167-227) needs stub implementations of those new methods. The `get_carrier_provider()` factory (lines 238-255) is already correct.

## Changes

### 1. Fix HologramProvider.__init__ (line 107-115) — Auth from headers to query params

Replace the `__init__` method. Change `headers={"apikey": ...}` to `params={"apikey": ...}`:

```python
def __init__(self, api_key: str, account_id: str | None = None, base_url: str | None = None):
    self.api_key = api_key
    self.account_id = account_id
    self.base_url = base_url or "https://dashboard.hologram.io/api/1"
    self.client = httpx.AsyncClient(
        base_url=self.base_url,
        params={"apikey": self.api_key},
        timeout=30.0,
    )
```

The ONLY change: line 113 goes from `headers={"apikey": self.api_key},` to `params={"apikey": self.api_key},`.

### 2. Enhance get_device_info (line 117-130) — Add state mapping

The endpoint `GET /devices/{id}` is correct. Enhance the response parsing to map Hologram states to our enum:

```python
async def get_device_info(self, carrier_device_id: str) -> CarrierDeviceInfo:
    resp = await self.client.get(f"/devices/{carrier_device_id}")
    resp.raise_for_status()
    data = resp.json().get("data", {})
    links = data.get("links", {}).get("cellular", [])
    link = links[0] if links else {}
    last_session = data.get("lastsession", {})

    # Map Hologram states to our enum
    hologram_state = (data.get("state") or "").lower()
    state_map = {"live": "active", "paused": "suspended", "deactivated": "deactivated"}
    sim_status = state_map.get(hologram_state, hologram_state or None)

    # Infer network status from last session
    network_status = "connected" if last_session.get("active") else "disconnected"

    return CarrierDeviceInfo(
        carrier_device_id=carrier_device_id,
        iccid=link.get("sim"),
        sim_status=sim_status,
        network_status=network_status,
        ip_address=last_session.get("ip"),
        network_type=link.get("networktype"),
        last_connection=link.get("last_connect_time"),
        raw=data,
    )
```

### 3. Fix get_usage (line 132-140) — Wrong endpoint entirely

Replace `GET /devices/{id}/usage` with `GET /usage/data?deviceid={id}`:

```python
async def get_usage(self, carrier_device_id: str) -> CarrierUsageInfo:
    resp = await self.client.get(
        "/usage/data", params={"deviceid": carrier_device_id}
    )
    resp.raise_for_status()
    records = resp.json().get("data", [])
    total_bytes = sum(r.get("bytes", 0) for r in records)
    return CarrierUsageInfo(
        carrier_device_id=carrier_device_id,
        data_used_bytes=total_bytes,
        sessions=records,
        raw={"records": records},
    )
```

### 4. Fix activate_sim (line 142-144) — Wrong endpoint

Replace `POST /devices/{id}/activate` with `POST /devices/{id}/state` body `{"state":"live"}`:

```python
async def activate_sim(self, carrier_device_id: str) -> bool:
    resp = await self.client.post(
        f"/devices/{carrier_device_id}/state", json={"state": "live"}
    )
    return resp.status_code == 200
```

### 5. Fix suspend_sim (line 146-148) — Wrong endpoint

Replace `POST /devices/{id}/pause` with `POST /devices/{id}/state` body `{"state":"pause"}`:

```python
async def suspend_sim(self, carrier_device_id: str) -> bool:
    resp = await self.client.post(
        f"/devices/{carrier_device_id}/state", json={"state": "pause"}
    )
    return resp.status_code == 200
```

### 6. Fix deactivate_sim (line 150-152) — Wrong endpoint

Replace `POST /devices/{id}/deactivate` with `POST /devices/{id}/state` body `{"state":"deactivate"}`:

```python
async def deactivate_sim(self, carrier_device_id: str) -> bool:
    resp = await self.client.post(
        f"/devices/{carrier_device_id}/state", json={"state": "deactivate"}
    )
    return resp.status_code == 200
```

### 7. Fix send_sms (line 154-159) — Wrong field name casing

Change `"fromNumber"` to `"fromnumber"` (Hologram API uses all lowercase):

```python
async def send_sms(self, carrier_device_id: str, message: str) -> bool:
    resp = await self.client.post(
        "/sms/incoming",
        json={"deviceid": int(carrier_device_id), "body": message, "fromnumber": "system"},
    )
    return resp.status_code == 200
```

### 8. Enhance get_network_diagnostics (line 161-164) — Add cellular link data

Fetch both device info and cellular link details for richer diagnostics:

```python
async def get_network_diagnostics(self, carrier_device_id: str) -> dict[str, Any]:
    resp = await self.client.get(f"/devices/{carrier_device_id}")
    resp.raise_for_status()
    device_data = resp.json().get("data", {})

    link_data = {}
    try:
        link_resp = await self.client.get(
            "/links/cellular", params={"deviceid": carrier_device_id}
        )
        if link_resp.status_code == 200:
            link_data = link_resp.json().get("data", [])
    except Exception:
        pass  # Non-critical; return device data alone

    return {
        "device": device_data,
        "cellular_links": link_data,
    }
```

### 9. Add two new abstract methods to CarrierProvider (after line 98)

Insert before the `HologramProvider` class definition, at the end of the `CarrierProvider` abstract class (after `get_network_diagnostics`):

```python
async def claim_sim(self, iccid: str, plan_id: int | None = None) -> dict:
    """Claim/provision a new SIM card. Returns carrier device info."""
    raise NotImplementedError

async def list_plans(self) -> list[dict]:
    """List available data plans from the carrier."""
    raise NotImplementedError
```

Note: These are NOT `@abstractmethod` — they have default implementations that raise `NotImplementedError`. This avoids breaking existing subclasses that don't support these operations.

### 10. Add claim_sim and list_plans to HologramProvider

Add these two methods at the end of the `HologramProvider` class (after `get_network_diagnostics`):

```python
async def claim_sim(self, iccid: str, plan_id: int | None = None) -> dict:
    body: dict[str, Any] = {"sim": iccid}
    if plan_id:
        body["plan"] = plan_id
    resp = await self.client.post(
        f"/links/cellular/sim_{iccid}/claim", json=body
    )
    resp.raise_for_status()
    return resp.json().get("data", {})

async def list_plans(self) -> list[dict]:
    params: dict[str, Any] = {}
    if self.account_id:
        params["orgid"] = self.account_id
    resp = await self.client.get("/plans", params=params)
    resp.raise_for_status()
    return resp.json().get("data", [])
```

### 11. Add no-op stubs to OneNCEProvider

Add these two methods at the end of the `OneNCEProvider` class (after `get_network_diagnostics`):

```python
async def claim_sim(self, iccid: str, plan_id: int | None = None) -> dict:
    # 1NCE SIMs are pre-provisioned; no claim flow needed.
    return {"iccid": iccid, "note": "1NCE SIMs are pre-provisioned"}

async def list_plans(self) -> list[dict]:
    # 1NCE has a single flat-rate plan; not queryable via API.
    return []
```

## Verification

```bash
cd services/ui_iot && python -c "
from services.carrier_service import HologramProvider, OneNCEProvider

# Verify auth is query param, not header
p = HologramProvider('test-key', account_id='12345')
assert 'apikey' not in (p.client.headers or {}), 'apikey should not be in headers'
# httpx stores params internally — verify the client was created with params
print('HologramProvider client created OK')

# Verify OneNCE stubs exist
o = OneNCEProvider('test-key')
import asyncio
result = asyncio.run(o.list_plans())
assert result == [], 'OneNCE list_plans should return empty list'
print('OneNCEProvider stubs OK')

print('All checks passed')
"
```
