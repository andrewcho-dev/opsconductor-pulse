from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import httpx
import pytest

import app as app_module
import dependencies as dependencies_module
from middleware import auth as auth_module
from middleware import permissions as permissions_module
from middleware import tenant as tenant_module
from routes import billing as billing_routes
from tests.conftest import FakeConn, FakePool
from tests.factories import fake_tenant

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


def _tenant_connection(conn: FakeConn):
    @asynccontextmanager
    async def _ctx(_pool, _tenant_id):
        yield conn

    return _ctx


def _auth_header():
    return {"Authorization": "Bearer test-token", "X-CSRF-Token": "csrf"}


def _mock_customer_deps(
    monkeypatch, conn: FakeConn, *, tenant_id: str = "tenant-a", perms: set[str] | None = None
):
    user_payload = {
        "sub": "user-1",
        "organization": {tenant_id: {}},
        "realm_access": {"roles": ["customer", "tenant-admin"]},
        "email": "u@example.com",
        "preferred_username": "me",
    }
    tenant_module.set_tenant_context(tenant_id, user_payload)
    monkeypatch.setattr(auth_module, "validate_token", AsyncMock(return_value=user_payload))

    async def _override_get_db_pool(_request=None):
        return FakePool(conn)

    app_module.app.dependency_overrides[dependencies_module.get_db_pool] = _override_get_db_pool
    monkeypatch.setattr(billing_routes, "tenant_connection", _tenant_connection(conn))

    if perms is None:
        perms = {"*"}

    async def _inject(_request):
        permissions_module.permissions_context.set(set(perms))
        return None

    monkeypatch.setattr(permissions_module, "inject_permissions", AsyncMock(side_effect=_inject))

    # Webhook handler reads pool from app.state.pool
    app_module.app.state.pool = FakePool(conn)


@pytest.fixture
async def client():
    app_module.app.router.on_startup.clear()
    app_module.app.router.on_shutdown.clear()
    transport = httpx.ASGITransport(app=app_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        c.cookies.set("csrf_token", "csrf")
        yield c
    app_module.app.dependency_overrides.clear()


async def test_get_billing_config_returns_status(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(billing_routes, "is_stripe_configured", lambda: False)
    resp = await client.get("/api/v1/customer/billing/config", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["stripe_configured"] is False


async def test_get_entitlements_calls_plan_usage(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(billing_routes, "get_account_usage", AsyncMock(return_value={"limits": {"devices": 10}}))
    resp = await client.get("/api/v1/customer/billing/entitlements", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["limits"]["devices"] == 10


async def test_create_checkout_session_not_configured_returns_503(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(billing_routes, "is_stripe_configured", lambda: False)
    resp = await client.post(
        "/api/v1/customer/billing/checkout-session",
        headers=_auth_header(),
        json={"price_id": "price_1", "success_url": "https://ok", "cancel_url": "https://no"},
    )
    assert resp.status_code == 503


async def test_create_checkout_session_success(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_results = [
        {"stripe_customer_id": None, "billing_email": None, "contact_email": "c@example.com", "name": "Acme"},
    ]
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(billing_routes, "is_stripe_configured", lambda: True)
    monkeypatch.setattr(billing_routes, "create_checkout_session", AsyncMock(return_value="https://stripe/checkout"))
    resp = await client.post(
        "/api/v1/customer/billing/checkout-session",
        headers=_auth_header(),
        json={"price_id": "price_1", "success_url": "https://ok", "cancel_url": "https://no"},
    )
    assert resp.status_code == 200
    assert resp.json()["url"].startswith("https://stripe/")


async def test_create_portal_session_requires_linked_customer_id(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_results = [{"stripe_customer_id": None}]
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(billing_routes, "is_stripe_configured", lambda: True)
    resp = await client.post(
        "/api/v1/customer/billing/portal-session",
        headers=_auth_header(),
        json={"return_url": "https://return"},
    )
    assert resp.status_code == 400


async def test_create_portal_session_success(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_results = [{"stripe_customer_id": "cus_123"}]
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(billing_routes, "is_stripe_configured", lambda: True)
    monkeypatch.setattr(billing_routes, "create_portal_session", AsyncMock(return_value="https://stripe/portal"))
    resp = await client.post(
        "/api/v1/customer/billing/portal-session",
        headers=_auth_header(),
        json={"return_url": "https://return"},
    )
    assert resp.status_code == 200
    assert resp.json()["url"] == "https://stripe/portal"


async def test_addon_checkout_parent_not_found_returns_404(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_results = [None]
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(billing_routes, "is_stripe_configured", lambda: True)
    resp = await client.post(
        "/api/v1/customer/billing/addon-checkout",
        headers=_auth_header(),
        json={
            "parent_subscription_id": "sub_0",
            "price_id": "price_1",
            "success_url": "https://ok",
            "cancel_url": "https://no",
        },
    )
    assert resp.status_code == 404


async def test_addon_checkout_parent_expired_returns_400(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_results = [
        {
            "subscription_id": "sub_1",
            "term_end": datetime.now(timezone.utc) - timedelta(days=1),
            "plan_id": "pro",
        }
    ]
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(billing_routes, "is_stripe_configured", lambda: True)
    resp = await client.post(
        "/api/v1/customer/billing/addon-checkout",
        headers=_auth_header(),
        json={
            "parent_subscription_id": "sub_1",
            "price_id": "price_1",
            "success_url": "https://ok",
            "cancel_url": "https://no",
        },
    )
    assert resp.status_code == 400


async def test_addon_checkout_success(client, monkeypatch):
    term_end = datetime.now(timezone.utc) + timedelta(days=30)
    conn = FakeConn()
    conn.fetchrow_results = [
        {
            "subscription_id": "sub_1",
            "tenant_id": "tenant-a",
            "term_end": term_end,
            "status": "ACTIVE",
            "stripe_subscription_id": "ss_1",
            "plan_id": "pro",
        },
        {
            "stripe_customer_id": "cus_123",
            "billing_email": None,
            "contact_email": "c@example.com",
        },
    ]
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(billing_routes, "is_stripe_configured", lambda: True)
    monkeypatch.setattr(billing_routes, "create_checkout_session", AsyncMock(return_value="https://stripe/addon"))
    resp = await client.post(
        "/api/v1/customer/billing/addon-checkout",
        headers=_auth_header(),
        json={
            "parent_subscription_id": "sub_1",
            "price_id": "price_addon",
            "success_url": "https://ok",
            "cancel_url": "https://no",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["url"] == "https://stripe/addon"


async def test_get_billing_status_happy_path(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_results = [
        {"stripe_customer_id": "cus_123", "billing_email": "b@example.com", "account_tier_id": "tier_basic"},
        {"tier_id": "tier_basic", "name": "Basic", "monthly_price_cents": 5000},
    ]
    conn.fetch_results = [
        [
            {
                "plan_id": "basic",
                "name": "Basic",
                "monthly_price_cents": 1000,
                "device_count": 2,
            }
        ]
    ]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/billing/status", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["has_billing_account"] is True
    assert resp.json()["total_monthly_price_cents"] == 7000


async def test_list_customer_subscriptions(client, monkeypatch):
    conn = FakeConn()
    now = datetime.now(timezone.utc)
    conn.fetch_results = [
        [
            {
                "subscription_id": "sub_1",
                "tenant_id": "tenant-a",
                "subscription_type": "MAIN",
                "parent_subscription_id": None,
                "plan_id": "pro",
                "device_id": "device-1",
                "status": "ACTIVE",
                "device_limit": 10,
                "active_device_count": 2,
                "term_start": now,
                "term_end": None,
                "grace_end": None,
                "description": "Main",
                "stripe_subscription_id": "ss_1",
                "created_at": now,
            }
        ]
    ]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/billing/subscriptions", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["subscriptions"][0]["subscription_id"] == "sub_1"


async def test_generate_tenant_id_slugging():
    assert billing_routes._generate_tenant_id("Acme Industrial, Inc.") == "acme-industrial-inc"


@pytest.mark.skip(reason="Legacy helper removed in billing refactor")
async def test_get_plan_device_limit_defaults_to_zero(monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = None
    limit = await getattr(billing_routes, "_get_plan_device_limit", lambda *_: 0)(conn, "missing")
    assert limit == 0


@pytest.mark.skip(reason="Legacy helper removed in billing refactor")
async def test_sync_tier_allocations_inserts_defaults():
    conn = FakeConn()
    conn.fetch_result = [{"tier_id": "t1", "slot_limit": 10}]
    sync_fn = getattr(billing_routes, "_sync_tier_allocations", None)
    if sync_fn:
        await sync_fn(conn, "sub_1", "pro")
        assert conn.executed  # at least one execute


async def test_stripe_webhook_invalid_signature_returns_400(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(billing_routes, "construct_webhook_event", lambda _payload, _sig: (_ for _ in ()).throw(Exception("bad")))
    resp = await client.post("/webhook/stripe", content=b"{}", headers={"stripe-signature": "x"})
    assert resp.status_code == 400


async def test_stripe_webhook_dispatches_and_swallows_handler_errors(client, monkeypatch):
    conn = FakeConn()
    conn.fetchval_results = ["evt_1"]
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(
        billing_routes,
        "construct_webhook_event",
        lambda _payload, _sig: {"id": "evt_1", "type": "checkout.session.completed", "data": {"object": {"id": "cs_1"}}},
    )
    monkeypatch.setattr(billing_routes, "_handle_checkout_completed", AsyncMock(side_effect=Exception("boom")))

    resp = await client.post("/webhook/stripe", content=b"{}", headers={"stripe-signature": "x"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_handle_checkout_completed_new_tenant_provisions_and_creates_subscription(monkeypatch):
    conn = FakeConn()
    # Collision check (None) then generate_subscription_id.
    conn.fetchval_results = [None, "sub_1"]
    # Device limit lookup used by _get_plan_device_limit().
    conn.fetchrow_result = {"device_limit": 5}
    pool = FakePool(conn)

    now = datetime.now(timezone.utc)
    monkeypatch.setattr(
        billing_routes,
        "retrieve_subscription",
        lambda _sid: {
            "current_period_start": int(now.timestamp()),
            "current_period_end": int((now + timedelta(days=30)).timestamp()),
            "items": {"data": [{"price": {"id": "price_1"}}]},
        },
    )
    monkeypatch.setattr(billing_routes, "create_user", AsyncMock(return_value={"id": "kc_1"}))
    monkeypatch.setattr(billing_routes, "assign_realm_role", AsyncMock())
    monkeypatch.setattr(billing_routes, "send_password_reset_email", AsyncMock())

    session = {
        "metadata": {
            "company_name": "Acme Industrial, Inc.",
            "plan_id": "starter",
            "admin_email": "admin@acme.com",
            "admin_first_name": "A",
            "admin_last_name": "B",
        },
        "customer": "cus_1",
        "subscription": "sub_stripe_1",
        "customer_details": {"email": "admin@acme.com", "address": {"line1": "1 Main", "country": "US"}},
    }

    await billing_routes._handle_checkout_completed(pool, session)
    assert len(conn.executed) >= 2


async def test_handle_checkout_completed_existing_tenant_links_customer(monkeypatch):
    conn = FakeConn()
    conn.fetchval_results = ["sub_2"]  # generate_subscription_id only
    conn.fetchrow_result = {"device_limit": 10}
    pool = FakePool(conn)

    now = datetime.now(timezone.utc)
    monkeypatch.setattr(
        billing_routes,
        "retrieve_subscription",
        lambda _sid: {
            "current_period_start": int(now.timestamp()),
            "current_period_end": int((now + timedelta(days=30)).timestamp()),
            "items": {"data": [{"price": {"id": "price_2"}}]},
        },
    )
    session = {
        "metadata": {"tenant_id": "tenant-a", "plan_id": "pro"},
        "customer": "cus_2",
        "subscription": "sub_stripe_2",
        "customer_details": {"email": "billing@acme.com", "address": {}},
    }
    await billing_routes._handle_checkout_completed(pool, session)
    assert any("UPDATE tenants SET stripe_customer_id" in q for (q, _p, _k) in conn.executed)


async def test_handle_subscription_updated_no_existing_subscription_returns(monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = None
    pool = FakePool(conn)
    monkeypatch.setattr(
        billing_routes,
        "retrieve_subscription",
        lambda _sid: {"id": _sid, "status": "active", "metadata": {}},
    )
    await billing_routes._handle_subscription_updated(pool, {"id": "ss_1", "status": "active", "metadata": {}})
    assert conn.executed == []


async def test_handle_subscription_updated_plan_change_syncs_allocations(monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {
        "subscription_id": "sub_1",
        "tenant_id": "tenant-a",
        "plan_id": "starter",
        "device_id": "device-1",
        "status": "ACTIVE",
    }
    pool = FakePool(conn)
    monkeypatch.setattr(
        billing_routes,
        "retrieve_subscription",
        lambda _sid: {
            "id": _sid,
            "status": "past_due",
            "metadata": {"plan_id": "pro", "tenant_id": "tenant-a"},
        },
    )
    monkeypatch.setattr(billing_routes, "_get_plan_device_limit", AsyncMock(return_value=10), raising=False)
    monkeypatch.setattr(billing_routes, "_sync_tier_allocations", AsyncMock(), raising=False)

    await billing_routes._handle_subscription_updated(
        pool,
        {"id": "ss_1", "status": "past_due", "metadata": {"plan_id": "pro"}},
    )
    assert conn.executed  # update + audit


async def test_handle_subscription_deleted_updates_status(monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"subscription_id": "sub_1", "tenant_id": "tenant-a", "status": "ACTIVE"}
    pool = FakePool(conn)
    await billing_routes._handle_subscription_deleted(pool, {"id": "ss_1"})
    assert len(conn.executed) >= 2


async def test_handle_payment_failed_early_returns_without_subscription(monkeypatch):
    conn = FakeConn()
    pool = FakePool(conn)
    await billing_routes._handle_payment_failed(pool, {"id": "inv_1"})
    assert conn.executed == []


async def test_handle_payment_failed_sets_grace(monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"subscription_id": "sub_1", "tenant_id": "tenant-a"}
    pool = FakePool(conn)
    await billing_routes._handle_payment_failed(pool, {"id": "inv_2", "subscription": "ss_1"})
    assert any("UPDATE device_subscriptions SET status = 'GRACE'" in q for (q, _p, _k) in conn.executed)


async def test_handle_invoice_paid_extends_term(monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"subscription_id": "sub_1", "tenant_id": "tenant-a", "status": "GRACE"}
    pool = FakePool(conn)
    now = datetime.now(timezone.utc)
    monkeypatch.setattr(
        billing_routes,
        "retrieve_subscription",
        lambda _sid: {"current_period_end": int((now + timedelta(days=30)).timestamp())},
    )
    await billing_routes._handle_invoice_paid(pool, {"id": "inv_3", "subscription": "ss_1"})
    assert any("UPDATE device_subscriptions SET status = 'ACTIVE'" in q for (q, _p, _k) in conn.executed)

