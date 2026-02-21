# Create Keycloak Admin Service

Create a service module that wraps the Keycloak Admin REST API for user management operations.

## File to Create

`services/ui_iot/services/keycloak_admin.py`

## Implementation

```python
"""
Keycloak Admin API client for user management.

Uses the Keycloak Admin REST API to manage users in the pulse realm.
Requires admin credentials to be configured via environment variables.
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

# Configuration
KEYCLOAK_INTERNAL_URL = os.getenv("KEYCLOAK_INTERNAL_URL", "http://pulse-keycloak:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "pulse")
KEYCLOAK_ADMIN_USERNAME = os.getenv("KEYCLOAK_ADMIN_USERNAME", "admin")
KEYCLOAK_ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin_dev")

# Token cache
_token_cache: dict = {"token": None, "expires_at": None}
_token_lock = asyncio.Lock()


class KeycloakAdminError(Exception):
    """Base exception for Keycloak Admin API errors."""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


async def _get_admin_token() -> str:
    """Get admin access token, using cache if valid."""
    async with _token_lock:
        now = datetime.utcnow()
        if _token_cache["token"] and _token_cache["expires_at"] and _token_cache["expires_at"] > now:
            return _token_cache["token"]

        token_url = f"{KEYCLOAK_INTERNAL_URL}/realms/master/protocol/openid-connect/token"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    token_url,
                    data={
                        "grant_type": "password",
                        "client_id": "admin-cli",
                        "username": KEYCLOAK_ADMIN_USERNAME,
                        "password": KEYCLOAK_ADMIN_PASSWORD,
                    }
                )
                response.raise_for_status()
                data = response.json()

                # Cache token with 60 second buffer before expiry
                expires_in = data.get("expires_in", 300) - 60
                _token_cache["token"] = data["access_token"]
                _token_cache["expires_at"] = now + timedelta(seconds=expires_in)

                return data["access_token"]
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get admin token: {e.response.status_code}")
            raise KeycloakAdminError("Failed to authenticate with Keycloak", 503)
        except Exception as e:
            logger.exception("Unexpected error getting admin token")
            raise KeycloakAdminError("Keycloak service unavailable", 503)


async def _admin_request(
    method: str,
    path: str,
    json: dict = None,
    params: dict = None
) -> dict | list | None:
    """Make authenticated request to Keycloak Admin API."""
    token = await _get_admin_token()
    url = f"{KEYCLOAK_INTERNAL_URL}/admin/realms/{KEYCLOAK_REALM}{path}"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.request(
                method,
                url,
                headers={"Authorization": f"Bearer {token}"},
                json=json,
                params=params
            )

            if response.status_code == 404:
                return None
            if response.status_code == 409:
                raise KeycloakAdminError("User already exists", 409)

            response.raise_for_status()

            if response.status_code == 204 or not response.content:
                return None
            return response.json()
    except KeycloakAdminError:
        raise
    except httpx.HTTPStatusError as e:
        logger.error(f"Keycloak API error: {e.response.status_code} - {e.response.text}")
        raise KeycloakAdminError(f"Keycloak API error: {e.response.text}", e.response.status_code)
    except Exception as e:
        logger.exception("Unexpected error calling Keycloak API")
        raise KeycloakAdminError("Keycloak service unavailable", 503)


# ============== USER OPERATIONS ==============

async def list_users(
    search: str = None,
    first: int = 0,
    max_results: int = 100
) -> list[dict]:
    """List users in the realm."""
    params = {"first": first, "max": max_results}
    if search:
        params["search"] = search

    users = await _admin_request("GET", "/users", params=params)
    return users or []


async def get_user(user_id: str) -> dict | None:
    """Get user by Keycloak ID."""
    return await _admin_request("GET", f"/users/{user_id}")


async def get_user_by_username(username: str) -> dict | None:
    """Get user by username."""
    users = await _admin_request("GET", "/users", params={"username": username, "exact": "true"})
    return users[0] if users else None


async def get_user_by_email(email: str) -> dict | None:
    """Get user by email."""
    users = await _admin_request("GET", "/users", params={"email": email, "exact": "true"})
    return users[0] if users else None


async def create_user(
    username: str,
    email: str,
    first_name: str = "",
    last_name: str = "",
    enabled: bool = True,
    email_verified: bool = False,
    temporary_password: str = None,
    attributes: dict = None
) -> str:
    """
    Create a new user in Keycloak.

    Returns the user ID if successful.
    """
    user_data = {
        "username": username,
        "email": email,
        "firstName": first_name,
        "lastName": last_name,
        "enabled": enabled,
        "emailVerified": email_verified,
        "attributes": attributes or {}
    }

    if temporary_password:
        user_data["credentials"] = [{
            "type": "password",
            "value": temporary_password,
            "temporary": True
        }]

    # Create user - Keycloak returns 201 with Location header
    token = await _get_admin_token()
    url = f"{KEYCLOAK_INTERNAL_URL}/admin/realms/{KEYCLOAK_REALM}/users"

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            url,
            headers={"Authorization": f"Bearer {token}"},
            json=user_data
        )

        if response.status_code == 409:
            raise KeycloakAdminError("User with this username or email already exists", 409)

        response.raise_for_status()

        # Extract user ID from Location header
        location = response.headers.get("Location", "")
        user_id = location.split("/")[-1] if location else None

        if not user_id:
            # Fetch user to get ID
            user = await get_user_by_username(username)
            user_id = user["id"] if user else None

        return user_id


async def update_user(user_id: str, updates: dict) -> None:
    """Update user attributes."""
    # Map friendly names to Keycloak field names
    user_data = {}
    if "first_name" in updates:
        user_data["firstName"] = updates["first_name"]
    if "last_name" in updates:
        user_data["lastName"] = updates["last_name"]
    if "email" in updates:
        user_data["email"] = updates["email"]
    if "enabled" in updates:
        user_data["enabled"] = updates["enabled"]
    if "attributes" in updates:
        user_data["attributes"] = updates["attributes"]

    await _admin_request("PUT", f"/users/{user_id}", json=user_data)


async def delete_user(user_id: str) -> None:
    """Delete a user."""
    await _admin_request("DELETE", f"/users/{user_id}")


async def set_user_password(user_id: str, password: str, temporary: bool = True) -> None:
    """Set user password."""
    await _admin_request("PUT", f"/users/{user_id}/reset-password", json={
        "type": "password",
        "value": password,
        "temporary": temporary
    })


async def enable_user(user_id: str) -> None:
    """Enable a user account."""
    await update_user(user_id, {"enabled": True})


async def disable_user(user_id: str) -> None:
    """Disable a user account."""
    await update_user(user_id, {"enabled": False})


# ============== ROLE OPERATIONS ==============

async def get_realm_roles() -> list[dict]:
    """Get all realm roles."""
    roles = await _admin_request("GET", "/roles")
    return roles or []


async def get_user_roles(user_id: str) -> list[dict]:
    """Get roles assigned to a user."""
    roles = await _admin_request("GET", f"/users/{user_id}/role-mappings/realm")
    return roles or []


async def assign_realm_role(user_id: str, role_name: str) -> None:
    """Assign a realm role to a user."""
    # First get the role to get its ID
    roles = await get_realm_roles()
    role = next((r for r in roles if r["name"] == role_name), None)

    if not role:
        raise KeycloakAdminError(f"Role '{role_name}' not found", 404)

    await _admin_request("POST", f"/users/{user_id}/role-mappings/realm", json=[role])


async def remove_realm_role(user_id: str, role_name: str) -> None:
    """Remove a realm role from a user."""
    roles = await get_realm_roles()
    role = next((r for r in roles if r["name"] == role_name), None)

    if not role:
        raise KeycloakAdminError(f"Role '{role_name}' not found", 404)

    await _admin_request("DELETE", f"/users/{user_id}/role-mappings/realm", json=[role])


# ============== ORGANIZATION OPERATIONS ==============

async def get_organizations() -> list[dict]:
    """Get all organizations (tenants)."""
    orgs = await _admin_request("GET", "/organizations")
    return orgs or []


async def get_organization_members(org_id: str) -> list[dict]:
    """Get members of an organization."""
    members = await _admin_request("GET", f"/organizations/{org_id}/members")
    return members or []


async def add_user_to_organization(user_id: str, org_id: str) -> None:
    """Add a user to an organization."""
    await _admin_request("PUT", f"/organizations/{org_id}/members/{user_id}")


async def remove_user_from_organization(user_id: str, org_id: str) -> None:
    """Remove a user from an organization."""
    await _admin_request("DELETE", f"/organizations/{org_id}/members/{user_id}")


# ============== UTILITY FUNCTIONS ==============

async def get_user_count() -> int:
    """Get total user count."""
    count = await _admin_request("GET", "/users/count")
    return count if isinstance(count, int) else 0


async def send_verify_email(user_id: str) -> None:
    """Send email verification to user."""
    await _admin_request("PUT", f"/users/{user_id}/send-verify-email")


async def send_password_reset_email(user_id: str) -> None:
    """Send password reset email to user."""
    await _admin_request("PUT", f"/users/{user_id}/execute-actions-email", json=["UPDATE_PASSWORD"])


def format_user_response(user: dict) -> dict:
    """Format Keycloak user for API response."""
    attributes = user.get("attributes", {})
    return {
        "id": user.get("id"),
        "username": user.get("username"),
        "email": user.get("email"),
        "first_name": user.get("firstName", ""),
        "last_name": user.get("lastName", ""),
        "enabled": user.get("enabled", False),
        "email_verified": user.get("emailVerified", False),
        "created_at": user.get("createdTimestamp"),
        "tenant_id": attributes.get("tenant_id", [None])[0] if attributes.get("tenant_id") else None,
        "attributes": attributes
    }
```

## Environment Variables

Add to `compose/docker-compose.yml` ui service environment:

```yaml
KEYCLOAK_ADMIN_USERNAME: "${KEYCLOAK_ADMIN_USERNAME:-admin}"
KEYCLOAK_ADMIN_PASSWORD: "${KEYCLOAK_ADMIN_PASSWORD:-admin_dev}"
```

## Notes

- Token caching reduces API calls (tokens valid ~5 minutes)
- All operations use async/await pattern consistent with codebase
- Error handling returns appropriate HTTP status codes
- Organizations feature uses Keycloak 26.0 Organizations API
- User attributes store tenant_id as array for multi-tenant support
