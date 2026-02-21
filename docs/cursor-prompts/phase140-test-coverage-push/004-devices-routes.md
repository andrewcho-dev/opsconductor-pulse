# 140-004: Route Coverage — Devices (Target: 70%+)

## Task
Write tests for `services/ui_iot/routes/devices.py` covering CRUD, entitlements, twin, bulk, and decommission.

## File
`tests/unit/test_devices_routes.py` (extend existing `test_device_management.py` or create new file)

## Route Endpoints (from devices.py)
```python
router = APIRouter(prefix="/api/v1/customer", dependencies=[JWTBearer(), inject_tenant_context, require_customer])

POST   /devices                    # create_device (+ check_device_limit)
GET    /devices                    # list_devices (pagination: page, limit)
GET    /devices/{device_id}        # get_device_detail
PATCH  /devices/{device_id}        # update_device
DELETE /devices/{device_id}        # delete_device
GET    /device-tiers               # list_customer_device_tiers
PUT    /devices/{device_id}/tier   # assign_device_tier (+ check_device_limit)
```

## Existing Test Pattern (FakeConn + monkeypatch)
```python
class FakeConn:
    def __init__(self):
        self.fetchrow_result = None
        self.fetch_result = []
        self.fetchval_result = 0
    async def fetchrow(self, query, *args): return self.fetchrow_result
    async def fetch(self, query, *args): return self.fetch_result
    async def fetchval(self, query, *args): return self.fetchval_result
    async def execute(self, *args, **kwargs): return "OK"

def _mock_customer_deps(monkeypatch, conn, tenant_id="tenant-a"):
    # Sets up auth/tenant/pool mocking
    ...
```

## Test Cases

### CRUD Operations
```python
async def test_list_devices_returns_paginated(client, monkeypatch):
    """GET /devices returns paginated device list."""
    conn = FakeConn()
    conn.fetch_result = [
        {"device_id": "d1", "tenant_id": "tenant-a", "site_id": "s1", "status": "ACTIVE", ...},
        {"device_id": "d2", "tenant_id": "tenant-a", "site_id": "s1", "status": "ACTIVE", ...},
    ]
    conn.fetchval_result = 2  # total count
    _mock_customer_deps(monkeypatch, conn)

    resp = await client.get("/api/v1/customer/devices?limit=50&offset=0", headers=_auth_header())
    assert resp.status_code == 200
    data = resp.json()
    assert "devices" in data
    assert data["total"] == 2

async def test_list_devices_with_search_filter(client, monkeypatch):
    """GET /devices?search=sensor filters by device name."""
    conn = FakeConn()
    conn.fetch_result = [{"device_id": "sensor-01", ...}]
    conn.fetchval_result = 1
    _mock_customer_deps(monkeypatch, conn)

    resp = await client.get("/api/v1/customer/devices?search=sensor", headers=_auth_header())
    assert resp.status_code == 200

async def test_get_device_detail_success(client, monkeypatch):
    """GET /devices/{id} returns device details."""
    conn = FakeConn()
    conn.fetchrow_result = {"device_id": "d1", "tenant_id": "tenant-a", ...}
    _mock_customer_deps(monkeypatch, conn)

    resp = await client.get("/api/v1/customer/devices/d1", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["device"]["device_id"] == "d1"

async def test_get_device_not_found(client, monkeypatch):
    """GET /devices/{id} returns 404 for nonexistent device."""
    conn = FakeConn()
    conn.fetchrow_result = None
    _mock_customer_deps(monkeypatch, conn)

    resp = await client.get("/api/v1/customer/devices/nonexistent", headers=_auth_header())
    assert resp.status_code == 404

async def test_create_device_success(client, monkeypatch):
    """POST /devices creates a new device."""
    conn = FakeConn()
    conn.fetchrow_result = {"device_id": "new-device", "tenant_id": "tenant-a", ...}
    _mock_customer_deps(monkeypatch, conn)
    # Mock entitlement check
    monkeypatch.setattr(devices_routes, "check_device_limit", AsyncMock())

    resp = await client.post("/api/v1/customer/devices", headers=_auth_header(),
        json={"device_id": "new-device", "site_id": "site-1"})
    assert resp.status_code in (200, 201)

async def test_create_device_over_limit(client, monkeypatch):
    """POST /devices fails when device limit is reached."""
    # Mock check_device_limit to raise HTTPException(403)

async def test_update_device_success(client, monkeypatch):
    """PATCH /devices/{id} updates device fields."""
    conn = FakeConn()
    conn.fetchrow_result = {"device_id": "d1", "tenant_id": "tenant-a", "model": "updated"}
    _mock_customer_deps(monkeypatch, conn)

    resp = await client.patch("/api/v1/customer/devices/d1", headers=_auth_header(),
        json={"model": "DHT22-v2"})
    assert resp.status_code == 200

async def test_delete_device_success(client, monkeypatch):
    """DELETE /devices/{id} decommissions device."""
    conn = FakeConn()
    conn.fetchrow_result = {"device_id": "d1"}
    _mock_customer_deps(monkeypatch, conn)

    resp = await client.delete("/api/v1/customer/devices/d1", headers=_auth_header())
    assert resp.status_code in (200, 204)

async def test_delete_device_not_found(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = None
    _mock_customer_deps(monkeypatch, conn)

    resp = await client.delete("/api/v1/customer/devices/missing", headers=_auth_header())
    assert resp.status_code == 404
```

### Auth/RBAC Enforcement
```python
async def test_devices_requires_auth(client):
    """Unauthenticated request returns 401."""
    resp = await client.get("/api/v1/customer/devices")
    assert resp.status_code == 401

async def test_devices_requires_customer_role(client, monkeypatch):
    """Operator role cannot access customer device routes."""
    # Set up operator auth context
    # Expect 403
```

### Pagination Edge Cases
```python
async def test_list_devices_page_beyond_total(client, monkeypatch):
    """Page beyond total returns empty list."""
    conn = FakeConn()
    conn.fetch_result = []
    conn.fetchval_result = 5  # 5 total but requesting page 100
    _mock_customer_deps(monkeypatch, conn)

    resp = await client.get("/api/v1/customer/devices?page=100&limit=50", headers=_auth_header())
    assert resp.status_code == 200
    assert len(resp.json()["devices"]) == 0

async def test_list_devices_invalid_limit(client, monkeypatch):
    """Invalid limit parameter returns 422."""
    _mock_customer_deps(monkeypatch, FakeConn())
    resp = await client.get("/api/v1/customer/devices?limit=-1", headers=_auth_header())
    assert resp.status_code == 422
```

### Device Tier Operations
```python
async def test_list_device_tiers(client, monkeypatch):
    conn = FakeConn()
    conn.fetch_result = [{"tier_id": "basic", "name": "Basic", ...}]
    _mock_customer_deps(monkeypatch, conn)

    resp = await client.get("/api/v1/customer/device-tiers", headers=_auth_header())
    assert resp.status_code == 200

async def test_assign_device_tier(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"device_id": "d1"}
    _mock_customer_deps(monkeypatch, conn)

    resp = await client.put("/api/v1/customer/devices/d1/tier", headers=_auth_header(),
        json={"tier_id": "premium"})
    assert resp.status_code in (200, 204)
```

## Verification
```bash
pytest tests/unit/test_devices_routes.py -v --cov=services/ui_iot/routes/devices --cov-report=term-missing
# Target: >= 70% coverage on routes/devices.py
```
