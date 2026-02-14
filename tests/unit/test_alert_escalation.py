from contextlib import asynccontextmanager
from datetime import datetime, timezone

import pytest

from services.evaluator_iot import evaluator
from services.dispatcher import dispatcher

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


class DispConn:
    def __init__(self):
        self.fetch_calls = []
        self.fetchval_calls = []
        self.fetchrow_calls = []
        self.inserted = True
        self.already = False

    async def fetch(self, query, *args):
        self.fetch_calls.append((query, args))
        if "FROM fleet_alert" in query:
            return [
                {
                    "id": 5,
                    "tenant_id": "tenant-a",
                    "site_id": "site-1",
                    "device_id": "dev-1",
                    "alert_type": "THRESHOLD",
                    "severity": 2,
                    "confidence": 0.9,
                    "summary": "Escalated",
                    "status": "OPEN",
                    "created_at": datetime.now(timezone.utc),
                    "details": {},
                    "escalated_at": datetime.now(timezone.utc),
                    "escalation_level": 1,
                }
            ]
        return []

    async def fetchval(self, query, *args):
        self.fetchval_calls.append((query, args))
        if "FROM delivery_jobs" in query:
            return 1 if self.already else None
        return None

    async def fetchrow(self, query, *args):
        self.fetchrow_calls.append((query, args))
        if "INSERT INTO delivery_jobs" in query and self.inserted:
            return {"job_id": 99}
        return None


async def test_dispatch_escalated_alerts_creates_job(monkeypatch):
    conn = DispConn()
    async def _routes(_conn, _tenant_id):
        return [
            {
                "route_id": "r1",
                "integration_id": "i1",
                "deliver_on": ["OPEN"],
                "min_severity": None,
                "alert_types": [],
                "site_ids": [],
                "device_prefixes": [],
            }
        ]
    monkeypatch.setattr(
        dispatcher,
        "fetch_routes",
        _routes,
    )
    created = await dispatcher.dispatch_escalated_alerts(conn, "tenant-a", lookback_minutes=5)
    assert created == 1


async def test_dispatch_escalated_no_duplicates(monkeypatch):
    conn = DispConn()
    conn.already = True
    async def _routes(_conn, _tenant_id):
        return [
            {
                "route_id": "r1",
                "integration_id": "i1",
                "deliver_on": ["OPEN"],
                "min_severity": None,
                "alert_types": [],
                "site_ids": [],
                "device_prefixes": [],
            }
        ]
    monkeypatch.setattr(
        dispatcher,
        "fetch_routes",
        _routes,
    )
    created = await dispatcher.dispatch_escalated_alerts(conn, "tenant-a", lookback_minutes=5)
    assert created == 0
