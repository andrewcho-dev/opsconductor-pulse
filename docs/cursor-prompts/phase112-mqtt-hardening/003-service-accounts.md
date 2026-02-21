# Phase 112 — Service Account Credentials + .env Updates

## Step 1: Add MQTT_ADMIN_PASSWORD to .env

The `.env` file (after Phase 110) already has a placeholder for
`MQTT_ADMIN_PASSWORD`. Verify it's present:

```bash
grep MQTT_ADMIN_PASSWORD compose/.env
```

If missing, add to `compose/.env`:
```bash
MQTT_ADMIN_PASSWORD=mqtt_dev_local
```

And to `compose/.env.example`:
```bash
# MQTT service account password (platform services → broker)
# Generate with: python3 -c "import secrets; print(secrets.token_hex(32))"
MQTT_ADMIN_PASSWORD=CHANGE_ME_generate_with_secrets_token_hex
```

## Step 2: Add MQTT_PASSWD_FILE to compose for provision_api

In `compose/docker-compose.yml`, add to the `api` (provision_api) service:

```yaml
  api:
    environment:
      MQTT_PASSWD_FILE: "/mosquitto/config/passwd"
    volumes:
      - mosquitto-passwd:/mosquitto/config
```

## Step 3: Declare mosquitto-passwd named volume

In the `volumes:` section at the bottom of docker-compose.yml:

```yaml
volumes:
  postgres-data:     # (if already exists or rename from bind mount)
  mosquitto-data:
  mosquitto-passwd:  # ← add this
```

## Step 4: Update mqtt service to use named volume for passwd

```yaml
  mqtt:
    volumes:
      - ./mosquitto/mosquitto.conf:/mosquitto/config/mosquitto.conf:ro
      - ./mosquitto/acl.conf:/mosquitto/config/acl.conf:ro
      - ./mosquitto/certs:/mosquitto/certs:ro
      - mosquitto-passwd:/mosquitto/config     # read-write, shared with provision_api
      - mosquitto-data:/mosquitto/data
```

## Step 5: Seed the passwd file into the named volume

Since the named volume starts empty, the initial passwd file must be seeded.
Add a one-time init to the mqtt service or run it manually:

```bash
# Create the passwd file in the named volume
docker compose -f compose/docker-compose.yml run --rm \
  -v compose_mosquitto-passwd:/mosquitto/config \
  eclipse-mosquitto:2.0.18 \
  mosquitto_passwd -c -b /mosquitto/config/passwd \
  "service:pulse" "$(grep MQTT_ADMIN_PASSWORD compose/.env | cut -d= -f2)"
```

Or add an entrypoint script to the mqtt service that creates the passwd file
on first start if it doesn't exist.

## Step 6: Verify Mosquitto reloads credentials

Mosquitto reloads the password file when it receives SIGHUP:

```bash
docker exec iot-mqtt kill -HUP 1
docker logs iot-mqtt --tail=5
```

Expected: log lines indicating password file reloaded (or no error if
the file was already loaded at start).
