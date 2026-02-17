from __future__ import annotations

import io
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
from routes import certificates as cert_routes

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.fixture(scope="session", autouse=True)
async def setup_delivery_tables():
    # Keep this file pure unit tests (override integration DB bootstrap fixture).
    yield


class _Tx:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class FakeConn:
    def __init__(self):
        self.fetchrow_result = None
        self.fetchrow_results: list[object] | None = None
        self.fetch_result = []
        self.fetch_results: list[list[object]] | None = None
        self.fetchval_result = None
        self.fetchval_results: list[object] | None = None
        self.execute_result = "DELETE 1"
        self.executed = []

    async def fetchrow(self, query, *args):
        if self.fetchrow_results is not None:
            if not self.fetchrow_results:
                return None
            return self.fetchrow_results.pop(0)
        return self.fetchrow_result

    async def fetch(self, query, *args):
        if self.fetch_results is not None:
            if not self.fetch_results:
                return []
            return self.fetch_results.pop(0)
        return self.fetch_result

    async def fetchval(self, query, *args):
        if self.fetchval_results is not None:
            if not self.fetchval_results:
                return None
            return self.fetchval_results.pop(0)
        return self.fetchval_result

    async def execute(self, query, *args):
        self.executed.append((query, args))
        return self.execute_result

    def transaction(self):
        return _Tx()


class FakePool:
    def __init__(self, conn: FakeConn):
        self.conn = conn

    @asynccontextmanager
    async def acquire(self):
        yield self.conn


def _tenant_connection(conn: FakeConn):
    @asynccontextmanager
    async def _ctx(_pool, _tenant_id):
        yield conn

    return _ctx


def _auth_header():
    return {"Authorization": "Bearer test-token", "X-CSRF-Token": "csrf"}


def _mock_customer_deps(monkeypatch, conn: FakeConn, *, tenant_id: str = "tenant-a", perms: set[str] | None = None, roles=None):
    if roles is None:
        roles = ["customer", "tenant-admin"]
    user_payload = {
        "sub": "user-1",
        "organization": {tenant_id: {}},
        "realm_access": {"roles": roles},
        "email": "u@example.com",
        "preferred_username": "me",
    }
    tenant_module.set_tenant_context(tenant_id if tenant_id else None, user_payload)
    monkeypatch.setattr(auth_module, "validate_token", AsyncMock(return_value=user_payload))

    async def _override_get_db_pool(_request=None):
        return FakePool(conn)

    app_module.app.dependency_overrides[dependencies_module.get_db_pool] = _override_get_db_pool
    monkeypatch.setattr(cert_routes, "tenant_connection", _tenant_connection(conn))

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


async def test_list_certificates_success(client, monkeypatch):
    conn = FakeConn()
    conn.fetch_result = [{"id": 1, "device_id": "d1", "status": "ACTIVE"}]
    conn.fetchval_result = 1
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/certificates", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


async def test_list_certificates_invalid_status_filter_returns_400(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/certificates?status=NOPE", headers=_auth_header())
    assert resp.status_code == 400


async def test_operator_list_all_certificates_invalid_status_returns_400(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn, tenant_id="", roles=["operator"])
    resp = await client.get("/api/v1/operator/certificates?status=NOPE", headers=_auth_header())
    assert resp.status_code == 400


async def test_operator_list_all_certificates_success(client, monkeypatch):
    conn = FakeConn()
    conn.fetch_result = [{"id": 1, "tenant_id": "tenant-a", "device_id": "d1", "status": "ACTIVE"}]
    conn.fetchval_result = 1
    _mock_customer_deps(monkeypatch, conn, tenant_id="", roles=["operator"])
    resp = await client.get("/api/v1/operator/certificates?tenant_id=tenant-a", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


async def test_upload_certificate_invalid_pem_returns_400(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post(
        "/api/v1/customer/certificates",
        headers=_auth_header(),
        # Must satisfy pydantic min_length before route can parse PEM.
        json={"device_id": "d1", "cert_pem": "x" * 60},
    )
    assert resp.status_code == 400


async def test_upload_certificate_cn_mismatch_returns_400(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn, tenant_id="tenant-a")
    now = datetime.now(timezone.utc)

    class _Attr:
        def __init__(self, value):
            self.value = value

    class _Name:
        def __init__(self, cn):
            self._cn = cn

        def get_attributes_for_oid(self, _oid):
            return [_Attr(self._cn)]

        def __str__(self):
            return self._cn

    class _FakeCert:
        subject = _Name("tenant-a/wrong-device")
        issuer = _Name("issuer")
        serial_number = 123
        not_valid_before = now - timedelta(days=1)
        not_valid_after = now + timedelta(days=1)

        def fingerprint(self, _algo):
            return b"\x11" * 32

    monkeypatch.setattr(cert_routes.x509, "load_pem_x509_certificate", lambda *_a, **_k: _FakeCert())
    monkeypatch.setattr(cert_routes, "_cert_validity_window", lambda _c: (now - timedelta(days=1), now + timedelta(days=1)))

    resp = await client.post(
        "/api/v1/customer/certificates",
        headers=_auth_header(),
        json={"device_id": "d1", "cert_pem": "x" * 60},
    )
    assert resp.status_code == 400


async def test_upload_certificate_ca_not_configured_returns_503(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn, tenant_id="tenant-a")

    # Return a minimal "cert" object such that CN matches expected and we hit the CA load.
    now = datetime.now(timezone.utc)

    class _Attr:
        def __init__(self, value):
            self.value = value

    class _Name:
        def __init__(self, cn):
            self._cn = cn

        def get_attributes_for_oid(self, _oid):
            return [_Attr(self._cn)]

        def __str__(self):
            return self._cn

    class _FakeCert:
        subject = _Name("tenant-a/d1")
        issuer = _Name("issuer")
        serial_number = 123
        not_valid_before = now - timedelta(days=1)
        not_valid_after = now + timedelta(days=1)

        def fingerprint(self, _algo):
            return b"\x00" * 32

    monkeypatch.setattr(cert_routes.x509, "load_pem_x509_certificate", lambda *_a, **_k: _FakeCert())
    monkeypatch.setattr(cert_routes, "_cert_validity_window", lambda _c: (now - timedelta(days=1), now + timedelta(days=1)))

    def _open_raises(*_a, **_k):
        raise FileNotFoundError()

    monkeypatch.setattr("builtins.open", _open_raises)

    resp = await client.post(
        "/api/v1/customer/certificates",
        headers=_auth_header(),
        json={"device_id": "d1", "cert_pem": "-----BEGIN CERTIFICATE-----\nMIIB\n-----END CERTIFICATE-----"},
    )
    assert resp.status_code == 503


async def test_get_certificate_not_found(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = None
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/certificates/1", headers=_auth_header())
    assert resp.status_code == 404


async def test_get_certificate_success(client, monkeypatch):
    now = datetime.now(timezone.utc)
    conn = FakeConn()
    conn.fetchrow_result = {
        "id": 1,
        "tenant_id": "tenant-a",
        "device_id": "d1",
        "cert_pem": "CERT",
        "fingerprint_sha256": "f",
        "common_name": "tenant-a/d1",
        "issuer": "Device CA",
        "serial_number": "aa",
        "status": "ACTIVE",
        "not_before": now,
        "not_after": now + timedelta(days=1),
        "revoked_at": None,
        "revoked_reason": None,
        "created_at": now,
        "updated_at": now,
    }
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/certificates/1", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["device_id"] == "d1"


async def test_revoke_certificate_success(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"id": 1, "fingerprint_sha256": "f", "status": "REVOKED", "revoked_at": datetime.now(timezone.utc)}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post("/api/v1/customer/certificates/1/revoke", headers=_auth_header(), json={"reason": "manual"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "REVOKED"


async def test_revoke_certificate_not_found_or_already_revoked_returns_404(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = None
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post("/api/v1/customer/certificates/1/revoke", headers=_auth_header(), json={"reason": "manual"})
    assert resp.status_code == 404


async def test_get_ca_bundle_not_configured_returns_503(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)

    def _open_raises(*_a, **_k):
        raise FileNotFoundError()

    monkeypatch.setattr("builtins.open", _open_raises)
    resp = await client.get("/api/v1/customer/ca-bundle", headers=_auth_header())
    assert resp.status_code == 503


async def test_get_ca_bundle_success_and_operator_alias(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)

    def _open_returns(*_a, **_k):
        return io.StringIO("PEM")

    monkeypatch.setattr("builtins.open", _open_returns)
    resp = await client.get("/api/v1/customer/ca-bundle", headers=_auth_header())
    assert resp.status_code == 200
    assert "PEM" in resp.text

    # operator endpoint delegates to get_ca_bundle
    conn2 = FakeConn()
    _mock_customer_deps(monkeypatch, conn2, tenant_id="", roles=["operator"])
    resp2 = await client.get("/api/v1/operator/ca-bundle", headers=_auth_header())
    assert resp2.status_code == 200


async def test_generate_device_certificate_device_not_found(client, monkeypatch):
    conn = FakeConn()
    conn.fetchval_result = None
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post("/api/v1/customer/devices/d1/certificates/generate", headers=_auth_header(), json={})
    assert resp.status_code == 404


async def test_generate_device_certificate_success_with_mocks(client, monkeypatch):
    conn = FakeConn()
    conn.fetchval_result = 1  # device exists
    now = datetime.now(timezone.utc)
    conn.fetchrow_result = {
        "id": 1,
        "fingerprint_sha256": "f",
        "common_name": "tenant-a/d1",
        "status": "ACTIVE",
        "not_before": now,
        "not_after": now + timedelta(days=365),
        "created_at": now,
    }
    _mock_customer_deps(monkeypatch, conn)

    class _Attr:
        def __init__(self, value):
            self.value = value

    class _Subject:
        def get_attributes_for_oid(self, _oid):
            return [_Attr("Device CA")]

        def __str__(self):
            return "Device CA"

    class _CaCert:
        subject = _Subject()

    monkeypatch.setattr(cert_routes, "_load_device_ca", lambda: (object(), _CaCert(), b"CA"))
    monkeypatch.setattr(
        cert_routes,
        "_generate_signed_device_certificate",
        lambda **_k: ("tenant-a/d1", "CERT", "KEY", "ff", "aa"),
    )

    resp = await client.post(
        "/api/v1/customer/devices/d1/certificates/generate",
        headers=_auth_header(),
        json={"validity_days": 365},
    )
    assert resp.status_code == 201
    assert "private_key_pem" in resp.json()


async def test_rotate_device_certificate_success_with_mocks(client, monkeypatch):
    conn = FakeConn()
    conn.fetchval_result = 1  # device exists
    conn.fetch_result = [{"id": 10, "fingerprint_sha256": "old", "not_after": datetime.now(timezone.utc) + timedelta(days=10)}]
    now = datetime.now(timezone.utc)
    conn.fetchrow_result = {
        "id": 2,
        "fingerprint_sha256": "new",
        "common_name": "tenant-a/d1",
        "status": "ACTIVE",
        "not_before": now,
        "not_after": now + timedelta(days=365),
        "created_at": now,
    }
    _mock_customer_deps(monkeypatch, conn)

    class _Attr:
        def __init__(self, value):
            self.value = value

    class _Subject:
        def get_attributes_for_oid(self, _oid):
            return [_Attr("Device CA")]

        def __str__(self):
            return "Device CA"

    class _CaCert:
        subject = _Subject()

    monkeypatch.setattr(cert_routes, "_load_device_ca", lambda: (object(), _CaCert(), b"CA"))
    monkeypatch.setattr(
        cert_routes,
        "_generate_signed_device_certificate",
        lambda **_k: ("tenant-a/d1", "CERT", "KEY", "ff", "aa"),
    )

    resp = await client.post(
        "/api/v1/customer/devices/d1/certificates/rotate",
        headers=_auth_header(),
        json={"validity_days": 365, "revoke_old_after_hours": 2},
    )
    assert resp.status_code == 201
    assert resp.json()["grace_period_hours"] == 2


async def test_rotate_device_certificate_uses_default_grace_hours(client, monkeypatch):
    conn = FakeConn()
    conn.fetchval_result = 1
    conn.fetch_result = []
    now = datetime.now(timezone.utc)
    conn.fetchrow_result = {
        "id": 2,
        "fingerprint_sha256": "new",
        "common_name": "tenant-a/d1",
        "status": "ACTIVE",
        "not_before": now,
        "not_after": now + timedelta(days=365),
        "created_at": now,
    }
    _mock_customer_deps(monkeypatch, conn)

    class _Attr:
        def __init__(self, value):
            self.value = value

    class _Subject:
        def get_attributes_for_oid(self, _oid):
            return [_Attr("Device CA")]

        def __str__(self):
            return "Device CA"

    class _CaCert:
        subject = _Subject()

    monkeypatch.setattr(cert_routes, "_load_device_ca", lambda: (object(), _CaCert(), b"CA"))
    monkeypatch.setattr(cert_routes, "_generate_signed_device_certificate", lambda **_k: ("tenant-a/d1", "CERT", "KEY", "ff", "aa"))

    resp = await client.post(
        "/api/v1/customer/devices/d1/certificates/rotate",
        headers=_auth_header(),
        json={"validity_days": 365},
    )
    assert resp.status_code == 201
    assert resp.json()["grace_period_hours"] == cert_routes.ROTATION_GRACE_HOURS


async def test_cert_validity_window_adds_utc_tzinfo():
    naive_before = datetime(2020, 1, 1, 0, 0, 0)
    naive_after = datetime(2021, 1, 1, 0, 0, 0)

    class _FakeCert:
        not_valid_before = naive_before
        not_valid_after = naive_after

    nb, na = cert_routes._cert_validity_window(_FakeCert())
    assert nb.tzinfo is not None
    assert na.tzinfo is not None


async def test_verify_signed_by_ca_unsupported_pubkey_raises():
    class _Ca:
        def public_key(self):
            return object()

    class _Cert:
        signature = b""
        tbs_certificate_bytes = b""
        signature_hash_algorithm = None

    with pytest.raises(ValueError):
        cert_routes._verify_signed_by_ca(_Cert(), _Ca())

