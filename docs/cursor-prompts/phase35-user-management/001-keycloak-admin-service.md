# 001: Keycloak Admin Service

## Task

Create a backend service to interact with Keycloak Admin API for user management.

## File to Create

`services/ui_iot/services/keycloak_admin.py`

## Environment Variables

Add to service configuration:
```python
KEYCLOAK_ADMIN_URL = os.getenv("KEYCLOAK_ADMIN_URL", "https://localhost/auth")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "iotcloud")
KEYCLOAK_ADMIN_CLIENT_ID = os.getenv("KEYCLOAK_ADMIN_CLIENT_ID", "admin-cli")
KEYCLOAK_ADMIN_CLIENT_SECRET = os.getenv("KEYCLOAK_ADMIN_CLIENT_SECRET", "")
# Or use username/password for service account
KEYCLOAK_ADMIN_USERNAME = os.getenv("KEYCLOAK_ADMIN_USERNAME", "admin")
KEYCLOAK_ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")
```

## Implementation

```python
"""
Keycloak Admin API client for user management.
"""
import os
import httpx
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

KEYCLOAK_ADMIN_URL = os.getenv("KEYCLOAK_ADMIN_URL", "https://localhost")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "iotcloud")
KEYCLOAK_ADMIN_USERNAME = os.getenv("KEYCLOAK_ADMIN_USERNAME", "admin")
KEYCLOAK_ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")


@dataclass
class KeycloakUser:
    id: str
    username: str
    email: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    enabled: bool
    tenant_id: Optional[str]
    roles: List[str]
    created_at: Optional[datetime]


class KeycloakAdminClient:
    """Client for Keycloak Admin REST API."""

    def __init__(self):
        self._token: Optional[str] = None
        self._token_expires: Optional[datetime] = None
        self._client = httpx.AsyncClient(verify=False, timeout=30.0)

    async def _get_admin_token(self) -> str:
        """Get admin access token from Keycloak."""
        # Check if we have a valid cached token
        if self._token and self._token_expires:
            if datetime.now(timezone.utc) < self._token_expires:
                return self._token

        # Get new token
        token_url = f"{KEYCLOAK_ADMIN_URL}/realms/master/protocol/openid-connect/token"

        response = await self._client.post(
            token_url,
            data={
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": KEYCLOAK_ADMIN_USERNAME,
                "password": KEYCLOAK_ADMIN_PASSWORD,
            },
        )
        response.raise_for_status()

        data = response.json()
        self._token = data["access_token"]
        # Expire 60 seconds before actual expiry
        expires_in = data.get("expires_in", 300) - 60
        self._token_expires = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        return self._token

    async def _request(
        self,
        method: str,
        path: str,
        json: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> httpx.Response:
        """Make authenticated request to Keycloak Admin API."""
        token = await self._get_admin_token()
        url = f"{KEYCLOAK_ADMIN_URL}/admin/realms/{KEYCLOAK_REALM}{path}"

        response = await self._client.request(
            method,
            url,
            json=json,
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )
        return response

    # ==================== User Operations ====================

    async def list_users(
        self,
        tenant_id: Optional[str] = None,
        search: Optional[str] = None,
        first: int = 0,
        max_results: int = 100,
    ) -> List[KeycloakUser]:
        """List users, optionally filtered by tenant."""
        params = {"first": first, "max": max_results}

        if search:
            params["search"] = search

        response = await self._request("GET", "/users", params=params)
        response.raise_for_status()

        users = []
        for u in response.json():
            user = self._map_user(u)
            # Filter by tenant if specified
            if tenant_id and user.tenant_id != tenant_id:
                continue
            users.append(user)

        return users

    async def get_user(self, user_id: str) -> Optional[KeycloakUser]:
        """Get user by ID."""
        response = await self._request("GET", f"/users/{user_id}")

        if response.status_code == 404:
            return None

        response.raise_for_status()
        return self._map_user(response.json())

    async def get_user_by_username(self, username: str) -> Optional[KeycloakUser]:
        """Get user by username."""
        response = await self._request("GET", "/users", params={"username": username, "exact": "true"})
        response.raise_for_status()

        users = response.json()
        if not users:
            return None

        return self._map_user(users[0])

    async def create_user(
        self,
        username: str,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        tenant_id: Optional[str] = None,
        password: Optional[str] = None,
        temporary_password: bool = True,
        roles: Optional[List[str]] = None,
    ) -> str:
        """Create a new user. Returns user ID."""
        user_data = {
            "username": username,
            "email": email,
            "enabled": True,
            "emailVerified": False,
            "attributes": {},
        }

        if first_name:
            user_data["firstName"] = first_name
        if last_name:
            user_data["lastName"] = last_name
        if tenant_id:
            user_data["attributes"]["tenant_id"] = [tenant_id]

        response = await self._request("POST", "/users", json=user_data)
        response.raise_for_status()

        # Get user ID from Location header
        location = response.headers.get("Location", "")
        user_id = location.split("/")[-1]

        # Set password if provided
        if password:
            await self.set_password(user_id, password, temporary_password)

        # Assign roles if provided
        if roles:
            for role in roles:
                await self.assign_role(user_id, role)

        return user_id

    async def update_user(
        self,
        user_id: str,
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        enabled: Optional[bool] = None,
        tenant_id: Optional[str] = None,
    ) -> None:
        """Update user attributes."""
        # Get current user first
        response = await self._request("GET", f"/users/{user_id}")
        response.raise_for_status()
        user_data = response.json()

        # Update fields
        if email is not None:
            user_data["email"] = email
        if first_name is not None:
            user_data["firstName"] = first_name
        if last_name is not None:
            user_data["lastName"] = last_name
        if enabled is not None:
            user_data["enabled"] = enabled
        if tenant_id is not None:
            if "attributes" not in user_data:
                user_data["attributes"] = {}
            user_data["attributes"]["tenant_id"] = [tenant_id]

        response = await self._request("PUT", f"/users/{user_id}", json=user_data)
        response.raise_for_status()

    async def delete_user(self, user_id: str) -> None:
        """Delete a user."""
        response = await self._request("DELETE", f"/users/{user_id}")
        response.raise_for_status()

    async def set_password(
        self,
        user_id: str,
        password: str,
        temporary: bool = False,
    ) -> None:
        """Set user password."""
        response = await self._request(
            "PUT",
            f"/users/{user_id}/reset-password",
            json={
                "type": "password",
                "value": password,
                "temporary": temporary,
            },
        )
        response.raise_for_status()

    # ==================== Role Operations ====================

    async def get_realm_roles(self) -> List[Dict[str, Any]]:
        """Get all realm roles."""
        response = await self._request("GET", "/roles")
        response.raise_for_status()
        return response.json()

    async def get_user_roles(self, user_id: str) -> List[str]:
        """Get roles assigned to a user."""
        response = await self._request("GET", f"/users/{user_id}/role-mappings/realm")
        response.raise_for_status()
        return [r["name"] for r in response.json()]

    async def assign_role(self, user_id: str, role_name: str) -> None:
        """Assign a realm role to a user."""
        # First get the role
        response = await self._request("GET", f"/roles/{role_name}")
        if response.status_code == 404:
            raise ValueError(f"Role '{role_name}' not found")
        response.raise_for_status()
        role = response.json()

        # Assign role to user
        response = await self._request(
            "POST",
            f"/users/{user_id}/role-mappings/realm",
            json=[role],
        )
        response.raise_for_status()

    async def remove_role(self, user_id: str, role_name: str) -> None:
        """Remove a realm role from a user."""
        response = await self._request("GET", f"/roles/{role_name}")
        if response.status_code == 404:
            return  # Role doesn't exist, nothing to remove
        response.raise_for_status()
        role = response.json()

        response = await self._request(
            "DELETE",
            f"/users/{user_id}/role-mappings/realm",
            json=[role],
        )
        response.raise_for_status()

    # ==================== Helper Methods ====================

    def _map_user(self, data: Dict[str, Any]) -> KeycloakUser:
        """Map Keycloak user response to KeycloakUser dataclass."""
        attributes = data.get("attributes", {})
        tenant_ids = attributes.get("tenant_id", [])

        return KeycloakUser(
            id=data["id"],
            username=data["username"],
            email=data.get("email"),
            first_name=data.get("firstName"),
            last_name=data.get("lastName"),
            enabled=data.get("enabled", True),
            tenant_id=tenant_ids[0] if tenant_ids else None,
            roles=[],  # Roles fetched separately if needed
            created_at=datetime.fromtimestamp(data["createdTimestamp"] / 1000, tz=timezone.utc)
            if "createdTimestamp" in data else None,
        )

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()


# Singleton instance
_keycloak_client: Optional[KeycloakAdminClient] = None


async def get_keycloak_client() -> KeycloakAdminClient:
    """Get or create Keycloak admin client."""
    global _keycloak_client
    if _keycloak_client is None:
        _keycloak_client = KeycloakAdminClient()
    return _keycloak_client
```

## Add to requirements.txt

Ensure `httpx` is in `services/ui_iot/requirements.txt` (likely already present).

## Verification

```python
# Test the client
import asyncio
from services.keycloak_admin import get_keycloak_client

async def test():
    client = await get_keycloak_client()
    users = await client.list_users()
    print(f"Found {len(users)} users")
    for u in users:
        print(f"  {u.username} - tenant: {u.tenant_id}")

asyncio.run(test())
```
