# Task 2: Update `operator_connection()` to Use Granular Roles

## Context

`services/ui_iot/db/pool.py:30-48` has a single `operator_connection()` that sets `pulse_operator` role. After Task 1, this must be split into read and write variants.

## Actions

1. Read `services/ui_iot/db/pool.py` in full.

2. Update or replace `operator_connection()` with two variants:

```python
@asynccontextmanager
async def operator_read_connection(pool: asyncpg.Pool):
    """
    Acquire a connection with read-only operator role.
    BYPASSRLS enabled — can query across all tenants.
    Use for: cross-tenant dashboards, NOC views, health matrices.
    """
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("SET LOCAL ROLE pulse_operator_read")
            yield conn


@asynccontextmanager
async def operator_write_connection(pool: asyncpg.Pool):
    """
    Acquire a connection with write operator role.
    NO BYPASSRLS — writes respect tenant RLS.
    Use for: operational updates (device status, subscription changes).
    """
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("SET LOCAL ROLE pulse_operator_write")
            yield conn
```

3. Search all route files under `services/ui_iot/routes/` for usages of `operator_connection`. For each usage:
   - If the code only does SELECT queries: change to `operator_read_connection`.
   - If the code does INSERT/UPDATE/DELETE: change to `operator_write_connection`.
   - If the code does both: split into two separate connection contexts (read first, then write).

4. Keep the old `operator_connection()` as a deprecated alias that calls `operator_read_connection()` with a deprecation log warning. Do not delete it yet.

5. Do not change any SQL queries.

## Verification

```bash
grep -rn 'operator_connection\b' services/ui_iot/
# Should show the deprecated wrapper and its usages being replaced
grep -rn 'operator_read_connection\|operator_write_connection' services/ui_iot/
# Should show new usage across route files
```
