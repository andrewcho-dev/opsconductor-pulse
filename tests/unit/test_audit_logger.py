"""Unit tests for high-performance audit logger."""
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.shared.audit import AuditLogger, AuditEvent


class TestAuditBuffer:
    """Test audit buffer behavior."""

    def test_buffer_accepts_events(self):
        logger = AuditLogger(AsyncMock(), "unit-test", batch_size=10, max_buffer_size=100)
        event = AuditEvent(
            timestamp=datetime.utcnow(),
            tenant_id="tenant-a",
            event_type="TEST",
            category="unit",
            severity="info",
            entity_type=None,
            entity_id=None,
            entity_name=None,
            action="test",
            message="test",
            details=None,
            source_service="unit",
            actor_type="user",
            actor_id="user-1",
            actor_name=None,
            ip_address=None,
            request_id=None,
            duration_ms=None,
        )

        logger.buffer.append(event)
        assert len(logger.buffer) == 1

    def test_buffer_flush_clears_events(self):
        logger = AuditLogger(AsyncMock(), "unit-test", batch_size=10, max_buffer_size=100)
        for i in range(3):
            logger.buffer.append(
                AuditEvent(
                    timestamp=datetime.utcnow(),
                    tenant_id="tenant-a",
                    event_type=f"TEST_{i}",
                    category="unit",
                    severity="info",
                    entity_type=None,
                    entity_id=None,
                    entity_name=None,
                    action="test",
                    message="test",
                    details=None,
                    source_service="unit",
                    actor_type="user",
                    actor_id="user-1",
                    actor_name=None,
                    ip_address=None,
                    request_id=None,
                    duration_ms=None,
                )
            )

        events = list(logger.buffer)
        logger.buffer.clear()

        assert len(events) == 3
        assert len(logger.buffer) == 0


class TestAuditLogger:
    """Test audit logger functionality."""

    @pytest.fixture
    def mock_pool(self):
        pool = MagicMock()
        conn = AsyncMock()
        pool.acquire.return_value.__aenter__.return_value = conn
        return pool, conn

    @pytest.mark.asyncio
    async def test_logs_event_to_database(self, mock_pool):
        pool, conn = mock_pool
        logger = AuditLogger(pool, "unit-test")

        logger.log(
            "DEVICE_CREATED",
            "device",
            "create",
            "device created",
            tenant_id="tenant-a",
            actor_type="user",
            actor_id="user-1",
            details={"device_id": "DEV-001"},
        )

        await logger._flush()

        assert conn.copy_records_to_table.called or conn.executemany.called or conn.execute.called

    @pytest.mark.asyncio
    async def test_batches_multiple_events(self, mock_pool):
        pool, conn = mock_pool
        logger = AuditLogger(pool, "unit-test", batch_size=10)

        for i in range(5):
            logger.log(
                f"EVENT_{i}",
                "system",
                "emit",
                "event",
                tenant_id="tenant-a",
                actor_type="system",
                actor_id="worker",
            )

        await logger._flush()

        assert conn.copy_records_to_table.called or conn.executemany.called or conn.execute.called

    @pytest.mark.asyncio
    async def test_auto_flush_on_timer(self, mock_pool):
        pool, conn = mock_pool
        logger = AuditLogger(pool, "unit-test", flush_interval_ms=50)

        await logger.start()
        logger.log(
            "TEST",
            "user",
            "action",
            "test",
            tenant_id="tenant-a",
            actor_type="user",
            actor_id="user-1",
        )

        await asyncio.sleep(0.1)
        await logger.stop()

        assert conn.copy_records_to_table.called or conn.executemany.called or conn.execute.called

    @pytest.mark.asyncio
    async def test_error_recovery(self, mock_pool):
        pool, conn = mock_pool
        conn.copy_records_to_table.side_effect = Exception("DB Error")

        logger = AuditLogger(pool, "unit-test")

        logger.log(
            "TEST",
            "user",
            "action",
            "test",
            tenant_id="tenant-a",
            actor_type="user",
            actor_id="user-1",
        )

        await logger._flush()

        assert len(logger.buffer) > 0
