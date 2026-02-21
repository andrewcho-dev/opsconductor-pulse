# 002 — UFW Firewall on 192.168.50.53 (Docker Host)

## Goal

Restrict Caddy's ports (80/443) so only the Apache host (192.168.50.99) can
reach them. Open MQTT ports for IoT devices. Block everything else.

**Note:** Docker manipulates iptables directly and can bypass UFW. The
`127.0.0.1` bindings from step 001 are the primary defence for Postgres etc.
UFW adds defence-in-depth and protects Caddy's ports from non-Apache sources.

## IMPORTANT — Add SSH First

```bash
sudo ufw allow OpenSSH
```

## Add Rules

```bash
# Caddy HTTP/HTTPS — only from Apache host
sudo ufw allow from 192.168.50.99 to any port 80 proto tcp
sudo ufw allow from 192.168.50.99 to any port 443 proto tcp

# MQTT over TLS — open to all (IoT devices connect from anywhere)
sudo ufw allow 8883/tcp

# MQTT WebSocket TLS — open to all
sudo ufw allow 9001/tcp
```

## Enable

```bash
sudo ufw enable
```

## Verify

```bash
sudo ufw status verbose
```

Expected:
```
Status: active
Default: deny (incoming), allow (outgoing)

To                         Action      From
--                         ------      ----
22/tcp (OpenSSH)           ALLOW IN    Anywhere
80/tcp                     ALLOW IN    192.168.50.99
443/tcp                    ALLOW IN    192.168.50.99
8883/tcp                   ALLOW IN    Anywhere
9001/tcp                   ALLOW IN    Anywhere
```

## What Is Now Blocked on 192.168.50.53

| Port | Service | Protection |
|------|---------|------------|
| 5432 | PostgreSQL | 127.0.0.1 bind + UFW deny |
| 6432 | PgBouncer | 127.0.0.1 bind + UFW deny |
| 8081 | Provision API | 127.0.0.1 bind + UFW deny |
| 9999 | Webhook Receiver | 127.0.0.1 bind + UFW deny |
| 80 | Caddy HTTP | UFW: only 192.168.50.99 |
| 443 | Caddy HTTPS | UFW: only 192.168.50.99 |

## Notes

- Remote DB access via SSH tunnel:
  `ssh -L 5432:127.0.0.1:5432 user@192.168.50.53`
- If Apache host IP changes, update the UFW rules:
  `sudo ufw delete allow from 192.168.50.99 to any port 80 proto tcp`
  `sudo ufw allow from <NEW_IP> to any port 80 proto tcp`
  (repeat for 443)
