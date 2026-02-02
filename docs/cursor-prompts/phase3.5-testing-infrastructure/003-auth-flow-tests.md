# Task 003: Auth Flow Tests

> **CURSOR: EXECUTE THIS TASK**
>
> This is an implementation task. Read the instructions below and implement them.
> Modify the files listed in "Files to Create/Modify" section.
> Follow the acceptance criteria to verify your work.
> Commit with the message in the "Commit" section when done.

---

## Context

We need to test the OAuth flow, token validation, cookie handling, and token refresh. This requires getting real tokens from Keycloak for test users.

**Read first**:
- `services/ui_iot/middleware/auth.py` (JWT validation)
- `services/ui_iot/app.py` (OAuth routes)
- `compose/keycloak/realm-pulse.json` (test users)

**Depends on**: Tasks 001, 002

## Task

### 3.1 Create token helper for tests

Create `tests/helpers/auth.py`:

```python
import httpx
import os
from typing import Optional

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8180")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "pulse")
CLIENT_ID = "pulse-ui"


async def get_token(username: str, password: str) -> str:
    """Get access token from Keycloak."""
    token_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            token_url,
            data={
                "grant_type": "password",
                "client_id": CLIENT_ID,
                "username": username,
                "password": password,
            },
        )
        response.raise_for_status()
        return response.json()["access_token"]


async def get_customer1_token() -> str:
    """Get token for customer1 (tenant-a, customer_admin)."""
    return await get_token("customer1", "test123")


async def get_customer2_token() -> str:
    """Get token for customer2 (tenant-b, customer_viewer)."""
    return await get_token("customer2", "test123")


async def get_operator_token() -> str:
    """Get token for operator1."""
    return await get_token("operator1", "test123")


async def get_operator_admin_token() -> str:
    """Get token for operator_admin."""
    return await get_token("operator_admin", "test123")


def decode_token_claims(token: str) -> dict:
    """Decode JWT claims without verification (for testing)."""
    import base64
    import json

    # Split token and get payload
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT format")

    # Decode payload (add padding if needed)
    payload = parts[1]
    payload += "=" * (4 - len(payload) % 4)
    decoded = base64.urlsafe_b64decode(payload)
    return json.loads(decoded)
```

### 3.2 Update conftest.py with real token fixtures

Update `tests/conftest.py`:

```python
import pytest
from tests.helpers.auth import (
    get_customer1_token,
    get_customer2_token,
    get_operator_token,
    get_operator_admin_token,
)


# ============================================
# Real Auth Fixtures (require Keycloak running)
# ============================================

@pytest.fixture(scope="session")
async def customer_a_token() -> str:
    """Get valid JWT for customer1 (tenant-a, customer_admin)."""
    return await get_customer1_token()


@pytest.fixture(scope="session")
async def customer_b_token() -> str:
    """Get valid JWT for customer2 (tenant-b, customer_viewer)."""
    return await get_customer2_token()


@pytest.fixture(scope="session")
async def customer_viewer_token() -> str:
    """Alias for customer_b_token (customer_viewer role)."""
    return await get_customer2_token()


@pytest.fixture(scope="session")
async def operator_token() -> str:
    """Get valid JWT for operator1."""
    return await get_operator_token()


@pytest.fixture(scope="session")
async def operator_admin_token() -> str:
    """Get valid JWT for operator_admin."""
    return await get_operator_admin_token()
```

### 3.3 Create auth tests

Create `tests/api/test_auth.py`:

```python
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
            "/customer/devices",
            headers={"Authorization": f"Bearer {customer_a_token}"}
        )
        assert response.status_code == 200

    async def test_invalid_token_rejected(self, client: AsyncClient):
        """Invalid token returns 401."""
        response = await client.get(
            "/customer/devices",
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        assert response.status_code == 401

    async def test_expired_token_rejected(self, client: AsyncClient):
        """Expired token returns 401."""
        # This is a token that was valid but is now expired
        expired_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2MDAwMDAwMDB9.fake"
        response = await client.get(
            "/customer/devices",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401

    async def test_missing_auth_returns_401(self, client: AsyncClient):
        """No auth returns 401."""
        response = await client.get("/customer/devices")
        assert response.status_code == 401

    async def test_malformed_auth_header(self, client: AsyncClient):
        """Malformed auth header returns 401."""
        response = await client.get(
            "/customer/devices",
            headers={"Authorization": "NotBearer token"}
        )
        assert response.status_code == 401


class TestCookieAuth:
    """Test cookie-based authentication."""

    async def test_cookie_auth_works(
        self, client: AsyncClient, customer_a_token: str
    ):
        """Cookie authentication is accepted."""
        response = await client.get(
            "/customer/devices",
            cookies={"pulse_session": customer_a_token}
        )
        assert response.status_code == 200

    async def test_bearer_takes_precedence_over_cookie(
        self, client: AsyncClient, customer_a_token: str, customer_b_token: str
    ):
        """When both present, Bearer header takes precedence."""
        response = await client.get(
            "/customer/devices",
            headers={"Authorization": f"Bearer {customer_a_token}"},
            cookies={"pulse_session": customer_b_token}
        )
        assert response.status_code == 200
        data = response.json()
        # Should use token from header (customer_a = tenant-a)
        assert data["tenant_id"] == "tenant-a"


class TestAuthStatus:
    """Test /api/auth/status endpoint."""

    async def test_auth_status_authenticated(
        self, client: AsyncClient, customer_a_token: str
    ):
        """Auth status returns user info when authenticated."""
        response = await client.get(
            "/api/auth/status",
            cookies={"pulse_session": customer_a_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] == True
        assert "user" in data
        assert "expires_in" in data

    async def test_auth_status_not_authenticated(self, client: AsyncClient):
        """Auth status returns false when not authenticated."""
        response = await client.get("/api/auth/status")
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] == False


class TestAuthRefresh:
    """Test /api/auth/refresh endpoint."""

    async def test_refresh_without_token_returns_401(self, client: AsyncClient):
        """Refresh without token fails."""
        response = await client.post("/api/auth/refresh")
        assert response.status_code == 401

    # Note: Full refresh test requires a refresh token from Keycloak
    # which requires completing the OAuth flow


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
            headers={"Authorization": f"Bearer {customer_a_token}"}
        )
        assert response.status_code == 403

    async def test_operator_cannot_access_customer_routes(
        self, client: AsyncClient, operator_token: str
    ):
        """Operator role cannot access customer routes."""
        response = await client.get(
            "/customer/devices",
            headers={"Authorization": f"Bearer {operator_token}"}
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
                "webhook_url": "https://example.com/hook"
            }
        )
        assert response.status_code == 403

    async def test_regular_operator_cannot_access_admin(
        self, client: AsyncClient, operator_token: str
    ):
        """Regular operator cannot access admin-only routes."""
        response = await client.get(
            "/operator/settings",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 403

    async def test_operator_admin_can_access_admin(
        self, client: AsyncClient, operator_admin_token: str
    ):
        """Operator admin can access admin routes."""
        response = await client.get(
            "/operator/settings",
            headers={"Authorization": f"Bearer {operator_admin_token}"}
        )
        assert response.status_code == 200
```

### 3.4 Create helpers directory

```bash
mkdir -p tests/helpers
touch tests/helpers/__init__.py
```

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `tests/helpers/__init__.py` |
| CREATE | `tests/helpers/auth.py` |
| MODIFY | `tests/conftest.py` |
| CREATE | `tests/api/test_auth.py` |

## Acceptance Criteria

- [ ] Token helper can get tokens from Keycloak
- [ ] Auth fixtures provide real tokens
- [ ] Token validation tests pass
- [ ] Cookie auth tests pass
- [ ] Role enforcement tests pass
- [ ] Token claim tests pass

**Prerequisites**:
- Keycloak must be running: `docker compose up -d keycloak`
- Test users must exist (from realm import)

**Run tests**:
```bash
pytest tests/api/test_auth.py -v
```

## Commit

```
Add auth flow tests

- Token helper for getting Keycloak tokens
- Real token fixtures for test users
- Tests for token validation, cookie auth
- Tests for role enforcement
- Tests for token claims

Part of Phase 3.5: Testing Infrastructure
```
