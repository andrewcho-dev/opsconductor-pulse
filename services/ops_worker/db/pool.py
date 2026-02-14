from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg


@asynccontextmanager
async def tenant_connection(pool: asyncpg.Pool, tenant_id: str) -> AsyncGenerator[asyncpg.Connection, None]:
    """
    Acquire a connection with tenant context set for RLS.

    Usage:
        async with tenant_connection(pool, tenant_id) as conn:
            rows = await conn.fetch("SELECT * FROM device_state")
            # RLS automatically filters to tenant_id
    """
    if not tenant_id:
        raise ValueError("tenant_id is required for tenant_connection")

    async with pool.acquire() as conn:
        async with conn.transaction():
            # Set role to pulse_app (subject to RLS)
            await conn.execute("SET LOCAL ROLE pulse_app")
            # Set tenant context for RLS policies
            await conn.execute("SELECT set_config('app.tenant_id', $1, true)", tenant_id)
            yield conn
            # Connection returned to pool; SET LOCAL resets automatically


@asynccontextmanager
async def operator_connection(pool: asyncpg.Pool) -> AsyncGenerator[asyncpg.Connection, None]:
    """
    Acquire a connection with operator role (bypasses RLS).

    WARNING: Only use for authenticated operator routes.
    All access through this connection should be audited.

    Usage:
        async with operator_connection(pool) as conn:
            rows = await conn.fetch("SELECT * FROM device_state")
            # Returns ALL rows, no RLS filtering
    """
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Set role to pulse_operator (BYPASSRLS)
            await conn.execute("SET LOCAL ROLE pulse_operator")
            yield conn
