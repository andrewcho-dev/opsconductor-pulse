import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestUserLifecycle:
    """Integration coverage for customer user management endpoints."""

    async def test_user_list_contract(
        self, client: AsyncClient, customer_a_token: str, clean_db
    ):
        headers = {"Authorization": f"Bearer {customer_a_token}"}
        resp = await client.get("/customer/users", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "users" in data
        assert isinstance(data["users"], list)

    async def test_operator_cannot_access_customer_users(
        self, client: AsyncClient, operator_token: str
    ):
        """
        Operators do not have tenant context, so customer-scoped endpoints should be blocked.
        Depending on middleware ordering, this can manifest as 401 or 403.
        """
        headers = {"Authorization": f"Bearer {operator_token}"}
        resp = await client.get("/customer/users", headers=headers)
        assert resp.status_code in (401, 403)

