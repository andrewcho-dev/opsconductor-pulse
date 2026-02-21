# 140-005: Route Coverage — Alerts & Alert Rules (Target: 70%+)

## Task
Write tests for `services/ui_iot/routes/alerts.py` covering alert CRUD, acknowledge, close, silence, and alert rules.

## File
`tests/unit/test_alerts_routes.py` (create or extend)

## Route Endpoints (from alerts.py)
```python
router = APIRouter(prefix="/api/v1/customer", dependencies=[JWTBearer(), inject_tenant_context, require_customer])

GET    /alerts                        # list_alerts (pagination, filters)
GET    /alerts/{alert_id}             # get_alert
PATCH  /alerts/{alert_id}/acknowledge # acknowledge_alert
PATCH  /alerts/{alert_id}/silence     # silence_alert (requires alerts.silence permission)
POST   /alert-rules                   # create_alert_rule (+ check_alert_rule_limit)
GET    /alert-rules                   # list_alert_rules
GET    /alert-rules/{rule_id}         # get_alert_rule
PATCH  /alert-rules/{rule_id}         # update_alert_rule
DELETE /alert-rules/{rule_id}         # delete_alert_rule
GET    /alert-digest-settings         # get_alert_digest_settings
PUT    /alert-digest-settings         # put_alert_digest_settings
```

## Test Cases

### Alert List & Detail
```python
async def test_list_alerts_default(client, monkeypatch):
    """GET /alerts returns alerts for tenant."""
    conn = FakeConn()
    conn.fetch_result = [
        {"alert_id": 1, "tenant_id": "tenant-a", "device_id": "d1", "severity": 2,
         "status": "OPEN", "alert_type": "THRESHOLD", "message": "High temp", ...}
    ]
    conn.fetchval_result = 1
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/alerts", headers=_auth_header())
    assert resp.status_code == 200
    assert len(resp.json()["alerts"]) == 1

async def test_list_alerts_filter_by_severity(client, monkeypatch):
    """GET /alerts?severity=1 filters by severity."""
    conn = FakeConn()
    conn.fetch_result = []
    conn.fetchval_result = 0
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/alerts?severity=1", headers=_auth_header())
    assert resp.status_code == 200

async def test_list_alerts_filter_by_status(client, monkeypatch):
    """GET /alerts?status=OPEN filters by status."""

async def test_get_alert_success(client, monkeypatch):
    """GET /alerts/{id} returns single alert."""
    conn = FakeConn()
    conn.fetchrow_result = {"alert_id": 1, "tenant_id": "tenant-a", ...}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/alerts/1", headers=_auth_header())
    assert resp.status_code == 200

async def test_get_alert_not_found(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = None
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/alerts/999", headers=_auth_header())
    assert resp.status_code == 404
```

### Alert Actions
```python
async def test_acknowledge_alert_success(client, monkeypatch):
    """PATCH /alerts/{id}/acknowledge marks alert as acknowledged."""
    conn = FakeConn()
    conn.fetchrow_result = {"alert_id": 1, "status": "OPEN"}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.patch("/api/v1/customer/alerts/1/acknowledge", headers=_auth_header())
    assert resp.status_code == 200

async def test_acknowledge_already_acknowledged(client, monkeypatch):
    """Acknowledging an already-acknowledged alert."""
    conn = FakeConn()
    conn.fetchrow_result = {"alert_id": 1, "status": "ACKNOWLEDGED"}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.patch("/api/v1/customer/alerts/1/acknowledge", headers=_auth_header())
    # May return 200 (idempotent) or 409 (conflict)

async def test_silence_alert_requires_permission(client, monkeypatch):
    """PATCH /alerts/{id}/silence requires alerts.silence permission."""
    # Test with user who doesn't have the permission
    # Expect 403

async def test_silence_alert_success(client, monkeypatch):
    """PATCH /alerts/{id}/silence with valid duration."""
    conn = FakeConn()
    conn.fetchrow_result = {"alert_id": 1, "status": "OPEN"}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.patch("/api/v1/customer/alerts/1/silence", headers=_auth_header(),
        json={"duration_minutes": 60, "reason": "Maintenance window"})
    assert resp.status_code == 200
```

### Alert Rules CRUD
```python
async def test_create_alert_rule_success(client, monkeypatch):
    """POST /alert-rules creates a new rule."""
    conn = FakeConn()
    conn.fetchrow_result = {"rule_id": "new-rule-id", "name": "High Temp", ...}
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(alerts_routes, "check_alert_rule_limit", AsyncMock())

    resp = await client.post("/api/v1/customer/alert-rules", headers=_auth_header(),
        json={
            "name": "High Temperature",
            "metric_name": "temp_c",
            "operator": "GT",
            "threshold": 35,
            "severity": 3,
        })
    assert resp.status_code in (200, 201)

async def test_create_alert_rule_missing_name(client, monkeypatch):
    """POST /alert-rules with missing name returns 422."""
    _mock_customer_deps(monkeypatch, FakeConn())
    resp = await client.post("/api/v1/customer/alert-rules", headers=_auth_header(),
        json={"metric_name": "temp_c", "operator": "GT", "threshold": 35})
    assert resp.status_code == 422

async def test_list_alert_rules(client, monkeypatch):
    conn = FakeConn()
    conn.fetch_result = [{"rule_id": "r1", "name": "Rule 1", ...}]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/alert-rules", headers=_auth_header())
    assert resp.status_code == 200

async def test_update_alert_rule(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"rule_id": "r1", "name": "Updated Rule"}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.patch("/api/v1/customer/alert-rules/r1", headers=_auth_header(),
        json={"name": "Updated Rule Name"})
    assert resp.status_code == 200

async def test_delete_alert_rule(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"rule_id": "r1"}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.delete("/api/v1/customer/alert-rules/r1", headers=_auth_header())
    assert resp.status_code in (200, 204)

async def test_delete_alert_rule_not_found(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = None
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.delete("/api/v1/customer/alert-rules/missing", headers=_auth_header())
    assert resp.status_code == 404
```

### Alert Digest Settings
```python
async def test_get_digest_settings(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"frequency": "daily", "enabled": True}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/alert-digest-settings", headers=_auth_header())
    assert resp.status_code == 200

async def test_update_digest_settings(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.put("/api/v1/customer/alert-digest-settings", headers=_auth_header(),
        json={"frequency": "weekly", "enabled": True})
    assert resp.status_code == 200
```

## Verification
```bash
pytest tests/unit/test_alerts_routes.py -v --cov=services/ui_iot/routes/alerts --cov-report=term-missing
# Target: >= 70% coverage on routes/alerts.py
```
