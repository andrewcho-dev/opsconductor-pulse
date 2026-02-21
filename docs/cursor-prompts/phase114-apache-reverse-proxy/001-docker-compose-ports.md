# 001 — Lock Down Docker Port Bindings on 192.168.50.53

## Topology

- **Apache host:** 192.168.50.99 (internet-facing, proxies to Docker host)
- **Docker host:** 192.168.50.53 (runs all containers)

## Step 0 — Backup

```bash
cd ~/simcloud/compose
cp docker-compose.yml docker-compose.yml.bak.$(date +%Y%m%d-%H%M%S)
```

## Step 1 — Rebind Dangerous Ports to 127.0.0.1

### PostgreSQL

Change:
```yaml
    ports:
      - "5432:5432"
```
To:
```yaml
    ports:
      - "127.0.0.1:5432:5432"
```

### PgBouncer

Change:
```yaml
    ports:
      - "6432:5432"
```
To:
```yaml
    ports:
      - "127.0.0.1:6432:5432"
```

### Provision API

Change:
```yaml
    ports:
      - "8081:8081"
```
To:
```yaml
    ports:
      - "127.0.0.1:8081:8081"
```

### Webhook Receiver

Change:
```yaml
    ports:
      - "9999:9999"
```
To:
```yaml
    ports:
      - "127.0.0.1:9999:9999"
```

## Step 2 — Do NOT Touch These

**Caddy** — stays as-is. Apache on 192.168.50.99 proxies here:
```yaml
    ports:
      - "80:80"
      - "443:443"
```

**MQTT** — stays as-is. IoT devices connect directly:
```yaml
    ports:
      - "8883:8883"
      - "9001:9001"
```

## Step 3 — Restart

```bash
cd ~/simcloud/compose
docker compose down
docker compose up -d
```

## Step 4 — Verify Port Bindings

```bash
docker compose ps --format "table {{.Name}}\t{{.Ports}}"
```

Expected: 5432, 6432, 8081, 9999 should all show `127.0.0.1:` prefix.
Caddy (80, 443) and MQTT (8883, 9001) should show `0.0.0.0:`.

## Step 5 — Verify Site Still Works

```bash
curl -sI https://pulse.enabledconsultants.com | head -3
# Expected: HTTP 200
```

## Rollback

```bash
cd ~/simcloud/compose
ls docker-compose.yml.bak.*
cp docker-compose.yml.bak.<TIMESTAMP> docker-compose.yml
docker compose down && docker compose up -d
```
