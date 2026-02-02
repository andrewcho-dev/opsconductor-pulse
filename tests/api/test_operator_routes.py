import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestOperatorDevices:
    """Test /operator/devices endpoints."""

    async def test_list_all_devices_requires_operator(
        self, client: AsyncClient, customer_a_token: str
    ):
        """Customer cannot access operator routes."""
        response = await client.get(
            "/operator/devices",
            headers={"Authorization": f"Bearer {customer_a_token}"},
        )
        assert response.status_code == 403

    async def test_list_all_devices(
        self, client: AsyncClient, operator_token: str, test_tenants
    ):
        """Operator sees all devices across tenants."""
        response = await client.get(
            "/operator/devices",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "devices" in data
        tenant_ids = set(d["tenant_id"] for d in data["devices"])
        assert test_tenants["tenant_a"] in tenant_ids
        assert test_tenants["tenant_b"] in tenant_ids

    async def test_list_devices_with_tenant_filter(
        self, client: AsyncClient, operator_token: str, test_tenants
    ):
        """Operator can filter by tenant."""
        response = await client.get(
            f"/operator/devices?tenant_filter={test_tenants['tenant_a']}",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        for device in data["devices"]:
            assert device["tenant_id"] == test_tenants["tenant_a"]


class TestOperatorAudit:
    """Test operator audit logging."""

    async def test_operator_access_creates_audit_entry(
        self, client: AsyncClient, operator_token: str, db_pool
    ):
        """Operator access is logged."""
        await client.get(
            "/operator/devices",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT user_id, action, rls_bypassed
                FROM operator_audit_log
                ORDER BY created_at DESC
                LIMIT 1
                """
            )
            assert len(rows) == 1
            assert rows[0]["action"] == "list_all_devices"
            assert rows[0]["rls_bypassed"] is True

    async def test_audit_log_endpoint_requires_admin(
        self, client: AsyncClient, operator_token: str
    ):
        """Regular operator cannot access audit log."""
        response = await client.get(
            "/operator/audit-log",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert response.status_code == 403

    async def test_audit_log_endpoint(
        self, client: AsyncClient, operator_admin_token: str
    ):
        """Operator admin can access audit log."""
        response = await client.get(
            "/operator/audit-log",
            headers={"Authorization": f"Bearer {operator_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "entries" in data
        assert isinstance(data["entries"], list)


class TestOperatorSettings:
    """Test /operator/settings endpoints."""

    async def test_settings_requires_admin(
        self, client: AsyncClient, operator_token: str
    ):
        """Regular operator cannot access settings."""
        response = await client.get(
            "/operator/settings",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert response.status_code == 403

    async def test_settings_admin_access(
        self, client: AsyncClient, operator_admin_token: str
    ):
        """Operator admin can access settings."""
        response = await client.get(
            "/operator/settings",
            headers={"Authorization": f"Bearer {operator_admin_token}"},
        )
        assert response.status_code == 200
