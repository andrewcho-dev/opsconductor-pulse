# 002 — Create Apache VirtualHost Configuration

## Goal

Configure Apache as the internet-facing reverse proxy for
`pulse.enabledconsultants.com`. This replicates the routing logic that was
previously in the Caddy configuration.

## Prerequisites

Install required Apache modules (run on the host):

```bash
sudo apt-get update
sudo apt-get install -y apache2
sudo a2enmod proxy proxy_http proxy_wstunnel headers rewrite ssl
sudo systemctl enable apache2
```

## File to Create

`/etc/apache2/sites-available/pulse.conf`

## Content

```apache
<VirtualHost *:80>
    ServerName pulse.enabledconsultants.com

    # Redirect all HTTP to HTTPS
    RewriteEngine On
    RewriteCond %{HTTPS} off
    RewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]
</VirtualHost>

<VirtualHost *:443>
    ServerName pulse.enabledconsultants.com

    # TLS — certbot will fill these in (see step 003)
    # SSLEngine on
    # SSLCertificateFile    /etc/letsencrypt/live/pulse.enabledconsultants.com/fullchain.pem
    # SSLCertificateKeyFile /etc/letsencrypt/live/pulse.enabledconsultants.com/privkey.pem

    # ── Forward proxy headers so backend services know the real client ──
    RequestHeader set X-Forwarded-Proto "https"
    RequestHeader set X-Forwarded-Port "443"
    ProxyPreserveHost On

    # ── Keycloak routes ──
    # These must come BEFORE the catch-all so they match first.

    ProxyPass         /realms  http://127.0.0.1:8180/realms
    ProxyPassReverse  /realms  http://127.0.0.1:8180/realms

    ProxyPass         /resources  http://127.0.0.1:8180/resources
    ProxyPassReverse  /resources  http://127.0.0.1:8180/resources

    ProxyPass         /admin  http://127.0.0.1:8180/admin
    ProxyPassReverse  /admin  http://127.0.0.1:8180/admin

    ProxyPass         /js  http://127.0.0.1:8180/js
    ProxyPassReverse  /js  http://127.0.0.1:8180/js

    # ── WebSocket support for real-time UI updates ──
    RewriteEngine On
    RewriteCond %{HTTP:Upgrade} websocket [NC]
    RewriteCond %{HTTP:Connection} upgrade [NC]
    RewriteRule ^/(.*)$ ws://127.0.0.1:8080/$1 [P,L]

    # ── Everything else → UI backend (FastAPI + SPA) ──
    ProxyPass         /  http://127.0.0.1:8080/
    ProxyPassReverse  /  http://127.0.0.1:8080/

    # ── Logging ──
    ErrorLog  ${APACHE_LOG_DIR}/pulse_error.log
    CustomLog ${APACHE_LOG_DIR}/pulse_access.log combined
</VirtualHost>
```

## Enable the Site

```bash
# Disable default site if active
sudo a2dissite 000-default.conf

# Enable the new site
sudo a2ensite pulse.conf

# Test config syntax
sudo apache2ctl configtest

# Reload (don't restart yet — TLS cert comes in step 003)
sudo systemctl reload apache2
```

## Notes

- The SSL directives are commented out initially. Certbot (step 003) will
  uncomment them and configure TLS automatically.
- `ProxyPreserveHost On` is critical — Keycloak uses the `Host` header to
  construct redirect URLs. Without it, Keycloak would see `127.0.0.1:8180`
  as the host and generate broken URLs.
- `X-Forwarded-Proto` and `X-Forwarded-Port` headers are required because
  Keycloak is configured with `KC_PROXY_HEADERS=xforwarded`.
- WebSocket rewrite rules ensure the UI's real-time features work through
  the proxy.
