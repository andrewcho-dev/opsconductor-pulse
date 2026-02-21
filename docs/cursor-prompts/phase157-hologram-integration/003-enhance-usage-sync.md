# Task 3: Enhance Usage Sync Worker

## File
`services/ui_iot/services/carrier_sync.py`

## Context

The sync worker (`carrier_sync.py`, 153 lines) polls carrier integrations every 5 minutes. The `_sync_integration` function (line 75) iterates over linked devices and calls `provider.get_usage()` per device, then updates only `data_used_mb` and `data_used_updated_at` in `device_connections`.

Task 1 already fixed `HologramProvider.get_usage()` to hit the correct endpoint. This task enhances the sync worker to:
1. Also fetch and store `sim_status` and `network_status` per device
2. Store `billing_cycle_start`/`billing_cycle_end` from usage data
3. Add an optional `get_bulk_usage()` method to `HologramProvider` for batch efficiency

## Changes

### 1. Add get_bulk_usage to CarrierProvider base class

In `services/ui_iot/services/carrier_service.py`, add a new default method to `CarrierProvider` (alongside the `claim_sim` and `list_plans` added in Task 1):

```python
async def get_bulk_usage(self, carrier_device_ids: list[str]) -> dict[str, CarrierUsageInfo]:
    """Get usage for multiple devices in one call. Default: call get_usage per device."""
    results = {}
    for device_id in carrier_device_ids:
        try:
            results[device_id] = await self.get_usage(device_id)
        except Exception:
            logger.warning("Bulk usage: failed for device %s", device_id)
    return results
```

### 2. Add efficient bulk implementation to HologramProvider

In `services/ui_iot/services/carrier_service.py`, add to `HologramProvider`:

```python
async def get_bulk_usage(self, carrier_device_ids: list[str]) -> dict[str, "CarrierUsageInfo"]:
    """Fetch usage for all devices in the org in a single API call."""
    if not self.account_id:
        return await super().get_bulk_usage(carrier_device_ids)

    resp = await self.client.get(
        "/usage/data", params={"orgid": self.account_id}
    )
    resp.raise_for_status()
    records = resp.json().get("data", [])

    # Group records by device ID
    by_device: dict[str, list[dict]] = {}
    for r in records:
        did = str(r.get("deviceid", ""))
        if did in carrier_device_ids:
            by_device.setdefault(did, []).append(r)

    results = {}
    for did in carrier_device_ids:
        device_records = by_device.get(did, [])
        total_bytes = sum(r.get("bytes", 0) for r in device_records)
        results[did] = CarrierUsageInfo(
            carrier_device_id=did,
            data_used_bytes=total_bytes,
            sessions=device_records,
            raw={"records": device_records},
        )
    return results
```

### 3. Enhance _sync_integration in carrier_sync.py

Replace the `_sync_integration` function (lines 75-152) with an enhanced version that:
- Uses `get_bulk_usage` when available
- Fetches `get_device_info` per device for sim_status/network_status
- Updates additional fields in `device_connections`

```python
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
        logger.warning("Bulk usage fetch failed for integration %s, falling back to per-device", integration_id)

    synced = 0
    errors = 0
    for device in devices:
        carrier_device_id = device["carrier_device_id"]
        try:
            # Get usage (from bulk map or individual call)
            usage = usage_map.get(carrier_device_id)
            if usage is None:
                usage = await provider.get_usage(carrier_device_id)

            data_used_mb = usage.data_used_bytes / (1024 * 1024) if usage.data_used_bytes else 0

            # Also fetch device info for sim_status / network_status
            sim_status = None
            network_status = None
            try:
                info = await provider.get_device_info(carrier_device_id)
                sim_status = info.sim_status
                network_status = info.network_status
            except Exception:
                logger.debug("Could not fetch device info for %s during sync", carrier_device_id)

            async with pool.acquire() as conn:
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
```

### 4. Add import for CarrierUsageInfo if needed

At the top of `carrier_sync.py`, update the import to include what's needed:

```python
from services.carrier_service import get_carrier_provider
```

This import is already sufficient since `get_bulk_usage` returns `CarrierUsageInfo` objects and we access them by attribute (`.data_used_bytes`, `.sim_status`, etc.) without needing the type directly.

## Notes

- The `sim_status` and `network_status` columns already exist on `device_connections` (added in Phase 149 migration).
- The `COALESCE($4, sim_status)` pattern ensures we only overwrite when we successfully fetched the value — if `get_device_info` fails, the existing value is preserved.
- The bulk usage approach trades one API call for N calls. For Hologram specifically, the org-level usage endpoint returns all device usage at once, making this a significant optimization for fleets >10 devices.
- The per-device `get_device_info` call during sync is a nice-to-have; if it creates too much API load, it could be throttled or made conditional (e.g., only every Nth sync).

## Verification

```bash
# Verify carrier_sync still imports cleanly
cd services/ui_iot && python -c "
from services.carrier_sync import carrier_sync_loop, _sync_integration
print('carrier_sync imports OK')
"
```
