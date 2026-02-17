from contextlib import asynccontextmanager
from datetime import datetime, timezone

import pytest

from services.evaluator_iot import evaluator

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class EvalConn:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.last_query = ""

    async def fetch(self, query, *args, **kwargs):
        self.last_query = query
        return self.rows


class EvalPool:
    def __init__(self, conn):
        self.conn = conn

    @asynccontextmanager
    async def acquire(self):
        yield self.conn


async def test_check_escalations_escalates_overdue_alert():
    conn = EvalConn(rows=[{"id": 1}])
    count = await evaluator.check_escalations(EvalPool(conn))
    assert count == 1


async def test_check_escalations_skips_acknowledged():
    conn = EvalConn()
    await evaluator.check_escalations(EvalPool(conn))
    assert "fa.status = 'OPEN'" in conn.last_query


async def test_check_escalations_skips_already_escalated():
    conn = EvalConn()
    await evaluator.check_escalations(EvalPool(conn))
    assert "fa.escalation_level = 0" in conn.last_query


async def test_check_escalations_skips_silenced():
    conn = EvalConn()
    await evaluator.check_escalations(EvalPool(conn))
    assert "fa.silenced_until IS NULL OR fa.silenced_until <= now()" in conn.last_query


async def test_check_escalations_no_escalation_minutes():
    conn = EvalConn()
    await evaluator.check_escalations(EvalPool(conn))
    assert "ar.escalation_minutes IS NOT NULL" in conn.last_query


async def test_check_escalations_severity_floor():
    conn = EvalConn()
    await evaluator.check_escalations(EvalPool(conn))
    assert "GREATEST(fa.severity - 1, 0)" in conn.last_query
