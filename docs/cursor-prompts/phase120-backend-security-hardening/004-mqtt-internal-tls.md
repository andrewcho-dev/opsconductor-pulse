# 004: MQTT Internal TLS

## Context

The Mosquitto broker configuration (`compose/mosquitto/mosquitto.conf`) has three listeners:

- **Port 1883** (lines 15-17): Internal plaintext listener. `allow_anonymous false`, password auth only. No TLS.
- **Port 8883** (lines 19-26): External TLS listener for devices. Uses `ca.crt`, `server.crt`, `server.key`.
- **Port 9001** (lines 28-36): WebSocket TLS listener. Uses same certs as 8883.

The internal listener on port 1883 carries production telemetry over the Docker network without encryption. While Docker network traffic is typically isolated, defense-in-depth requires TLS for all MQTT traffic.

The CA and server certificates already exist in `compose/mosquitto/certs/`:
- `ca.crt` -- CA certificate
- `ca.key` -- CA private key
- `server.crt` -- server certificate
- `server.key` -- server private key
- `server.csr` -- certificate signing request

The internal services that connect to MQTT on port 1883:
1. **ingest_iot** (`services/ingest_iot/ingest.py`, line 1369-1374): paho-mqtt `client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)`. Env: `MQTT_HOST=iot-mqtt`, `MQTT_PORT=1883`.
2. **ui_iot MQTT sender** (`services/ui_iot/services/mqtt_sender.py`, lines 50-56): paho-mqtt `client.connect(host, port, keepalive=timeout)`. Uses `MQTT_BROKER_URL=mqtt://iot-mqtt:1883`.

The evaluator and dispatcher services do NOT connect to MQTT directly (confirmed by grep -- no mqtt imports).

## Step 1: Update Mosquitto Config for Internal TLS

### File: `compose/mosquitto/mosquitto.conf`

Change the internal listener (port 1883) to require TLS using the same certs as the external listener. Since these are internal services, they can use the same CA.

```conf
# BEFORE (lines 14-17):
# Internal plaintext listener (Docker network only)
listener 1883
allow_anonymous false
password_file /mosquitto/passwd/passwd

# AFTER:
# Internal TLS listener (Docker network services)
listener 1883
allow_anonymous false
password_file /mosquitto/passwd/passwd
cafile /mosquitto/certs/ca.crt
certfile /mosquitto/certs/server.crt
keyfile /mosquitto/certs/server.key
tls_version tlsv1.2
```

The full file should look like:

```conf
# mosquitto.conf -- OpsConductor-Pulse
# Auth required. TLS on all listeners.

log_dest stdout
log_type error
log_type warning
log_type notice
log_timestamp true

persistence true
persistence_location /mosquitto/data/
per_listener_settings true

# Internal TLS listener (Docker network services)
listener 1883
allow_anonymous false
password_file /mosquitto/passwd/passwd
cafile /mosquitto/certs/ca.crt
certfile /mosquitto/certs/server.crt
keyfile /mosquitto/certs/server.key
tls_version tlsv1.2

# TLS listener (external devices)
listener 8883
allow_anonymous false
password_file /mosquitto/passwd/passwd
cafile /mosquitto/certs/ca.crt
certfile /mosquitto/certs/server.crt
keyfile /mosquitto/certs/server.key
tls_version tlsv1.2

# WebSocket TLS listener
listener 9001
protocol websockets
allow_anonymous false
password_file /mosquitto/passwd/passwd
cafile /mosquitto/certs/ca.crt
certfile /mosquitto/certs/server.crt
keyfile /mosquitto/certs/server.key

acl_file /mosquitto/config/acl.conf
```

## Step 2: Update Ingest Service MQTT Connection

### File: `services/ingest_iot/ingest.py`

**Lines 1369-1374**: The paho-mqtt client needs TLS configuration before connecting.

```python
# BEFORE (lines 1369-1374):
client = mqtt.Client()
if MQTT_USERNAME and MQTT_PASSWORD:
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
client.on_connect = self.on_connect
client.on_message = self.on_message
client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)

# AFTER:
client = mqtt.Client()
if MQTT_USERNAME and MQTT_PASSWORD:
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

# Enable TLS for internal MQTT connection
mqtt_ca_cert = os.getenv("MQTT_CA_CERT", "/mosquitto/certs/ca.crt")
if os.path.exists(mqtt_ca_cert):
    import ssl
    client.tls_set(
        ca_certs=mqtt_ca_cert,
        tls_version=ssl.PROTOCOL_TLSv1_2,
    )
    # For internal Docker network: server cert CN may not match hostname
    mqtt_tls_insecure = os.getenv("MQTT_TLS_INSECURE", "false").lower() == "true"
    if mqtt_tls_insecure:
        client.tls_insecure_set(True)

client.on_connect = self.on_connect
client.on_message = self.on_message
client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
```

Add the `ssl` import near the top of the file if not already present (check existing imports). The `os` import is already at line 2.

Also add a constant near the existing MQTT constants (around line 27-31):
```python
MQTT_CA_CERT = os.getenv("MQTT_CA_CERT", "/mosquitto/certs/ca.crt")
```

## Step 3: Update UI IoT MQTT Sender

### File: `services/ui_iot/services/mqtt_sender.py`

**Lines 50-56**: The `_publish_blocking()` function inside `publish_alert()` creates a paho-mqtt client and connects without TLS.

```python
# BEFORE (lines 50-56):
def _publish_blocking() -> None:
    mqtt_username = os.getenv("MQTT_USERNAME")
    mqtt_password = os.getenv("MQTT_PASSWORD")
    client = mqtt.Client()
    if mqtt_username and mqtt_password:
        client.username_pw_set(mqtt_username, mqtt_password)
    client.connect(host, port, keepalive=timeout)

# AFTER:
def _publish_blocking() -> None:
    mqtt_username = os.getenv("MQTT_USERNAME")
    mqtt_password = os.getenv("MQTT_PASSWORD")
    mqtt_ca_cert = os.getenv("MQTT_CA_CERT", "/mosquitto/certs/ca.crt")
    client = mqtt.Client()
    if mqtt_username and mqtt_password:
        client.username_pw_set(mqtt_username, mqtt_password)

    # Enable TLS if CA cert is available
    if os.path.exists(mqtt_ca_cert):
        import ssl
        client.tls_set(
            ca_certs=mqtt_ca_cert,
            tls_version=ssl.PROTOCOL_TLSv1_2,
        )
        mqtt_tls_insecure = os.getenv("MQTT_TLS_INSECURE", "false").lower() == "true"
        if mqtt_tls_insecure:
            client.tls_insecure_set(True)

    client.connect(host, port, keepalive=timeout)
```

## Step 4: Update Docker Compose Environment and Volumes

### File: `compose/docker-compose.yml`

The cert directory is already mounted into the mosquitto container at line 11:
```yaml
- ./mosquitto/certs:/mosquitto/certs
```

The services that connect to MQTT need the CA cert available. Add a volume mount for the cert directory to the ingest and ui_iot services, plus the env var.

**For the `ingest` service** (around line 82-86):

Add to `volumes`:
```yaml
- ./mosquitto/certs/ca.crt:/mosquitto/certs/ca.crt:ro
```

Add to `environment`:
```yaml
MQTT_CA_CERT: "/mosquitto/certs/ca.crt"
MQTT_TLS_INSECURE: "true"  # Internal Docker network, CN may not match
```

**For the `ui` service** (the ui_iot service, around line 300-370):

Add to `volumes`:
```yaml
- ./mosquitto/certs/ca.crt:/mosquitto/certs/ca.crt:ro
```

Add to `environment`:
```yaml
MQTT_CA_CERT: "/mosquitto/certs/ca.crt"
MQTT_TLS_INSECURE: "true"
```

**Note on `MQTT_TLS_INSECURE`**: This flag allows the client to skip hostname verification. In the Docker network, the server cert may have a CN/SAN that does not match the Docker service hostname (`iot-mqtt`). For production, the proper fix is to regenerate the server cert with `iot-mqtt` as a SAN. For now, `MQTT_TLS_INSECURE=true` maintains backward compatibility while still encrypting the traffic.

**Recommended follow-up** (not in scope for this phase): Regenerate `server.crt` with `iot-mqtt` as a Subject Alternative Name, then set `MQTT_TLS_INSECURE=false`.

## Step 5: Verify Server Certificate Covers `iot-mqtt` Hostname

Check if the existing server certificate already has `iot-mqtt` as a SAN:

```bash
openssl x509 -in compose/mosquitto/certs/server.crt -text -noout | grep -A2 "Subject Alternative Name"
```

If `iot-mqtt` is NOT listed, the `MQTT_TLS_INSECURE=true` env var is required. If it IS listed, set `MQTT_TLS_INSECURE=false` or remove the env var.

If you need to regenerate the cert with the correct SAN:

```bash
cd compose/mosquitto/certs

# Create OpenSSL config with SAN
cat > server.cnf << 'EOF'
[req]
default_bits = 2048
prompt = no
distinguished_name = dn
req_extensions = v3_req

[dn]
CN = iot-mqtt

[v3_req]
subjectAltName = DNS:iot-mqtt,DNS:localhost,IP:127.0.0.1
EOF

# Generate new CSR and sign with existing CA
openssl req -new -key server.key -out server.csr -config server.cnf
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out server.crt -days 3650 -extensions v3_req -extfile server.cnf
```

## Verification

```bash
# 1. Validate compose config
docker compose -f compose/docker-compose.yml config --quiet
# Should exit 0 with no errors

# 2. Restart the stack
docker compose -f compose/docker-compose.yml down
docker compose -f compose/docker-compose.yml up -d

# 3. Check mosquitto started without errors
docker compose -f compose/docker-compose.yml logs mqtt | tail -20
# Should show "Opening ipv4 listen socket on port 1883" and "Opening ipv4 listen socket on port 8883"
# No "Error: Unable to load" messages

# 4. Test TLS connection from inside the network
docker compose -f compose/docker-compose.yml exec mqtt \
  mosquitto_pub -h localhost -p 1883 \
  --cafile /mosquitto/certs/ca.crt \
  -u service_pulse -P "$MQTT_ADMIN_PASSWORD" \
  -t "test/tls" -m "hello"
# Should succeed

# 5. Verify plaintext connection is rejected
docker compose -f compose/docker-compose.yml exec mqtt \
  mosquitto_pub -h localhost -p 1883 \
  -u service_pulse -P "$MQTT_ADMIN_PASSWORD" \
  -t "test/tls" -m "hello"
# Should fail (no TLS)

# 6. Verify ingest service can still receive MQTT messages
# Send a test telemetry message and check ingest logs
docker compose -f compose/docker-compose.yml logs ingest --tail 20

# 7. Verify ui_iot MQTT sender works
# Trigger a shadow update or command that publishes via MQTT
# Check for "shadow_desired_published" in ui logs
```
