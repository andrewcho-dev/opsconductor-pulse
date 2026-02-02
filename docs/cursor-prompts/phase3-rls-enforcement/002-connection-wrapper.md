# Task 002: Connection Wrapper

> **CURSOR: EXECUTE THIS TASK**
>
> This is an implementation task. Read the instructions below and implement them.
> Modify the files listed in "Files to Create/Modify" section.
> Follow the acceptance criteria to verify your work.
> Commit with the message in the "Commit" section when done.

---

## Context

RLS policies are now in place, but they require `app.tenant_id` to be set via `SET LOCAL` before queries execute. We need connection wrappers that automatically set this context.

**Read first**:
- `db/migrations/004_enable_rls.sql` (RLS policies)
- `services/ui_iot/routes/customer.py` (current connection usage)
- `services/ui_iot/routes/operator.py` (current connection usage)

**Depends on**: Task 001 (RLS migration applied)

## Task

### 2.1 Create connection pool module

Create `services/ui_iot/db/pool.py`:

**Imports**:
```python
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import asyncpg
```

**Tenant connection wrapper**:
```python
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
        # Set role to pulse_app (subject to RLS)
        await conn.execute("SET LOCAL ROLE pulse_app")
        # Set tenant context for RLS policies
        await conn.execute("SET LOCAL app.tenant_id = $1", tenant_id)
        yield conn
        # Connection returned to pool; SET LOCAL resets automatically
```

**Operator connection wrapper**:
```python
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
        # Set role to pulse_operator (BYPASSRLS)
        await conn.execute("SET LOCAL ROLE pulse_operator")
        yield conn
```

### 2.2 Update customer routes

Modify `services/ui_iot/routes/customer.py`:

**Import the wrapper**:
```python
from db.pool import tenant_connection
```

**Replace direct pool usage**:

Before:
```python
async with pool.acquire() as conn:
    devices = await fetch_devices(conn, tenant_id)
```

After:
```python
async with tenant_connection(pool, tenant_id) as conn:
    devices = await fetch_devices(conn, tenant_id)
```

**Update all route handlers**:
- `GET /customer/dashboard`
- `GET /customer/devices`
- `GET /customer/devices/{device_id}`
- `GET /customer/alerts`
- `GET /customer/alerts/{alert_id}`
- `GET /customer/integrations`
- `POST /customer/integrations`
- `PATCH /customer/integrations/{integration_id}`
- `DELETE /customer/integrations/{integration_id}`
- `POST /customer/integrations/{integration_id}/test`
- `GET /customer/integration-routes`
- All other customer routes

### 2.3 Update operator routes

Modify `services/ui_iot/routes/operator.py`:

**Import the wrapper**:
```python
from db.pool import operator_connection
```

**Replace direct pool usage**:

Before:
```python
async with pool.acquire() as conn:
    devices = await conn.fetch("SELECT * FROM device_state ...")
```

After:
```python
async with operator_connection(pool) as conn:
    devices = await conn.fetch("SELECT * FROM device_state ...")
```

**Update all operator route handlers**.

### 2.4 Verify query builders still work

The query builders in `services/ui_iot/db/queries.py` still include `WHERE tenant_id = $1`. This is fine — it's belt-and-suspenders:
- Application code passes tenant_id (belt)
- RLS enforces tenant_id (suspenders)

Both layers provide protection. Do NOT remove tenant_id from query builders.

### 2.5 Handle pool access

Ensure the pool is accessible in routes. If pool is stored in `app.state.pool`, access it via:
```python
pool = request.app.state.pool
```

Or import from a central location if structured differently.

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `services/ui_iot/db/pool.py` |
| MODIFY | `services/ui_iot/routes/customer.py` |
| MODIFY | `services/ui_iot/routes/operator.py` |

## Acceptance Criteria

- [ ] `tenant_connection` sets `ROLE pulse_app` and `app.tenant_id`
- [ ] `operator_connection` sets `ROLE pulse_operator`
- [ ] All customer routes use `tenant_connection`
- [ ] All operator routes use `operator_connection`
- [ ] Customer API returns only tenant's data (RLS + app filtering)
- [ ] Operator API returns all data (RLS bypassed)
- [ ] Existing functionality unchanged (all routes still work)

**Test**:
```bash
# Customer route - should return only tenant-a devices
curl -H "Authorization: Bearer <customer1_token>" http://localhost:8080/customer/devices

# Operator route - should return all devices
curl -H "Authorization: Bearer <operator_token>" http://localhost:8080/operator/devices
```

## Commit

```
Add connection wrappers for RLS enforcement

- tenant_connection: sets pulse_app role + app.tenant_id
- operator_connection: sets pulse_operator role (BYPASSRLS)
- Update customer routes to use tenant_connection
- Update operator routes to use operator_connection
- Belt-and-suspenders: app filtering + RLS

Part of Phase 3: RLS Enforcement
```
