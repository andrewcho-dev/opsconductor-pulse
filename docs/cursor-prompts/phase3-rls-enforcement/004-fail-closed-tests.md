# Task 004: Fail-Closed Tests

> **CURSOR: EXECUTE THIS TASK**
>
> This is an implementation task. Read the instructions below and implement them.
> Modify the files listed in "Files to Create/Modify" section.
> Follow the acceptance criteria to verify your work.
> Commit with the message in the "Commit" section when done.

---

## Context

RLS must fail closed: if tenant context is missing or wrong, queries should return zero rows (not all rows). We need tests to verify this behavior and catch regressions.

**Read first**:
- `db/migrations/004_enable_rls.sql` (RLS policies)
- `services/ui_iot/db/pool.py` (connection wrappers)
- Existing test patterns in the codebase

**Depends on**: Tasks 001, 002, 003

## Task

### 4.1 Create RLS test file

Create `tests/test_rls_enforcement.py`:

**Test structure**:
```python
import pytest
import asyncpg
import os

# Database connection for tests
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://iot:iot_dev@localhost:5432/iotcloud")

@pytest.fixture
async def db_pool():
    pool = await asyncpg.create_pool(DATABASE_URL)
    yield pool
    await pool.close()

@pytest.fixture
async def test_data(db_pool):
    """Create test data in two tenants."""
    async with db_pool.acquire() as conn:
        # Insert test devices
        await conn.execute("""
            INSERT INTO device_state (tenant_id, device_id, site_id, status)
            VALUES
                ('test-tenant-a', 'device-a1', 'site-a', 'ONLINE'),
                ('test-tenant-a', 'device-a2', 'site-a', 'ONLINE'),
                ('test-tenant-b', 'device-b1', 'site-b', 'ONLINE')
            ON CONFLICT DO NOTHING
        """)
    yield
    # Cleanup
    async with db_pool.acquire() as conn:
        await conn.execute("""
            DELETE FROM device_state WHERE tenant_id IN ('test-tenant-a', 'test-tenant-b')
        """)
```

### 4.2 Test: No context returns zero rows

```python
@pytest.mark.asyncio
async def test_no_tenant_context_returns_zero_rows(db_pool, test_data):
    """Without app.tenant_id set, RLS should return zero rows."""
    async with db_pool.acquire() as conn:
        # Set role to pulse_app but do NOT set app.tenant_id
        await conn.execute("SET LOCAL ROLE pulse_app")

        # Query should return zero rows
        rows = await conn.fetch(
            "SELECT * FROM device_state WHERE tenant_id IN ('test-tenant-a', 'test-tenant-b')"
        )

        assert len(rows) == 0, "Expected zero rows when tenant context not set"
```

### 4.3 Test: Wrong tenant returns zero rows

```python
@pytest.mark.asyncio
async def test_wrong_tenant_returns_zero_rows(db_pool, test_data):
    """With wrong app.tenant_id, RLS should return zero rows."""
    async with db_pool.acquire() as conn:
        await conn.execute("SET LOCAL ROLE pulse_app")
        await conn.execute("SET LOCAL app.tenant_id = 'wrong-tenant'")

        # Query for tenant-a data with wrong context
        rows = await conn.fetch(
            "SELECT * FROM device_state WHERE tenant_id = 'test-tenant-a'"
        )

        assert len(rows) == 0, "Expected zero rows for wrong tenant"
```

### 4.4 Test: Correct tenant returns matching rows

```python
@pytest.mark.asyncio
async def test_correct_tenant_returns_matching_rows(db_pool, test_data):
    """With correct app.tenant_id, RLS returns only that tenant's rows."""
    async with db_pool.acquire() as conn:
        await conn.execute("SET LOCAL ROLE pulse_app")
        await conn.execute("SET LOCAL app.tenant_id = 'test-tenant-a'")

        # Query should return only tenant-a rows
        rows = await conn.fetch("SELECT * FROM device_state")

        assert len(rows) == 2, "Expected 2 rows for test-tenant-a"
        for row in rows:
            assert row['tenant_id'] == 'test-tenant-a'
```

### 4.5 Test: Operator bypasses RLS

```python
@pytest.mark.asyncio
async def test_operator_bypasses_rls(db_pool, test_data):
    """Operator role should see all rows regardless of tenant context."""
    async with db_pool.acquire() as conn:
        await conn.execute("SET LOCAL ROLE pulse_operator")
        # No tenant_id set, but operator should still see all

        rows = await conn.fetch(
            "SELECT * FROM device_state WHERE tenant_id IN ('test-tenant-a', 'test-tenant-b')"
        )

        assert len(rows) == 3, "Operator should see all 3 test rows"
```

### 4.6 Test: Cross-tenant query blocked

```python
@pytest.mark.asyncio
async def test_cross_tenant_query_blocked(db_pool, test_data):
    """App role cannot see other tenant's data even with explicit query."""
    async with db_pool.acquire() as conn:
        await conn.execute("SET LOCAL ROLE pulse_app")
        await conn.execute("SET LOCAL app.tenant_id = 'test-tenant-a'")

        # Try to query tenant-b data explicitly
        rows = await conn.fetch(
            "SELECT * FROM device_state WHERE tenant_id = 'test-tenant-b'"
        )

        assert len(rows) == 0, "Cross-tenant query should return zero rows"
```

### 4.7 Test: INSERT respects WITH CHECK

```python
@pytest.mark.asyncio
async def test_insert_wrong_tenant_blocked(db_pool):
    """Cannot insert data for a different tenant."""
    async with db_pool.acquire() as conn:
        await conn.execute("SET LOCAL ROLE pulse_app")
        await conn.execute("SET LOCAL app.tenant_id = 'test-tenant-a'")

        # Try to insert for tenant-b (should fail)
        with pytest.raises(asyncpg.exceptions.InsufficientPrivilegeError):
            await conn.execute("""
                INSERT INTO device_state (tenant_id, device_id, site_id, status)
                VALUES ('test-tenant-b', 'hacked-device', 'site', 'ONLINE')
            """)
```

### 4.8 Test connection wrappers

```python
from db.pool import tenant_connection, operator_connection

@pytest.mark.asyncio
async def test_tenant_connection_wrapper(db_pool, test_data):
    """tenant_connection should set correct context."""
    async with tenant_connection(db_pool, 'test-tenant-a') as conn:
        rows = await conn.fetch("SELECT * FROM device_state")
        assert len(rows) == 2
        for row in rows:
            assert row['tenant_id'] == 'test-tenant-a'

@pytest.mark.asyncio
async def test_operator_connection_wrapper(db_pool, test_data):
    """operator_connection should bypass RLS."""
    async with operator_connection(db_pool) as conn:
        rows = await conn.fetch(
            "SELECT * FROM device_state WHERE tenant_id IN ('test-tenant-a', 'test-tenant-b')"
        )
        assert len(rows) == 3
```

### 4.9 Add pytest configuration

If not present, create `tests/conftest.py`:
```python
import pytest

pytest_plugins = ['pytest_asyncio']

@pytest.fixture(scope="session")
def event_loop_policy():
    import asyncio
    return asyncio.DefaultEventLoopPolicy()
```

And ensure `pytest-asyncio` is in requirements:
```
pytest-asyncio>=0.21.0
```

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `tests/test_rls_enforcement.py` |
| CREATE | `tests/conftest.py` (if not exists) |
| MODIFY | `requirements.txt` or `services/ui_iot/requirements.txt` (add pytest-asyncio) |

## Acceptance Criteria

- [ ] All 8 test cases pass
- [ ] No context → zero rows (fail-closed)
- [ ] Wrong tenant → zero rows
- [ ] Correct tenant → matching rows only
- [ ] Operator → all rows
- [ ] Cross-tenant query → zero rows
- [ ] INSERT wrong tenant → rejected
- [ ] Connection wrappers work correctly

**Run tests**:
```bash
# From project root or services/ui_iot
pytest tests/test_rls_enforcement.py -v
```

Expected output:
```
test_no_tenant_context_returns_zero_rows PASSED
test_wrong_tenant_returns_zero_rows PASSED
test_correct_tenant_returns_matching_rows PASSED
test_operator_bypasses_rls PASSED
test_cross_tenant_query_blocked PASSED
test_insert_wrong_tenant_blocked PASSED
test_tenant_connection_wrapper PASSED
test_operator_connection_wrapper PASSED
```

## Commit

```
Add RLS enforcement tests

- Test fail-closed: no context returns zero rows
- Test tenant isolation: wrong tenant returns zero rows
- Test correct access: matching rows returned
- Test operator bypass: all rows visible
- Test INSERT blocked for wrong tenant
- Test connection wrappers set correct context

Part of Phase 3: RLS Enforcement
```
