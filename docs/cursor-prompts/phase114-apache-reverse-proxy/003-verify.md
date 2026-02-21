# 003 — End-to-End Verification

## 1. Public Site

```bash
curl -sI https://pulse.enabledconsultants.com | head -3
# Expected: HTTP/2 200

curl -sI http://pulse.enabledconsultants.com | head -3
# Expected: 301 → https://
```

## 2. Login

Open `https://pulse.enabledconsultants.com` in a browser:
- [ ] Login page loads
- [ ] Login completes
- [ ] Dashboard renders

## 3. Keycloak OIDC

```bash
curl -s https://pulse.enabledconsultants.com/realms/pulse/.well-known/openid-configuration | python3 -m json.tool | head -5
```

## 4. MQTT Reachable

```bash
nc -zv pulse.enabledconsultants.com 8883 -w 5
nc -zv pulse.enabledconsultants.com 9001 -w 5
# Both: Connection succeeded
```

## 5. Dangerous Ports Blocked (from external machine, NOT 192.168.50.53)

```bash
nc -zv 192.168.50.53 5432 -w 3   # Postgres     → timeout/refused
nc -zv 192.168.50.53 6432 -w 3   # PgBouncer    → timeout/refused
nc -zv 192.168.50.53 8081 -w 3   # Provision API → timeout/refused
nc -zv 192.168.50.53 9999 -w 3   # Webhook      → timeout/refused
```

## 6. Caddy Only From Apache Host

```bash
# From 192.168.50.99 (Apache host) — should work:
curl -sk https://192.168.50.53:443/healthz

# From any other LAN machine — should be blocked by UFW:
nc -zv 192.168.50.53 443 -w 3    # → timeout/refused
```

## 7. Docker Health

```bash
cd ~/simcloud/compose
docker compose ps
# All services: Up / healthy
```

## 8. Port Bindings

```bash
docker compose ps --format "table {{.Name}}\t{{.Ports}}" | grep -E '5432|6432|8081|9999'
# All four: 127.0.0.1 prefix
```

## Troubleshooting

### 502 from Apache after restart
Caddy may have been slow to start. Wait 30s, retry. Check:
`docker compose logs caddy`

### Keycloak redirect loop
Verify Apache sends: `ProxyPreserveHost On` + `X-Forwarded-Proto: https`

### MQTT refused on 8883
```bash
docker compose logs mqtt
ss -tlnp | grep 8883
# Should show 0.0.0.0:8883 (NOT 127.0.0.1)
```

### Rollback
```bash
cd ~/simcloud/compose
cp docker-compose.yml.bak.<TIMESTAMP> docker-compose.yml
docker compose down && docker compose up -d
```
