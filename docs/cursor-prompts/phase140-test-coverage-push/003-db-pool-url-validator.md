# 140-003: Critical Path — DB Pool & URL Validator (Target: 90%+)

## Task
Write comprehensive tests for `services/ui_iot/db/pool.py` and `services/ui_iot/utils/url_validator.py`.

## Files
- `tests/unit/test_db_pool.py` (create or extend)
- `tests/unit/test_url_validator.py` (create or extend)

---

## Part 1: DB Pool (pool.py)

### Key Functions
From `services/ui_iot/db/pool.py`:
- `tenant_connection(pool, tenant_id)` — async context manager: acquires connection, sets RLS context (`SET LOCAL ROLE pulse_app`, `SET app.tenant_id`), yields, commits/rolls back
- `operator_connection(pool)` — async context manager: acquires connection, sets operator role (`SET LOCAL ROLE pulse_operator` which bypasses RLS), yields

### Test Cases
```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class FakeConnection:
    """Mock asyncpg connection for pool tests."""
    def __init__(self):
        self.executed = []
        self._transaction = FakeTransaction()

    async def execute(self, query, *args):
        self.executed.append((query, args))

    def transaction(self):
        return self._transaction


class FakeTransaction:
    def __init__(self):
        self.started = False
        self.committed = False
        self.rolled_back = False

    async def start(self):
        self.started = True

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *args):
        pass


class FakePool:
    def __init__(self, conn):
        self.conn = conn

    @asynccontextmanager
    async def acquire(self):
        yield self.conn


async def test_tenant_connection_sets_rls_context():
    """tenant_connection sets app role and tenant_id."""
    from db.pool import tenant_connection  # adjust import path
    conn = FakeConnection()
    pool = FakePool(conn)

    async with tenant_connection(pool, "tenant-a") as c:
        assert c is conn

    # Verify RLS setup queries were executed
    queries = [q[0] for q in conn.executed]
    assert any("pulse_app" in q for q in queries), "Should set pulse_app role"
    assert any("app.tenant_id" in q and "tenant-a" in str(q) for q in conn.executed), \
        "Should set tenant_id config"

async def test_tenant_connection_uses_transaction():
    """tenant_connection wraps operations in a transaction."""
    from db.pool import tenant_connection
    conn = FakeConnection()
    pool = FakePool(conn)

    async with tenant_connection(pool, "tenant-a"):
        pass

    # Transaction should have been started
    assert conn._transaction.started

async def test_operator_connection_sets_operator_role():
    """operator_connection sets pulse_operator role (bypasses RLS)."""
    from db.pool import operator_connection
    conn = FakeConnection()
    pool = FakePool(conn)

    async with operator_connection(pool) as c:
        assert c is conn

    queries = [q[0] for q in conn.executed]
    assert any("pulse_operator" in q for q in queries), "Should set pulse_operator role"

async def test_tenant_connection_different_tenants():
    """Different tenant_ids result in different RLS context."""
    from db.pool import tenant_connection
    conn = FakeConnection()
    pool = FakePool(conn)

    async with tenant_connection(pool, "tenant-a"):
        pass
    first_queries = list(conn.executed)

    conn.executed.clear()
    async with tenant_connection(pool, "tenant-b"):
        pass

    # Should have set tenant-b this time
    assert any("tenant-b" in str(q) for q in conn.executed)

async def test_tenant_connection_propagates_exceptions():
    """Exceptions inside tenant_connection propagate correctly."""
    from db.pool import tenant_connection
    conn = FakeConnection()
    pool = FakePool(conn)

    with pytest.raises(ValueError, match="test error"):
        async with tenant_connection(pool, "tenant-a"):
            raise ValueError("test error")
```

---

## Part 2: URL Validator (url_validator.py)

### Key Functions
From `services/ui_iot/utils/url_validator.py`:
- `validate_webhook_url(url, allow_http=None)` — returns `(is_valid: bool, error_message: str | None)`
  - Blocks: private IPs (10.x, 172.16.x, 192.168.x, 127.x), link-local, cloud metadata
  - Blocks: localhost, .local, .internal, .localhost hostnames
  - Requires HTTPS by default (unless allow_http=True)

### Test Cases
```python
import pytest

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class TestValidateWebhookUrl:
    """Tests for SSRF prevention in webhook URL validation."""

    # --- Valid URLs ---
    async def test_valid_https_url(self):
        from utils.url_validator import validate_webhook_url
        ok, err = await validate_webhook_url("https://hooks.slack.com/services/T00/B00/xxx")
        assert ok is True
        assert err is None

    async def test_valid_https_custom_port(self):
        ok, err = await validate_webhook_url("https://webhook.example.com:8443/hook")
        assert ok is True

    # --- Protocol enforcement ---
    async def test_http_blocked_by_default(self):
        ok, err = await validate_webhook_url("http://example.com/webhook")
        assert ok is False
        assert "https" in err.lower() or "protocol" in err.lower()

    async def test_http_allowed_when_flag_set(self):
        ok, err = await validate_webhook_url("http://example.com/webhook", allow_http=True)
        assert ok is True

    async def test_ftp_protocol_blocked(self):
        ok, err = await validate_webhook_url("ftp://example.com/file")
        assert ok is False

    # --- SSRF: Private IPs ---
    async def test_blocks_10_network(self):
        ok, err = await validate_webhook_url("https://10.0.0.1/internal")
        assert ok is False
        assert "private" in err.lower() or "blocked" in err.lower()

    async def test_blocks_172_16_network(self):
        ok, err = await validate_webhook_url("https://172.16.0.1/internal")
        assert ok is False

    async def test_blocks_192_168_network(self):
        ok, err = await validate_webhook_url("https://192.168.1.1/admin")
        assert ok is False

    async def test_blocks_127_loopback(self):
        ok, err = await validate_webhook_url("https://127.0.0.1/secret")
        assert ok is False

    async def test_blocks_169_254_link_local(self):
        ok, err = await validate_webhook_url("https://169.254.169.254/latest/meta-data/")
        assert ok is False

    # --- SSRF: Hostname blocking ---
    async def test_blocks_localhost(self):
        ok, err = await validate_webhook_url("https://localhost/hook")
        assert ok is False

    async def test_blocks_dot_local(self):
        ok, err = await validate_webhook_url("https://myservice.local/webhook")
        assert ok is False

    async def test_blocks_dot_internal(self):
        ok, err = await validate_webhook_url("https://api.internal/webhook")
        assert ok is False

    # --- SSRF: Cloud metadata ---
    async def test_blocks_aws_metadata_endpoint(self):
        ok, err = await validate_webhook_url("https://169.254.169.254/latest/meta-data/")
        assert ok is False

    # --- Edge cases ---
    async def test_empty_url(self):
        ok, err = await validate_webhook_url("")
        assert ok is False

    async def test_malformed_url(self):
        ok, err = await validate_webhook_url("not-a-url")
        assert ok is False

    async def test_url_without_host(self):
        ok, err = await validate_webhook_url("https:///path")
        assert ok is False

    async def test_url_with_credentials(self):
        """URL with embedded credentials should still validate the host."""
        ok, err = await validate_webhook_url("https://user:pass@example.com/webhook")
        assert ok is True  # Valid external host, credentials in URL is okay

    async def test_ipv6_loopback_blocked(self):
        ok, err = await validate_webhook_url("https://[::1]/webhook")
        assert ok is False
```

## Verification
```bash
pytest tests/unit/test_db_pool.py -v --cov=services/ui_iot/db/pool --cov-report=term-missing
# pool.py: >= 90%

pytest tests/unit/test_url_validator.py -v --cov=services/ui_iot/utils/url_validator --cov-report=term-missing
# url_validator.py: >= 90%
```
