# 004 — Break-Glass Recovery

Use this only during outage recovery. The goal is to restore service quickly, then return to hardened settings.

## Scope

- Docker host: `192.168.50.53` (OpsConductor-Pulse)
- Apache host: `192.168.50.99` (internet-facing reverse proxy)
- Public URL: `https://pulse.enabledconsultants.com`

---

## A) Public site down (fast checks)

On `192.168.50.99` (Apache host):

```bash
sudo apachectl configtest
sudo systemctl status httpd --no-pager
curl -k -I https://192.168.50.53/
curl -I https://pulse.enabledconsultants.com
```

On `192.168.50.53` (Docker host):

```bash
cd ~/simcloud/compose
docker compose ps
docker compose logs --tail=80 caddy ui keycloak
```

---

## B) Emergency restore of previous Docker port map

If lock-down changes caused an outage, restore the backup compose file and restart:

```bash
cd ~/simcloud/compose
ls -1 docker-compose.yml.bak-*
cp docker-compose.yml.bak-<TIMESTAMP> docker-compose.yml
docker compose up -d --force-recreate
docker compose ps
```

Known backup from Phase 114 execution:

```text
docker-compose.yml.bak-20260215-090906
```

---

## C) Temporarily relax firewall on Docker host (last resort)

If Apache (`192.168.50.99`) cannot reach Docker host `80/443` and root cause is unclear:

```bash
sudo ufw status numbered
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw reload
```

After incident is resolved, re-apply hardened rules:

```bash
sudo ufw allow from 192.168.50.99 to any port 80 proto tcp
sudo ufw allow from 192.168.50.99 to any port 443 proto tcp
sudo ufw deny 80/tcp
sudo ufw deny 443/tcp
sudo ufw reload
sudo ufw status numbered
```

---

## D) Validate auth host alignment (login failures)

On `192.168.50.53`:

```bash
cd ~/simcloud/compose
grep -E '^(KEYCLOAK_URL|UI_BASE_URL|KC_HOSTNAME)=' .env
docker compose logs --tail=60 ui | rg "OAuth config"
curl -k https://localhost/realms/pulse/.well-known/openid-configuration | rg '"issuer"'
```

Expected host in all three places:

```text
pulse.enabledconsultants.com
```

---

## E) Minimal success criteria before closing incident

- `curl -I https://pulse.enabledconsultants.com` returns `200`/`302` (not `5xx`)
- Browser login works end-to-end
- `docker compose ps` shows `caddy`, `ui`, `keycloak` healthy
- Hardened state restored:
  - `5432`, `6432`, `8081`, `9999` bound to `127.0.0.1` in compose
  - UFW allows `80/443` only from `192.168.50.99`

