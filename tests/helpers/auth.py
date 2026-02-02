import base64
import json
import os

import httpx

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
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT format")
    payload = parts[1]
    payload += "=" * (4 - len(payload) % 4)
    decoded = base64.urlsafe_b64decode(payload)
    return json.loads(decoded)
