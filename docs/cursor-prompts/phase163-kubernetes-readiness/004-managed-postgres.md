# Task 4: Managed PostgreSQL Migration Path

## Files to Modify

- `helm/pulse/values.yaml` — document external DB config
- Create: `docs/operations/managed-postgres.md`

## What to Do

Document how to switch from the bundled PostgreSQL to a managed instance (RDS, Azure DB for PG, Cloud SQL, Timescale Cloud).

### values.yaml Configuration

```yaml
# Option A: Bundled PostgreSQL (default for dev/small deployments)
postgresql:
  enabled: true

# Option B: Managed PostgreSQL (production)
postgresql:
  enabled: false
externalDatabase:
  enabled: true
  host: "mydb.cluster-xxxxx.us-east-1.rds.amazonaws.com"
  port: 5432
  database: "iotcloud"
  username: "iot"
  existingSecret: "pulse-db-secret"  # Must contain key "password"
```

### Requirements for Managed PG

Document these requirements:

1. **TimescaleDB extension must be available**
   - RDS: Use the `timescaledb` parameter group (available on PG 14+)
   - Cloud SQL: Enable `timescaledb` extension in the instance config
   - Timescale Cloud: Native, no setup needed
   - Azure: TimescaleDB extension available on Azure Database for PostgreSQL Flexible Server

2. **Extensions to enable:**
   ```sql
   CREATE EXTENSION IF NOT EXISTS timescaledb;
   CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- used for gen_random_uuid()
   ```

3. **PgBouncer consideration:**
   - RDS Proxy is an alternative to PgBouncer (transaction pooling built-in)
   - Azure: Built-in PgBouncer support on Flexible Server
   - If using cloud-native pooling, disable the PgBouncer sidecar/deployment

4. **Connection string format:**
   ```
   postgresql://iot:PASSWORD@HOST:5432/iotcloud?sslmode=require
   ```

5. **Instance sizing recommendations:**

   | Customers | Instance | vCPU | RAM | Storage | IOPS |
   |-----------|----------|------|-----|---------|------|
   | 1-50 | db.t3.large / Standard_D2s_v3 | 2 | 8GB | 50GB gp3 | Baseline |
   | 50-250 | db.r6g.xlarge / Standard_E4s_v3 | 4 | 32GB | 100GB gp3 | 6,000 |
   | 250-500 | db.r6g.2xlarge / Standard_E8s_v3 | 8 | 64GB | 200GB gp3 | 10,000 |
   | 500+ | db.r6g.4xlarge + read replica | 16 | 128GB | 400GB+ | 15,000+ |

6. **Backup configuration:**
   - Automated daily snapshots with 7-day retention (minimum)
   - Point-in-time recovery enabled
   - Cross-region backup for disaster recovery (500+ customers)

### Migration Steps

Document the process:

1. Provision managed PG instance with TimescaleDB extension
2. Run the migrator against the new instance to create schema
3. Update Helm values to point at the new instance
4. (Optional) Migrate existing data using `pg_dump`/`pg_restore`
5. Verify with a test deployment
6. Cut over by deploying with new values

## Important Notes

- **Don't migrate data on first deploy** — start fresh with the managed instance. Only migrate if the existing data matters.
- **PgBouncer:** If using RDS Proxy or Azure's built-in pooler, remove the PgBouncer deployment from the Helm chart. The services connect directly to the managed pooler.
- **SSL:** Managed PG instances require SSL. Ensure `sslmode=require` in connection strings.
- **Timescale Cloud** is the easiest option if you want fully managed TimescaleDB without extension compatibility concerns.
