"""Unit tests for subscription worker state transitions and notifications."""
import sys
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, "services/subscription_worker")
from worker import (  # noqa: E402
    schedule_renewal_notifications,
    process_grace_transitions,
    reconcile_device_counts,
    NOTIFICATION_DAYS,
    GRACE_PERIOD_DAYS,
)


class TestRenewalNotifications:
    """Test renewal notification scheduling."""

    @pytest.fixture
    def mock_pool(self):
        pool = MagicMock()
        conn = AsyncMock()
        pool.acquire.return_value.__aenter__.return_value = conn
        return pool, conn

    @pytest.mark.asyncio
    async def test_schedules_notification_for_expiring_subscription(self, mock_pool):
        """Notification scheduled when subscription expires within window."""
        pool, conn = mock_pool
        conn.fetch.return_value = [
            {
                "subscription_id": "SUB-001",
                "tenant_id": "tenant-a",
                "term_end": datetime.now(timezone.utc) + timedelta(days=30),
                "tenant_name": "Test Tenant",
            }
        ]

        await schedule_renewal_notifications(pool)

        assert conn.execute.called
        call_args = conn.execute.call_args[0][0]
        assert "INSERT INTO subscription_notifications" in call_args

    @pytest.mark.asyncio
    async def test_skips_already_notified(self, mock_pool):
        """No duplicate notification if already scheduled."""
        pool, conn = mock_pool
        conn.fetch.return_value = []

        await schedule_renewal_notifications(pool)

        insert_calls = [c for c in conn.execute.call_args_list if "INSERT" in str(c)]
        assert len(insert_calls) == 0

    @pytest.mark.asyncio
    async def test_all_notification_windows(self, mock_pool):
        """Test all notification day windows are checked."""
        pool, conn = mock_pool
        conn.fetch.return_value = []

        await schedule_renewal_notifications(pool)

        assert len(conn.fetch.call_args_list) == len(NOTIFICATION_DAYS)


class TestGraceTransitions:
    """Test subscription status transitions."""

    @pytest.fixture
    def mock_pool(self):
        pool = MagicMock()
        conn = AsyncMock()
        pool.acquire.return_value.__aenter__.return_value = conn
        return pool, conn

    @pytest.mark.asyncio
    async def test_active_to_grace_transition(self, mock_pool):
        """ACTIVE → GRACE when term_end passes."""
        pool, conn = mock_pool
        conn.fetch.side_effect = [
            [{"subscription_id": "SUB-001", "tenant_id": "tenant-a"}],
            [],
        ]

        await process_grace_transitions(pool)

        assert conn.execute.called
        assert len(conn.fetch.call_args_list) == 2

    @pytest.mark.asyncio
    async def test_grace_to_suspended_transition(self, mock_pool):
        """GRACE → SUSPENDED when grace_end passes."""
        pool, conn = mock_pool
        conn.fetch.side_effect = [
            [],
            [{"subscription_id": "SUB-002", "tenant_id": "tenant-b"}],
        ]

        await process_grace_transitions(pool)

        execute_calls = [c for c in conn.execute.call_args_list if "subscription_audit" in str(c)]
        assert len(execute_calls) >= 1

    @pytest.mark.asyncio
    async def test_grace_period_calculation(self, mock_pool):
        """Grace end is set to term_end + grace period."""
        pool, conn = mock_pool
        conn.fetch.side_effect = [
            [{"subscription_id": "SUB-001", "tenant_id": "tenant-a"}],
            [],
        ]

        await process_grace_transitions(pool)

        fetch_call = conn.fetch.call_args_list[0][0][0]
        assert "interval '14 days'" in fetch_call or str(GRACE_PERIOD_DAYS) in fetch_call


class TestDeviceCountReconciliation:
    """Test device count reconciliation."""

    @pytest.fixture
    def mock_pool(self):
        pool = MagicMock()
        conn = AsyncMock()
        pool.acquire.return_value.__aenter__.return_value = conn
        return pool, conn

    @pytest.mark.asyncio
    async def test_reconciles_mismatched_counts(self, mock_pool):
        """Corrects active_device_count when out of sync."""
        pool, conn = mock_pool
        conn.execute.return_value = "UPDATE 3"

        await reconcile_device_counts(pool)

        assert conn.execute.called
        call_args = conn.execute.call_args[0][0]
        assert "UPDATE subscriptions" in call_args
        assert "active_device_count" in call_args

    @pytest.mark.asyncio
    async def test_no_update_when_counts_match(self, mock_pool):
        """No updates when counts are correct."""
        pool, conn = mock_pool
        conn.execute.return_value = "UPDATE 0"

        await reconcile_device_counts(pool)

        assert conn.execute.called
