---
last-verified: 2026-02-19
sources:
  - helm/pulse/values.yaml
phases: [163]
---

# Managed PostgreSQL

> How to run Pulse against a managed PostgreSQL instance (RDS / Azure / Timescale Cloud / self-managed).

## Helm Values

Bundled PostgreSQL (default for dev/small deployments):

```yaml
postgresql:
  enabled: true
```

Managed PostgreSQL (production):

```yaml
postgresql:
  enabled: false

externalDatabase:
  enabled: true
  host: "mydb.example.com"
  port: 5432
  database: "iotcloud"
  username: "iot"
  existingSecret: "pulse-db-secret"
```

## Requirements

1. TimescaleDB extension availability (telemetry hypertables)
2. Required extensions:

```sql
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

3. SSL/TLS: managed instances typically require SSL; use `sslmode=require` in DSNs.

## Migration Steps (high level)

1. Provision the managed PG instance
2. Enable required extensions
3. Run the migrator job against the new instance (schema/bootstrap)
4. Deploy Helm release with `externalDatabase` enabled
5. (Optional) migrate existing data using `pg_dump`/`pg_restore`

## Notes

- Cloud providers differ on Timescale availability; Timescale Cloud works across providers.
- If using a cloud-native pooler (RDS Proxy / built-in pooler), you may not need PgBouncer.

