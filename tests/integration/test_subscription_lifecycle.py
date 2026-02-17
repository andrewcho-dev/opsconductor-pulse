import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestSubscriptionLifecycle:
    """Integration coverage for subscription and tier visibility."""

    async def test_view_subscriptions_and_device_tiers(
        self, client: AsyncClient, customer_a_token: str, test_tenants, clean_db
    ):
        headers = {"Authorization": f"Bearer {customer_a_token}"}

        # 1) List current subscriptions (may be empty in minimal schema)
        subs_resp = await client.get("/customer/subscriptions", headers=headers)
        assert subs_resp.status_code == 200
        data = subs_resp.json()
        assert "subscriptions" in data
        assert "summary" in data

        # 2) If any subscription exists, detail endpoint works.
        subs = data.get("subscriptions", [])
        if subs:
            sub_id = subs[0]["subscription_id"]
            detail = await client.get(f"/customer/subscriptions/{sub_id}", headers=headers)
            assert detail.status_code == 200

        # 3) Device tiers list should be available for customers
        tiers_resp = await client.get("/customer/device-tiers", headers=headers)
        assert tiers_resp.status_code == 200
        tiers = tiers_resp.json().get("tiers", [])
        assert isinstance(tiers, list)

