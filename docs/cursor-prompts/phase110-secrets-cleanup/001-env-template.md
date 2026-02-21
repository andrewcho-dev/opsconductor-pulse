# Phase 110 — .env Template + .gitignore

## Step 1: Create compose/.env.example

Create `compose/.env.example` with safe placeholder values and instructions.
This file IS committed to the repo — it documents what variables are required.

```bash
# OpsConductor-Pulse — Environment Configuration
# Copy this file to .env and fill in real values before running.
#   cp .env.example .env
# NEVER commit .env with real values.

# ── Network / Hostname ──────────────────────────────────────────────────────
# The IP or hostname where this stack is reachable from browsers and devices.
HOST_IP=localhost
KEYCLOAK_URL=https://localhost
UI_BASE_URL=https://localhost

# ── PostgreSQL ───────────────────────────────────────────────────────────────
POSTGRES_PASSWORD=CHANGE_ME_strong_password_here
PG_PASS=CHANGE_ME_strong_password_here

# ── Admin / Provision API keys ───────────────────────────────────────────────
# Generate with: python3 -c "import secrets; print(secrets.token_hex(32))"
ADMIN_KEY=CHANGE_ME_generate_with_secrets_token_hex
PROVISION_ADMIN_KEY=CHANGE_ME_generate_with_secrets_token_hex

# ── Keycloak ─────────────────────────────────────────────────────────────────
KEYCLOAK_ADMIN_USERNAME=admin
KEYCLOAK_ADMIN_PASSWORD=CHANGE_ME_strong_password_here
KC_DB_PASSWORD=CHANGE_ME_strong_password_here

# The public hostname Keycloak uses for redirects (must match HOST_IP or DNS name)
KC_HOSTNAME=localhost

# ── MQTT ─────────────────────────────────────────────────────────────────────
# Set after Phase 112 (MQTT hardening) adds authentication
MQTT_ADMIN_PASSWORD=CHANGE_ME_strong_password_here

# ── Logging ──────────────────────────────────────────────────────────────────
LOG_LEVEL=INFO
```

## Step 2: Overwrite compose/.env with safe dev defaults

Replace the current `compose/.env` (which has a real LAN IP) with:

```bash
# Local development defaults — safe to use on localhost only.
# For production or shared environments, use real values.

HOST_IP=localhost
KEYCLOAK_URL=https://localhost
UI_BASE_URL=https://localhost

POSTGRES_PASSWORD=iot_dev_local
PG_PASS=iot_dev_local

ADMIN_KEY=dev-admin-key-not-for-production
PROVISION_ADMIN_KEY=dev-provision-key-not-for-production

KEYCLOAK_ADMIN_USERNAME=admin
KEYCLOAK_ADMIN_PASSWORD=admin_dev_local
KC_DB_PASSWORD=iot_dev_local
KC_HOSTNAME=localhost

MQTT_ADMIN_PASSWORD=mqtt_dev_local

LOG_LEVEL=INFO
```

## Step 3: Add .env to .gitignore

Check if `compose/.gitignore` exists. If not, create it.
If a root `.gitignore` exists, add the entry there.

Add:
```
# Local environment — never commit real credentials
compose/.env
.env
```

Also verify that `compose/.env` is not currently tracked by git:

```bash
git ls-files compose/.env
```

If it returns a path, remove it from tracking:

```bash
git rm --cached compose/.env
```

This removes it from git's index without deleting the file from disk.

## Step 4: Verify .env.example is committed but .env is not

```bash
git status compose/
```

Expected:
- `compose/.env.example` — new file, will be committed
- `compose/.env` — untracked (no longer tracked)
