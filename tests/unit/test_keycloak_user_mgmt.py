from unittest.mock import AsyncMock

import httpx
import pytest

import app as app_module
from middleware import auth as auth_module
from middleware import tenant as tenant_module
from routes import users as users_routes

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


def _auth_header():
    return {"Authorization": "Bearer test-token", "X-CSRF-Token": "csrf"}


def _mock_operator_auth(monkeypatch):
    payload = {
        "sub": "op-1",
        "preferred_username": "operator",
        "tenant_id": "operator",
        "organization": {"operator": {}},
        "realm_access": {"roles": ["operator", "operator-admin"]},
    }
    tenant_module.set_tenant_context("operator", payload)
    monkeypatch.setattr(auth_module, "validate_token", AsyncMock(return_value=payload))
    monkeypatch.setattr(users_routes, "get_user", lambda: payload)
    monkeypatch.setattr(users_routes, "is_operator", lambda: True)


@pytest.fixture
async def client():
    app_module.app.router.on_startup.clear()
    app_module.app.router.on_shutdown.clear()
    transport = httpx.ASGITransport(app=app_module.app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as c:
        c.cookies.set("csrf_token", "csrf")
        yield c


async def test_list_users_returns_list(client, monkeypatch):
    _mock_operator_auth(monkeypatch)
    monkeypatch.setattr(users_routes, "list_users", AsyncMock(return_value=[{"id": "u1", "username": "u1"}]))
    monkeypatch.setattr(users_routes, "format_user_response", lambda u: {"id": u["id"], "username": u["username"]})
    monkeypatch.setattr(users_routes, "get_user_roles", AsyncMock(return_value=[]))
    resp = await client.get("/operator/users", headers=_auth_header())
    assert resp.status_code == 200
    assert "users" in resp.json()


async def test_get_user_with_roles(client, monkeypatch):
    _mock_operator_auth(monkeypatch)
    monkeypatch.setattr(users_routes, "kc_get_user", AsyncMock(return_value={"id": "u1", "username": "u1"}))
    monkeypatch.setattr(users_routes, "format_user_response", lambda u: {"id": u["id"], "username": u["username"]})
    monkeypatch.setattr(users_routes, "get_user_roles", AsyncMock(return_value=[{"name": "operator"}]))
    resp = await client.get("/operator/users/u1", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json().get("roles") == ["operator"]


async def test_get_user_not_found(client, monkeypatch):
    _mock_operator_auth(monkeypatch)
    monkeypatch.setattr(users_routes, "kc_get_user", AsyncMock(return_value=None))
    resp = await client.get("/operator/users/missing", headers=_auth_header())
    assert resp.status_code == 404


async def test_create_user_success(client, monkeypatch):
    _mock_operator_auth(monkeypatch)
    monkeypatch.setattr(users_routes, "create_user", AsyncMock(return_value={"id": "u1", "username": "user1"}))
    monkeypatch.setattr(users_routes, "assign_realm_role", AsyncMock(return_value=None))
    resp = await client.post(
        "/operator/users",
        headers=_auth_header(),
        json={
            "username": "user1",
            "email": "user1@example.com",
            "temporary_password": "Password123",
            "role": "operator",
        },
    )
    assert resp.status_code == 200
    assert resp.json().get("id") == "u1"


async def test_create_user_invalid_email(client, monkeypatch):
    _mock_operator_auth(monkeypatch)
    resp = await client.post(
        "/operator/users",
        headers=_auth_header(),
        json={"username": "user1", "email": "not-an-email", "temporary_password": "Password123"},
    )
    assert resp.status_code == 422


async def test_update_user_success(client, monkeypatch):
    _mock_operator_auth(monkeypatch)
    monkeypatch.setattr(users_routes, "kc_get_user", AsyncMock(return_value={"id": "u1", "username": "user1"}))
    monkeypatch.setattr(users_routes, "update_user", AsyncMock(return_value=None))
    resp = await client.put(
        "/operator/users/u1",
        headers=_auth_header(),
        json={"first_name": "A"},
    )
    assert resp.status_code == 200


async def test_delete_user_success(client, monkeypatch):
    _mock_operator_auth(monkeypatch)
    monkeypatch.setattr(users_routes, "kc_get_user", AsyncMock(return_value={"id": "u1", "username": "user1"}))
    monkeypatch.setattr(users_routes, "delete_user", AsyncMock(return_value=None))
    resp = await client.delete("/operator/users/u1", headers=_auth_header())
    assert resp.status_code == 200


async def test_send_password_reset_success(client, monkeypatch):
    _mock_operator_auth(monkeypatch)
    monkeypatch.setattr(users_routes, "kc_get_user", AsyncMock(return_value={"id": "u1", "username": "user1"}))
    monkeypatch.setattr(users_routes, "send_password_reset_email", AsyncMock(return_value=None))
    resp = await client.post("/operator/users/u1/reset-password", headers=_auth_header())
    assert resp.status_code == 200


async def test_set_password_success(client, monkeypatch):
    _mock_operator_auth(monkeypatch)
    monkeypatch.setattr(users_routes, "kc_get_user", AsyncMock(return_value={"id": "u1", "username": "user1"}))
    monkeypatch.setattr(users_routes, "set_user_password", AsyncMock(return_value=None))
    resp = await client.post(
        "/operator/users/u1/password",
        headers=_auth_header(),
        json={"password": "Password123", "temporary": True},
    )
    assert resp.status_code == 200


async def test_assign_role_success(client, monkeypatch):
    _mock_operator_auth(monkeypatch)
    monkeypatch.setattr(users_routes, "kc_get_user", AsyncMock(return_value={"id": "u1", "username": "user1"}))
    monkeypatch.setattr(users_routes, "assign_realm_role", AsyncMock(return_value=None))
    resp = await client.post("/operator/users/u1/roles", headers=_auth_header(), json={"role": "operator"})
    assert resp.status_code == 200


async def test_remove_role_success(client, monkeypatch):
    _mock_operator_auth(monkeypatch)
    monkeypatch.setattr(users_routes, "kc_get_user", AsyncMock(return_value={"id": "u1", "username": "user1"}))
    monkeypatch.setattr(users_routes, "remove_realm_role", AsyncMock(return_value=None))
    resp = await client.delete("/operator/users/u1/roles/operator", headers=_auth_header())
    assert resp.status_code == 200
