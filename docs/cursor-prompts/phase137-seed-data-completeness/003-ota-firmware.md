# 137-003: OTA & Firmware

## Task
Add seed functions for firmware_versions, ota_campaigns, and ota_device_status.

## File
`scripts/seed_demo_data.py`

## Table Schemas (from migrations)

### firmware_versions
```sql
-- Columns: id (SERIAL), tenant_id, version (VARCHAR 50), description, file_url, file_size_bytes, checksum_sha256 (VARCHAR 64), device_type (VARCHAR 50), created_at, created_by
-- UNIQUE: (tenant_id, version, device_type)
```

### ota_campaigns
```sql
-- Columns: id (SERIAL), tenant_id, name (VARCHAR 100), firmware_version_id (FK), target_group_id, rollout_strategy ('linear'|'canary'), rollout_rate (INT), abort_threshold (FLOAT), status ('CREATED'|'RUNNING'|'PAUSED'|'COMPLETED'|'ABORTED'), total_devices, succeeded, failed, started_at, completed_at, created_at, created_by
```

### ota_device_status
```sql
-- Check migration 090 for exact columns. Likely: id, campaign_id, device_id, tenant_id, status, started_at, completed_at, error_message
```

## 1. seed_firmware_versions

Create 2 firmware versions per tenant:

**Both tenants**:
```python
firmware_data = [
    {
        "version": "1.0.0",
        "description": "Initial release - basic telemetry and heartbeat",
        "file_url": "https://firmware.example.com/v1.0.0/firmware.bin",
        "file_size_bytes": 524288,  # 512 KB
        "checksum_sha256": "a" * 64,  # demo placeholder
        "device_type": "sensor",
    },
    {
        "version": "1.1.0",
        "description": "Added OTA update support and improved power management",
        "file_url": "https://firmware.example.com/v1.1.0/firmware.bin",
        "file_size_bytes": 589824,  # 576 KB
        "checksum_sha256": "b" * 64,  # demo placeholder
        "device_type": "sensor",
    },
]
```

```python
for tenant_id in TENANTS:
    for fw in firmware_data:
        await conn.execute("""
            INSERT INTO firmware_versions (tenant_id, version, description, file_url, file_size_bytes, checksum_sha256, device_type, created_by)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (tenant_id, version, device_type) DO NOTHING
        """, tenant_id, fw["version"], fw["description"], fw["file_url"],
            fw["file_size_bytes"], fw["checksum_sha256"], fw["device_type"],
            f"demo-admin-{tenant_id}")
```

## 2. seed_ota_campaigns

Create 1 completed campaign per tenant (upgrading from v1.0.0 to v1.1.0):

```python
for tenant_id in TENANTS:
    # Get firmware version IDs
    fw_id = await conn.fetchval(
        "SELECT id FROM firmware_versions WHERE tenant_id = $1 AND version = $2 AND device_type = $3",
        tenant_id, "1.1.0", "sensor"
    )
    if not fw_id:
        continue

    # Count devices for this tenant
    device_count = await conn.fetchval(
        "SELECT COUNT(*) FROM device_registry WHERE tenant_id = $1", tenant_id
    )

    await conn.execute("""
        INSERT INTO ota_campaigns (tenant_id, name, firmware_version_id, target_group_id,
            rollout_strategy, rollout_rate, abort_threshold, status,
            total_devices, succeeded, failed, started_at, completed_at, created_by)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11,
            NOW() - INTERVAL '2 days', NOW() - INTERVAL '1 day', $12)
        ON CONFLICT DO NOTHING
    """, tenant_id, "Fleet Update to v1.1.0", fw_id, "all",
        "linear", 20, 0.1, "COMPLETED",
        device_count or 15, (device_count or 15) - 1, 1,
        f"demo-admin-{tenant_id}")
```

**Note**: Use `ON CONFLICT DO NOTHING`. The campaigns table may not have a natural unique key besides the auto-increment ID. Use a check-before-insert pattern:
```python
existing = await conn.fetchval(
    "SELECT COUNT(*) FROM ota_campaigns WHERE tenant_id = $1 AND name = $2",
    tenant_id, "Fleet Update to v1.1.0"
)
if existing == 0:
    await conn.execute("INSERT INTO ...")
```

## 3. seed_ota_device_status

Create device status records for each device in the campaign:

```python
for tenant_id in TENANTS:
    campaign_id = await conn.fetchval(
        "SELECT id FROM ota_campaigns WHERE tenant_id = $1 AND name = $2",
        tenant_id, "Fleet Update to v1.1.0"
    )
    if not campaign_id:
        continue

    devices = await conn.fetch(
        "SELECT device_id FROM device_registry WHERE tenant_id = $1", tenant_id
    )

    for i, device in enumerate(devices):
        status = "FAILED" if i == 0 else "SUCCEEDED"  # First device fails for demo
        error_msg = "Checksum mismatch after download" if status == "FAILED" else None

        await conn.execute("""
            INSERT INTO ota_device_status (campaign_id, device_id, tenant_id, status,
                started_at, completed_at, error_message)
            VALUES ($1, $2, $3, $4,
                NOW() - INTERVAL '2 days' + ($5 * INTERVAL '10 minutes'),
                NOW() - INTERVAL '1 day' + ($5 * INTERVAL '5 minutes'),
                $6)
            ON CONFLICT DO NOTHING
        """, campaign_id, device["device_id"], tenant_id, status, i, error_msg)
```

**Check the exact column names in migration 090** before implementing.

## Wire Up in main()
```python
await seed_firmware_versions(pool)
await seed_ota_campaigns(pool)
await seed_ota_device_status(pool)
```

## Verification
```sql
SELECT tenant_id, version, device_type FROM firmware_versions;
-- 4 rows (2 per tenant)
SELECT tenant_id, name, status, total_devices, succeeded, failed FROM ota_campaigns;
-- 2 rows (1 per tenant, COMPLETED)
SELECT campaign_id, COUNT(*), COUNT(*) FILTER (WHERE status = 'SUCCEEDED'), COUNT(*) FILTER (WHERE status = 'FAILED') FROM ota_device_status GROUP BY campaign_id;
-- Shows counts per campaign
```
