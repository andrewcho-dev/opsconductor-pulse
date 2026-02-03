import pytest
from httpx import AsyncClient

from tests.helpers.auth import decode_token_claims

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestTokenValidation:
    """Test JWT token validation."""

    async def test_valid_token_accepted(
        self, client: AsyncClient, customer_a_token: str
    ):
        """Valid token is accepted."""
        response = await client.get(
            "/customer/devices?format=json",
            headers={"Authorization": f"Bearer {customer_a_token}"},
        )
        assert response.status_code == 200

    async def test_invalid_token_rejected(self, client: AsyncClient):
        """Invalid token returns 401."""
        response = await client.get(
            "/customer/devices?format=json",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401

    async def test_expired_token_rejected(self, client: AsyncClient):
        """Expired token returns 401."""
        expired_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2MDAwMDAwMDB9.fake"
        response = await client.get(
            "/customer/devices?format=json",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401

    async def test_missing_auth_returns_401(self, client: AsyncClient):
        """No auth returns 401."""
        response = await client.get("/customer/devices?format=json")
        assert response.status_code == 401

    async def test_malformed_auth_header(self, client: AsyncClient):
        """Malformed auth header returns 401."""
        response = await client.get(
            "/customer/devices?format=json",
            headers={"Authorization": "NotBearer token"},
        )
        assert response.status_code == 401


class TestCookieAuth:
    """Test cookie-based authentication."""

    async def test_cookie_auth_works(
        self, client: AsyncClient, customer_a_token: str
    ):
        """Cookie authentication is accepted."""
        response = await client.get(
            "/customer/devices?format=json",
            cookies={"pulse_session": customer_a_token},
        )
        assert response.status_code == 200

    async def test_bearer_takes_precedence_over_cookie(
        self, client: AsyncClient, customer_a_token: str, customer_b_token: str
    ):
        """When both present, Bearer header takes precedence."""
        response = await client.get(
            "/customer/devices?format=json",
            headers={"Authorization": f"Bearer {customer_a_token}"},
            cookies={"pulse_session": customer_b_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "tenant-a"


class TestAuthStatus:
    """Test /api/auth/status endpoint."""

    async def test_auth_status_authenticated(
        self, client: AsyncClient, customer_a_token: str
    ):
        """Auth status returns user info when authenticated."""
        response = await client.get(
            "/api/auth/status",
            cookies={"pulse_session": customer_a_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert "user" in data
        assert "expires_in" in data

    async def test_auth_status_not_authenticated(self, client: AsyncClient):
        """Auth status returns false when not authenticated."""
        response = await client.get("/api/auth/status")
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False


class TestAuthRefresh:
    """Test /api/auth/refresh endpoint."""

    async def test_refresh_without_token_returns_401(self, client: AsyncClient):
        """Refresh without token fails."""
        response = await client.post("/api/auth/refresh")
        assert response.status_code == 401


class TestTokenClaims:
    """Test that tokens have expected claims."""

    async def test_customer_token_has_tenant_id(self, customer_a_token: str):
        """Customer token contains tenant_id claim."""
        claims = decode_token_claims(customer_a_token)
        assert "tenant_id" in claims
        assert claims["tenant_id"] == "tenant-a"

    async def test_customer_token_has_role(self, customer_a_token: str):
        """Customer token contains role claim."""
        claims = decode_token_claims(customer_a_token)
        assert "role" in claims
        assert claims["role"] == "customer_admin"

    async def test_operator_token_no_tenant(self, operator_token: str):
        """Operator token has no tenant_id (or empty)."""
        claims = decode_token_claims(operator_token)
        tenant = claims.get("tenant_id")
        assert tenant is None or tenant == ""

    async def test_operator_token_has_role(self, operator_token: str):
        """Operator token has operator role."""
        claims = decode_token_claims(operator_token)
        assert claims["role"] == "operator"


class TestRoleEnforcement:
    """Test role-based access control."""

    async def test_customer_cannot_access_operator_routes(
        self, client: AsyncClient, customer_a_token: str
    ):
        """Customer role cannot access operator routes."""
        response = await client.get(
            "/operator/devices",
            headers={"Authorization": f"Bearer {customer_a_token}"},
        )
        assert response.status_code == 403

    async def test_operator_cannot_access_customer_routes(
        self, client: AsyncClient, operator_token: str
    ):
        """Operator role cannot access customer routes."""
        response = await client.get(
            "/customer/devices",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert response.status_code == 403

    async def test_viewer_cannot_write(
        self, client: AsyncClient, customer_viewer_token: str
    ):
        """Customer viewer cannot create integrations."""
        response = await client.post(
            "/customer/integrations",
            headers={"Authorization": f"Bearer {customer_viewer_token}"},
            json={
                "name": "Test",
                "webhook_url": "https://example.com/hook",
            },
        )
        assert response.status_code == 403

    async def test_regular_operator_cannot_access_admin(
        self, client: AsyncClient, operator_token: str
    ):
        """Regular operator cannot access admin-only routes."""
        response = await client.get(
            "/operator/settings",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert response.status_code == 403

    async def test_operator_admin_can_access_admin(
        self, client: AsyncClient, operator_admin_token: str
    ):
        """Operator admin can access admin routes."""
        response = await client.get(
            "/operator/settings",
            headers={"Authorization": f"Bearer {operator_admin_token}"},
        )
        assert response.status_code == 200
