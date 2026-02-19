"""Background worker to sync carrier data usage for all active integrations."""

import asyncio
import logging

import asyncpg

from services.carrier_service import get_carrier_provider

logger = logging.getLogger(__name__)

SYNC_CHECK_INTERVAL = 300  # Check every 5 minutes which integrations need syncing


async def carrier_sync_loop(pool: asyncpg.Pool):
    """Main loop: periodically check for integrations that need syncing."""
    logger.info("Carrier sync worker started")
    while True:
        try:
            await _sync_due_integrations(pool)
        except Exception:
            logger.exception("Carrier sync loop error")
        await asyncio.sleep(SYNC_CHECK_INTERVAL)


async def _sync_due_integrations(pool: asyncpg.Pool):
    """Find integrations that are due for a sync and process them."""
    try:
        async with pool.acquire() as conn:
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
    except (asyncpg.UndefinedTableError, asyncpg.UndefinedColumnError):
        # Migrations not applied yet; don't crash the service.
        return

    for row in rows:
        integration = dict(row)
        try:
            await _sync_integration(pool, integration)
        except Exception as e:
            logger.exception(
                "Failed to sync carrier integration %s for tenant %s",
                integration.get("id"),
                integration.get("tenant_id"),
            )
            integration["_last_error"] = str(e)
            try:
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
            except Exception:
                logger.debug("Failed to update carrier_integrations sync status", exc_info=True)


async def _sync_integration(pool: asyncpg.Pool, integration: dict):
    """Sync usage data for all devices linked to this carrier integration."""
    provider = get_carrier_provider(integration)
    if not provider:
        logger.warning("No provider for carrier %s", integration.get("carrier_name"))
        return

    tenant_id = integration["tenant_id"]
    integration_id = integration["id"]

    try:
        async with pool.acquire() as conn:
            devices = await conn.fetch(
                """
                SELECT dc.device_id, dc.carrier_device_id
                FROM device_connections dc
                WHERE dc.tenant_id = $1 AND dc.carrier_integration_id = $2
                  AND dc.carrier_device_id IS NOT NULL
                """,
                tenant_id,
                integration_id,
            )
    except (asyncpg.UndefinedTableError, asyncpg.UndefinedColumnError):
        return

    if not devices:
        return

    # Attempt bulk usage fetch for efficiency
    carrier_ids = [d["carrier_device_id"] for d in devices]
    usage_map: dict = {}
    try:
        usage_map = await provider.get_bulk_usage(carrier_ids)
    except Exception:
        logger.warning(
            "Bulk usage fetch failed for integration %s, falling back to per-device",
            integration_id,
        )

    synced = 0
    errors = 0
    for device in devices:
        carrier_device_id = device["carrier_device_id"]
        try:
            usage = usage_map.get(carrier_device_id)
            if usage is None:
                usage = await provider.get_usage(carrier_device_id)
            data_used_mb = usage.data_used_bytes / (1024 * 1024) if usage.data_used_bytes else 0

            sim_status = None
            network_status = None
            try:
                info = await provider.get_device_info(carrier_device_id)
                sim_status = info.sim_status
                network_status = info.network_status
            except Exception:
                logger.debug(
                    "Could not fetch device info for %s during sync",
                    carrier_device_id,
                )

            async with pool.acquire() as conn:
                # Use SET LOCAL for RLS-like behavior (matches existing patterns in repo).
                await conn.execute("SELECT set_config('app.tenant_id', $1, true)", tenant_id)
                await conn.execute("SELECT set_config('app.role', 'iot_service', true)")
                await conn.execute(
                    """
                    UPDATE device_connections
                    SET data_used_mb = $1,
                        data_used_updated_at = now(),
                        sim_status = COALESCE($4, sim_status),
                        network_status = COALESCE($5, network_status),
                        updated_at = now()
                    WHERE tenant_id = $2 AND device_id = $3
                    """,
                    round(float(data_used_mb), 2),
                    tenant_id,
                    device["device_id"],
                    sim_status,
                    network_status,
                )
            synced += 1
        except Exception as e:
            logger.warning(
                "Failed to sync usage for device %s: %s",
                device.get("device_id"),
                str(e),
            )
            errors += 1

    try:
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
                integration_id,
                errors,
            )
    except Exception:
        logger.debug("Failed to update carrier_integrations final sync status", exc_info=True)

    logger.info(
        "Carrier sync complete for integration %s: %d synced, %d errors",
        integration_id,
        synced,
        errors,
    )

