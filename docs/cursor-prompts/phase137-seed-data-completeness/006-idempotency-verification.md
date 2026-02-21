# 137-006: Idempotency & Verification

## Task
Ensure all seed functions are fully idempotent, add a `--tables` CLI flag, and add a verification report.

## File
`scripts/seed_demo_data.py`

## 1. Idempotency Audit

Review ALL seed functions (existing + new) and ensure each uses one of:
- `ON CONFLICT (unique_columns) DO NOTHING` — preferred when a unique constraint exists
- `ON CONFLICT (unique_columns) DO UPDATE SET ...` — for upsert behavior
- Check-before-insert: `SELECT COUNT(*) ... if count == 0: INSERT` — when no unique constraint exists

Common pitfalls to fix:
- **SERIAL columns**: Don't include the auto-increment `id` in INSERT — let the DB generate it
- **JSONB fields**: Use `json.dumps()` when passing Python dicts. If asyncpg doesn't auto-convert, cast with `$N::jsonb` in the query
- **Timestamps**: Use `NOW()` or pass `datetime.now(timezone.utc)` — don't use string dates
- **Foreign keys**: Always fetch the referenced ID dynamically (don't hardcode IDs from SERIAL columns)

## 2. Add `--tables` CLI Flag

Add argument parsing to `main()`:

```python
import argparse

async def main():
    parser = argparse.ArgumentParser(description="Seed demo data")
    parser.add_argument(
        "--tables",
        type=str,
        default=None,
        help="Comma-separated table groups to seed (e.g., 'notifications,ota,dashboards'). Default: all."
    )
    args = parser.parse_args()

    pool = await asyncpg.create_pool(...)

    # Define table groups
    table_groups = {
        "tenants": [seed_tenants],
        "devices": [seed_device_registry, seed_device_state],
        "alerts": [seed_alert_rules, seed_fleet_alerts],
        "telemetry": [seed_timescaledb],
        "tiers": [seed_device_tiers, seed_tier_allocations],
        "roles": [seed_role_assignments],
        "notifications": [seed_notification_channels, seed_notification_routing_rules],
        "escalation": [seed_escalation_policies, seed_escalation_levels],
        "oncall": [seed_oncall_schedules, seed_oncall_layers, seed_oncall_overrides],
        "ota": [seed_firmware_versions, seed_ota_campaigns, seed_ota_device_status],
        "dashboards": [seed_dashboards, seed_dashboard_widgets],
        "routes": [seed_message_routes],
        "exports": [seed_export_jobs],
        "groups": [seed_dynamic_device_groups],
        "connections": [seed_device_connection_events],
        "certificates": [seed_device_certificates],
        "preferences": [seed_user_preferences],
    }

    if args.tables:
        selected = [t.strip() for t in args.tables.split(",")]
        for group_name in selected:
            if group_name not in table_groups:
                print(f"  ✗ Unknown table group: {group_name}")
                print(f"    Available: {', '.join(sorted(table_groups.keys()))}")
                continue
            for fn in table_groups[group_name]:
                await fn(pool)
    else:
        # Run all in dependency order
        for group_name, fns in table_groups.items():
            for fn in fns:
                await fn(pool)

    # Always run verification at the end
    await verify_seed(pool)

    await pool.close()
```

## 3. Add Verification Report

```python
async def verify_seed(pool):
    """Report row counts for all seeded tables."""
    print("\n" + "=" * 60)
    print("SEED VERIFICATION REPORT")
    print("=" * 60)

    tables = [
        "tenants", "device_registry", "device_state", "alert_rules",
        "fleet_alert", "notification_channels", "notification_routing_rules",
        "escalation_policies", "escalation_levels",
        "oncall_schedules", "oncall_layers", "oncall_overrides",
        "firmware_versions", "ota_campaigns", "ota_device_status",
        "dashboards", "dashboard_widgets", "message_routes", "export_jobs",
        "dynamic_device_groups", "device_connection_events", "device_certificates",
        "user_preferences", "roles", "permissions", "role_permissions",
    ]

    async with pool.acquire() as conn:
        all_ok = True
        for table in tables:
            try:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                status = "✓" if count > 0 else "✗"
                if count == 0:
                    all_ok = False
                print(f"  {status} {table}: {count} rows")
            except Exception:
                print(f"  ? {table}: table not found (migration may not have run)")

    print("=" * 60)
    if all_ok:
        print("ALL TABLES SEEDED SUCCESSFULLY")
    else:
        print("WARNING: Some tables are empty. Check errors above.")
    print("=" * 60)
```

## 4. Error Handling

Wrap each seed function call in a try/except so one failure doesn't block the rest:

```python
for fn in fns:
    try:
        await fn(pool)
    except Exception as e:
        print(f"  ✗ {fn.__name__} failed: {e}")
```

## Verification
```bash
# Seed all tables
docker compose --profile seed run --rm seed
# Output should show verification report with all ✓

# Seed specific groups
docker compose --profile seed run --rm seed -- python scripts/seed_demo_data.py --tables notifications,ota
# Should only seed those groups

# Run twice — idempotent
docker compose --profile seed run --rm seed
docker compose --profile seed run --rm seed
# Second run: no errors, same row counts
```
