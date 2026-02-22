# Task 1: Add Valkey Service

## File 1 — compose/docker-compose.yml

### Change 1a — Add Valkey service

Add the following service block. Insert it after the `pgbouncer` service and
before the `nats` service for logical grouping:

```yaml
  valkey:
    image: valkey/valkey:7-alpine
    container_name: iot-valkey
    restart: unless-stopped
    command: >
      valkey-server
      --appendonly yes
      --maxmemory 512mb
      --maxmemory-policy allkeys-lru
    volumes:
      - valkey_data:/data
    healthcheck:
      test: ["CMD", "valkey-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - default
```

### Change 1b — Add valkey_data volume

In the top-level `volumes:` section, add:

```yaml
  valkey_data:
```

### Change 1c — Add VALKEY_URL to evaluator environment

In the `evaluator` service `environment:` block, add:

```yaml
      VALKEY_URL: "redis://iot-valkey:6379"
      RULE_COOLDOWN_SECONDS: "300"
      TENANT_BUDGET_MS: "500"
      EVALUATION_INTERVAL_SECONDS: "60"
      MIN_EVAL_INTERVAL_SECONDS: "10"
      EVALUATOR_SHARD_INDEX: "0"
      EVALUATOR_SHARD_COUNT: "1"
```

### Change 1d — Add depends_on for evaluator

In the `evaluator` service `depends_on:` block, add `valkey`:

```yaml
    depends_on:
      valkey:
        condition: service_healthy
```

(Add alongside the existing depends_on entries; do not replace them.)

---

## File 2 — services/evaluator_iot/requirements.txt

Add at the end:

```
redis[asyncio]>=5.0.0
```

---

## Verification

```bash
cd /home/opsconductor/simcloud
docker compose -f compose/docker-compose.yml up -d valkey
docker compose -f compose/docker-compose.yml exec valkey valkey-cli ping
```

Expected output: `PONG`

```bash
docker compose -f compose/docker-compose.yml exec valkey valkey-cli info server | grep valkey_version
```

Expected: `valkey_version:7.x.x`
