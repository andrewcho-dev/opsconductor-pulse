from unittest.mock import AsyncMock

import httpx
import pytest

import app as app_module
from middleware import auth as auth_module
from routes import users as users_routes
from middleware import permissions as permissions_module
import dependencies as dependencies_module
from tests.conftest import FakePool, FakeConn

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


def _auth_header():
    return {"Authorization": "Bearer test-token", "X-CSRF-Token": "csrf"}


def _mock_token(monkeypatch, roles, tenant_id=None):
    conn = FakeConn()
    token = {
        "sub": "user-1",
        "preferred_username": "tester",
        "realm_access": {"roles": roles},
    }
    if tenant_id:
        token["organization"] = {tenant_id: {}}
        token["tenant_id"] = tenant_id
    else:
        token["organization"] = {}
    monkeypatch.setattr(auth_module, "validate_token", AsyncMock(return_value=token))
    if not conn.fetchrow_results:
        # permissions middleware does one fetchrow (role), then route fetchrow calls for users.
        conn.fetchrow_results = [
            {"id": "role-uuid-system"},
            {"id": "u2", "username": "member", "tenant_id": tenant_id or "tenant-a"},
            {"id": "u2", "username": "member", "tenant_id": tenant_id or "tenant-a"},
        ]
    # Default single fetchrow fallback should also have id/tenant_id
    conn.fetchrow_result = {"id": "u2", "username": "member", "tenant_id": tenant_id or "tenant-a"}
    if not conn.fetchval_results:
        conn.fetchval_results = [0, 0]
    # Dependency overrides for DB access paths
    async def _override_get_db_pool(_request=None):
        return FakePool(conn)
    app_module.app.dependency_overrides[dependencies_module.get_db_pool] = _override_get_db_pool
    app_module.app.state.pool = FakePool(conn)
    return conn


@pytest.fixture
async def client():
    app_module.app.router.on_startup.clear()
    app_module.app.router.on_shutdown.clear()
    transport = httpx.ASGITransport(app=app_module.app)
    # Provide a fake pool for tenant routes used in this file.
    fake_pool = FakePool()
    app_module.app.state.pool = fake_pool
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        follow_redirects=True,
    ) as c:
        c.cookies.set("csrf_token", "csrf")
        yield c


async def test_list_users_returns_keycloak_users(client, monkeypatch):
    _mock_token(monkeypatch, ["operator"])
    monkeypatch.setattr(users_routes, "list_users", AsyncMock(return_value=[{"id": "u1", "username": "alice"}]))
    monkeypatch.setattr(users_routes, "get_organizations", AsyncMock(return_value=[]))
    monkeypatch.setattr(users_routes, "format_user_response", lambda user: {"id": user["id"], "username": user["username"]})
    monkeypatch.setattr(users_routes, "get_user_roles", AsyncMock(return_value=[{"name": "customer"}]))

    resp = await client.get("/operator/users", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["users"][0]["username"] == "alice"


async def test_create_user_calls_keycloak(client, monkeypatch):
    _mock_token(monkeypatch, ["operator-admin"])
    create_user = AsyncMock(return_value={"id": "u1", "username": "alice", "email": "alice@example.com"})
    assign_role = AsyncMock()
    monkeypatch.setattr(users_routes, "create_user", create_user)
    monkeypatch.setattr(users_routes, "assign_realm_role", assign_role)
    monkeypatch.setattr(users_routes, "_get_org_for_tenant", AsyncMock(return_value=None))

    resp = await client.post(
        "/operator/users",
        headers=_auth_header(),
        json={
            "username": "alice",
            "email": "alice@example.com",
            "first_name": "Alice",
            "last_name": "Ops",
            "tenant_id": "tenant-a",
            "role": "operator",
        },
    )
    assert resp.status_code == 200
    create_user.assert_awaited()
    assign_role.assert_awaited_with("u1", "operator")


async def test_create_user_validates_email(client, monkeypatch):
    _mock_token(monkeypatch, ["operator-admin"])
    resp = await client.post(
        "/operator/users",
        headers=_auth_header(),
        json={"username": "alice", "email": "not-an-email"},
    )
    assert resp.status_code == 422


async def test_assign_role_validates_role(client, monkeypatch):
    _mock_token(monkeypatch, ["operator-admin"])
    monkeypatch.setattr(users_routes, "kc_get_user", AsyncMock(return_value={"id": "u1", "username": "alice"}))
    resp = await client.post(
        "/operator/users/u1/roles",
        headers=_auth_header(),
        json={"role": "superadmin"},
    )
    assert resp.status_code == 400


async def test_assign_role_updates_keycloak(client, monkeypatch):
    _mock_token(monkeypatch, ["operator-admin"])
    monkeypatch.setattr(users_routes, "kc_get_user", AsyncMock(return_value={"id": "u1", "username": "alice"}))
    assign_role = AsyncMock()
    monkeypatch.setattr(users_routes, "assign_realm_role", assign_role)
    resp = await client.post(
        "/operator/users/u1/roles",
        headers=_auth_header(),
        json={"role": "operator"},
    )
    assert resp.status_code == 200
    assign_role.assert_awaited_with("u1", "operator")


async def test_delete_user_calls_keycloak(client, monkeypatch):
    _mock_token(monkeypatch, ["operator-admin"])
    monkeypatch.setattr(users_routes, "kc_get_user", AsyncMock(return_value={"id": "u2", "username": "bob"}))
    delete_user = AsyncMock()
    monkeypatch.setattr(users_routes, "delete_user", delete_user)
    resp = await client.delete("/operator/users/u2", headers=_auth_header())
    assert resp.status_code == 200
    delete_user.assert_awaited_with("u2")


async def test_user_management_requires_operator_admin(client, monkeypatch):
    _mock_token(monkeypatch, ["operator"])
    resp = await client.post(
        "/operator/users",
        headers=_auth_header(),
        json={"username": "alice", "email": "alice@example.com"},
    )
    assert resp.status_code == 403


async def test_tenant_admin_can_list_tenant_users(client, monkeypatch):
    _mock_token(monkeypatch, ["tenant-admin"], tenant_id="tenant-a")
    async def _grant_all(_request):
        permissions_module.permissions_context.set({"*"})
    monkeypatch.setattr(permissions_module, "inject_permissions", _grant_all)
    monkeypatch.setattr(users_routes, "list_users", AsyncMock(return_value=[{"id": "u1", "username": "alice"}]))
    monkeypatch.setattr(users_routes, "format_user_response", lambda _u: {"id": "u1", "username": "alice", "tenant_id": "tenant-a"})
    monkeypatch.setattr(users_routes, "get_user_roles", AsyncMock(return_value=[{"name": "customer"}]))
    monkeypatch.setattr(users_routes, "_tenant_member_ids", AsyncMock(return_value=set()))
    resp = await client.get("/customer/users", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


async def test_tenant_viewer_cannot_manage_users(client, monkeypatch):
    _mock_token(monkeypatch, ["customer"], tenant_id="tenant-a")
    resp = await client.post(
        "/customer/users/invite",
        headers=_auth_header(),
        json={"email": "new@example.com", "role": "customer"},
    )
    assert resp.status_code == 403


async def test_change_tenant_user_role(client, monkeypatch):
    _mock_token(monkeypatch, ["tenant-admin"], tenant_id="tenant-a")
    async def _grant_all(_request):
        permissions_module.permissions_context.set({"*"})
    monkeypatch.setattr(permissions_module, "inject_permissions", _grant_all)
    monkeypatch.setattr(users_routes, "kc_get_user", AsyncMock(return_value={"id": "u2", "username": "member"}))
    monkeypatch.setattr(users_routes, "_is_user_in_tenant", AsyncMock(return_value=True))
    monkeypatch.setattr(users_routes, "get_user_roles", AsyncMock(return_value=[{"name": "customer"}]))
    monkeypatch.setattr(users_routes, "remove_realm_role", AsyncMock())
    assign_role = AsyncMock()
    monkeypatch.setattr(users_routes, "assign_realm_role", assign_role)
    resp = await client.post(
        "/customer/users/u2/role",
        headers=_auth_header(),
        json={"role": "tenant-admin"},
    )
    assert resp.status_code == 200
    assign_role.assert_awaited_with("u2", "tenant-admin")


async def test_cannot_manage_other_tenant_users(client, monkeypatch):
    _mock_token(monkeypatch, ["tenant-admin"], tenant_id="tenant-a")
    monkeypatch.setattr(users_routes, "kc_get_user", AsyncMock(return_value={"id": "u2", "username": "member"}))
    monkeypatch.setattr(users_routes, "_is_user_in_tenant", AsyncMock(return_value=False))
    resp = await client.post(
        "/customer/users/u2/role",
        headers=_auth_header(),
        json={"role": "customer"},
    )
    assert resp.status_code == 403
