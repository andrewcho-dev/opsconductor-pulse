import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestDeprecatedRoutes:
    """Test deprecated routes return proper responses."""

    async def test_old_device_route_returns_410(self, client: AsyncClient):
        """Old /device/{id} route returns 410 Gone."""
        response = await client.get("/device/any-device-id")
        assert response.status_code == 410
        assert "deprecated" in response.text.lower() or "gone" in response.text.lower()
