from contextlib import asynccontextmanager

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.fixture(scope="session", autouse=True)
async def setup_delivery_tables():
    # Override the integration DB bootstrap fixture from tests/conftest.py
    # so this file remains pure unit tests.
    yield


class FakeTransaction:
    def __init__(self):
        self.started = False

    async def start(self):
        self.started = True

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *args):
        # asyncpg controls commit/rollback; we just track entry.
        return False


class FakeConnection:
    """Mock asyncpg connection for pool tests."""

    def __init__(self):
        self.executed: list[tuple[str, tuple]] = []
        self._transaction = FakeTransaction()

    async def execute(self, query, *args):
        self.executed.append((query, args))

    def transaction(self):
        return self._transaction


class FakePool:
    def __init__(self, conn):
        self.conn = conn

    @asynccontextmanager
    async def acquire(self):
        yield self.conn


async def test_tenant_connection_sets_rls_context():
    """tenant_connection sets app role and tenant_id."""
    from db.pool import tenant_connection

    conn = FakeConnection()
    pool = FakePool(conn)

    async with tenant_connection(pool, "tenant-a") as c:
        assert c is conn

    assert ("SET LOCAL ROLE pulse_app", ()) in conn.executed
    assert (
        "SELECT set_config('app.tenant_id', $1, true)",
        ("tenant-a",),
    ) in conn.executed


async def test_tenant_connection_uses_transaction():
    """tenant_connection wraps operations in a transaction."""
    from db.pool import tenant_connection

    conn = FakeConnection()
    pool = FakePool(conn)

    async with tenant_connection(pool, "tenant-a"):
        pass

    assert conn._transaction.started is True


async def test_operator_connection_sets_operator_role():
    """operator_connection sets pulse_operator role (bypasses RLS)."""
    from db.pool import operator_connection

    conn = FakeConnection()
    pool = FakePool(conn)

    async with operator_connection(pool) as c:
        assert c is conn

    assert ("SET LOCAL ROLE pulse_operator", ()) in conn.executed


async def test_tenant_connection_different_tenants():
    """Different tenant_ids result in different RLS context."""
    from db.pool import tenant_connection

    conn = FakeConnection()
    pool = FakePool(conn)

    async with tenant_connection(pool, "tenant-a"):
        pass
    first = list(conn.executed)

    conn.executed.clear()
    async with tenant_connection(pool, "tenant-b"):
        pass

    assert first != conn.executed
    assert (
        "SELECT set_config('app.tenant_id', $1, true)",
        ("tenant-b",),
    ) in conn.executed


async def test_tenant_connection_propagates_exceptions():
    """Exceptions inside tenant_connection propagate correctly."""
    from db.pool import tenant_connection

    conn = FakeConnection()
    pool = FakePool(conn)

    with pytest.raises(ValueError, match="test error"):
        async with tenant_connection(pool, "tenant-a"):
            raise ValueError("test error")


async def test_tenant_connection_requires_tenant_id():
    from db.pool import tenant_connection

    conn = FakeConnection()
    pool = FakePool(conn)

    with pytest.raises(ValueError, match="tenant_id is required"):
        async with tenant_connection(pool, ""):
            pass
print("placeholder")
print("placeholder")
from contextlib import asynccontextmanager

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class FakeTransaction:
    def __init__(self):
        self.started = False

    async def start(self):
        self.started = True

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *args):
        # asyncpg controls commit/rollback; we just track entry.
        return False


class FakeConnection:
    """Mock asyncpg connection for pool tests."""

    def __init__(self):
        self.executed: list[tuple[str, tuple]] = []
        self._transaction = FakeTransaction()

    async def execute(self, query, *args):
        self.executed.append((query, args))

    def transaction(self):
        return self._transaction


class FakePool:
    def __init__(self, conn):
        self.conn = conn

    @asynccontextmanager
    async def acquire(self):
        yield self.conn


async def test_tenant_connection_sets_rls_context():
    """tenant_connection sets app role and tenant_id."""
    from db.pool import tenant_connection

    conn = FakeConnection()
    pool = FakePool(conn)

    async with tenant_connection(pool, "tenant-a") as c:
        assert c is conn

    assert ("SET LOCAL ROLE pulse_app", ()) in conn.executed
    assert (
        "SELECT set_config('app.tenant_id', $1, true)",
        ("tenant-a",),
    ) in conn.executed


async def test_tenant_connection_uses_transaction():
    """tenant_connection wraps operations in a transaction."""
    from db.pool import tenant_connection

    conn = FakeConnection()
    pool = FakePool(conn)

    async with tenant_connection(pool, "tenant-a"):
        pass

    assert conn._transaction.started is True


async def test_operator_connection_sets_operator_role():
    """operator_connection sets pulse_operator role (bypasses RLS)."""
    from db.pool import operator_connection

    conn = FakeConnection()
    pool = FakePool(conn)

    async with operator_connection(pool) as c:
        assert c is conn

    assert ("SET LOCAL ROLE pulse_operator", ()) in conn.executed


async def test_tenant_connection_different_tenants():
    """Different tenant_ids result in different RLS context."""
    from db.pool import tenant_connection

    conn = FakeConnection()
    pool = FakePool(conn)

    async with tenant_connection(pool, "tenant-a"):
        pass
    first = list(conn.executed)

    conn.executed.clear()
    async with tenant_connection(pool, "tenant-b"):
        pass

    assert first != conn.executed
    assert (
        "SELECT set_config('app.tenant_id', $1, true)",
        ("tenant-b",),
    ) in conn.executed


async def test_tenant_connection_propagates_exceptions():
    """Exceptions inside tenant_connection propagate correctly."""
    from db.pool import tenant_connection

    conn = FakeConnection()
    pool = FakePool(conn)

    with pytest.raises(ValueError, match="test error"):
        async with tenant_connection(pool, "tenant-a"):
            raise ValueError("test error")


async def test_tenant_connection_requires_tenant_id():
    from db.pool import tenant_connection

    conn = FakeConnection()
    pool = FakePool(conn)

    with pytest.raises(ValueError, match="tenant_id is required"):
        async with tenant_connection(pool, ""):
            pass

from contextlib import asynccontextmanager

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class FakeTransaction:
    def __init__(self):
        self.started = False

    async def start(self):
        self.started = True

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *args):
        # asyncpg controls commit/rollback; we just track entry.
        return False


class FakeConnection:
    """Mock asyncpg connection for pool tests."""

    def __init__(self):
        self.executed: list[tuple[str, tuple]] = []
        self._transaction = FakeTransaction()

    async def execute(self, query, *args):
        self.executed.append((query, args))

    def transaction(self):
        return self._transaction


class FakePool:
    def __init__(self, conn):
        self.conn = conn

    @asynccontextmanager
    async def acquire(self):
        yield self.conn


async def test_tenant_connection_sets_rls_context():
    """tenant_connection sets app role and tenant_id."""
    from db.pool import tenant_connection

    conn = FakeConnection()
    pool = FakePool(conn)

    async with tenant_connection(pool, "tenant-a") as c:
        assert c is conn

    assert ("SET LOCAL ROLE pulse_app", ()) in conn.executed
    assert (
        "SELECT set_config('app.tenant_id', $1, true)",
        ("tenant-a",),
    ) in conn.executed


async def test_tenant_connection_uses_transaction():
    """tenant_connection wraps operations in a transaction."""
    from db.pool import tenant_connection

    conn = FakeConnection()
    pool = FakePool(conn)

    async with tenant_connection(pool, "tenant-a"):
        pass

    assert conn._transaction.started is True


async def test_operator_connection_sets_operator_role():
    """operator_connection sets pulse_operator role (bypasses RLS)."""
    from db.pool import operator_connection

    conn = FakeConnection()
    pool = FakePool(conn)

    async with operator_connection(pool) as c:
        assert c is conn

    assert ("SET LOCAL ROLE pulse_operator", ()) in conn.executed


async def test_tenant_connection_different_tenants():
    """Different tenant_ids result in different RLS context."""
    from db.pool import tenant_connection

    conn = FakeConnection()
    pool = FakePool(conn)

    async with tenant_connection(pool, "tenant-a"):
        pass
    first = list(conn.executed)

    conn.executed.clear()
    async with tenant_connection(pool, "tenant-b"):
        pass

    assert first != conn.executed
    assert (
        "SELECT set_config('app.tenant_id', $1, true)",
        ("tenant-b",),
    ) in conn.executed


async def test_tenant_connection_propagates_exceptions():
    """Exceptions inside tenant_connection propagate correctly."""
    from db.pool import tenant_connection

    conn = FakeConnection()
    pool = FakePool(conn)

    with pytest.raises(ValueError, match="test error"):
        async with tenant_connection(pool, "tenant-a"):
            raise ValueError("test error")


async def test_tenant_connection_requires_tenant_id():
    from db.pool import tenant_connection

    conn = FakeConnection()
    pool = FakePool(conn)

    with pytest.raises(ValueError, match="tenant_id is required"):
        async with tenant_connection(pool, ""):
            pass

