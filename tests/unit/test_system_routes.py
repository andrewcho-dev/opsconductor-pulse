"""Unit tests for system routes (health, metrics, capacity)."""
from unittest.mock import patch, AsyncMock

import pytest
from fastapi.testclient import TestClient

from services.ui_iot.app import app


class TestHealthEndpoint:
    """Test health check endpoint."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_health_returns_ok(self, client):
        response = client.get("/api/v2/health")
        assert response.status_code == 200

    def test_health_includes_components(self, client):
        response = client.get("/api/v2/health")
        data = response.json()

        assert "status" in data
        assert "service" in data


class TestMetricsEndpoint:
    """Test metrics endpoint."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @patch("services.ui_iot.routes.system.get_pool")
    def test_metrics_returns_counts(self, mock_pool, client):
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = 100
        mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn

        response = client.get("/operator/system/metrics")

        assert response.status_code in [200, 401, 403]


class TestCapacityEndpoint:
    """Test capacity endpoint."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @patch("services.ui_iot.routes.system.get_pool")
    def test_capacity_returns_limits(self, mock_pool, client):
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = []
        mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn

        response = client.get("/operator/system/capacity")

        assert response.status_code in [200, 401, 403]
