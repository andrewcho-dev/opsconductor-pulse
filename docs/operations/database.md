---
last-verified: 2026-02-17
sources:
  - db/migrate.py
  - db/migrations/
phases: [20, 21, 34, 137, 142]
---

# Database

> PostgreSQL + TimescaleDB schema, migrations, and maintenance.

## Architecture

OpsConductor-Pulse uses:

- PostgreSQL (TimescaleDB image in compose)
- TimescaleDB extension for time-series telemetry and system metrics

## Connection Pooling (PgBouncer)

PgBouncer is used for connection pooling (transaction pooling mode in compose). Services typically connect via a `DATABASE_URL` pointing at PgBouncer.

## Schema Overview

High-level table groupings:

### Device & Fleet Tables

- Device registry and state tables (`device_registry`, `device_state`)
- Sites, tags, groups, maintenance windows
- Device API token tables

### Alert Tables

- `fleet_alert` (alerts)
- Alert rules and conditions tables
- Escalation policy and level tables

### Telemetry Tables

- `telemetry` hypertable (time-series)
- `quarantine_events`
- Supporting telemetry catalog/normalization tables (metric catalog/mappings)

### Subscription & Billing Tables

- `subscriptions` and lifecycle fields
- Tier allocation and usage/assignment tables
- Subscription audit history tables

### Integration Tables

- Notification routing tables (`notification_channels`, `notification_routing_rules`, `notification_log`)
- Message routing and DLQ tables
- Legacy delivery retention tables (no longer used for active delivery)

### User & Auth Tables

- Tenant profile tables
- Preferences tables
- Operator audit/system audit tables

### System Tables

- `system_metrics` hypertable
- Settings and audit tables

## Migrations

### Running Migrations

Idempotent runner:

```bash
python db/migrate.py
```

Manual (single file):

```bash
psql "$DATABASE_URL" -f db/migrations/NNN_name.sql
```

`db/migrate.py` applies all `db/migrations/*.sql` in numeric order and records applied versions in `schema_migrations`.

### Migration Index

There are 84 migration files in `db/migrations/`:

| Version | Filename |
|---------|----------|
| 000 | 000_base_schema.sql |
| 001 | 001_webhook_delivery_v1.sql |
| 002 | 002_operator_audit_log.sql |
| 003 | 003_rate_limits.sql |
| 004 | 004_enable_rls.sql |
| 005 | 005_audit_rls_bypass.sql |
| 011 | 011_snmp_integrations.sql |
| 012 | 012_delivery_log.sql |
| 013 | 013_email_integrations.sql |
| 014 | 014_mqtt_integrations.sql |
| 016 | 016_deprecate_raw_events.sql |
| 017 | 017_alert_rules_rls.sql |
| 018 | 018_tenants_table.sql |
| 019 | 019_remove_tenant_plan_fields.sql |
| 020 | 020_enable_timescaledb.sql |
| 021 | 021_telemetry_hypertable.sql |
| 022 | 022_system_metrics_hypertable.sql |
| 023 | 023_timescale_policies.sql |
| 024 | 024_device_extended_attributes.sql |
| 025 | 025_fix_alert_rules_schema.sql |
| 026 | 026_metric_catalog.sql |
| 027 | 027_metric_normalization.sql |
| 028 | 028_system_audit_log.sql |
| 029 | 029_subscription_entitlements.sql |
| 030 | 030_multi_subscription.sql |
| 031 | 031_migrate_subscription_data.sql |
| 032 | 032_remove_tenant_subscription.sql |
| 033 | 033_fix_integration_routes_severities.sql |
| 034 | 034_fix_telemetry_compression.sql |
| 035 | 035_device_registry_rls.sql |
| 036 | 036_add_foreign_keys.sql |
| 036a | 036a_cleanup_tenant_refs.sql |
| 037 | 037_add_missing_indexes.sql |
| 038 | 038_add_check_constraints.sql |
| 039 | 039_cleanup_deprecated_policies.sql |
| 040 | 040_verify_alert_rules_schema.sql |
| 050 | 050_cleanup_test_data.sql |
| 051 | 051_log_retention_policies.sql |
| 052 | 052_seed_test_data.sql |
| 054 | 054_alert_rules_duration_seconds.sql |
| 055 | 055_fix_operator_constraint.sql |
| 056 | 056_listen_notify_triggers.sql |
| 057 | 057_alert_ack_fields.sql |
| 058 | 058_device_decommission.sql |
| 059 | 059_alert_escalation.sql |
| 060 | 060_anomaly_alert_type.sql |
| 061 | 061_device_groups.sql |
| 062 | 062_maintenance_windows.sql |
| 063 | 063_no_telemetry_alert_type.sql |
| 064 | 064_device_api_tokens.sql |
| 065 | 065_alert_digest_settings.sql |
| 066 | 066_escalation_policies.sql |
| 067 | 067_report_runs.sql |
| 068 | 068_notification_channels.sql |
| 069 | 069_oncall_schedules.sql |
| 070 | 070_unify_notification_pipeline.sql |
| 071 | 071_drop_old_delivery_pipeline.sql |
| 072 | 072_drop_dead_operator_read_policy.sql |
| 073 | 073_envelope_version.sql |
| 074 | 074_alert_rule_duration.sql |
| 075 | 075_device_search_indexes.sql |
| 076 | 076_device_shadow.sql |
| 077 | 077_iot_jobs.sql |
| 078 | 078_alert_rule_match_mode.sql |
| 079 | 079_device_commands.sql |
| 080 | 080_iam_permissions.sql |
| 081 | 081_rbac_write_permissions.sql |
| 082 | 082_alert_window_rules.sql |
| 083 | 083_alert_dedup.sql |
| 084 | 084_rule_device_group.sql |
| 085 | 085_dynamic_device_groups.sql |
| 086 | 086_device_connection_events.sql |
| 087 | 087_user_preferences.sql |
| 088 | 088_firmware_versions.sql |
| 089 | 089_ota_campaigns.sql |
| 090 | 090_ota_device_status.sql |
| 091 | 091_dashboards.sql |
| 092 | 092_export_jobs.sql |
| 093 | 093_message_routes.sql |
| 094 | 094_dead_letter_messages.sql |
| 095 | 095_device_certificates.sql |
| 096 | 096_tenant_profile.sql |
| 097 | 097_device_tiers.sql |
| 098 | 098_fix_customer_viewer_bootstrap.sql |

## TimescaleDB

### Hypertables

Common hypertables include:

- `telemetry`
- `system_metrics`

### Compression Policies

Compression policies are defined by migrations and should be verified against retention needs.

### Retention Policies

Retention policies are defined by migrations (and may be adjusted per deployment).

## Backup & Restore

At minimum:

- Take periodic logical backups (pg_dump) or physical backups depending on size and RPO/RTO needs.
- Validate restore procedures regularly.
- Consider hypertable retention/compression implications when restoring.

## See Also

- [Deployment](deployment.md)
- [Runbook](runbook.md)
- [Tenant Isolation](../architecture/tenant-isolation.md)

