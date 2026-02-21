# 140-007: Route Coverage — OTA, Certificates, Escalation (Target: 60%+)

## Task
Write tests for OTA, certificates, and escalation route modules.

## Files to Create
- `tests/unit/test_ota_routes.py`
- `tests/unit/test_certificates_routes.py`
- `tests/unit/test_escalation_routes.py`

---

## Part 1: OTA Routes

Read `services/ui_iot/routes/ota.py` for exact endpoints. Expected:
```python
GET    /api/v1/customer/firmware-versions            # list firmware
POST   /api/v1/customer/firmware-versions            # upload firmware
GET    /api/v1/customer/ota-campaigns                # list campaigns
POST   /api/v1/customer/ota-campaigns                # create campaign
GET    /api/v1/customer/ota-campaigns/{id}           # campaign detail
PATCH  /api/v1/customer/ota-campaigns/{id}/abort     # abort campaign
GET    /api/v1/customer/ota-campaigns/{id}/devices   # device status in campaign
```

### Test Cases
```python
async def test_list_firmware_versions(client, monkeypatch):
    conn = FakeConn()
    conn.fetch_result = [{"id": 1, "version": "1.0.0", "device_type": "sensor", ...}]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/firmware-versions", headers=_auth_header())
    assert resp.status_code == 200

async def test_create_campaign_success(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"id": 1, "name": "Update v1.1", "status": "CREATED"}
    conn.fetchval_result = 1  # firmware version exists
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post("/api/v1/customer/ota-campaigns", headers=_auth_header(),
        json={"name": "Update v1.1", "firmware_version_id": 1,
              "target_group_id": "all", "rollout_strategy": "linear"})
    assert resp.status_code in (200, 201)

async def test_abort_campaign_success(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"id": 1, "status": "RUNNING"}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.patch("/api/v1/customer/ota-campaigns/1/abort", headers=_auth_header())
    assert resp.status_code == 200

async def test_abort_campaign_already_completed(client, monkeypatch):
    """Cannot abort a completed campaign."""
    conn = FakeConn()
    conn.fetchrow_result = {"id": 1, "status": "COMPLETED"}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.patch("/api/v1/customer/ota-campaigns/1/abort", headers=_auth_header())
    assert resp.status_code in (400, 409)

async def test_get_campaign_device_status(client, monkeypatch):
    conn = FakeConn()
    conn.fetch_result = [{"device_id": "d1", "status": "SUCCEEDED"}, ...]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/ota-campaigns/1/devices", headers=_auth_header())
    assert resp.status_code == 200
```

---

## Part 2: Certificates Routes

Read `services/ui_iot/routes/certificates.py` for exact endpoints. Expected:
```python
GET    /api/v1/customer/devices/{device_id}/certificates   # list certs
POST   /api/v1/customer/devices/{device_id}/certificates   # upload cert
PATCH  /api/v1/customer/certificates/{id}/revoke           # revoke cert
```

### Test Cases
```python
async def test_list_device_certificates(client, monkeypatch):
    conn = FakeConn()
    conn.fetch_result = [{"id": 1, "common_name": "device.iot.local", "status": "ACTIVE", ...}]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/devices/d1/certificates", headers=_auth_header())
    assert resp.status_code == 200

async def test_revoke_certificate_success(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"id": 1, "status": "ACTIVE"}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.patch("/api/v1/customer/certificates/1/revoke", headers=_auth_header())
    assert resp.status_code == 200

async def test_revoke_already_revoked(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"id": 1, "status": "REVOKED"}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.patch("/api/v1/customer/certificates/1/revoke", headers=_auth_header())
    assert resp.status_code in (400, 409)
```

---

## Part 3: Escalation Routes

Read `services/ui_iot/routes/escalation.py` for exact endpoints. Expected:
```python
GET    /api/v1/customer/escalation-policies          # list policies
POST   /api/v1/customer/escalation-policies          # create policy
GET    /api/v1/customer/escalation-policies/{id}     # policy detail
PATCH  /api/v1/customer/escalation-policies/{id}     # update policy
DELETE /api/v1/customer/escalation-policies/{id}     # delete policy
```

### Test Cases
```python
async def test_list_escalation_policies(client, monkeypatch):
    conn = FakeConn()
    conn.fetch_result = [{"policy_id": 1, "name": "Default", "is_default": True, ...}]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/escalation-policies", headers=_auth_header())
    assert resp.status_code == 200

async def test_create_policy_success(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"policy_id": 1, "name": "New Policy"}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post("/api/v1/customer/escalation-policies", headers=_auth_header(),
        json={"name": "Critical Escalation", "description": "For critical alerts"})
    assert resp.status_code in (200, 201)

async def test_delete_default_policy_blocked(client, monkeypatch):
    """Cannot delete the default escalation policy."""
    conn = FakeConn()
    conn.fetchrow_result = {"policy_id": 1, "is_default": True}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.delete("/api/v1/customer/escalation-policies/1", headers=_auth_header())
    assert resp.status_code in (400, 409)
```

## Verification
```bash
pytest tests/unit/test_ota_routes.py tests/unit/test_certificates_routes.py tests/unit/test_escalation_routes.py \
  -v --cov=services/ui_iot/routes/ota --cov=services/ui_iot/routes/certificates --cov=services/ui_iot/routes/escalation \
  --cov-report=term-missing
# Each module: >= 60% coverage
```
