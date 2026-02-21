# Phase 112 — Mosquitto Config: Auth + TLS + ACL

## Step 1: Find current Mosquitto config

```bash
find compose/ -name "mosquitto.conf" -o -name "acl.conf" | head -5
ls compose/mosquitto/
```

Read the existing `mosquitto.conf` and `acl.conf` files.

## Step 2: Replace mosquitto.conf

Overwrite the existing `mosquitto.conf` with:

```conf
# mosquitto.conf — OpsConductor-Pulse
# Auth required. TLS on port 8883. Plaintext 1883 internal only.

# ── Logging ──────────────────────────────────────────────────────────────────
log_dest stdout
log_type error
log_type warning
log_type notice
log_timestamp true

# ── Persistence ──────────────────────────────────────────────────────────────
persistence true
persistence_location /mosquitto/data/

# ── Internal plaintext listener (Docker network only, NOT exposed to host) ───
listener 1883
allow_anonymous false
password_file /mosquitto/config/passwd

# ── TLS listener (external devices) ──────────────────────────────────────────
listener 8883
allow_anonymous false
password_file /mosquitto/config/passwd
cafile /mosquitto/certs/ca.crt
certfile /mosquitto/certs/server.crt
keyfile /mosquitto/certs/server.key
tls_version tlsv1.2

# ── WebSocket TLS listener ────────────────────────────────────────────────────
listener 9001
protocol websockets
allow_anonymous false
password_file /mosquitto/config/passwd
cafile /mosquitto/certs/ca.crt
certfile /mosquitto/certs/server.crt
keyfile /mosquitto/certs/server.key

# ── ACL ───────────────────────────────────────────────────────────────────────
acl_file /mosquitto/config/acl.conf
```

## Step 3: Replace acl.conf

```conf
# acl.conf — OpsConductor-Pulse topic access control
#
# Username format:
#   Platform services:  service:pulse
#   Devices:            device:{tenant_id}:{device_id}
#
# service:pulse can publish/subscribe to all topics (needed for ingest and ui services)
# device credentials are restricted to their own tenant/device topics

# ── Platform service account ──────────────────────────────────────────────────
user service:pulse
topic readwrite #

# ── Device accounts ───────────────────────────────────────────────────────────
# Pattern: device:{tenant_id}:{device_id}
# Devices can publish telemetry and shadow/reported, subscribe to shadow/desired,
# jobs notifications, and commands topics.
#
# Mosquitto ACL supports %u (username) but not sub-field extraction.
# The pattern below grants access to all tenant/+/device/+/... topics for
# any authenticated device user. Per-tenant isolation is enforced at the
# application layer (ingest_iot validates tenant_id from topic matches token).
#
# For strict per-device ACL, use a dynamic security plugin or an auth plugin.
# This static ACL provides authentication (no anonymous) with broad topic
# access — sufficient for Phase 112.

pattern readwrite tenant/%u/#

# Allow device to publish telemetry
pattern write tenant/+/device/+/telemetry/#
pattern write tenant/+/device/+/shadow/reported
pattern write tenant/+/device/+/commands/ack

# Allow device to subscribe to inbound topics
pattern read tenant/+/device/+/shadow/desired
pattern read tenant/+/device/+/commands
pattern read tenant/+/device/+/jobs/#
```

**Note on ACL limitation:** Mosquitto's static ACL cannot enforce that
`device:tenant-a:dev-001` can ONLY access `tenant/tenant-a/device/dev-001/*`
topics. The `%u` pattern substitutes the full username, not sub-fields.
Full per-device topic isolation requires the Mosquitto dynamic security plugin
or an external auth plugin. For Phase 112, authentication (no anonymous) plus
application-layer tenant validation is the baseline. Document this as a
known limitation.

## Step 4: Generate TLS certificates for development

For development (Docker compose), use self-signed certs. Create
`compose/mosquitto/certs/` directory and generate certs:

```bash
mkdir -p compose/mosquitto/certs
cd compose/mosquitto/certs

# Generate CA key and certificate
openssl genrsa -out ca.key 4096
openssl req -new -x509 -days 1826 -key ca.key -out ca.crt \
  -subj "/CN=OpsConductor-Pulse-CA/O=OpsConductor/C=US"

# Generate server key and CSR
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr \
  -subj "/CN=iot-mqtt/O=OpsConductor/C=US"

# Sign server cert with CA
openssl x509 -req -days 730 -in server.csr \
  -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out server.crt

# Verify
openssl verify -CAfile ca.crt server.crt
```

Add certs to `.gitignore` (private keys must not be committed):
```
compose/mosquitto/certs/*.key
compose/mosquitto/certs/*.csr
compose/mosquitto/certs/*.srl
```

The `ca.crt` and `server.crt` (public certs) CAN be committed — they are
not secrets. The `ca.crt` needs to be distributed to devices that connect
on port 8883.

## Step 5: Update docker-compose.yml for new ports and cert volume

```yaml
  mqtt:
    image: eclipse-mosquitto:2.0.18
    container_name: iot-mqtt
    ports:
      - "8883:8883"    # TLS — exposed to host/internet
      - "9001:9001"    # WebSocket TLS — exposed to host
      # 1883 NOT exposed to host — internal Docker network only
    volumes:
      - ../compose/mosquitto/mosquitto.conf:/mosquitto/config/mosquitto.conf:ro
      - ../compose/mosquitto/acl.conf:/mosquitto/config/acl.conf:ro
      - ../compose/mosquitto/passwd:/mosquitto/config/passwd:ro
      - ../compose/mosquitto/certs:/mosquitto/certs:ro
      - mosquitto-data:/mosquitto/data
    networks:
      - iot-network
```

Add `mosquitto-data` to the named volumes section:
```yaml
volumes:
  mosquitto-data:
```
