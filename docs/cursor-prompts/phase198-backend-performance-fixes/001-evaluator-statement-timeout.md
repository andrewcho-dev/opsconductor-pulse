# Task 1: Add statement_timeout to Evaluator Database Pool

## Context

`services/evaluator_iot/evaluator.py:1212-1225` creates an asyncpg connection pool without a `statement_timeout`. The `ui_iot` service correctly sets this via a pool `init` callback. The evaluator running without a timeout means a slow evaluation query can hold a connection open indefinitely, blocking other evaluations.

## Actions

1. Read `services/ui_iot/app.py` and find the pool `init` callback that sets `statement_timeout`. Note the exact implementation pattern.

2. Read `services/evaluator_iot/evaluator.py` and find the `asyncpg.create_pool(...)` call (around line 1212).

3. Add an init callback to the evaluator pool that mirrors the `ui_iot` pattern:

```python
async def _init_db_connection(conn: asyncpg.Connection) -> None:
    await conn.execute("SET statement_timeout = '10s'")
    await conn.execute("SET lock_timeout = '5s'")
```

4. Add `init=_init_db_connection` to the `asyncpg.create_pool(...)` call.

5. Make the timeout value configurable via environment variable with a safe default:
```python
STATEMENT_TIMEOUT_MS = optional_env("EVALUATOR_STATEMENT_TIMEOUT_MS", "10000")
# Then in the init callback:
await conn.execute(f"SET statement_timeout = '{STATEMENT_TIMEOUT_MS}ms'")
```

6. Do not change any other pool configuration.

## Verification

```bash
grep -n 'statement_timeout\|_init_db_connection' services/evaluator_iot/evaluator.py
# Must show the init callback and its use in create_pool
```
