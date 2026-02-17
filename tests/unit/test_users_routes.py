from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest

import app as app_module
from middleware import auth as auth_module
from middleware import permissions as permissions_module
from middleware import tenant as tenant_module
from routes import users as users_routes

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.fixture(scope="session", autouse=True)
async def setup_delivery_tables():
    # Keep this file pure unit tests (override integration DB bootstrap fixture).
    yield


def _auth_header():
    return {"Authorization": "Bearer test-token", "X-CSRF-Token": "csrf"}


def _mock_user_deps(monkeypatch, *, tenant_id: str = "tenant-a", perms: set[str] | None = None, roles=None):
    if roles is None:
        roles = ["customer", "tenant-admin"]
    user_payload = {
        "sub": "user-1",
        "organization": {tenant_id: {}},
        "realm_access": {"roles": roles},
        "email": "u@example.com",
        "preferred_username": "me",
    }
    tenant_module.set_tenant_context(tenant_id, user_payload)
    monkeypatch.setattr(auth_module, "validate_token", AsyncMock(return_value=user_payload))

    if perms is None:
        perms = {"*"}

    async def _inject(_request):
        permissions_module.permissions_context.set(set(perms))
        return None

    monkeypatch.setattr(permissions_module, "inject_permissions", AsyncMock(side_effect=_inject))


@pytest.fixture
async def client():
    app_module.app.router.on_startup.clear()
    app_module.app.router.on_shutdown.clear()
    transport = httpx.ASGITransport(app=app_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        c.cookies.set("csrf_token", "csrf")
        yield c
    app_module.app.dependency_overrides.clear()


async def test_list_users_success(client, monkeypatch):
    _mock_user_deps(monkeypatch)
    users = [
        {"id": "u1", "username": "admin"},
        {"id": "u2", "username": "other"},
    ]
    monkeypatch.setattr(users_routes, "list_users", AsyncMock(return_value=users))
    monkeypatch.setattr(users_routes, "get_organizations", AsyncMock(return_value=[{"id": "org-1", "alias": "tenant-a"}]))
    monkeypatch.setattr(users_routes, "get_organization_members", AsyncMock(return_value=[{"id": "u2"}]))
    monkeypatch.setattr(
        users_routes,
        "format_user_response",
        lambda u: {"user_id": u["id"], "username": u["username"], "tenant_id": "tenant-a" if u["id"] == "u1" else None},
    )
    monkeypatch.setattr(users_routes, "get_user_roles", AsyncMock(return_value=[{"name": "customer"}]))

    resp = await client.get("/api/v1/customer/users", headers=_auth_header())
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["users"]) == 2


async def test_list_users_with_search_passes_to_keycloak(client, monkeypatch):
    _mock_user_deps(monkeypatch)
    list_mock = AsyncMock(return_value=[])
    monkeypatch.setattr(users_routes, "list_users", list_mock)
    monkeypatch.setattr(users_routes, "get_organizations", AsyncMock(return_value=[]))
    monkeypatch.setattr(users_routes, "get_organization_members", AsyncMock(return_value=[]))
    monkeypatch.setattr(users_routes, "format_user_response", lambda u: {"user_id": u.get("id"), "tenant_id": None})

    resp = await client.get("/api/v1/customer/users?search=admin", headers=_auth_header())
    assert resp.status_code == 200
    assert list_mock.await_args.kwargs["search"] == "admin"


async def test_get_tenant_user_detail_forbidden_if_not_in_tenant(client, monkeypatch):
    _mock_user_deps(monkeypatch, tenant_id="tenant-a", roles=["customer", "tenant-admin"])
    monkeypatch.setattr(users_routes, "kc_get_user", AsyncMock(return_value={"id": "u2", "username": "x"}))
    monkeypatch.setattr(users_routes, "_is_user_in_tenant", AsyncMock(return_value=False))
    monkeypatch.setattr(users_routes, "is_operator", lambda: False)

    resp = await client.get("/api/v1/customer/users/u2", headers=_auth_header())
    assert resp.status_code == 403


async def test_get_tenant_user_detail_success(client, monkeypatch):
    _mock_user_deps(monkeypatch)
    monkeypatch.setattr(users_routes, "kc_get_user", AsyncMock(return_value={"id": "u2", "username": "x"}))
    monkeypatch.setattr(users_routes, "_is_user_in_tenant", AsyncMock(return_value=True))
    monkeypatch.setattr(users_routes, "format_user_response", lambda u: {"user_id": u["id"], "username": u["username"]})
    monkeypatch.setattr(users_routes, "get_user_roles", AsyncMock(return_value=[{"name": "tenant-admin"}]))

    resp = await client.get("/api/v1/customer/users/u2", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["roles"] == ["tenant-admin"]


async def test_get_tenant_user_detail_not_found(client, monkeypatch):
    _mock_user_deps(monkeypatch)
    monkeypatch.setattr(users_routes, "kc_get_user", AsyncMock(return_value=None))
    resp = await client.get("/api/v1/customer/users/missing", headers=_auth_header())
    assert resp.status_code == 404


async def test_invite_user_invalid_email_returns_422(client, monkeypatch):
    _mock_user_deps(monkeypatch)
    resp = await client.post(
        "/api/v1/customer/users/invite",
        headers=_auth_header(),
        json={"email": "not-an-email", "role": "customer"},
    )
    assert resp.status_code == 422


async def test_invite_user_invalid_role_returns_400(client, monkeypatch):
    _mock_user_deps(monkeypatch)
    resp = await client.post(
        "/api/v1/customer/users/invite",
        headers=_auth_header(),
        json={"email": "new@example.com", "role": "operator"},
    )
    assert resp.status_code == 400


async def test_invite_user_existing_email_returns_409(client, monkeypatch):
    _mock_user_deps(monkeypatch)
    monkeypatch.setattr(users_routes, "get_user_by_email", AsyncMock(return_value={"id": "u1"}))
    resp = await client.post(
        "/api/v1/customer/users/invite",
        headers=_auth_header(),
        json={"email": "new@example.com", "role": "customer"},
    )
    assert resp.status_code == 409


async def test_invite_user_success_username_collision_generates_suffix(client, monkeypatch):
    _mock_user_deps(monkeypatch, tenant_id="tenant-a")
    # Enable audit path to cover _audit() internals.
    class _Audit:
        def __init__(self):
            self.calls = []

        def log(self, *args, **kwargs):
            self.calls.append((args, kwargs))

    audit = _Audit()
    app_module.app.state.audit = audit

    monkeypatch.setattr(users_routes, "get_user_by_email", AsyncMock(return_value=None))
    monkeypatch.setattr(users_routes, "get_user_by_username", AsyncMock(return_value={"id": "existing"}))
    monkeypatch.setattr(users_routes.secrets, "token_hex", lambda n: "abc123")
    monkeypatch.setattr(users_routes, "create_user", AsyncMock(return_value={"id": "new-id", "username": "new_abc123"}))
    monkeypatch.setattr(users_routes, "assign_realm_role", AsyncMock())
    monkeypatch.setattr(users_routes, "_get_org_for_tenant", AsyncMock(return_value={"id": "org-1"}))
    monkeypatch.setattr(users_routes, "add_user_to_organization", AsyncMock())
    monkeypatch.setattr(users_routes, "send_password_reset_email", AsyncMock())

    resp = await client.post(
        "/api/v1/customer/users/invite",
        headers=_auth_header(),
        json={"email": "new@example.com", "role": "customer"},
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == "new-id"
    assert audit.calls


async def test_invite_user_created_user_missing_id_returns_500(client, monkeypatch):
    _mock_user_deps(monkeypatch)
    monkeypatch.setattr(users_routes, "get_user_by_email", AsyncMock(return_value=None))
    monkeypatch.setattr(users_routes, "get_user_by_username", AsyncMock(return_value=None))
    monkeypatch.setattr(users_routes, "create_user", AsyncMock(return_value={"username": "x"}))

    resp = await client.post(
        "/api/v1/customer/users/invite",
        headers=_auth_header(),
        json={"email": "new@example.com", "role": "customer"},
    )
    assert resp.status_code == 500


async def test_change_user_role_cannot_change_self(client, monkeypatch):
    _mock_user_deps(monkeypatch, tenant_id="tenant-a")
    monkeypatch.setattr(users_routes, "kc_get_user", AsyncMock(return_value={"id": "user-1", "username": "me"}))
    monkeypatch.setattr(users_routes, "_is_user_in_tenant", AsyncMock(return_value=True))

    resp = await client.post(
        "/api/v1/customer/users/user-1/role",
        headers=_auth_header(),
        json={"role": "customer"},
    )
    assert resp.status_code == 400


async def test_change_user_role_success_removes_existing_tenant_roles(client, monkeypatch):
    _mock_user_deps(monkeypatch, tenant_id="tenant-a")
    monkeypatch.setattr(users_routes, "kc_get_user", AsyncMock(return_value={"id": "u2", "username": "x"}))
    monkeypatch.setattr(users_routes, "_is_user_in_tenant", AsyncMock(return_value=True))
    monkeypatch.setattr(users_routes, "get_user_roles", AsyncMock(return_value=[{"name": "customer"}, {"name": "other"}]))
    remove_mock = AsyncMock()
    assign_mock = AsyncMock()
    monkeypatch.setattr(users_routes, "remove_realm_role", remove_mock)
    monkeypatch.setattr(users_routes, "assign_realm_role", assign_mock)

    resp = await client.post(
        "/api/v1/customer/users/u2/role",
        headers=_auth_header(),
        json={"role": "tenant-admin"},
    )
    assert resp.status_code == 200
    # Only tenant-scoped roles are removed.
    assert remove_mock.await_count == 1
    assert assign_mock.await_count == 1


async def test_remove_user_cannot_remove_self(client, monkeypatch):
    _mock_user_deps(monkeypatch, tenant_id="tenant-a")
    monkeypatch.setattr(users_routes, "kc_get_user", AsyncMock(return_value={"id": "user-1", "username": "me"}))
    monkeypatch.setattr(users_routes, "_is_user_in_tenant", AsyncMock(return_value=True))

    resp = await client.delete("/api/v1/customer/users/user-1", headers=_auth_header())
    assert resp.status_code == 400


async def test_remove_user_success_clears_tenant_attribute(client, monkeypatch):
    _mock_user_deps(monkeypatch, tenant_id="tenant-a")
    monkeypatch.setattr(
        users_routes,
        "kc_get_user",
        AsyncMock(return_value={"id": "u2", "username": "x", "attributes": {"tenant_id": ["tenant-a"]}}),
    )
    monkeypatch.setattr(users_routes, "_is_user_in_tenant", AsyncMock(return_value=True))
    update_mock = AsyncMock()
    monkeypatch.setattr(users_routes, "update_user", update_mock)
    monkeypatch.setattr(users_routes, "_get_org_for_tenant", AsyncMock(return_value={"id": "org-1"}))
    monkeypatch.setattr(users_routes, "remove_user_from_organization", AsyncMock())

    resp = await client.delete("/api/v1/customer/users/u2", headers=_auth_header())
    assert resp.status_code == 200
    # update_user(user_id, updates) is called positionally.
    assert update_mock.await_args.args[1]["attributes"]["tenant_id"] == []


def _mock_operator_deps(monkeypatch, *, roles: list[str]):
    # Operator routes use require_operator/require_operator_admin (no require_permission).
    user_payload = {
        "sub": "op-1",
        "organization": {},  # operators may not be tenant-scoped
        "realm_access": {"roles": roles},
        "email": "op@example.com",
        "preferred_username": "operator",
    }
    tenant_module.set_tenant_context(None, user_payload)
    monkeypatch.setattr(auth_module, "validate_token", AsyncMock(return_value=user_payload))


async def test_operator_list_all_users_applies_org_fallback(client, monkeypatch):
    _mock_operator_deps(monkeypatch, roles=["operator"])
    monkeypatch.setattr(users_routes, "list_users", AsyncMock(return_value=[{"id": "u1", "username": "x"}]))
    monkeypatch.setattr(users_routes, "get_organizations", AsyncMock(return_value=[{"id": "org-1", "alias": "acme"}]))
    monkeypatch.setattr(users_routes, "get_organization_members", AsyncMock(return_value=[{"userId": "u1"}]))
    monkeypatch.setattr(users_routes, "format_user_response", lambda _u: {"user_id": "u1", "username": "x"})
    monkeypatch.setattr(users_routes, "get_user_roles", AsyncMock(return_value=[{"name": "customer"}]))

    resp = await client.get("/api/v1/operator/users", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["users"][0]["tenant_id"] == "acme"


async def test_operator_get_user_detail_not_found(client, monkeypatch):
    _mock_operator_deps(monkeypatch, roles=["operator"])
    monkeypatch.setattr(users_routes, "kc_get_user", AsyncMock(return_value=None))
    resp = await client.get("/api/v1/operator/users/missing", headers=_auth_header())
    assert resp.status_code == 404


async def test_operator_create_user_missing_id_returns_500(client, monkeypatch):
    _mock_operator_deps(monkeypatch, roles=["operator-admin"])
    monkeypatch.setattr(users_routes, "create_user", AsyncMock(return_value={"username": "x"}))
    resp = await client.post(
        "/api/v1/operator/users",
        headers=_auth_header(),
        json={"username": "x", "email": "x@example.com", "role": "customer"},
    )
    assert resp.status_code == 500


async def test_operator_create_user_success_adds_org_membership(client, monkeypatch):
    _mock_operator_deps(monkeypatch, roles=["operator-admin"])
    monkeypatch.setattr(users_routes, "create_user", AsyncMock(return_value={"id": "u1", "username": "x", "email": "x@example.com"}))
    monkeypatch.setattr(users_routes, "assign_realm_role", AsyncMock())
    monkeypatch.setattr(users_routes, "_get_org_for_tenant", AsyncMock(return_value={"id": "org-1"}))
    add_mock = AsyncMock()
    monkeypatch.setattr(users_routes, "add_user_to_organization", add_mock)

    resp = await client.post(
        "/api/v1/operator/users",
        headers=_auth_header(),
        json={"username": "x", "email": "x@example.com", "tenant_id": "acme", "role": "customer"},
    )
    assert resp.status_code == 200
    assert add_mock.await_count == 1


async def test_operator_update_user_no_updates_still_ok(client, monkeypatch):
    _mock_operator_deps(monkeypatch, roles=["operator-admin"])
    monkeypatch.setattr(users_routes, "kc_get_user", AsyncMock(return_value={"id": "u1", "username": "x"}))
    update_mock = AsyncMock()
    monkeypatch.setattr(users_routes, "update_user", update_mock)

    resp = await client.put("/api/v1/operator/users/u1", headers=_auth_header(), json={})
    assert resp.status_code == 200
    assert update_mock.await_count == 0


async def test_operator_delete_user_cannot_delete_self(client, monkeypatch):
    _mock_operator_deps(monkeypatch, roles=["operator-admin"])
    monkeypatch.setattr(users_routes, "kc_get_user", AsyncMock(return_value={"id": "op-1", "username": "operator"}))
    resp = await client.delete("/api/v1/operator/users/op-1", headers=_auth_header())
    assert resp.status_code == 400


async def test_operator_enable_disable_paths(client, monkeypatch):
    _mock_operator_deps(monkeypatch, roles=["operator-admin"])
    monkeypatch.setattr(users_routes, "kc_get_user", AsyncMock(return_value={"id": "u2", "username": "x"}))
    monkeypatch.setattr(users_routes, "enable_user", AsyncMock())

    resp = await client.post("/api/v1/operator/users/u2/enable", headers=_auth_header())
    assert resp.status_code == 200

    # Self-disable is blocked
    monkeypatch.setattr(users_routes, "kc_get_user", AsyncMock(return_value={"id": "op-1", "username": "operator"}))
    resp2 = await client.post("/api/v1/operator/users/op-1/disable", headers=_auth_header())
    assert resp2.status_code == 400


async def test_operator_assign_and_remove_role(client, monkeypatch):
    _mock_operator_deps(monkeypatch, roles=["operator-admin"])
    monkeypatch.setattr(users_routes, "kc_get_user", AsyncMock(return_value={"id": "u2", "username": "x"}))

    resp = await client.post(
        "/api/v1/operator/users/u2/roles",
        headers=_auth_header(),
        json={"role": "not-a-role"},
    )
    assert resp.status_code == 400

    monkeypatch.setattr(users_routes, "assign_realm_role", AsyncMock())
    resp2 = await client.post(
        "/api/v1/operator/users/u2/roles",
        headers=_auth_header(),
        json={"role": "customer"},
    )
    assert resp2.status_code == 200

    monkeypatch.setattr(users_routes, "remove_realm_role", AsyncMock())
    resp3 = await client.delete("/api/v1/operator/users/u2/roles/customer", headers=_auth_header())
    assert resp3.status_code == 200


async def test_operator_assign_user_to_tenant_org_not_found(client, monkeypatch):
    _mock_operator_deps(monkeypatch, roles=["operator-admin"])
    monkeypatch.setattr(users_routes, "kc_get_user", AsyncMock(return_value={"id": "u2", "username": "x"}))
    monkeypatch.setattr(users_routes, "update_user", AsyncMock())
    monkeypatch.setattr(users_routes, "_get_org_for_tenant", AsyncMock(return_value=None))

    resp = await client.post(
        "/api/v1/operator/users/u2/tenant",
        headers=_auth_header(),
        json={"tenant_id": "acme"},
    )
    assert resp.status_code == 200


async def test_operator_password_reset_welcome_and_set_password(client, monkeypatch):
    _mock_operator_deps(monkeypatch, roles=["operator-admin"])
    monkeypatch.setattr(users_routes, "kc_get_user", AsyncMock(return_value={"id": "u2", "username": "x"}))
    monkeypatch.setattr(users_routes, "send_password_reset_email", AsyncMock())

    resp = await client.post("/api/v1/operator/users/u2/reset-password", headers=_auth_header())
    assert resp.status_code == 200

    resp2 = await client.post("/api/v1/operator/users/u2/send-welcome-email", headers=_auth_header())
    assert resp2.status_code == 200

    monkeypatch.setattr(users_routes, "set_user_password", AsyncMock())
    resp3 = await client.post(
        "/api/v1/operator/users/u2/password",
        headers=_auth_header(),
        json={"password": "Secret123!", "temporary": True},
    )
    assert resp3.status_code == 200


async def test_operator_list_organizations(client, monkeypatch):
    _mock_operator_deps(monkeypatch, roles=["operator"])
    monkeypatch.setattr(users_routes, "get_organizations", AsyncMock(return_value=[{"id": "org-1"}]))
    resp = await client.get("/api/v1/operator/organizations", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["organizations"][0]["id"] == "org-1"


async def test_user_helpers_cover_normalization_and_roles():
    assert users_routes._normalize_tenant_key(123) == ""
    assert users_routes._normalize_tenant_key("Acme Industrial") == "acme-industrial"
    assert users_routes._user_roles({"realm_access": {"roles": ["a", "b"]}}) == ["a", "b"]
    assert users_routes._user_roles({"realm_access": {"roles": "nope"}}) == []

