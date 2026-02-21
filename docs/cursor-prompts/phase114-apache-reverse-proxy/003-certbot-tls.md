# 003 — Obtain Let's Encrypt TLS Certificate

## Goal

Use certbot to obtain and auto-renew a real TLS certificate for
`pulse.enabledconsultants.com`.

## Prerequisites

- DNS for `pulse.enabledconsultants.com` must resolve to this server's
  public IP address.
- Port 80 must be reachable from the internet (certbot uses HTTP-01
  challenge).
- Apache must be running with the VirtualHost from step 002.

## Install Certbot

```bash
sudo apt-get update
sudo apt-get install -y certbot python3-certbot-apache
```

## Obtain Certificate

```bash
sudo certbot --apache \
  -d pulse.enabledconsultants.com \
  --non-interactive \
  --agree-tos \
  --email admin@enabledconsultants.com \
  --redirect
```

This will:
1. Prove domain ownership via HTTP-01 challenge on port 80
2. Obtain the certificate from Let's Encrypt
3. Automatically modify `/etc/apache2/sites-available/pulse.conf` (or create
   `pulse-le-ssl.conf`) to enable SSL with the correct cert paths
4. Set up HTTP → HTTPS redirect if not already present

## Verify Auto-Renewal

Certbot installs a systemd timer for auto-renewal. Verify it:

```bash
# Check timer is active
sudo systemctl status certbot.timer

# Dry run to confirm renewal works
sudo certbot renew --dry-run
```

## Post-Certbot Verification

```bash
# Check the Apache SSL config was created/updated
sudo apache2ctl -S

# Verify the certificate
echo | openssl s_client -servername pulse.enabledconsultants.com \
  -connect pulse.enabledconsultants.com:443 2>/dev/null | \
  openssl x509 -noout -dates -subject

# Should show:
#   subject=CN = pulse.enabledconsultants.com
#   notBefore=...
#   notAfter=... (90 days from now)
```

## Notes

- If certbot creates a separate `pulse-le-ssl.conf` instead of modifying
  `pulse.conf` in place, that is fine — the proxy rules will be duplicated
  into the new SSL vhost by certbot.
- If certbot does NOT copy the ProxyPass directives, you must manually copy
  the Keycloak proxy rules, WebSocket rewrite, and catch-all ProxyPass from
  `pulse.conf` into the `*:443` block of `pulse-le-ssl.conf`.
- Certificates auto-renew every 60 days. No manual intervention needed.
