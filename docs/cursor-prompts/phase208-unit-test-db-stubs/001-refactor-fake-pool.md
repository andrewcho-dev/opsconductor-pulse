# Task 1: Refactor FakePool and Expose mock_conn Fixture

## File to modify
- `tests/conftest.py`

## What to do

### Step 1 — Read the file first
Read `tests/conftest.py` in full before making any changes.

### Step 2 — Promote FakeConn to a top-level class

Replace the inline `mock_conn = AsyncMock()` block inside the `db_pool` exception
handler with a proper top-level `FakeConn` class. The class must:

- Store separate configurable return values for `fetchrow`, `fetch`, `fetchval`, `execute`
- Expose a `set_response(method: str, value)` helper for test-level overrides
- Have sensible defaults (empty list for `fetch`, `None` for `fetchrow`/`fetchval`,
  `"OK"` for `execute`)
- Support the `transaction()` asynccontextmanager on the conn itself
- Be importable from other test files via `from tests.conftest import FakeConn`

Sketch of the class shape (implement this, don't copy-paste verbatim):

```python
class FakeConn:
    def __init__(self):
        self._responses = {}
        # defaults
        self._responses["fetch"] = []
        self._responses["fetchrow"] = None
        self._responses["fetchval"] = None
        self._responses["execute"] = "OK"

    def set_response(self, method: str, value):
        self._responses[method] = value

    async def fetch(self, *a, **kw):
        r = self._responses["fetch"]
        return r() if callable(r) else r

    async def fetchrow(self, *a, **kw):
        r = self._responses["fetchrow"]
        return r() if callable(r) else r

    async def fetchval(self, *a, **kw):
        r = self._responses["fetchval"]
        return r() if callable(r) else r

    async def execute(self, *a, **kw):
        return self._responses["execute"]

    async def executemany(self, *a, **kw):
        return None

    async def copy_records_to_table(self, *a, **kw):
        return None

    @asynccontextmanager
    async def transaction(self):
        yield
```

### Step 3 — Create a FakePool class that uses FakeConn

```python
class FakePool:
    def __init__(self):
        self.conn = FakeConn()

    @asynccontextmanager
    async def acquire(self):
        yield self.conn

    async def close(self):
        return None
```

### Step 4 — Update the db_pool fixture

In the exception handler fallback, replace the inline mock_conn construction with:
```python
fake_pool = FakePool()
yield fake_pool
```

### Step 5 — Add a mock_conn fixture

Add a new session-scoped fixture that returns the `FakePool`'s `FakeConn` instance
when the pool is a `FakePool`, so individual tests can configure responses:

```python
@pytest.fixture
def mock_conn(db_pool):
    """
    Returns the FakeConn instance when running without a live DB,
    allowing individual tests to configure return values via set_response().
    Returns None if a real DB pool is in use.
    """
    if isinstance(db_pool, FakePool):
        return db_pool.conn
    return None
```

### Step 6 — Verify

Run:
```bash
cd /home/opsconductor/simcloud && python -m pytest tests/unit/ -q --tb=no 2>&1 | tail -5
```

The failure count should be unchanged at this point (we haven't fixed test data yet —
that's task 003). What matters here is that no new failures are introduced.
