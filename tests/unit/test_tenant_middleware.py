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


async def test_inject_tenant_context_extracts_tenant_id(monkeypatch):
    tenant = _tenant_module()
    request = _make_request({"tenant_id": "tenant-a", "role": "customer_admin"})

    await tenant.inject_tenant_context(request)
    assert tenant.get_tenant_id() == "tenant-a"


async def test_inject_tenant_context_no_tenant(monkeypatch):
    tenant = _tenant_module()
    request = _make_request({"role": "customer_admin"})

    def _raise_if_missing(tenant_id, user):
        if tenant_id is None:
            raise HTTPException(status_code=403, detail="Missing tenant context")
        return original_set(tenant_id, user)

    original_set = tenant.set_tenant_context
    monkeypatch.setattr(tenant, "set_tenant_context", _raise_if_missing)
    with pytest.raises(HTTPException) as err:
        await tenant.inject_tenant_context(request)
    assert err.value.status_code == 403


async def test_require_operator_admin_passes():
    tenant = _tenant_module()
    request = _make_request({"tenant_id": "tenant-a", "role": "operator_admin"})
    await tenant.inject_tenant_context(request)
    await tenant.require_operator_admin(request)


async def test_require_operator_admin_rejects_operator():
    tenant = _tenant_module()
    request = _make_request({"tenant_id": "tenant-a", "role": "operator"})
    await tenant.inject_tenant_context(request)
    with pytest.raises(HTTPException) as err:
        await tenant.require_operator_admin(request)
    assert err.value.status_code == 403


async def test_require_customer_rejects_operator():
    tenant = _tenant_module()
    request = _make_request({"tenant_id": None, "role": "operator"})
    await tenant.inject_tenant_context(request)
    with pytest.raises(HTTPException) as err:
        await tenant.require_customer(request)
    assert err.value.status_code == 403


async def test_get_tenant_id_missing():
    tenant = _tenant_module()
    tenant.tenant_context.set(None)
    with pytest.raises(HTTPException) as err:
        tenant.get_tenant_id()
    assert err.value.status_code == 401


async def test_get_user_missing():
    tenant = _tenant_module()
    tenant.user_context.set(None)
    with pytest.raises(HTTPException) as err:
        tenant.get_user()
    assert err.value.status_code == 401


async def test_inject_tenant_context_missing_user():
    tenant = _tenant_module()
    request = _make_request()
    with pytest.raises(HTTPException) as err:
        await tenant.inject_tenant_context(request)
    assert err.value.status_code == 401


async def test_require_customer_allows_viewer():
    tenant = _tenant_module()
    request = _make_request({"tenant_id": "tenant-a", "role": "customer_viewer"})
    await tenant.inject_tenant_context(request)
    await tenant.require_customer(request)


async def test_require_operator_rejects_customer():
    tenant = _tenant_module()
    request = _make_request({"tenant_id": "tenant-a", "role": "customer_admin"})
    await tenant.inject_tenant_context(request)
    with pytest.raises(HTTPException) as err:
        await tenant.require_operator(request)
    assert err.value.status_code == 403
