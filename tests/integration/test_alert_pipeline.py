import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestAlertPipeline:
    """Integration coverage for alerts: list -> (optional) acknowledge/close; rules listing."""

    async def test_alert_list_and_optional_acknowledge(
        self, client: AsyncClient, customer_a_token: str, test_tenants, clean_db
    ):
        headers = {"Authorization": f"Bearer {customer_a_token}"}

        # 1) List alerts for tenant A.
        alerts_resp = await client.get("/customer/alerts?format=json", headers=headers)
        assert alerts_resp.status_code == 200
        alerts = alerts_resp.json().get("alerts", [])
        for a in alerts:
            assert a["tenant_id"] == test_tenants["tenant_a"]

        # 2) If any OPEN alerts exist, exercise acknowledge and close flows.
        if alerts:
            alert_id = alerts[0]["alert_id"]
            ack = await client.patch(f"/customer/alerts/{alert_id}/acknowledge", headers=headers)
            assert ack.status_code == 200
            ack_data = ack.json()
            assert ack_data.get("ok") is True

            close = await client.patch(f"/customer/alerts/{alert_id}/close", headers=headers)
            assert close.status_code == 200
            close_data = close.json()
            assert close_data.get("ok") is True

    async def test_alert_rules_list_contract(
        self, client: AsyncClient, customer_a_token: str, clean_db
    ):
        """
        Rule creation can be blocked by entitlement limits (402) depending on plan setup.
        This test focuses on the list API contract being reachable for an authenticated tenant.
        """
        headers = {"Authorization": f"Bearer {customer_a_token}"}
        resp = await client.get("/customer/alert-rules", headers=headers)
        assert resp.status_code == 200
        assert "rules" in resp.json()

