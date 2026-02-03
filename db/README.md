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
| 001 | webhook_delivery_v1.sql | Core delivery tables |
| 002 | operator_audit_log.sql | Operator audit logging |
| 003 | rate_limits.sql | Rate limiting table |
| 004 | enable_rls.sql | Enable RLS on tables |
| 005 | audit_rls_bypass.sql | Operator RLS bypass |
| 011 | snmp_integrations.sql | SNMP support columns |
| 012 | delivery_log.sql | Delivery logging table |

## Notes

- Migrations are idempotent (use IF NOT EXISTS)
- Run in numeric order
- Gap in numbering (006-010) reserved for future use
