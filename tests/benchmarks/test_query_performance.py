import asyncio
import math
import os
import random
import json
import uuid
import time

import asyncpg
import pytest

pytestmark = [pytest.mark.benchmark, pytest.mark.asyncio]

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://iot:iot_dev@localhost:5432/iotcloud"
)

TENANTS = [f"bench-tenant-{i}" for i in range(5)]


def _p95_ms(benchmark) -> float:
    data = benchmark.stats.stats.sorted_data
    if not data:
        return 0.0
    index = max(int(math.ceil(0.95 * len(data))) - 1, 0)
    return data[index] * 1000.0


def _benchmark_query(benchmark, loop, runner, rounds: int, threshold_ms: float):
    benchmark.pedantic(runner, rounds=rounds, warmup_rounds=3)
    p95_ms = _p95_ms(benchmark)
    assert p95_ms < threshold_ms


async def _seed_data(conn: asyncpg.Connection):
    device_rows = []
    for tenant in TENANTS:
        for i in range(20):
            device_rows.append(
                (
                    tenant,
                    f"{tenant}-site",
                    f"{tenant}-device-{i}",
                    "ONLINE" if i % 2 == 0 else "STALE",
                )
            )
    await conn.executemany(
        """
        INSERT INTO device_state (tenant_id, site_id, device_id, status, last_seen_at)
        VALUES ($1, $2, $3, $4, now())
        ON CONFLICT (tenant_id, device_id) DO NOTHING
        """,
        device_rows,
    )

    alert_rows = []
    for i in range(500):
        tenant = TENANTS[i % len(TENANTS)]
        device_id = f"{tenant}-device-{i % 20}"
        alert_rows.append(
            (
                tenant,
                f"{tenant}-site",
                device_id,
                "DEVICE_OFFLINE",
                str(uuid.uuid4()),
                "OPEN",
                random.randint(0, 2),
                0.9,
                f"Alert {i}",
            )
        )
    await conn.executemany(
        """
        INSERT INTO fleet_alert (
            tenant_id, site_id, device_id, alert_type, fingerprint,
            status, severity, confidence, summary
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """,
        alert_rows,
    )

    integration_rows = []
    route_rows = []
    integration_ids = []
    route_ids = []
    for i in range(50):
        tenant = TENANTS[i % len(TENANTS)]
        integration_id = uuid.uuid4()
        route_id = uuid.uuid4()
        integration_ids.append((tenant, integration_id))
        route_ids.append((tenant, route_id))
        integration_rows.append(
            (
                tenant,
                integration_id,
                f"Integration {i}",
                "webhook",
                json.dumps({"url": f"https://example.com/hook-{i}"}),
            )
        )
        route_rows.append((tenant, route_id, integration_id, f"Route {i}"))

    await conn.executemany(
        """
        INSERT INTO integrations (tenant_id, integration_id, name, type, config_json)
        VALUES ($1, $2, $3, $4, $5::jsonb)
        ON CONFLICT DO NOTHING
        """,
        integration_rows,
    )
    await conn.executemany(
        """
        INSERT INTO integration_routes (tenant_id, route_id, integration_id, name)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT DO NOTHING
        """,
        route_rows,
    )

    job_rows = []
    for i in range(200):
        tenant, integration_id = integration_ids[i % len(integration_ids)]
        _, route_id = route_ids[i % len(route_ids)]
        job_rows.append(
            (
                tenant,
                i + 1,
                integration_id,
                route_id,
                "OPEN",
                "PENDING",
                "{}",
            )
        )
    await conn.executemany(
        """
        INSERT INTO delivery_jobs (
            tenant_id, alert_id, integration_id, route_id,
            deliver_on_event, status, payload_json
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
        """,
        job_rows,
    )


async def _cleanup_data(conn: asyncpg.Connection):
    await conn.execute(
        "DELETE FROM delivery_jobs WHERE tenant_id LIKE 'bench-tenant-%'"
    )
    await conn.execute(
        "DELETE FROM integration_routes WHERE tenant_id LIKE 'bench-tenant-%'"
    )
    await conn.execute(
        "DELETE FROM integrations WHERE tenant_id LIKE 'bench-tenant-%'"
    )
    await conn.execute(
        "DELETE FROM fleet_alert WHERE tenant_id LIKE 'bench-tenant-%'"
    )
    await conn.execute(
        "DELETE FROM device_state WHERE tenant_id LIKE 'bench-tenant-%'"
    )


@pytest.fixture(scope="module")
def db_context():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    conn = loop.run_until_complete(asyncpg.connect(DATABASE_URL))
    loop.run_until_complete(_seed_data(conn))
    yield loop, conn
    loop.run_until_complete(_cleanup_data(conn))
    loop.run_until_complete(conn.close())
    loop.close()
    asyncio.set_event_loop(None)


def test_benchmark_query_devices_by_tenant(benchmark, db_context):
    loop, conn = db_context
    tenant_id = TENANTS[0]

    def runner():
        return loop.run_until_complete(
            conn.fetch(
                "SELECT * FROM device_state WHERE tenant_id = $1",
                tenant_id,
            )
        )

    _benchmark_query(benchmark, loop, runner, rounds=50, threshold_ms=50)


def test_benchmark_query_alerts_by_tenant(benchmark, db_context):
    loop, conn = db_context
    tenant_id = TENANTS[0]

    def runner():
        return loop.run_until_complete(
            conn.fetch(
                """
                SELECT * FROM fleet_alert
                WHERE tenant_id = $1
                ORDER BY created_at DESC
                LIMIT 50
                """,
                tenant_id,
            )
        )

    _benchmark_query(benchmark, loop, runner, rounds=50, threshold_ms=100)


def test_benchmark_query_integrations_by_tenant(benchmark, db_context):
    loop, conn = db_context
    tenant_id = TENANTS[0]

    def runner():
        return loop.run_until_complete(
            conn.fetch(
                "SELECT * FROM integrations WHERE tenant_id = $1",
                tenant_id,
            )
        )

    _benchmark_query(benchmark, loop, runner, rounds=50, threshold_ms=50)


def test_benchmark_query_delivery_jobs_pending(benchmark, db_context):
    loop, conn = db_context

    def runner():
        return loop.run_until_complete(
            conn.fetch(
                """
                SELECT * FROM delivery_jobs
                WHERE status = 'pending'
                ORDER BY created_at
                LIMIT 10
                """
            )
        )

    _benchmark_query(benchmark, loop, runner, rounds=50, threshold_ms=100)


def test_benchmark_query_cross_tenant_devices(benchmark, db_context):
    loop, conn = db_context

    def runner():
        return loop.run_until_complete(
            conn.fetch("SELECT * FROM device_state")
        )

    _benchmark_query(benchmark, loop, runner, rounds=20, threshold_ms=200)


def test_benchmark_rls_overhead(benchmark, db_context):
    loop, conn = db_context
    tenant_id = TENANTS[0]

    def runner():
        async def _query():
            await conn.execute(
                f"SET LOCAL app.tenant_id = '{tenant_id}'"
            )
            return await conn.fetch(
                "SELECT * FROM device_state WHERE tenant_id = $1",
                tenant_id,
            )

        return loop.run_until_complete(_query())

    benchmark.pedantic(runner, rounds=20, warmup_rounds=3)
    p95_with_rls = _p95_ms(benchmark)

    timings = []
    for _ in range(20):
        start = time.perf_counter()
        loop.run_until_complete(
            conn.fetch(
                "SELECT * FROM device_state WHERE tenant_id = $1",
                tenant_id,
            )
        )
        timings.append(time.perf_counter() - start)
    timings.sort()
    index = max(int(math.ceil(0.95 * len(timings))) - 1, 0)
    p95_without_rls = timings[index] * 1000.0
    overhead_ms = p95_with_rls - p95_without_rls
    print(
        f"RLS overhead p95: {overhead_ms:.2f}ms (with={p95_with_rls:.2f}ms, without={p95_without_rls:.2f}ms)"
    )
