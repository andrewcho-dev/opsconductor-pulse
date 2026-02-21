# Task 002 -- Mutual TLS MQTT Authentication

## Goal

Configure Mosquitto to require client certificates on port 8883, use the certificate CN as the MQTT username, set up ACL rules for CN-based topic isolation, and update ingest_iot to validate certificate-authenticated connections against the `device_certificates` table.

## Commit scope

One commit: `feat: enable mutual TLS on MQTT 8883 with cert-based device auth`

---

## Step 1: Update Mosquitto Configuration

Edit file: `compose/mosquitto/mosquitto.conf`

The current 8883 listener block (lines 20-26) looks like this:

```
# TLS listener (external devices)
listener 8883
allow_anonymous false
password_file /mosquitto/passwd/passwd
cafile /mosquitto/certs/ca.crt
certfile /mosquitto/certs/server.crt
keyfile /mosquitto/certs/server.key
tls_version tlsv1.2
```

Replace it with the following. Key changes:
1. `require_certificate true` -- devices MUST present a client cert
2. `cafile` points to the **Device CA** (for validating client certs)
3. Add the **server TLS CA** separately for the server cert chain
4. `use_identity_as_username true` -- cert CN becomes MQTT username
5. Remove `password_file` on this listener (cert replaces password auth)

```
# TLS listener (external devices -- mutual TLS)
listener 8883
allow_anonymous false
cafile /mosquitto/certs/device-ca.crt
certfile /mosquitto/certs/server.crt
keyfile /mosquitto/certs/server.key
tls_version tlsv1.2
require_certificate true
use_identity_as_username true
```

**Important considerations:**

- The `cafile` here serves double duty: it validates the client cert AND is the CA chain for the server cert. If the server cert is signed by a different CA than the device CA, you need to create a combined CA bundle file:
  ```bash
  cat compose/mosquitto/certs/ca.crt compose/mosquitto/certs/device-ca.crt > compose/mosquitto/certs/combined-ca.crt
  ```
  Then use `cafile /mosquitto/certs/combined-ca.crt` instead. The script in Task 001 can do this automatically.

- Alternatively, Mosquitto 2.x supports separate `cafile` (for server cert chain) and a separate mechanism. The simplest approach for our setup: if the server cert is self-signed with `ca.crt`, concatenate both CAs into a single bundle file.

- For now, if device-ca.crt is the only CA needed for client validation and server cert validation is handled by the client, use `cafile /mosquitto/certs/device-ca.crt`. But verify your server cert chain. If it fails, use the combined approach.

**Create the combined CA bundle** -- add this step to `scripts/generate_device_ca.sh` (append at the end before the final echo):

```bash
# Create combined CA bundle for Mosquitto (server CA + device CA)
COMBINED="$CERT_DIR/combined-ca.crt"
cat "$CERT_DIR/ca.crt" "$CA_CERT" > "$COMBINED"
echo "    Combined CA bundle: $COMBINED"
```

Then in `mosquitto.conf`, use:
```
cafile /mosquitto/certs/combined-ca.crt
```

**Add CRL file reference** (will be populated by Task 003):

```
crlfile /mosquitto/certs/device-crl.pem
```

Note: Mosquitto will fail to start if `crlfile` is specified but the file does not exist. Two options:
1. Create an empty/initial CRL in `scripts/generate_device_ca.sh`
2. Only add the `crlfile` directive in Task 003 after the CRL generation is implemented

**Recommended:** Create an initial empty CRL in the CA generation script:

```bash
# Generate initial (empty) CRL
openssl ca -gencrl \
    -keyfile "$CA_KEY" \
    -cert "$CA_CERT" \
    -out "$CERT_DIR/device-crl.pem" \
    -config <(cat <<EOF
[ ca ]
default_ca = CA_default
[ CA_default ]
database = /dev/null
crlnumber = $CERT_DIR/crlnumber
default_md = sha256
default_crl_days = 30
EOF
) 2>/dev/null || true

# If the openssl ca approach fails, use a simpler method:
if [ ! -f "$CERT_DIR/device-crl.pem" ]; then
    # Create a minimal valid CRL using Python + cryptography
    python3 -c "
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from datetime import datetime, timezone, timedelta

ca_key = serialization.load_pem_private_key(open('$CA_KEY','rb').read(), None, default_backend())
ca_cert = x509.load_pem_x509_certificate(open('$CA_CERT','rb').read(), default_backend())
now = datetime.now(timezone.utc)
builder = x509.CertificateRevocationListBuilder()
builder = builder.issuer_name(ca_cert.subject)
builder = builder.last_update(now)
builder = builder.next_update(now + timedelta(days=30))
crl = builder.sign(ca_key, hashes.SHA256(), default_backend())
open('$CERT_DIR/device-crl.pem','wb').write(crl.public_bytes(serialization.Encoding.PEM))
print('Initial empty CRL created')
"
fi
```

The final `mosquitto.conf` 8883 block:

```
# TLS listener (external devices -- mutual TLS)
listener 8883
allow_anonymous false
cafile /mosquitto/certs/combined-ca.crt
certfile /mosquitto/certs/server.crt
keyfile /mosquitto/certs/server.key
tls_version tlsv1.2
require_certificate true
use_identity_as_username true
crlfile /mosquitto/certs/device-crl.pem
```

The 1883 listener remains unchanged (internal Docker network, password-based auth for services).

The 9001 (WebSocket) listener remains unchanged (password-based for UI/web clients).

---

## Step 2: Update ACL Configuration

Edit file: `compose/mosquitto/acl.conf`

The current file (from our codebase read):

```
# acl.conf -- OpsConductor-Pulse topic access control

# Platform service account
user service_pulse
topic readwrite #

# Device accounts
# NOTE: static ACL cannot strictly enforce tenant/device tuple from username
# segments. Application-layer validation in ingest_iot remains in place.
pattern readwrite tenant/%u/#

pattern write tenant/+/device/+/telemetry/#
pattern write tenant/+/device/+/shadow/reported
pattern write tenant/+/device/+/commands/ack

pattern read tenant/+/device/+/shadow/desired
pattern read tenant/+/device/+/commands
pattern read tenant/+/device/+/jobs/#
```

With `use_identity_as_username true`, the MQTT username for cert-authenticated devices will be the CN: `{tenant_id}/{device_id}`. The `%u` substitution in ACL patterns will be this entire CN string.

The existing `pattern readwrite tenant/%u/#` would expand to `tenant/{tenant_id}/{device_id}/#` which does NOT match the topic structure `tenant/{tenant_id}/device/{device_id}/#`.

We need **username-specific** ACL entries. Since the username contains a `/`, the `%u` pattern won't work directly for our topic structure. Mosquitto does not support splitting `%u` on delimiters.

**Solution:** Use a Mosquitto dynamic security plugin or an auth plugin, OR structure the ACL using the `%u` pattern where the topic structure aligns.

**Practical approach for our architecture:**

Since ingest_iot already performs application-layer validation (checking the device exists, is ACTIVE, tenant matches, etc.), the ACL serves as a first layer of defense. The key constraint is: a cert-authenticated device should only be able to publish/subscribe to topics containing its own tenant and device IDs.

**Option A: Accept the looser ACL and rely on ingest_iot** (recommended for simplicity)

Keep the existing patterns. Since `%u = tenant_id/device_id`, the pattern `tenant/%u/#` expands to `tenant/tenant_id/device_id/#` which does not match `tenant/tenant_id/device/device_id/#`. This means the generic pattern will NOT match, which will actually DENY access.

**Option B: Use explicit topic patterns** (required)

We need to add patterns that work with the CN format. The approach:

Replace the ACL file with:

```
# acl.conf -- OpsConductor-Pulse topic access control
#
# Username formats:
#   - Certificate-authenticated (port 8883): CN = "{tenant_id}/{device_id}"
#   - Password-authenticated (port 1883): username = "service_pulse" or device client_id
#
# With use_identity_as_username, %u = full CN for cert devices.
# Since CN contains '/', and topics use 'tenant/{t}/device/{d}/...', we cannot
# use %u directly in topic patterns. Instead, ingest_iot enforces topic isolation.
# ACL provides coarse access control.

# Platform service account (internal, port 1883)
user service_pulse
topic readwrite #

# Certificate-authenticated devices get broad write access to telemetry topics.
# Fine-grained tenant/device isolation is enforced by ingest_iot which parses
# the CN and validates it against the topic.
# The 'pattern' keyword uses %u substitution.
# For cert auth: %u = "tenant_id/device_id"

# Allow cert-authenticated devices to write telemetry
pattern write tenant/+/device/+/telemetry/#
pattern write tenant/+/device/+/shadow/reported
pattern write tenant/+/device/+/commands/ack

# Allow cert-authenticated devices to read commands/shadow/jobs
pattern read tenant/+/device/+/shadow/desired
pattern read tenant/+/device/+/commands
pattern read tenant/+/device/+/jobs/#
```

**Key insight:** The `pattern` rules with `+` wildcards (without `%u`) will match any device publishing to any `tenant/X/device/Y/telemetry/...` topic. The real enforcement happens in ingest_iot, which:
1. Extracts tenant_id/device_id from the MQTT topic
2. Extracts tenant_id/device_id from the MQTT username (which is the cert CN)
3. Validates they match
4. Validates the certificate is ACTIVE in the database

This is the same defense-in-depth pattern already in place (see the NOTE comment in the existing ACL).

---

## Step 3: Update ingest_iot for Certificate Authentication

Edit file: `services/ingest_iot/ingest.py`

### 3a: Add new environment variable

Near the top with other env vars (around line 43-44):

```python
CERT_AUTH_ENABLED = os.getenv("CERT_AUTH_ENABLED", "0") == "1"
```

### 3b: Add certificate auth cache

Add a new cache class (after the existing `DeviceSubscriptionCache` class around line 622):

```python
class CertificateAuthCache:
    """Cache certificate authentication status to avoid DB lookups on every message."""

    def __init__(self, ttl_seconds: int = 300, max_size: int = 50000):
        self.ttl = ttl_seconds
        self.max_size = max_size
        self._cache: dict[str, dict] = {}  # key = "tenant_id/device_id"
        self._lock = asyncio.Lock()

    async def get(self, cn: str) -> dict | None:
        entry = self._cache.get(cn)
        if entry and time.time() < entry["expires_at"]:
            return entry
        return None

    async def put(self, cn: str, has_active_cert: bool) -> None:
        async with self._lock:
            if len(self._cache) >= self.max_size:
                now = time.time()
                self._cache = {k: v for k, v in self._cache.items() if v["expires_at"] > now}
            self._cache[cn] = {
                "has_active_cert": has_active_cert,
                "expires_at": time.time() + self.ttl,
            }

    def invalidate(self, cn: str) -> None:
        self._cache.pop(cn, None)
```

### 3c: Initialize the cache in `Ingestor.__init__`

In the `__init__` method (around line 714):

```python
self.cert_auth_cache = CertificateAuthCache(ttl_seconds=300, max_size=50000)
```

### 3d: Add cert auth validation method to `Ingestor`

```python
async def _validate_cert_auth(self, mqtt_username: str, topic_tenant: str, topic_device: str) -> bool:
    """
    Validate a certificate-authenticated device.
    mqtt_username = cert CN = "{tenant_id}/{device_id}"
    Returns True if auth passes.
    """
    if not mqtt_username or "/" not in mqtt_username:
        return False

    parts = mqtt_username.split("/", 1)
    if len(parts) != 2:
        return False

    cert_tenant, cert_device = parts

    # Verify CN matches the topic
    if cert_tenant != topic_tenant or cert_device != topic_device:
        return False

    # Check cache
    cached = await self.cert_auth_cache.get(mqtt_username)
    if cached is not None:
        return cached["has_active_cert"]

    # DB lookup: does this device have an ACTIVE, non-expired certificate?
    assert self.pool is not None
    async with self.pool.acquire() as conn:
        has_cert = await conn.fetchval(
            """
            SELECT 1 FROM device_certificates
            WHERE tenant_id = $1
              AND device_id = $2
              AND status = 'ACTIVE'
              AND not_after > now()
            LIMIT 1
            """,
            cert_tenant, cert_device,
        )

    result = has_cert is not None
    await self.cert_auth_cache.put(mqtt_username, result)
    return result
```

### 3e: Modify the `on_message` handler

The current `on_message` handler (line 1293) passes `(msg.topic, payload)` to the queue. We need to also pass the MQTT username so the db_worker can check cert auth.

**However**, the paho MQTT client `on_message` callback does not provide the sender's username. The username is available on the Mosquitto broker side, but not in the subscriber's callback.

**Important architectural consideration:** The ingest_iot service subscribes to MQTT topics on port 1883 (internal). It receives messages published by devices on port 8883 (external mTLS). The ingest service does NOT directly know the publisher's certificate CN.

**How Mosquitto handles this:** When `use_identity_as_username true` is set, the CN becomes the MQTT username. But the subscriber (ingest_iot) connecting on port 1883 with its own credentials does NOT receive the publisher's username in the message.

**Solution: The ingest_iot must infer cert authentication from the topic structure.**

Since cert-authenticated devices have their CN = `{tenant_id}/{device_id}` and the topic is `tenant/{tenant_id}/device/{device_id}/{msg_type}`, ingest already extracts tenant_id and device_id from the topic.

The authentication flow changes:

1. **If CERT_AUTH_ENABLED and REQUIRE_TOKEN is False:** Skip token validation for devices that have an ACTIVE certificate in `device_certificates`. If a device has a cert, it was already authenticated by Mosquitto at the TLS layer.

2. **If REQUIRE_TOKEN is True and device has a cert:** The cert-authenticated path bypasses the provision_token check.

**Modify the `db_worker` method** (in the section starting around line 994 where token auth happens):

After the device registry lookup and before the `REQUIRE_TOKEN` check (around line 1095), add:

```python
# Certificate-based authentication bypass
# If the device has an active certificate, Mosquitto already validated
# the client cert at the TLS layer. Skip token validation.
if CERT_AUTH_ENABLED:
    cn = f"{tenant_id}/{device_id}"
    cert_valid = await self._validate_cert_auth(cn, tenant_id, device_id)
    if cert_valid:
        # Device authenticated via client certificate -- skip token check
        log_event(
            logger,
            "cert_auth_accepted",
            level="DEBUG",
            tenant_id=tenant_id,
            device_id=device_id,
        )
        # Jump past the REQUIRE_TOKEN block
        # (use a flag variable or restructure the if/else)
```

**Restructured auth logic:** Introduce a `device_authenticated` flag:

```python
device_authenticated = False

# Certificate-based authentication (if enabled)
if CERT_AUTH_ENABLED and not device_authenticated:
    cn = f"{tenant_id}/{device_id}"
    has_active_cert = await self._validate_cert_auth(cn, tenant_id, device_id)
    if has_active_cert:
        device_authenticated = True

# Token-based authentication (fallback / legacy)
if REQUIRE_TOKEN and not device_authenticated:
    expected = reg["provision_token_hash"]
    if expected is None:
        await self._insert_quarantine(topic, tenant_id, site_id, device_id, msg_type, "TOKEN_NOT_SET_IN_REGISTRY", payload, event_ts)
        continue
    if token is None:
        await self._insert_quarantine(topic, tenant_id, site_id, device_id, msg_type, "TOKEN_MISSING", payload, event_ts)
        continue
    if token_hash != expected:
        await self._insert_quarantine(topic, tenant_id, site_id, device_id, msg_type, "TOKEN_INVALID", payload, event_ts)
        continue
    device_authenticated = True

# If neither cert nor token auth passed
if not device_authenticated and REQUIRE_TOKEN:
    await self._insert_quarantine(topic, tenant_id, site_id, device_id, msg_type, "AUTH_FAILED", payload, event_ts)
    continue
```

This block replaces the existing `if REQUIRE_TOKEN:` block (lines 1095-1105). Insert the cert check before it and wrap both in the flag pattern.

---

## Step 4: Docker Compose Volume Mount

Edit file: `compose/docker-compose.yml`

The existing mqtt service volume mount (line 10-13):

```yaml
volumes:
  - ./mosquitto/mosquitto.conf:/mosquitto/config/mosquitto.conf
  - ./mosquitto/acl.conf:/mosquitto/config/acl.conf
  - ./mosquitto/certs:/mosquitto/certs
  - mosquitto-passwd:/mosquitto/passwd
  - mosquitto-data:/mosquitto/data
```

The `./mosquitto/certs:/mosquitto/certs` mount already maps the entire certs directory, so `device-ca.crt`, `device-ca.key`, `combined-ca.crt`, and `device-crl.pem` will all be available inside the container automatically. No additional volumes needed.

**However**, for the CRL file to be updateable at runtime (by ops_worker), we need the certs directory to be a shared volume or bind mount that ops_worker can also write to.

Add a named volume or ensure the bind mount is writable:

The existing bind mount `./mosquitto/certs:/mosquitto/certs` is a host directory bind -- ops_worker can write to the host path. But ops_worker runs in a separate container.

**Add the certs volume to ops_worker** in docker-compose.yml:

Find the ops_worker service and add:

```yaml
  ops-worker:
    # ... existing config ...
    volumes:
      # ... existing volumes ...
      - ./mosquitto/certs:/mosquitto/certs  # For CRL updates
```

**Add the CERT_AUTH_ENABLED env var to the ingest service:**

```yaml
  ingest:
    environment:
      # ... existing env vars ...
      CERT_AUTH_ENABLED: "1"
```

Also add the `DEVICE_CA_CERT_PATH` and `DEVICE_CA_KEY_PATH` env vars to the ui_iot service for the certificate generation API:

```yaml
  ui:
    environment:
      # ... existing env vars ...
      DEVICE_CA_CERT_PATH: "/mosquitto/certs/device-ca.crt"
      DEVICE_CA_KEY_PATH: "/mosquitto/certs/device-ca.key"
    volumes:
      # ... existing volumes ...
      - ./mosquitto/certs:/mosquitto/certs:ro  # Read-only access to device CA
```

---

## Step 5: Create a Test Script

Create file: `scripts/test_mtls_device.sh` (for manual verification):

```bash
#!/usr/bin/env bash
set -euo pipefail

# Test script: generate a device cert and test mTLS MQTT connection
# Prerequisites:
#   - Device CA generated (./scripts/generate_device_ca.sh)
#   - Mosquitto running with mTLS config
#   - Device registered in DB

CERT_DIR="$(dirname "$0")/../compose/mosquitto/certs"
TENANT_ID="${1:-tenant-test}"
DEVICE_ID="${2:-DEVICE-001}"
MQTT_HOST="${3:-localhost}"
MQTT_PORT="${4:-8883}"

WORK_DIR=$(mktemp -d)
trap "rm -rf $WORK_DIR" EXIT

CN="${TENANT_ID}/${DEVICE_ID}"

echo "==> Generating device key and CSR for CN=${CN}..."
openssl genrsa -out "$WORK_DIR/device.key" 2048

openssl req -new \
    -key "$WORK_DIR/device.key" \
    -out "$WORK_DIR/device.csr" \
    -subj "/CN=${CN}/O=OpsConductor Pulse"

echo "==> Signing with Device CA..."
openssl x509 -req \
    -in "$WORK_DIR/device.csr" \
    -CA "$CERT_DIR/device-ca.crt" \
    -CAkey "$CERT_DIR/device-ca.key" \
    -CAcreateserial \
    -out "$WORK_DIR/device.crt" \
    -days 365 \
    -sha256

echo "==> Device certificate:"
openssl x509 -in "$WORK_DIR/device.crt" -noout -subject -issuer -dates

echo ""
echo "==> Testing MQTT publish with mTLS..."
mosquitto_pub \
    --cafile "$CERT_DIR/combined-ca.crt" \
    --cert "$WORK_DIR/device.crt" \
    --key "$WORK_DIR/device.key" \
    -h "$MQTT_HOST" \
    -p "$MQTT_PORT" \
    -t "tenant/${TENANT_ID}/device/${DEVICE_ID}/telemetry" \
    -m "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"site_id\":\"site-1\",\"metrics\":{\"temp\":22.5}}" \
    -d

echo ""
echo "==> Publish complete. Check ingest_iot logs for acceptance/rejection."
```

---

## Verification

```bash
# 1. Verify mosquitto.conf is correct
cat compose/mosquitto/mosquitto.conf

# 2. Restart Mosquitto
docker compose -f compose/docker-compose.yml restart mqtt

# 3. Check Mosquitto logs for startup (should load certs without error)
docker compose -f compose/docker-compose.yml logs mqtt --tail 20

# 4. Test: connection WITHOUT client cert should be rejected
mosquitto_pub \
  --cafile compose/mosquitto/certs/combined-ca.crt \
  -h localhost -p 8883 \
  -t "test/topic" -m "hello" 2>&1 || echo "EXPECTED: Connection refused (no client cert)"

# 5. Test: connection WITH valid client cert should succeed
# (use test script or API-generated cert from Task 001)
chmod +x scripts/test_mtls_device.sh
./scripts/test_mtls_device.sh tenant-test DEVICE-001

# 6. Verify ingest_iot received and processed the message
docker compose -f compose/docker-compose.yml logs ingest --tail 20

# 7. Verify port 1883 still works for internal services (password auth)
docker compose -f compose/docker-compose.yml exec ingest \
  mosquitto_pub -h iot-mqtt -p 1883 -u service_pulse -P "$MQTT_PASSWORD" \
  -t "test/internal" -m "internal test"
```
