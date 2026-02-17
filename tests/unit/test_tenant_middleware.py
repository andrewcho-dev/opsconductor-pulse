import importlib

import pytest
from fastapi import HTTPException
from starlette.requests import Request

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.fixture(scope="session", autouse=True)
async def setup_delivery_tables():
    yield


def _tenant_module():
    return importlib.import_module("middleware.tenant")


def _make_request(user=None):
    scope = {"type": "http", "method": "GET", "path": "/", "headers": []}
    request = Request(scope)
    if user is not None:
        request.state.user = user
    return request


def _user_payload(tenant_id: str | None, roles: list[str]) -> dict:
    payload = {"realm_access": {"roles": roles}}
    if tenant_id:
        payload["organization"] = {tenant_id: {}}
        payload["tenant_id"] = tenant_id
    return payload


@pytest.fixture(autouse=True)
def _reset_contextvars():
    tenant = _tenant_module()
    tenant.tenant_context.set(None)
    tenant.user_context.set(None)
    yield
    tenant.tenant_context.set(None)
    tenant.user_context.set(None)


async def test_set_and_get_tenant_context():
    tenant = _tenant_module()
    user = {"sub": "user-1"}
    tenant.set_tenant_context("tenant-a", user)
    assert tenant.get_tenant_id() == "tenant-a"
    assert tenant.get_user() == user


async def test_inject_tenant_context_extracts_tenant_id(monkeypatch):
    tenant = _tenant_module()
    request = _make_request(_user_payload("tenant-a", ["customer", "tenant-admin"]))

    await tenant.inject_tenant_context(request)
    assert tenant.get_tenant_id() == "tenant-a"


async def test_inject_tenant_context_organization_list_shape():
    tenant = _tenant_module()
    user = {
        "realm_access": {"roles": ["customer"]},
        "organization": ["tenant-a", "tenant-b"],
    }
    request = _make_request(user)
    await tenant.inject_tenant_context(request)
    assert tenant.get_tenant_id() == "tenant-a"


async def test_inject_tenant_context_legacy_tenant_id_fallback():
    tenant = _tenant_module()
    user = {"realm_access": {"roles": ["customer"]}, "tenant_id": "tenant-legacy"}
    request = _make_request(user)
    await tenant.inject_tenant_context(request)
    assert tenant.get_tenant_id() == "tenant-legacy"


async def test_require_operator_admin_passes():
    tenant = _tenant_module()
    request = _make_request(_user_payload("tenant-a", ["operator-admin"]))
    await tenant.inject_tenant_context(request)
    await tenant.require_operator_admin(request)


async def test_require_operator_admin_rejects_operator():
    tenant = _tenant_module()
    request = _make_request(_user_payload("tenant-a", ["operator"]))
    await tenant.inject_tenant_context(request)
    with pytest.raises(HTTPException) as err:
        await tenant.require_operator_admin(request)
    assert err.value.status_code == 403
    assert err.value.detail == "Operator admin access required"


async def test_require_operator_admin_rejects_customer():
    tenant = _tenant_module()
    request = _make_request(_user_payload("tenant-a", ["customer", "tenant-admin"]))
    await tenant.inject_tenant_context(request)
    with pytest.raises(HTTPException) as err:
        await tenant.require_operator_admin(request)
    assert err.value.status_code == 403


async def test_require_customer_allows_operator():
    tenant = _tenant_module()
    request = _make_request(_user_payload(None, ["operator"]))
    await tenant.inject_tenant_context(request)
    await tenant.require_customer(request)


async def test_get_tenant_id_missing():
    tenant = _tenant_module()
    tenant.tenant_context.set(None)
    with pytest.raises(HTTPException) as err:
        tenant.get_tenant_id()
    assert err.value.status_code == 401
    assert err.value.detail == "Tenant context not established"


async def test_get_user_missing():
    tenant = _tenant_module()
    tenant.user_context.set(None)
    with pytest.raises(HTTPException) as err:
        tenant.get_user()
    assert err.value.status_code == 401
    assert err.value.detail == "User context not established"


async def test_inject_tenant_context_missing_user():
    tenant = _tenant_module()
    request = _make_request()
    with pytest.raises(HTTPException) as err:
        await tenant.inject_tenant_context(request)
    assert err.value.status_code == 401
    assert err.value.detail == "Missing authorization"


async def test_require_customer_allows_viewer():
    tenant = _tenant_module()
    request = _make_request(_user_payload("tenant-a", ["customer"]))
    await tenant.inject_tenant_context(request)
    await tenant.require_customer(request)


async def test_require_customer_allows_tenant_admin():
    tenant = _tenant_module()
    request = _make_request(_user_payload("tenant-a", ["tenant-admin"]))
    await tenant.inject_tenant_context(request)
    await tenant.require_customer(request)


async def test_require_customer_blocks_no_org_membership():
    tenant = _tenant_module()
    request = _make_request(_user_payload(None, ["customer"]))
    await tenant.inject_tenant_context(request)
    with pytest.raises(HTTPException) as err:
        await tenant.require_customer(request)
    assert err.value.status_code == 403
    assert err.value.detail == "No organization membership"


async def test_require_customer_blocks_wrong_roles():
    tenant = _tenant_module()
    request = _make_request(_user_payload("tenant-a", ["viewer"]))
    await tenant.inject_tenant_context(request)
    with pytest.raises(HTTPException) as err:
        await tenant.require_customer(request)
    assert err.value.status_code == 403
    assert err.value.detail == "Customer access required"


async def test_require_operator_rejects_customer():
    tenant = _tenant_module()
    request = _make_request(_user_payload("tenant-a", ["customer", "tenant-admin"]))
    await tenant.inject_tenant_context(request)
    with pytest.raises(HTTPException) as err:
        await tenant.require_operator(request)
    assert err.value.status_code == 403
    assert err.value.detail == "Operator access required"


async def test_require_operator_allows_operator():
    tenant = _tenant_module()
    request = _make_request(_user_payload(None, ["operator"]))
    await tenant.inject_tenant_context(request)
    await tenant.require_operator(request)


async def test_get_user_roles_extracts_realm_roles():
    tenant = _tenant_module()
    tenant.set_tenant_context("t1", {"realm_access": {"roles": ["customer", "tenant-admin"]}})
    roles = tenant.get_user_roles()
    assert "customer" in roles
    assert "tenant-admin" in roles


async def test_get_user_roles_empty_when_no_realm_access():
    tenant = _tenant_module()
    tenant.set_tenant_context("t1", {"sub": "user-1"})
    assert tenant.get_user_roles() == []


async def test_get_user_roles_empty_when_no_roles_key():
    tenant = _tenant_module()
    tenant.set_tenant_context("t1", {"realm_access": {}})
    assert tenant.get_user_roles() == []


async def test_has_role_true_false():
    tenant = _tenant_module()
    tenant.set_tenant_context("t1", {"realm_access": {"roles": ["operator-admin"]}})
    assert tenant.has_role("operator-admin") is True
    assert tenant.has_role("operator") is False


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


async def test_get_user_organizations_dict():
    tenant = _tenant_module()
    tenant.set_tenant_context("t1", {"organization": {"tenant-a": {}, "tenant-b": {}}})
    orgs = tenant.get_user_organizations()
    assert isinstance(orgs, dict)
    assert "tenant-a" in orgs


async def test_get_user_organizations_list_normalizes():
    tenant = _tenant_module()
    tenant.set_tenant_context("t1", {"organization": ["tenant-a", "tenant-b"]})
    orgs = tenant.get_user_organizations()
    assert orgs["tenant-a"] == {}


async def test_get_user_organizations_other_type_returns_empty():
    tenant = _tenant_module()
    tenant.set_tenant_context("t1", {"organization": "tenant-a"})
    assert tenant.get_user_organizations() == {}


async def test_extract_tenant_id_from_user_prefers_org_dict():
    tenant = _tenant_module()
    user = {"organization": {"tenant-a": {}, "tenant-b": {}}, "tenant_id": "legacy"}
    assert tenant._extract_tenant_id_from_user(user) == "tenant-a"


async def test_extract_tenant_id_from_user_org_list():
    tenant = _tenant_module()
    user = {"organization": ["tenant-a", "tenant-b"]}
    assert tenant._extract_tenant_id_from_user(user) == "tenant-a"


async def test_extract_tenant_id_from_user_legacy_fallback():
    tenant = _tenant_module()
    user = {"tenant_id": "tenant-legacy"}
    assert tenant._extract_tenant_id_from_user(user) == "tenant-legacy"


async def test_extract_tenant_id_from_user_none_when_missing():
    tenant = _tenant_module()
    assert tenant._extract_tenant_id_from_user({"sub": "u1"}) is None
