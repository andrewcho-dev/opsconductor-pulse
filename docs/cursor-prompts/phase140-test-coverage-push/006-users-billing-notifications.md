# 140-006: Route Coverage — Users, Billing, Notifications (Target: 70%+)

## Task
Write tests for users, billing, and notifications route modules.

## Files to Create
- `tests/unit/test_users_routes.py`
- `tests/unit/test_billing_routes.py`
- `tests/unit/test_notifications_routes.py`

---

## Part 1: Users Routes

### Endpoints (from routes/users.py)
Read `services/ui_iot/routes/users.py` to confirm exact endpoints. Expected:
```python
POST   /api/v1/customer/users/invite    # invite user
GET    /api/v1/customer/users           # list tenant users
PATCH  /api/v1/customer/users/{id}/role # update user role
DELETE /api/v1/customer/users/{id}      # remove user from tenant
```

### Test Cases
```python
async def test_list_users_success(client, monkeypatch):
    """Returns paginated user list for tenant."""
    conn = FakeConn()
    conn.fetch_result = [{"user_id": "u1", "username": "admin", "email": "a@b.com", ...}]
    conn.fetchval_result = 1
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/users", headers=_auth_header())
    assert resp.status_code == 200
    assert "users" in resp.json()

async def test_list_users_with_search(client, monkeypatch):
    """Search filter works on username/email."""

async def test_invite_user_success(client, monkeypatch):
    """POST /users/invite creates invitation."""
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    # Mock Keycloak user creation
    resp = await client.post("/api/v1/customer/users/invite", headers=_auth_header(),
        json={"email": "new@example.com", "role": "customer"})
    assert resp.status_code in (200, 201)

async def test_invite_user_invalid_email(client, monkeypatch):
    """Invalid email returns 422."""
    _mock_customer_deps(monkeypatch, FakeConn())
    resp = await client.post("/api/v1/customer/users/invite", headers=_auth_header(),
        json={"email": "not-an-email", "role": "customer"})
    assert resp.status_code == 422

async def test_change_user_role_success(client, monkeypatch):
    """PATCH /users/{id}/role updates role."""

async def test_remove_user_success(client, monkeypatch):
    """DELETE /users/{id} removes user."""

async def test_remove_user_cannot_remove_self(client, monkeypatch):
    """User cannot remove themselves."""
```

---

## Part 2: Billing Routes

### Endpoints (from routes/billing.py)
Read `services/ui_iot/routes/billing.py` to confirm exact endpoints. Expected:
```python
GET    /api/v1/customer/subscription     # get current subscription
POST   /api/v1/customer/subscription     # create/change subscription
GET    /api/v1/customer/plans            # list available plans
```

### Test Cases
```python
async def test_get_subscription_success(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"subscription_id": "sub-1", "plan_id": "pro", "status": "ACTIVE", ...}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/subscription", headers=_auth_header())
    assert resp.status_code == 200

async def test_get_subscription_none(client, monkeypatch):
    """No subscription returns appropriate response."""
    conn = FakeConn()
    conn.fetchrow_result = None
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/subscription", headers=_auth_header())
    assert resp.status_code in (200, 404)

async def test_list_plans(client, monkeypatch):
    conn = FakeConn()
    conn.fetch_result = [
        {"plan_id": "starter", "name": "Starter", "price_cents": 2900},
        {"plan_id": "pro", "name": "Professional", "price_cents": 9900},
    ]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/plans", headers=_auth_header())
    assert resp.status_code == 200
```

---

## Part 3: Notifications Routes

### Endpoints (from routes/notifications.py)
```python
GET    /api/v1/customer/notification-channels          # list channels
POST   /api/v1/customer/notification-channels          # create channel
PATCH  /api/v1/customer/notification-channels/{id}     # update channel
DELETE /api/v1/customer/notification-channels/{id}     # delete channel
POST   /api/v1/customer/notification-channels/{id}/test # test channel
GET    /api/v1/customer/notification-routing-rules     # list routing rules
POST   /api/v1/customer/notification-routing-rules     # create routing rule
```

### Test Cases
```python
async def test_list_channels_success(client, monkeypatch):
    conn = FakeConn()
    conn.fetch_result = [
        {"channel_id": 1, "name": "Slack", "channel_type": "webhook", "is_enabled": True, ...}
    ]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/notification-channels", headers=_auth_header())
    assert resp.status_code == 200

async def test_create_channel_success(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"channel_id": 1}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post("/api/v1/customer/notification-channels", headers=_auth_header(),
        json={"name": "Test Channel", "channel_type": "webhook",
              "config": {"url": "https://hooks.example.com/test"}})
    assert resp.status_code in (200, 201)

async def test_create_channel_ssrf_blocked(client, monkeypatch):
    """Channel with private IP webhook URL is rejected."""
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post("/api/v1/customer/notification-channels", headers=_auth_header(),
        json={"name": "Evil", "channel_type": "webhook",
              "config": {"url": "https://10.0.0.1/internal"}})
    assert resp.status_code == 400

async def test_test_channel_success(client, monkeypatch):
    """POST /notification-channels/{id}/test sends test notification."""
    conn = FakeConn()
    conn.fetchrow_result = {"channel_id": 1, "channel_type": "email", "config": {...}, ...}
    _mock_customer_deps(monkeypatch, conn)
    # Mock the actual sending
    resp = await client.post("/api/v1/customer/notification-channels/1/test", headers=_auth_header())
    assert resp.status_code in (200, 204)

async def test_delete_channel_success(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"channel_id": 1}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.delete("/api/v1/customer/notification-channels/1", headers=_auth_header())
    assert resp.status_code in (200, 204)

async def test_list_routing_rules(client, monkeypatch):
    conn = FakeConn()
    conn.fetch_result = [{"rule_id": 1, "channel_id": 1, "min_severity": 2, ...}]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/notification-routing-rules", headers=_auth_header())
    assert resp.status_code == 200

async def test_create_routing_rule(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"rule_id": 1}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post("/api/v1/customer/notification-routing-rules", headers=_auth_header(),
        json={"channel_id": 1, "min_severity": 2})
    assert resp.status_code in (200, 201)
```

## Verification
```bash
pytest tests/unit/test_users_routes.py tests/unit/test_billing_routes.py tests/unit/test_notifications_routes.py \
  -v --cov=services/ui_iot/routes/users --cov=services/ui_iot/routes/billing --cov=services/ui_iot/routes/notifications \
  --cov-report=term-missing
# Each module: >= 70% coverage
```
