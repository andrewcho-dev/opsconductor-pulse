# Task 004 — Usage Sync Background Worker

## File

Create `services/ui_iot/services/carrier_sync.py`

## Purpose

A background task that periodically syncs data usage from carrier APIs and updates `device_connections.data_used_mb`. Runs inside the ui_iot service using FastAPI's lifespan or a background task pattern.

## Implementation

```python
"""Background worker to sync carrier data usage for all active integrations."""

import asyncio
import logging
from datetime import datetime, timezone

from services.carrier_service import get_carrier_provider
from db.pool import get_pool

logger = logging.getLogger(__name__)

SYNC_CHECK_INTERVAL = 300  # Check every 5 minutes which integrations need syncing


async def carrier_sync_loop(pool):
    """Main loop: periodically check for integrations that need syncing."""
    logger.info("Carrier sync worker started")
    while True:
        try:
            await _sync_due_integrations(pool)
        except Exception:
            logger.exception("Carrier sync loop error")
        await asyncio.sleep(SYNC_CHECK_INTERVAL)


async def _sync_due_integrations(pool):
    """Find integrations that are due for a sync and process them."""
    async with pool.acquire() as conn:
        # Find integrations that are:
        # 1. Enabled and sync_enabled
        # 2. Due for sync (last_sync_at + interval < now, or never synced)
        rows = await conn.fetch(
            """
            SELECT id, tenant_id, carrier_name, api_key, api_secret, api_base_url,
                   account_id, config, sync_interval_minutes
            FROM carrier_integrations
            WHERE enabled = true AND sync_enabled = true
              AND (
                  last_sync_at IS NULL
                  OR last_sync_at + (sync_interval_minutes || ' minutes')::INTERVAL < now()
              )
            ORDER BY last_sync_at NULLS FIRST
            LIMIT 10
            """,
        )

    for row in rows:
        integration = dict(row)
        try:
            await _sync_integration(pool, integration)
        except Exception:
            logger.exception(
                "Failed to sync carrier integration %s for tenant %s",
                integration["id"],
                integration["tenant_id"],
            )
            # Update sync status to error
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE carrier_integrations
                    SET last_sync_at = now(), last_sync_status = 'error',
                        last_sync_error = $2, updated_at = now()
                    WHERE id = $1
                    """,
                    integration["id"],
                    str(integration.get("_last_error", "Unknown error"))[:500],
                )


async def _sync_integration(pool, integration: dict):
    """Sync usage data for all devices linked to this carrier integration."""
    provider = get_carrier_provider(integration)
    if not provider:
        logger.warning("No provider for carrier %s", integration["carrier_name"])
        return

    tenant_id = integration["tenant_id"]
    integration_id = integration["id"]

    # Get all device_connections linked to this integration
    async with pool.acquire() as conn:
        devices = await conn.fetch(
            """
            SELECT dc.device_id, dc.carrier_device_id
            FROM device_connections dc
            WHERE dc.tenant_id = $1 AND dc.carrier_integration_id = $2
              AND dc.carrier_device_id IS NOT NULL
            """,
            tenant_id, integration_id,
        )

    synced = 0
    errors = 0
    for device in devices:
        try:
            usage = await provider.get_usage(device["carrier_device_id"])
            data_used_mb = usage.data_used_bytes / (1024 * 1024) if usage.data_used_bytes else 0

            async with pool.acquire() as conn:
                # Use SET LOCAL for RLS
                await conn.execute("SELECT set_config('app.tenant_id', $1, true)", tenant_id)
                await conn.execute("SELECT set_config('app.role', 'iot_service', true)")
                await conn.execute(
                    """
                    UPDATE device_connections
                    SET data_used_mb = $1, data_used_updated_at = now(), updated_at = now()
                    WHERE tenant_id = $2 AND device_id = $3
                    """,
                    round(data_used_mb, 2),
                    tenant_id,
                    device["device_id"],
                )
            synced += 1
        except Exception as e:
            logger.warning(
                "Failed to sync usage for device %s: %s",
                device["device_id"], str(e),
            )
            errors += 1

    # Update sync status
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE carrier_integrations
            SET last_sync_at = now(),
                last_sync_status = CASE WHEN $2 = 0 THEN 'success' ELSE 'partial' END,
                last_sync_error = NULL,
                updated_at = now()
            WHERE id = $1
            """,
            integration_id, errors,
        )

    logger.info(
        "Carrier sync complete for integration %s: %d synced, %d errors",
        integration_id, synced, errors,
    )
```

## Startup Integration

In `services/ui_iot/app.py`, add the sync worker to the FastAPI lifespan:

```python
from services.carrier_sync import carrier_sync_loop

# In the lifespan or startup event:
@app.on_event("startup")
async def start_carrier_sync():
    pool = app.state.pool
    asyncio.create_task(carrier_sync_loop(pool))
```

Or if using lifespan context manager pattern:
```python
async def lifespan(app):
    # ... existing startup ...
    sync_task = asyncio.create_task(carrier_sync_loop(app.state.pool))
    yield
    sync_task.cancel()
```

Match whatever startup pattern the app already uses.

## Notes

- The sync worker runs every 5 minutes but only syncs integrations whose `last_sync_at + sync_interval_minutes` has elapsed
- Processes max 10 integrations per cycle to avoid overwhelming carrier APIs
- Each device is synced individually — if one fails, others continue
- Sync status is tracked per integration (success/error/partial)
- Rate limiting: carrier APIs typically allow 60-120 req/min. With 10 integrations × ~50 devices each, a single sync cycle is ~500 requests. Space them if needed.

## Verification

```bash
cd services/ui_iot && python3 -c "from services.carrier_sync import carrier_sync_loop; print('OK')"
```
