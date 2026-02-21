# 002: Database Safety -- statement_timeout, Transactions, Pool Usage

## Context

Three database safety issues exist:

1. **Missing `statement_timeout`**: The `asyncpg.create_pool()` calls in `app.py` (line 293, 298) and `ops_worker/main.py` (line 33, 38) set `command_timeout=30` (client-side timeout for asyncpg) but do NOT set the PostgreSQL server-side `statement_timeout`. The pool in `system.py` (line 50-58) has neither. Without `statement_timeout`, a runaway query (e.g., full table scan on telemetry) will hold a connection and a database backend indefinitely.

2. **Missing transaction wrapper**: `delete_device` in `devices.py` (lines 620-669) performs three sequential writes (UPDATE device_registry, UPDATE subscriptions, INSERT subscription_event_log) without an explicit `async with conn.transaction():` block. If the second or third statement fails, the first is already committed.

3. **Raw `asyncpg.connect()` in system.py**: `check_postgres()` (lines 62-88) and `get_postgres_capacity()` (lines 770-821) open direct connections via `asyncpg.connect()` instead of using the pool. Each health check creates and destroys a connection, contributing to connection churn.

## Step 1: Add `statement_timeout` to All Pool Inits

The `server_settings` parameter on `asyncpg.create_pool()` passes SET commands to every new connection. Adding `statement_timeout` here ensures the PostgreSQL backend kills any query that runs longer than the specified milliseconds.

### File: `services/ui_iot/app.py`

**Line 293** -- DSN-based pool creation:
```python
# BEFORE (line 293):
pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=2, max_size=10, command_timeout=30)

# AFTER:
pool = await asyncpg.create_pool(
    dsn=DATABASE_URL, min_size=2, max_size=10, command_timeout=30,
    server_settings={'statement_timeout': '30000'}
)
```

**Lines 295-298** -- explicit host pool creation:
```python
# BEFORE (lines 295-299):
pool = await asyncpg.create_pool(
    host=PG_HOST, port=PG_PORT, database=PG_DB,
    user=PG_USER, password=PG_PASS,
    min_size=2, max_size=10, command_timeout=30
)

# AFTER:
pool = await asyncpg.create_pool(
    host=PG_HOST, port=PG_PORT, database=PG_DB,
    user=PG_USER, password=PG_PASS,
    min_size=2, max_size=10, command_timeout=30,
    server_settings={'statement_timeout': '30000'}
)
```

### File: `services/ops_worker/main.py`

**Line 33** -- DSN-based pool:
```python
# BEFORE (line 33):
_pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=2, max_size=10, command_timeout=30)

# AFTER:
_pool = await asyncpg.create_pool(
    dsn=DATABASE_URL, min_size=2, max_size=10, command_timeout=30,
    server_settings={'statement_timeout': '30000'}
)
```

**Lines 35-44** -- explicit host pool:
```python
# BEFORE (lines 35-44):
_pool = await asyncpg.create_pool(
    host=PG_HOST,
    port=PG_PORT,
    database=PG_DB,
    user=PG_USER,
    password=PG_PASS,
    min_size=2,
    max_size=10,
    command_timeout=30,
)

# AFTER:
_pool = await asyncpg.create_pool(
    host=PG_HOST,
    port=PG_PORT,
    database=PG_DB,
    user=PG_USER,
    password=PG_PASS,
    min_size=2,
    max_size=10,
    command_timeout=30,
    server_settings={'statement_timeout': '30000'},
)
```

### File: `services/ui_iot/routes/system.py`

**Lines 50-58** -- the operator system health pool is missing BOTH `command_timeout` and `statement_timeout`:
```python
# BEFORE (lines 50-58):
_pool = await asyncpg.create_pool(
    host=POSTGRES_HOST,
    port=POSTGRES_PORT,
    database=POSTGRES_DB,
    user=POSTGRES_USER,
    password=POSTGRES_PASS,
    min_size=1,
    max_size=5,
)

# AFTER:
_pool = await asyncpg.create_pool(
    host=POSTGRES_HOST,
    port=POSTGRES_PORT,
    database=POSTGRES_DB,
    user=POSTGRES_USER,
    password=POSTGRES_PASS,
    min_size=1,
    max_size=5,
    command_timeout=30,
    server_settings={'statement_timeout': '30000'},
)
```

### File: `services/ingest_iot/ingest.py`

**Lines 758-768** -- the ingest service pool already has `command_timeout=30` but no `statement_timeout`:

```python
# Line 758 (DSN branch):
# BEFORE:
self.pool = await asyncpg.create_pool(
    dsn=DATABASE_URL,
    min_size=2,
    max_size=10,
    command_timeout=30,
)
# AFTER:
self.pool = await asyncpg.create_pool(
    dsn=DATABASE_URL,
    min_size=2,
    max_size=10,
    command_timeout=30,
    server_settings={'statement_timeout': '30000'},
)

# Line 765 (explicit host branch):
# BEFORE:
self.pool = await asyncpg.create_pool(
    host=PG_HOST, port=PG_PORT, database=PG_DB, user=PG_USER, password=PG_PASS,
    min_size=2, max_size=10, command_timeout=30
)
# AFTER:
self.pool = await asyncpg.create_pool(
    host=PG_HOST, port=PG_PORT, database=PG_DB, user=PG_USER, password=PG_PASS,
    min_size=2, max_size=10, command_timeout=30,
    server_settings={'statement_timeout': '30000'}
)
```

## Step 2: Wrap `delete_device` in a Transaction

### File: `services/ui_iot/routes/devices.py`

**Lines 620-669**: The `delete_device` function performs three writes within a single `tenant_connection` context but without an explicit transaction. The `tenant_connection` context manager acquires a connection but does NOT automatically start a transaction.

```python
# BEFORE (lines 626-668):
async with tenant_connection(p, tenant_id) as conn:
    device = await conn.fetchrow(...)
    if not device:
        raise HTTPException(404, "Device not found")

    await conn.execute(
        """UPDATE device_registry SET status = 'DELETED' ...""",
        tenant_id, device_id,
    )

    subscription_id = device["subscription_id"]
    if subscription_id:
        await conn.execute(
            """UPDATE subscriptions SET active_device_count = GREATEST(0, active_device_count - 1)...""",
            subscription_id,
        )

    await log_subscription_event(conn, tenant_id, ...)

# AFTER:
async with tenant_connection(p, tenant_id) as conn:
    device = await conn.fetchrow(...)
    if not device:
        raise HTTPException(404, "Device not found")

    async with conn.transaction():
        await conn.execute(
            """UPDATE device_registry SET status = 'DELETED' ...""",
            tenant_id, device_id,
        )

        subscription_id = device["subscription_id"]
        if subscription_id:
            await conn.execute(
                """UPDATE subscriptions SET active_device_count = GREATEST(0, active_device_count - 1)...""",
                subscription_id,
            )

        await log_subscription_event(conn, tenant_id, ...)
```

The read (fetchrow to check existence) stays outside the transaction. The three writes go inside.

### Audit Other Multi-Statement Writes

Scan the codebase for other endpoints that do multiple writes without a transaction wrapper. The following are patterns to check:

- **`devices.py` line 213 `rotate_device_token`** (lines 221-261): Does UPDATE (revoke all) then INSERT (new token). These are inside `tenant_connection` but no `conn.transaction()`. **Wrap in transaction**.

- **`devices.py` line 264 `import_devices_csv`** (lines 291-391): Does multiple inserts per device in a loop. Already inside a single `tenant_connection` context. This is a bulk operation -- **wrap the entire loop body in a transaction per device**, or wrap the entire block. Given the loop already has try/except per device, wrapping per-device is better.

- **`devices.py` line 822 `update_device`** (lines 880-921): UPDATE device_registry, then conditionally DELETE + INSERT tags. Inside `tenant_connection` but no explicit transaction. **Wrap in transaction**.

- **`escalation.py` line 104 `create_escalation_policy`** (lines 107-141): Conditionally updates existing, inserts policy, inserts levels. Inside `tenant_connection`. **Wrap in transaction**.

- **`escalation.py` line 154 `update_escalation_policy`** (lines 157-204): Multiple updates, DELETE + re-INSERT levels. Inside `tenant_connection`. **Wrap in transaction**.

- **`oncall.py` line 94 `create_schedule`** (lines 97-127): INSERT schedule, then INSERT layers. Inside `tenant_connection`. **Wrap in transaction**.

- **`oncall.py` line 140 `update_schedule`** (lines 143-181): UPDATE schedule, DELETE layers, INSERT layers. Inside `tenant_connection`. **Wrap in transaction**.

For each of these, add `async with conn.transaction():` wrapping the multi-statement write block. Keep reads that check existence/authorization outside the transaction where possible.

## Step 3: Fix system.py `check_postgres()` and `get_postgres_capacity()`

### File: `services/ui_iot/routes/system.py`

**`check_postgres()` at lines 62-88**: Replace `asyncpg.connect()` with pool usage.

```python
# BEFORE (lines 62-88):
async def check_postgres() -> dict:
    start = time.time()
    try:
        conn = await asyncpg.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASS,
            timeout=5,
        )
        connections = await conn.fetchval(
            "SELECT count(*) FROM pg_stat_activity WHERE datname = $1",
            POSTGRES_DB,
        )
        max_conn = await conn.fetchval("SHOW max_connections")
        await conn.close()
        latency = int((time.time() - start) * 1000)
        return {
            "status": "healthy",
            "latency_ms": latency,
            "connections": connections,
            "max_connections": int(max_conn),
        }
    except Exception as e:
        logger.error("Postgres health check failed: %s", e)
        return {"status": "down", "error": str(e)}

# AFTER:
async def check_postgres() -> dict:
    start = time.time()
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            connections = await conn.fetchval(
                "SELECT count(*) FROM pg_stat_activity WHERE datname = $1",
                POSTGRES_DB,
            )
            max_conn = await conn.fetchval("SHOW max_connections")
        latency = int((time.time() - start) * 1000)
        return {
            "status": "healthy",
            "latency_ms": latency,
            "connections": connections,
            "max_connections": int(max_conn),
        }
    except Exception as e:
        logger.error("Postgres health check failed: %s", e)
        return {"status": "down", "error": str(e)}
```

**`get_postgres_capacity()` at lines 770-821**: Same pattern -- replace `asyncpg.connect()` with pool.

```python
# BEFORE (lines 770-821):
async def get_postgres_capacity() -> dict:
    try:
        conn = await asyncpg.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASS,
            timeout=5,
        )
        db_size = await conn.fetchval(...)
        connections = await conn.fetchval(...)
        max_conn = await conn.fetchval(...)
        table_sizes = await conn.fetch(...)
        await conn.close()
        return {...}
    except Exception as e:
        ...

# AFTER:
async def get_postgres_capacity() -> dict:
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            db_size = await conn.fetchval("SELECT pg_database_size($1)", POSTGRES_DB)
            connections = await conn.fetchval(
                "SELECT count(*) FROM pg_stat_activity WHERE datname = $1",
                POSTGRES_DB,
            )
            max_conn = await conn.fetchval("SHOW max_connections")
            table_sizes = await conn.fetch(
                """
                SELECT
                    schemaname || '.' || relname as table_name,
                    pg_total_relation_size(relid) as total_size,
                    pg_relation_size(relid) as data_size,
                    pg_indexes_size(relid) as index_size
                FROM pg_catalog.pg_statio_user_tables
                ORDER BY pg_total_relation_size(relid) DESC
                LIMIT 10
                """
            )
        return {
            "db_size_bytes": db_size,
            "db_size_mb": round(db_size / (1024 * 1024), 2),
            "connections_used": connections,
            "connections_max": int(max_conn),
            "connections_pct": round(connections / int(max_conn) * 100, 1),
            "top_tables": [
                {
                    "name": r["table_name"],
                    "total_mb": round(r["total_size"] / (1024 * 1024), 2),
                    "data_mb": round(r["data_size"] / (1024 * 1024), 2),
                    "index_mb": round(r["index_size"] / (1024 * 1024), 2),
                }
                for r in table_sizes
            ],
        }
    except Exception as e:
        logger.error("Failed to get Postgres capacity: %s", e)
        raise
```

After these changes, the `import asyncpg` at line 10 of `system.py` is still needed for the pool type annotation, but the direct `asyncpg.connect()` calls are eliminated.

## Verification

```bash
# 1. Verify statement_timeout is active
# Connect to DB and run:
psql "$DATABASE_URL" -c "SHOW statement_timeout;"
# Pool connections should show 30s

# 2. Test statement_timeout kills long queries
psql "$DATABASE_URL" -c "SELECT pg_sleep(35);"
# Expected: ERROR: canceling statement due to statement timeout

# 3. Test delete_device atomicity
# Create a device, then simulate a constraint failure on the subscription update.
# The device_registry should NOT show status='DELETED' if the transaction rolled back.

# 4. Verify system health endpoint still works
curl -H "Authorization: Bearer $OPERATOR_TOKEN" http://localhost:8080/operator/system/health
# Should return component statuses without connection errors

# 5. Verify no asyncpg.connect() calls remain in system.py
grep -n "asyncpg.connect" services/ui_iot/routes/system.py
# Should return no results

# 6. Run tests
cd services/ui_iot && python -m pytest tests/ -x -q
```
