"""Unit tests for telemetry query functions."""
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock

import pytest

from services.ui_iot.db.telemetry_queries import (
    fetch_device_telemetry,
    fetch_device_telemetry_latest,
    fetch_telemetry_time_series,
    fetch_fleet_telemetry_summary,
)


class TestFetchTelemetry:
    """Test telemetry fetch functions."""

    @pytest.fixture
    def mock_conn(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_fetch_with_time_range(self, mock_conn):
        mock_conn.fetch.return_value = [
            {
                "time": datetime.now(timezone.utc),
                "device_id": "DEV-001",
                "metrics": {"temp": 25},
                "seq": 1,
                "msg_type": "telemetry",
            },
        ]

        result = await fetch_device_telemetry(
            mock_conn,
            tenant_id="tenant-a",
            device_id="DEV-001",
            start=datetime.now(timezone.utc) - timedelta(hours=1),
            end=datetime.now(timezone.utc),
        )

        assert len(result) == 1
        assert mock_conn.fetch.called

    @pytest.mark.asyncio
    async def test_fetch_latest(self, mock_conn):
        mock_conn.fetchrow.return_value = {
            "time": datetime.now(timezone.utc),
            "metrics": {"temp": 25},
            "seq": 1,
        }

        result = await fetch_device_telemetry_latest(
            mock_conn,
            tenant_id="tenant-a",
            device_id="DEV-001",
        )

        assert result is not None
        assert mock_conn.fetchrow.called


class TestAggregatedQueries:
    """Test time-bucket aggregation queries."""

    @pytest.fixture
    def mock_conn(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_time_bucket_aggregation(self, mock_conn):
        mock_conn.fetch.return_value = []

        await fetch_telemetry_time_series(
            mock_conn,
            tenant_id="tenant-a",
            device_id="DEV-001",
            metric_key="temperature",
            hours=6,
            bucket_minutes=5,
        )

        call_args = mock_conn.fetch.call_args[0][0]
        assert "time_bucket" in call_args

    @pytest.mark.asyncio
    async def test_fleet_summary_query(self, mock_conn):
        mock_conn.fetchrow.return_value = {
            "sample_count": 0,
            "device_count": 0,
            "temperature_avg": None,
            "temperature_min": None,
            "temperature_max": None,
        }

        result = await fetch_fleet_telemetry_summary(
            mock_conn,
            tenant_id="tenant-a",
            metric_keys=["temperature"],
            hours=1,
        )

        assert result["metrics"]["temperature"]["avg"] is None
        assert mock_conn.fetchrow.called
