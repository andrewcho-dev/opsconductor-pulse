# Phase 100 — Tenant Isolation Unit Tests

## File to create
`tests/unit/test_tenant_isolation.py`

## Tests to write

```python
"""Unit tests for tenant isolation context and RLS setup."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call


class TestTenantConnection:

    @pytest.mark.asyncio
    async def test_sets_tenant_id_config(self):
        """tenant_connection sets app.tenant_id on the DB connection."""
        mock_conn = AsyncMock()
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=MagicMock(
            __aenter__=AsyncMock(return_value=mock_conn),
            __aexit__=AsyncMock(return_value=False),
        ))
        mock_conn.transaction = MagicMock(return_value=MagicMock(
            __aenter__=AsyncMock(return_value=None),
            __aexit__=AsyncMock(return_value=False),
        ))

        from db.pool import tenant_connection  # adjust path
        async with tenant_connection(mock_pool, "tenant-xyz") as conn:
            pass

        # Verify SET LOCAL ROLE pulse_app was called
        role_calls = [str(c) for c in mock_conn.execute.call_args_list]
        assert any("pulse_app" in c for c in role_calls), \
            "SET LOCAL ROLE pulse_app not called"

        # Verify set_config was called with the correct tenant_id
        config_calls = [str(c) for c in mock_conn.execute.call_args_list]
        assert any("app.tenant_id" in c for c in config_calls), \
            "set_config('app.tenant_id') not called"

    @pytest.mark.asyncio
    async def test_raises_on_empty_tenant_id(self):
        """tenant_connection raises ValueError if tenant_id is empty."""
        from db.pool import tenant_connection

        with pytest.raises(ValueError, match="tenant_id"):
            async with tenant_connection(MagicMock(), "") as conn:
                pass

    @pytest.mark.asyncio
    async def test_operator_connection_uses_bypass_role(self):
        """operator_connection sets pulse_operator role (BYPASSRLS)."""
        mock_conn = AsyncMock()
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=MagicMock(
            __aenter__=AsyncMock(return_value=mock_conn),
            __aexit__=AsyncMock(return_value=False),
        ))
        mock_conn.transaction = MagicMock(return_value=MagicMock(
            __aenter__=AsyncMock(return_value=None),
            __aexit__=AsyncMock(return_value=False),
        ))

        from db.pool import operator_connection
        async with operator_connection(mock_pool) as conn:
            pass

        role_calls = [str(c) for c in mock_conn.execute.call_args_list]
        assert any("pulse_operator" in c for c in role_calls), \
            "SET LOCAL ROLE pulse_operator not called"

        # operator_connection must NOT set app.tenant_id (operators see all tenants)
        assert not any("app.tenant_id" in c for c in role_calls), \
            "operator_connection must not set tenant context"


class TestIngestTenantValidation:

    def test_topic_tenant_matches_device_tenant(self):
        """Ingest rejects message if topic tenant_id differs from device's registered tenant."""
        # This test documents the expected behavior — the actual enforcement
        # is via the device auth cache lookup which validates the provision token
        # against the correct tenant.
        from ingest_iot.ingest import topic_extract  # adjust path

        tenant_id, device_id, msg_type = topic_extract(
            "tenant/attacker-tenant/device/victim-device/telemetry"
        )
        # The auth cache will reject this because victim-device is not
        # registered under attacker-tenant. We can only test the topic parse here.
        assert tenant_id == "attacker-tenant"
        assert device_id == "victim-device"
        # The auth validation step (separate function) must be tested to confirm rejection

    def test_device_auth_rejects_wrong_tenant(self):
        """DeviceAuthCache lookup returns False when device is under different tenant."""
        # Find the DeviceAuthCache or equivalent in ingest_iot/ingest.py
        # and test that authenticate(tenant_id, device_id, token) returns False
        # when the device belongs to a different tenant.
        # Adjust class name and method to match actual implementation.
        from unittest.mock import MagicMock

        # Example pattern — adjust to actual cache class:
        # cache = DeviceAuthCache(pool=MagicMock())
        # cache._cache = {"correct-tenant:dev-001": "valid-hash"}
        # result = cache.is_valid("wrong-tenant", "dev-001", "valid-hash")
        # assert result is False
        pytest.skip("Adjust to actual DeviceAuthCache implementation")
```

## Run

```bash
pytest tests/unit/test_tenant_isolation.py -v
```

Expected: all non-skipped tests pass.
The skipped test (`test_device_auth_rejects_wrong_tenant`) should be implemented once
the DeviceAuthCache interface is confirmed by reading the actual ingest code.
