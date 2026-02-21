# Task 1: EMQX Configuration and Docker Compose

## Files to Create/Modify

- **Create:** `compose/emqx/emqx.conf`
- **Modify:** `compose/docker-compose.yml`
- **Keep (read-only reference):** `compose/mosquitto/` — don't delete, keep for rollback

## What to Do

### Step 1: Create EMQX configuration file

Create `compose/emqx/emqx.conf`:

```hocon
## EMQX Configuration for OpsConductor-Pulse
## Replaces Mosquitto — same ports, same TLS, same topic structure

node {
  name = "emqx@127.0.0.1"
  cookie = "${EMQX_NODE_COOKIE}"
}

## ─── LISTENERS ─────────────────────────────────────────

## Internal MQTT (password auth, service accounts)
listeners.tcp.internal {
  bind = "0.0.0.0:1883"
  max_connections = 1024
  enable_authn = true
}

## External MQTT (mutual TLS, device certificates)
listeners.ssl.external {
  bind = "0.0.0.0:8883"
  max_connections = 102400

  ssl_options {
    cacertfile = "/certs/combined-ca.crt"
    certfile   = "/certs/server.crt"
    keyfile    = "/certs/server.key"
    verify     = verify_peer
    fail_if_no_peer_cert = true
    versions   = ["tlsv1.2", "tlsv1.3"]
  }

  # Use certificate CN as the MQTT username
  # CN format: "{tenant_id}/{device_id}"
  peer_cert_as_username = cn
}

## WebSocket (password auth, browser clients)
listeners.ws.websocket {
  bind = "0.0.0.0:9001"
  max_connections = 1024
  websocket.mqtt_path = "/mqtt"
}

## ─── AUTHENTICATION ────────────────────────────────────

## Chain 1: Built-in password database (for service_pulse and internal accounts)
authentication = [
  {
    mechanism = password_based
    backend   = built_in_database
    user_id_type = username
  },
  {
    mechanism = password_based
    backend   = http
    method    = post
    url       = "http://iot-ui:8080/api/v1/internal/mqtt-auth"
    body {
      username   = "${username}"
      client_id  = "${clientid}"
      peer_cert_cn = "${cert_common_name}"
    }
    headers {
      "Content-Type" = "application/json"
      "X-Internal-Auth" = "${MQTT_INTERNAL_AUTH_SECRET}"
    }
    connect_timeout = "5s"
    request_timeout = "5s"
    pool_size = 8
  }
]

## ─── AUTHORIZATION (ACL) ───────────────────────────────

authorization {
  no_match = deny
  deny_action = disconnect

  sources = [
    {
      type = http
      enable = true
      method = post
      url = "http://iot-ui:8080/api/v1/internal/mqtt-acl"
      body {
        username = "${username}"
        topic    = "${topic}"
        action   = "${action}"
        client_id = "${clientid}"
      }
      headers {
        "Content-Type" = "application/json"
        "X-Internal-Auth" = "${MQTT_INTERNAL_AUTH_SECRET}"
      }
      connect_timeout = "5s"
      request_timeout = "5s"
      pool_size = 8
    }
  ]
}

## ─── RATE LIMITING ─────────────────────────────────────

## Per-client publish rate limit
listeners.ssl.external {
  messages_rate = "10/s"
  bytes_rate    = "100KB/s"
}

## ─── DASHBOARD ─────────────────────────────────────────

dashboard {
  listeners.http {
    bind = "0.0.0.0:18083"
  }
  default_username = "admin"
  default_password = "${EMQX_DASHBOARD_PASSWORD}"
}

## ─── LOGGING ───────────────────────────────────────────

log {
  console {
    enable = true
    level  = warning
  }
}
```

**Note:** EMQX config syntax is HOCON. The exact structure depends on the EMQX version (5.x). Read the EMQX 5.x documentation to verify the config keys. Some settings may need to be in separate files or set via environment variables. The structure above is directional — verify against `emqx/emqx:5.x` container docs.

### Step 2: Replace Mosquitto with EMQX in docker-compose.yml

Replace the `mqtt` service (lines 2-14):

```yaml
  mqtt:
    image: emqx/emqx:5.8  # Use latest 5.x stable
    container_name: iot-mqtt
    environment:
      EMQX_NODE_COOKIE: "${EMQX_NODE_COOKIE:-emqx_pulse_secret}"
      EMQX_DASHBOARD_PASSWORD: "${EMQX_DASHBOARD_PASSWORD:-admin123}"
      MQTT_INTERNAL_AUTH_SECRET: "${MQTT_INTERNAL_AUTH_SECRET}"
    ports:
      - "8883:8883"   # Device mTLS
      - "9001:9001"   # WebSocket
      - "18083:18083"  # EMQX Dashboard
    volumes:
      - ./emqx/emqx.conf:/opt/emqx/etc/emqx.conf:ro
      - ./mosquitto/certs:/certs:ro      # Reuse existing cert directory
      - emqx-data:/opt/emqx/data
    healthcheck:
      test: ["CMD", "emqx", "ctl", "status"]
      interval: 10s
      timeout: 5s
      retries: 12
      start_period: 15s
    restart: unless-stopped
```

Add the `emqx-data` volume to the volumes section:

```yaml
volumes:
  emqx-data:
  # ... existing volumes ...
```

**Note:** Port 1883 is NOT exposed externally — it's only accessible on the Docker network (same as Mosquitto). Only 8883 (device TLS), 9001 (WebSocket), and 18083 (dashboard) are published.

### Step 3: Create the service_pulse internal user

EMQX's built-in database needs the `service_pulse` user created. This can be done via the dashboard or CLI after first startup:

```bash
# After EMQX starts, create the internal service account
docker exec iot-mqtt emqx ctl admins add service_pulse "${MQTT_ADMIN_PASSWORD}"
# Or via the REST API:
curl -u "admin:${EMQX_DASHBOARD_PASSWORD}" -X POST \
  http://localhost:18083/api/v5/authentication/password_based%3Abuilt_in_database/users \
  -H "Content-Type: application/json" \
  -d '{"user_id":"service_pulse","password":"'"${MQTT_ADMIN_PASSWORD}"'"}'
```

Consider adding this to the migrator service or a one-time init container.

### Step 4: Update .env / .env.example

Add new env vars:

```bash
EMQX_NODE_COOKIE=emqx_pulse_secret
EMQX_DASHBOARD_PASSWORD=changeme
MQTT_INTERNAL_AUTH_SECRET=changeme_auth_secret
```

### Step 5: Update ingest service connection

The ingest service environment in docker-compose.yml doesn't need to change — it still connects to `iot-mqtt:1883` with `service_pulse` credentials. EMQX accepts the same MQTT 3.1.1 protocol.

The only potential change: if EMQX requires different TLS settings on port 1883 (check if internal listener uses TLS). If internal listener is plain TCP, remove `MQTT_CA_CERT` and `MQTT_TLS_INSECURE` from the ingest service env. If internal listener uses TLS, keep them.

## Important Notes

- **Cert reuse:** The same TLS certificates work — EMQX uses the same `server.crt`, `server.key`, and `combined-ca.crt` files
- **Topic structure unchanged:** `tenant/+/device/+/+` — EMQX understands standard MQTT wildcards
- **Rollback:** Keep the `compose/mosquitto/` directory. To rollback, just swap the docker-compose service definition back to Mosquitto
- **Dashboard access:** EMQX dashboard at `http://localhost:18083` provides broker monitoring, client connections, topic metrics — much richer than Mosquitto's log-only observability
- **EMQX version:** Use 5.x (latest stable). The config format changed significantly between 4.x and 5.x
- **Resource usage:** EMQX uses more RAM than Mosquitto (~200MB base vs ~10MB). This is expected for the feature set

## Verification

```bash
# EMQX is healthy
docker compose up -d mqtt
docker compose exec mqtt emqx ctl status

# Dashboard accessible
curl -s http://localhost:18083/api/v5/status

# Internal MQTT works
mosquitto_pub -h localhost -p 1883 -u service_pulse -P "$MQTT_ADMIN_PASSWORD" \
  -t "test/ping" -m "pong" 2>&1
```
