# 140-002: Critical Path — Tenant Middleware (Target: 90%+)

## Task
Write comprehensive tests for `services/ui_iot/middleware/tenant.py` (103 lines).

## File
`tests/unit/test_tenant_middleware.py` (extend existing file)

## Key Functions (from tenant.py)
1. `set_tenant_context(tenant_id, user)` — sets ContextVars
2. `get_tenant_id()` — returns tenant from ContextVar, raises 401 if missing
3. `get_user()` — returns user payload from ContextVar, raises 401 if missing
4. `get_user_roles()` — extracts realm_access.roles from user payload
5. `is_operator()` — checks if "operator" or "operator-admin" in roles
6. `inject_tenant_context(request)` — dependency that extracts tenant from JWT
7. `require_customer(request)` — enforces customer role
8. `require_operator(request)` — enforces operator role
9. `require_operator_admin(request)` — enforces operator-admin role

## Existing Test Helpers
```python
def _tenant_module():
    return importlib.import_module("middleware.tenant")

def _make_request(user=None):
    scope = {"type": "http", "method": "GET", "path": "/", "headers": []}
    request = Request(scope)
    if user is not None:
        request.state.user = user
    return request

def _user_payload(tenant_id, roles):
    payload = {"realm_access": {"roles": roles}}
    if tenant_id:
        payload["organization"] = {tenant_id: {}}
        payload["tenant_id"] = tenant_id
    return payload
```

## Test Cases to Add

### set_tenant_context / get_tenant_id / get_user
```python
async def test_set_and_get_tenant_context():
    """Setting tenant context makes it retrievable."""
    tenant = _tenant_module()
    tenant.set_tenant_context("tenant-a", {"sub": "user-1"})
    assert tenant.get_tenant_id() == "tenant-a"

async def test_get_tenant_id_without_context_raises_401():
    """get_tenant_id without prior set raises 401."""
    tenant = _tenant_module()
    # Reset context vars
    tenant.tenant_context.set(None)  # or however the module clears context
    with pytest.raises(HTTPException) as err:
        tenant.get_tenant_id()
    assert err.value.status_code == 401

async def test_get_user_returns_payload():
    tenant = _tenant_module()
    user = {"sub": "user-1", "email": "test@example.com"}
    tenant.set_tenant_context("t1", user)
    assert tenant.get_user() == user

async def test_get_user_without_context_raises_401():
    tenant = _tenant_module()
    tenant.user_context.set(None)
    with pytest.raises(HTTPException) as err:
        tenant.get_user()
    assert err.value.status_code == 401
```

### get_user_roles
```python
async def test_get_user_roles_extracts_realm_roles():
    tenant = _tenant_module()
    tenant.set_tenant_context("t1", {"realm_access": {"roles": ["customer", "tenant-admin"]}})
    roles = tenant.get_user_roles()
    assert "customer" in roles
    assert "tenant-admin" in roles

async def test_get_user_roles_empty_when_no_realm_access():
    tenant = _tenant_module()
    tenant.set_tenant_context("t1", {"sub": "user-1"})  # no realm_access
    roles = tenant.get_user_roles()
    assert roles == [] or roles == set()

async def test_get_user_roles_empty_when_no_roles_key():
    tenant = _tenant_module()
    tenant.set_tenant_context("t1", {"realm_access": {}})
    roles = tenant.get_user_roles()
    assert len(roles) == 0
```

### is_operator
```python
async def test_is_operator_true_for_operator_role():
    tenant = _tenant_module()
    tenant.set_tenant_context("t1", _user_payload("t1", ["operator"]))
    assert tenant.is_operator() is True

async def test_is_operator_true_for_operator_admin_role():
    tenant = _tenant_module()
    tenant.set_tenant_context("t1", _user_payload("t1", ["operator-admin"]))
    assert tenant.is_operator() is True

async def test_is_operator_false_for_customer_role():
    tenant = _tenant_module()
    tenant.set_tenant_context("t1", _user_payload("t1", ["customer"]))
    assert tenant.is_operator() is False
```

### inject_tenant_context
```python
async def test_inject_tenant_context_extracts_tenant_from_organization():
    """Extracts tenant_id from JWT organization claim."""
    tenant = _tenant_module()
    request = _make_request(_user_payload("tenant-a", ["customer", "tenant-admin"]))
    await tenant.inject_tenant_context(request)
    assert tenant.get_tenant_id() == "tenant-a"

async def test_inject_tenant_context_multi_tenant_user():
    """Handles user with access to multiple tenants."""
    tenant = _tenant_module()
    user = {
        "realm_access": {"roles": ["customer"]},
        "organization": {"tenant-a": {}, "tenant-b": {}},
        "tenant_id": "tenant-a",
    }
    request = _make_request(user)
    await tenant.inject_tenant_context(request)
    assert tenant.get_tenant_id() == "tenant-a"

async def test_inject_tenant_context_missing_user_state():
    """Missing request.state.user raises appropriate error."""
    tenant = _tenant_module()
    request = _make_request()  # no user set
    with pytest.raises((HTTPException, AttributeError)):
        await tenant.inject_tenant_context(request)

async def test_inject_tenant_context_operator_with_tenant_header():
    """Operator can override tenant via X-Tenant-Id header."""
    tenant = _tenant_module()
    user = _user_payload(None, ["operator"])
    request = _make_request(user)
    # If the middleware reads tenant from header for operators:
    # Add X-Tenant-Id header and verify it's used
```

### require_customer / require_operator / require_operator_admin
```python
async def test_require_customer_allows_customer_role():
    tenant = _tenant_module()
    request = _make_request(_user_payload("t1", ["customer"]))
    await tenant.inject_tenant_context(request)
    await tenant.require_customer(request)  # should not raise

async def test_require_customer_blocks_operator_role():
    tenant = _tenant_module()
    request = _make_request(_user_payload("t1", ["operator"]))
    await tenant.inject_tenant_context(request)
    with pytest.raises(HTTPException) as err:
        await tenant.require_customer(request)
    assert err.value.status_code == 403

async def test_require_operator_allows_operator_role():
    tenant = _tenant_module()
    request = _make_request(_user_payload(None, ["operator"]))
    await tenant.inject_tenant_context(request)
    await tenant.require_operator(request)  # should not raise

async def test_require_operator_blocks_customer_role():
    tenant = _tenant_module()
    request = _make_request(_user_payload("t1", ["customer"]))
    await tenant.inject_tenant_context(request)
    with pytest.raises(HTTPException) as err:
        await tenant.require_operator(request)
    assert err.value.status_code == 403

async def test_require_operator_admin_allows_operator_admin():
    tenant = _tenant_module()
    request = _make_request(_user_payload(None, ["operator-admin"]))
    await tenant.inject_tenant_context(request)
    await tenant.require_operator_admin(request)  # should not raise

async def test_require_operator_admin_blocks_regular_operator():
    tenant = _tenant_module()
    request = _make_request(_user_payload(None, ["operator"]))
    await tenant.inject_tenant_context(request)
    with pytest.raises(HTTPException) as err:
        await tenant.require_operator_admin(request)
    assert err.value.status_code == 403

async def test_require_operator_admin_blocks_customer():
    tenant = _tenant_module()
    request = _make_request(_user_payload("t1", ["customer", "tenant-admin"]))
    await tenant.inject_tenant_context(request)
    with pytest.raises(HTTPException) as err:
        await tenant.require_operator_admin(request)
    assert err.value.status_code == 403
```

## Verification
```bash
pytest tests/unit/test_tenant_middleware.py -v --cov=services/ui_iot/middleware/tenant --cov-report=term-missing
# Target: >= 90% coverage on tenant.py
```
