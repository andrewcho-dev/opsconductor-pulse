# Database Migrations

## Running Migrations

### Manual (recommended for production)

```bash
cd db
PGPASSWORD=iot_dev ./run_migrations.sh localhost 5432 iotcloud iot
```

### Individual Migration

```bash
PGPASSWORD=iot_dev psql -h localhost -U iot -d iotcloud -f db/migrations/012_delivery_log.sql
```

## Verifying Migrations

```bash
PGPASSWORD=iot_dev psql -h localhost -U iot -d iotcloud -f db/verify_migrations.sql
```

## Migration Files

| # | File | Description |
|---|------|-------------|
| 000 | base_schema.sql | Core tables: device_registry, device_state, fleet_alert, alert_rules, quarantine |
| 001 | webhook_delivery_v1.sql | Delivery system: integrations, integration_routes, delivery_jobs |
| 002 | operator_audit_log.sql | Operator audit logging |
| 003 | rate_limits.sql | Rate limiting table |
| 004 | enable_rls.sql | Row-level security policies |
| 005 | audit_rls_bypass.sql | Operator RLS bypass |
| 011 | snmp_integrations.sql | SNMP support columns |
| 012 | delivery_log.sql | Delivery logging table |
| 013 | email_integrations.sql | Email delivery support |
| 014 | mqtt_integrations.sql | MQTT delivery support |
| 016 | deprecate_raw_events.sql | Rename raw_events to deprecated table |
| 017 | alert_rules_rls.sql | Alert rules RLS policies |
| 018 | tenants_table.sql | Multi-tenant support |
| 019 | remove_tenant_plan_fields.sql | Schema cleanup |
| 020 | enable_timescaledb.sql | TimescaleDB extension |
| 021 | telemetry_hypertable.sql | Telemetry hypertable |
| 022 | system_metrics_hypertable.sql | System metrics hypertable |
| 023 | timescale_policies.sql | Compression and retention |
| 024 | device_extended_attributes.sql | Device attributes, geocoding |
| 025 | fix_alert_rules_schema.sql | Alert rules column fixes |
| 026 | metric_catalog.sql | Metric catalog table |
| 027 | metric_normalization.sql | Metric normalization mappings |
| 028 | system_audit_log.sql | System-wide audit log |
| 029 | subscription_entitlements.sql | Subscription tables |
| 030 | multi_subscription.sql | Multi-subscription schema |
| 031 | migrate_subscription_data.sql | Data migration |
| 032 | remove_tenant_subscription.sql | Deprecation cleanup |
| 033 | fix_integration_routes_severities.sql | Add severities column |
| 034 | fix_telemetry_compression.sql | Telemetry compression policies |
| 035 | device_registry_rls.sql | RLS policies for device_registry, delivery_jobs, quarantine_events |
| 036 | add_foreign_keys.sql | Tenant foreign keys |
| 037 | add_missing_indexes.sql | Performance indexes |
| 038 | add_check_constraints.sql | Data validation constraints |
| 039 | cleanup_deprecated_policies.sql | Remove orphaned RLS policies |
| 040 | verify_alert_rules_schema.sql | Align alert_rules schema |

## Notes

- Migrations are idempotent (use IF NOT EXISTS)
- Run in numeric order
- Gap in numbering (006-010, 015) reserved for future use
