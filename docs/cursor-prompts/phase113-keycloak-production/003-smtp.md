# Phase 113 — Keycloak SMTP Configuration

## Context

Keycloak's realm config has `smtp: {}` — empty. Password reset, email
verification, and OTP emails all silently fail. For production, SMTP must
be configured.

## Step 1: Add SMTP env vars to .env and .env.example

Add to `compose/.env.example`:
```bash
# ── SMTP (for Keycloak email flows) ──────────────────────────────────────────
# Required for password reset, email verification, OTP emails.
# Leave blank to disable email (users will not receive emails from Keycloak).
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=noreply@example.com
SMTP_PASSWORD=CHANGE_ME_smtp_password
SMTP_FROM=noreply@example.com
SMTP_FROM_DISPLAY_NAME=OpsConductor Pulse
SMTP_SSL=false
SMTP_STARTTLS=true
```

Add to `compose/.env` (for local dev, leave blank or use a local SMTP relay):
```bash
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM=noreply@localhost
SMTP_FROM_DISPLAY_NAME=OpsConductor Pulse
SMTP_SSL=false
SMTP_STARTTLS=false
```

When SMTP_HOST is empty, Keycloak will not send emails — acceptable for local dev.

## Step 2: Update realm-pulse.json with SMTP config

Read `compose/keycloak/realm-pulse.json`. Find the `"smtpServer"` section
(currently `{}`). Replace with:

```json
"smtpServer": {
  "host": "${env.SMTP_HOST}",
  "port": "${env.SMTP_PORT}",
  "from": "${env.SMTP_FROM}",
  "fromDisplayName": "${env.SMTP_FROM_DISPLAY_NAME}",
  "auth": "true",
  "user": "${env.SMTP_USERNAME}",
  "password": "${env.SMTP_PASSWORD}",
  "ssl": "${env.SMTP_SSL}",
  "starttls": "${env.SMTP_STARTTLS}"
}
```

**Note:** Keycloak realm JSON supports `${env.VAR_NAME}` substitution for
environment variables when importing realms. This means SMTP credentials
are injected at import time, not hardcoded in the realm file.

## Step 3: Pass SMTP env vars to Keycloak container

In `compose/docker-compose.yml`, add to the keycloak service environment:

```yaml
  keycloak:
    environment:
      SMTP_HOST: ${SMTP_HOST}
      SMTP_PORT: ${SMTP_PORT}
      SMTP_FROM: ${SMTP_FROM}
      SMTP_FROM_DISPLAY_NAME: ${SMTP_FROM_DISPLAY_NAME}
      SMTP_USERNAME: ${SMTP_USERNAME}
      SMTP_PASSWORD: ${SMTP_PASSWORD}
      SMTP_SSL: ${SMTP_SSL}
      SMTP_STARTTLS: ${SMTP_STARTTLS}
```

## Step 4: For local dev — use Mailpit (optional but recommended)

Mailpit is a lightweight local SMTP server that captures all outgoing emails
and shows them in a web UI. Add to docker-compose.yml as a dev-profile service:

```yaml
  mailpit:
    image: axllent/mailpit:latest
    container_name: iot-mailpit
    ports:
      - "8025:8025"    # Web UI — visit http://localhost:8025
      - "1025:1025"    # SMTP
    networks:
      - iot-network
    profiles:
      - dev
```

When using Mailpit, set in `.env`:
```bash
SMTP_HOST=iot-mailpit
SMTP_PORT=1025
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_STARTTLS=false
```

This lets you test password reset and email verification flows locally
without a real SMTP server.
