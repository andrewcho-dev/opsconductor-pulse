# Phase 30.8: Remove InfluxDB

## Task

Remove InfluxDB from the stack now that telemetry is stored in TimescaleDB.

---

## Update Docker Compose

**File:** `compose/docker-compose.yml`

Remove the influxdb service entirely:

```yaml
# DELETE this entire section:
#
#   influxdb:
#     image: influxdb:3-core
#     container_name: iot-influxdb
#     environment:
#       INFLUXDB3_HTTP_BIND_ADDR: "0.0.0.0:8181"
#       ...
#     ports:
#       - "8181:8181"
#     volumes:
#       - ../data/influxdb3:/var/lib/influxdb3:z
#     ...
```

Remove `influxdb` from all service dependencies:

```yaml
  ingest:
    depends_on:
      mqtt:
        condition: service_started
      postgres:
        condition: service_healthy
      # REMOVE: influxdb: condition: service_healthy

  evaluator:
    depends_on:
      postgres:
        condition: service_healthy
      # REMOVE: influxdb: condition: service_healthy

  api:
    depends_on:
      postgres:
        condition: service_healthy
      # REMOVE: influxdb: condition: service_healthy

  ui:
    depends_on:
      postgres:
        condition: service_healthy
      api:
        condition: service_started
      # REMOVE: influxdb: condition: service_healthy
```

Remove InfluxDB environment variables from all services:

```yaml
# REMOVE from ingest, evaluator, api, ui, etc:
#   INFLUXDB_URL: "http://iot-influxdb:8181"
#   INFLUXDB_TOKEN: "${INFLUXDB_TOKEN:-influx-dev-token-change-me}"
```

---

## Remove InfluxDB Code

**File:** `services/ui_iot/routes/operator.py`

Remove InfluxDB-related code:

```python
# REMOVE these imports and variables:
# INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://iot-influxdb:8181")
# INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "")
# _influx_client: httpx.AsyncClient | None = None

# REMOVE these functions:
# def _get_influx_client() -> httpx.AsyncClient:
# async def provision_tenant_influxdb(tenant_id: str) -> bool:
# async def check_tenant_influxdb(tenant_id: str) -> dict:

# UPDATE create_tenant to remove InfluxDB provisioning:
# Remove: influx_ok = await provision_tenant_influxdb(tenant.tenant_id)
# Remove: "influxdb_provisioned": influx_ok from response

# UPDATE get_tenant_stats to remove InfluxDB check:
# Remove: influx_status = await check_tenant_influxdb(tenant_id)
# Remove: "influxdb": influx_status from response
```

**File:** `services/ui_iot/db/influx_queries.py`

Delete this file entirely (replaced by `telemetry_queries.py`).

**File:** `services/ingest_iot/ingest.py`

Remove any remaining InfluxDB references:

```python
# REMOVE InfluxDB imports and configuration
# REMOVE InfluxBatchWriter class (now in shared/ingest_core.py as TimescaleBatchWriter)
```

**File:** `services/shared/ingest_core.py`

Remove `InfluxBatchWriter` class if still present (keep only `TimescaleBatchWriter`).

---

## Update Frontend

**File:** `frontend/src/features/operator/OperatorTenantDetailPage.tsx`

Remove InfluxDB status display:

```typescript
// REMOVE InfluxDB status section
// REMOVE "Provision InfluxDB" button
// REMOVE influxdb-related state and handlers
```

**File:** `frontend/src/services/api/tenants.ts`

Remove influxdb from response types:

```typescript
// REMOVE influxdb field from TenantStats type
```

---

## Clean Up Data Directory

```bash
# Stop all services
cd /home/opsconductor/simcloud/compose
docker compose down

# Remove InfluxDB data
rm -rf ../data/influxdb3

# Remove InfluxDB Docker volume if created
docker volume rm compose_influxdb_data 2>/dev/null || true
```

---

## Update .env.example

**File:** `.env.example` or `compose/.env.example`

Remove InfluxDB variables:

```bash
# REMOVE:
# INFLUXDB_TOKEN=influx-dev-token-change-me
```

---

## Rebuild and Restart

```bash
cd /home/opsconductor/simcloud/compose

# Rebuild all services
docker compose build

# Start without InfluxDB
docker compose up -d

# Verify InfluxDB is not running
docker compose ps
# Should NOT show iot-influxdb

# Check logs for errors
docker compose logs --tail=50
```

---

## Verification

```bash
# Verify no InfluxDB references in running containers
docker compose exec ui env | grep -i influx
# Should return nothing

# Test telemetry ingestion still works
docker compose exec mqtt mosquitto_pub \
  -t "tenant/enabled/device/test-001/telemetry" \
  -m '{"site_id":"lab-1","seq":1,"metrics":{"temp":25.5}}'

# Verify data in TimescaleDB
docker compose exec postgres psql -U iot -d iotcloud -c "
SELECT time, tenant_id, device_id, metrics
FROM telemetry
ORDER BY time DESC
LIMIT 5;
"

# Test API endpoints
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8080/api/v2/devices/test-001/telemetry"
```

---

## Files to Modify/Delete

| Action | File |
|--------|------|
| MODIFY | `compose/docker-compose.yml` |
| MODIFY | `services/ui_iot/routes/operator.py` |
| DELETE | `services/ui_iot/db/influx_queries.py` |
| MODIFY | `services/ingest_iot/ingest.py` |
| MODIFY | `services/shared/ingest_core.py` |
| MODIFY | `frontend/src/features/operator/OperatorTenantDetailPage.tsx` |
| MODIFY | `frontend/src/services/api/tenants.ts` |
| DELETE | `../data/influxdb3/` (data directory) |
