# Task 001 -- Certificate Infrastructure

## Goal

Create the database table for device certificates, a script to generate the internal Device CA, and REST API routes for certificate CRUD (upload, list, revoke, generate, CA bundle download).

## Commit scope

One commit: `feat: add device certificate infrastructure (table, CA, REST API)`

---

## Step 1: Database Migration

Create file: `db/migrations/081_device_certificates.sql`

Follow the pattern established in `db/migrations/064_device_api_tokens.sql` for RLS and FK setup.

```sql
BEGIN;

CREATE TABLE IF NOT EXISTS device_certificates (
    id              SERIAL PRIMARY KEY,
    tenant_id       TEXT NOT NULL,
    device_id       TEXT NOT NULL,
    cert_pem        TEXT NOT NULL,
    fingerprint_sha256 VARCHAR(64) NOT NULL UNIQUE,
    common_name     VARCHAR(200) NOT NULL,
    issuer          VARCHAR(200) NOT NULL,
    serial_number   VARCHAR(100) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
                    CHECK (status IN ('ACTIVE', 'REVOKED', 'EXPIRED')),
    not_before      TIMESTAMPTZ NOT NULL,
    not_after       TIMESTAMPTZ NOT NULL,
    revoked_at      TIMESTAMPTZ,
    revoked_reason  VARCHAR(100),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Foreign key to device_registry
ALTER TABLE device_certificates
    DROP CONSTRAINT IF EXISTS fk_device_certificates_device;
ALTER TABLE device_certificates
    ADD CONSTRAINT fk_device_certificates_device
    FOREIGN KEY (tenant_id, device_id)
    REFERENCES device_registry(tenant_id, device_id)
    ON DELETE CASCADE;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_device_certificates_tenant_device
    ON device_certificates(tenant_id, device_id);
CREATE INDEX IF NOT EXISTS idx_device_certificates_fingerprint
    ON device_certificates(fingerprint_sha256);
CREATE INDEX IF NOT EXISTS idx_device_certificates_status_expiry
    ON device_certificates(status, not_after);
CREATE INDEX IF NOT EXISTS idx_device_certificates_tenant
    ON device_certificates(tenant_id);

-- RLS
ALTER TABLE device_certificates ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS device_certificates_tenant_isolation ON device_certificates;
CREATE POLICY device_certificates_tenant_isolation
    ON device_certificates
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

-- Operator bypass (read-only for fleet overview)
DROP POLICY IF EXISTS device_certificates_operator_read ON device_certificates;
CREATE POLICY device_certificates_operator_read
    ON device_certificates
    FOR SELECT
    TO pulse_operator
    USING (true);

COMMIT;
```

---

## Step 2: Device CA Generation Script

Create file: `scripts/generate_device_ca.sh`

Make it executable (`chmod +x`). This generates a **separate** CA used only to sign device client certificates. It must NOT overwrite the existing server TLS CA at `compose/mosquitto/certs/ca.crt`.

```bash
#!/usr/bin/env bash
set -euo pipefail

# Generate a Device CA for signing IoT device client certificates.
# Output: compose/mosquitto/certs/device-ca.crt and device-ca.key
# This CA is SEPARATE from the server TLS CA (ca.crt).

CERT_DIR="$(dirname "$0")/../compose/mosquitto/certs"
mkdir -p "$CERT_DIR"

CA_KEY="$CERT_DIR/device-ca.key"
CA_CERT="$CERT_DIR/device-ca.crt"
CA_DAYS="${DEVICE_CA_DAYS:-3650}"
CA_SUBJECT="${DEVICE_CA_SUBJECT:-/C=US/ST=CA/O=OpsConductor/OU=IoT/CN=OpsConductor Pulse Device CA}"

if [ -f "$CA_CERT" ] && [ -f "$CA_KEY" ]; then
    echo "Device CA already exists at $CA_CERT -- skipping generation."
    echo "To regenerate, remove $CA_CERT and $CA_KEY first."
    exit 0
fi

echo "==> Generating Device CA private key..."
openssl genrsa -out "$CA_KEY" 4096

echo "==> Generating Device CA certificate (valid $CA_DAYS days)..."
openssl req -new -x509 \
    -key "$CA_KEY" \
    -out "$CA_CERT" \
    -days "$CA_DAYS" \
    -subj "$CA_SUBJECT" \
    -addext "basicConstraints=critical,CA:TRUE,pathlen:0" \
    -addext "keyUsage=critical,keyCertSign,cRLSign"

echo "==> Device CA created:"
echo "    Certificate: $CA_CERT"
echo "    Private key: $CA_KEY"
echo ""
echo "    Fingerprint:"
openssl x509 -in "$CA_CERT" -noout -fingerprint -sha256
echo ""
echo "    Subject:"
openssl x509 -in "$CA_CERT" -noout -subject
echo ""
echo "NOTE: In production, use an external CA and set DEVICE_CA_CERT_PATH / DEVICE_CA_KEY_PATH"
echo "      environment variables instead of using this self-signed CA."
```

---

## Step 3: Certificate API Routes

Create file: `services/ui_iot/routes/certificates.py`

Use the same patterns as `services/ui_iot/routes/devices.py`:
- Import from `routes.customer` using `from routes.customer import *`
- Use `APIRouter(prefix="/customer", tags=["certificates"], dependencies=[Depends(JWTBearer()), Depends(inject_tenant_context), Depends(require_customer)])`
- Use `tenant_connection(pool, tenant_id)` for DB access
- Use `get_tenant_id()` for tenant isolation
- Use `get_db_pool` dependency for the pool

### Environment variables to read

```python
import os

# Path to Device CA cert and key for signing operations
DEVICE_CA_CERT_PATH = os.getenv("DEVICE_CA_CERT_PATH", "/mosquitto/certs/device-ca.crt")
DEVICE_CA_KEY_PATH = os.getenv("DEVICE_CA_KEY_PATH", "/mosquitto/certs/device-ca.key")
```

For local development (running outside Docker), these paths may need to resolve to `compose/mosquitto/certs/device-ca.crt`. The Docker compose mount handles the container path.

### Python cryptography imports

```python
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import hashlib
from datetime import datetime, timezone, timedelta
```

Add `cryptography` to the service's `requirements.txt` if not already present.

### Route 1: `GET /customer/certificates`

List device certificates for the tenant, with optional filters.

```python
@router.get("/certificates")
async def list_certificates(
    device_id: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        conditions = ["tenant_id = $1"]
        params: list = [tenant_id]
        idx = 2

        if device_id:
            conditions.append(f"device_id = ${idx}")
            params.append(device_id)
            idx += 1

        if status:
            status_upper = status.upper()
            if status_upper not in ("ACTIVE", "REVOKED", "EXPIRED"):
                raise HTTPException(400, "Invalid status filter")
            conditions.append(f"status = ${idx}")
            params.append(status_upper)
            idx += 1

        where = " AND ".join(conditions)
        params.extend([limit, offset])

        rows = await conn.fetch(
            f"""
            SELECT id, tenant_id, device_id, fingerprint_sha256, common_name,
                   issuer, serial_number, status, not_before, not_after,
                   revoked_at, revoked_reason, created_at, updated_at
            FROM device_certificates
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT ${idx} OFFSET ${idx + 1}
            """,
            *params,
        )

        total = await conn.fetchval(
            f"SELECT COUNT(*) FROM device_certificates WHERE {where}",
            *params[:-2],  # exclude limit/offset
        )

    return {
        "certificates": [dict(r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
```

### Route 2: `POST /customer/certificates`

Upload/register an existing device certificate (PEM). Parse, validate, store.

```python
class CertificateUpload(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=200)
    cert_pem: str = Field(..., min_length=50)

@router.post("/certificates", status_code=201)
async def upload_certificate(body: CertificateUpload, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()

    # Parse the PEM certificate
    try:
        cert = x509.load_pem_x509_certificate(body.cert_pem.encode(), default_backend())
    except Exception:
        raise HTTPException(400, "Invalid PEM certificate")

    # Extract metadata
    cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
    common_name = cn[0].value if cn else ""
    issuer_cn = cert.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)
    issuer_str = issuer_cn[0].value if issuer_cn else str(cert.issuer)
    serial_hex = format(cert.serial_number, "x")
    fingerprint = cert.fingerprint(hashes.SHA256()).hex()
    not_before = cert.not_valid_before_utc  # Python 3.11+ / cryptography 42+
    not_after = cert.not_valid_after_utc

    # Validate: CN should match tenant_id/device_id pattern
    expected_cn = f"{tenant_id}/{body.device_id}"
    if common_name != expected_cn:
        raise HTTPException(
            400,
            f"Certificate CN '{common_name}' does not match expected '{expected_cn}'"
        )

    # Validate: cert should be signed by trusted Device CA
    try:
        ca_cert_pem = open(DEVICE_CA_CERT_PATH, "rb").read()
        ca_cert = x509.load_pem_x509_certificate(ca_cert_pem, default_backend())
        # Verify signature (raises InvalidSignature on failure)
        ca_cert.public_key().verify(
            cert.signature,
            cert.tbs_certificate_bytes,
            cert.signature_hash_algorithm,
        )
    except FileNotFoundError:
        raise HTTPException(503, "Device CA not configured -- cannot validate certificate")
    except Exception:
        raise HTTPException(400, "Certificate not signed by trusted Device CA")

    # Validate: cert not expired
    now = datetime.now(timezone.utc)
    if now < not_before:
        raise HTTPException(400, "Certificate not yet valid")
    if now > not_after:
        raise HTTPException(400, "Certificate has expired")

    # Validate: device exists
    async with tenant_connection(pool, tenant_id) as conn:
        exists = await conn.fetchval(
            "SELECT 1 FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
            tenant_id, body.device_id,
        )
        if not exists:
            raise HTTPException(404, "Device not found")

        # Check for duplicate fingerprint
        dup = await conn.fetchval(
            "SELECT 1 FROM device_certificates WHERE fingerprint_sha256 = $1",
            fingerprint,
        )
        if dup:
            raise HTTPException(409, "Certificate already registered (duplicate fingerprint)")

        row = await conn.fetchrow(
            """
            INSERT INTO device_certificates
                (tenant_id, device_id, cert_pem, fingerprint_sha256, common_name,
                 issuer, serial_number, status, not_before, not_after)
            VALUES ($1, $2, $3, $4, $5, $6, $7, 'ACTIVE', $8, $9)
            RETURNING id, fingerprint_sha256, common_name, status, not_before, not_after, created_at
            """,
            tenant_id, body.device_id, body.cert_pem, fingerprint, common_name,
            issuer_str, serial_hex, not_before, not_after,
        )

    return dict(row)
```

**Note on signature verification:** The `ca_cert.public_key().verify()` call depends on the key type (RSA vs EC). For RSA, you need:
```python
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding

ca_cert.public_key().verify(
    cert.signature,
    cert.tbs_certificate_bytes,
    asym_padding.PKCS1v15(),
    cert.signature_hash_algorithm,
)
```
Handle both RSA and EC key types with a try/except or isinstance check.

### Route 3: `GET /customer/certificates/{cert_id}`

```python
@router.get("/certificates/{cert_id}")
async def get_certificate(cert_id: int, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            SELECT id, tenant_id, device_id, cert_pem, fingerprint_sha256,
                   common_name, issuer, serial_number, status,
                   not_before, not_after, revoked_at, revoked_reason,
                   created_at, updated_at
            FROM device_certificates
            WHERE id = $1 AND tenant_id = $2
            """,
            cert_id, tenant_id,
        )
    if not row:
        raise HTTPException(404, "Certificate not found")
    return dict(row)
```

### Route 4: `POST /customer/certificates/{cert_id}/revoke`

```python
class RevokeRequest(BaseModel):
    reason: str = Field(default="manual_revocation", max_length=100)

@router.post("/certificates/{cert_id}/revoke")
async def revoke_certificate(cert_id: int, body: RevokeRequest, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            UPDATE device_certificates
            SET status = 'REVOKED',
                revoked_at = now(),
                revoked_reason = $3,
                updated_at = now()
            WHERE id = $1 AND tenant_id = $2 AND status = 'ACTIVE'
            RETURNING id, fingerprint_sha256, status, revoked_at
            """,
            cert_id, tenant_id, body.reason,
        )
    if not row:
        raise HTTPException(404, "Certificate not found or already revoked")
    return dict(row)
```

### Route 5: `GET /customer/ca-bundle`

Download the Device CA certificate (for device provisioning).

```python
@router.get("/ca-bundle")
async def get_ca_bundle():
    try:
        ca_pem = open(DEVICE_CA_CERT_PATH, "r").read()
    except FileNotFoundError:
        raise HTTPException(503, "Device CA not configured")
    return Response(
        content=ca_pem,
        media_type="application/x-pem-file",
        headers={"Content-Disposition": "attachment; filename=device-ca-bundle.pem"},
    )
```

### Route 6: `POST /customer/devices/{device_id}/certificates/generate`

Generate a new device certificate signed by the internal Device CA. Returns the cert PEM + private key (one-time download -- private key is NOT stored).

```python
class CertGenerateRequest(BaseModel):
    validity_days: int = Field(default=365, ge=1, le=3650)

@router.post("/devices/{device_id}/certificates/generate", status_code=201)
async def generate_device_certificate(
    device_id: str,
    body: CertGenerateRequest = CertGenerateRequest(),
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()

    # Verify device exists
    async with tenant_connection(pool, tenant_id) as conn:
        exists = await conn.fetchval(
            "SELECT 1 FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
            tenant_id, device_id,
        )
        if not exists:
            raise HTTPException(404, "Device not found")

    # Load Device CA
    try:
        ca_key_pem = open(DEVICE_CA_KEY_PATH, "rb").read()
        ca_cert_pem = open(DEVICE_CA_CERT_PATH, "rb").read()
        ca_key = serialization.load_pem_private_key(ca_key_pem, password=None, backend=default_backend())
        ca_cert = x509.load_pem_x509_certificate(ca_cert_pem, default_backend())
    except FileNotFoundError:
        raise HTTPException(503, "Device CA not configured -- cannot generate certificates")

    # Generate device key pair
    device_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )

    # Build certificate
    cn = f"{tenant_id}/{device_id}"
    now = datetime.now(timezone.utc)
    not_after = now + timedelta(days=body.validity_days)

    subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, cn),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "OpsConductor Pulse"),
    ])

    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(device_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(not_after)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True, key_encipherment=True,
                content_commitment=False, data_encipherment=False,
                key_agreement=False, key_cert_sign=False,
                crl_sign=False, encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH]),
            critical=False,
        )
    )

    # Sign with CA key
    device_cert = builder.sign(
        private_key=ca_key,
        algorithm=hashes.SHA256(),
        backend=default_backend(),
    )

    # Serialize
    cert_pem = device_cert.public_bytes(serialization.Encoding.PEM).decode()
    key_pem = device_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ).decode()

    # Extract metadata for DB storage
    fingerprint = device_cert.fingerprint(hashes.SHA256()).hex()
    serial_hex = format(device_cert.serial_number, "x")
    issuer_cn = ca_cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
    issuer_str = issuer_cn[0].value if issuer_cn else str(ca_cert.subject)

    # Store cert (NOT the private key) in database
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO device_certificates
                (tenant_id, device_id, cert_pem, fingerprint_sha256, common_name,
                 issuer, serial_number, status, not_before, not_after)
            VALUES ($1, $2, $3, $4, $5, $6, $7, 'ACTIVE', $8, $9)
            RETURNING id, fingerprint_sha256, common_name, status, not_before, not_after, created_at
            """,
            tenant_id, device_id, cert_pem, fingerprint, cn,
            issuer_str, serial_hex, now, not_after,
        )

    return {
        "certificate": dict(row),
        "cert_pem": cert_pem,
        "private_key_pem": key_pem,
        "ca_cert_pem": ca_cert_pem.decode(),
        "warning": "Save the private key now -- it will NOT be shown again.",
    }
```

---

## Step 4: Register Router in app.py

Edit file: `services/ui_iot/app.py`

Add the import alongside the existing router imports (around line 25):

```python
from routes.certificates import router as certificates_router
```

Add the router inclusion alongside the existing `app.include_router()` calls (around line 186):

```python
app.include_router(certificates_router)
```

---

## Step 5: Requirements

If `cryptography` is not already in the service's dependencies, add it.

Check `services/ui_iot/requirements.txt` (or `services/requirements.txt` if shared). Add:

```
cryptography>=42.0.0
```

Also ensure ingest_iot has access if it needs to parse certs (it will in task 002).

---

## Verification

```bash
# 1. Run the migration
psql $DATABASE_URL -f db/migrations/081_device_certificates.sql

# 2. Verify table exists
psql $DATABASE_URL -c "\d device_certificates"
psql $DATABASE_URL -c "SELECT * FROM pg_policies WHERE tablename = 'device_certificates';"

# 3. Generate device CA
chmod +x scripts/generate_device_ca.sh
./scripts/generate_device_ca.sh
ls -la compose/mosquitto/certs/device-ca.*

# 4. Verify CA cert
openssl x509 -in compose/mosquitto/certs/device-ca.crt -noout -text | head -20

# 5. Test API endpoints (with valid JWT)
# Generate a device cert
curl -X POST http://localhost:8080/customer/devices/DEVICE-001/certificates/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF" \
  -d '{"validity_days": 365}' | jq .

# List certificates
curl http://localhost:8080/customer/certificates \
  -H "Authorization: Bearer $TOKEN" | jq .

# List for specific device
curl "http://localhost:8080/customer/certificates?device_id=DEVICE-001" \
  -H "Authorization: Bearer $TOKEN" | jq .

# Get CA bundle
curl http://localhost:8080/customer/ca-bundle \
  -H "Authorization: Bearer $TOKEN" -o /tmp/ca-bundle.pem
openssl x509 -in /tmp/ca-bundle.pem -noout -subject

# Revoke a certificate
curl -X POST http://localhost:8080/customer/certificates/1/revoke \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF" \
  -d '{"reason": "test_revocation"}' | jq .
```
