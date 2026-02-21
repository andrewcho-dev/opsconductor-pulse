# Task 003 -- Certificate Lifecycle Management

## Goal

Implement certificate rotation workflow, CRL (Certificate Revocation List) generation and distribution, and certificate expiry alerting as a background task in ops_worker.

## Commit scope

One commit: `feat: add certificate rotation, CRL generation, and expiry alerting`

---

## Step 1: Certificate Rotation API Endpoint

Edit file: `services/ui_iot/routes/certificates.py`

Add the rotation endpoint. The workflow:
1. Generate a new certificate for the device
2. Both old and new certs are ACTIVE during a grace period
3. Device presents the new cert on its next connection
4. After grace period (or manual confirmation), the old cert is revoked

### Add configuration constant

```python
ROTATION_GRACE_HOURS = int(os.getenv("ROTATION_GRACE_HOURS", "24"))
```

### Add Pydantic model

```python
class RotateRequest(BaseModel):
    validity_days: int = Field(default=365, ge=1, le=3650)
    revoke_old_after_hours: int | None = Field(default=None, ge=1, le=720)
```

### Add rotation endpoint

```python
@router.post("/devices/{device_id}/certificates/rotate", status_code=201)
async def rotate_device_certificate(
    device_id: str,
    body: RotateRequest = RotateRequest(),
    pool=Depends(get_db_pool),
):
    """
    Rotate a device's certificate:
    1. Generate a new certificate
    2. Old certificates remain ACTIVE for a grace period
    3. The caller should update the device with the new cert
    4. Old certs can be revoked manually or via the scheduled revocation
    """
    tenant_id = get_tenant_id()
    grace_hours = body.revoke_old_after_hours or ROTATION_GRACE_HOURS

    async with tenant_connection(pool, tenant_id) as conn:
        # Verify device exists
        exists = await conn.fetchval(
            "SELECT 1 FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
            tenant_id, device_id,
        )
        if not exists:
            raise HTTPException(404, "Device not found")

        # Get current active certificates
        old_certs = await conn.fetch(
            """
            SELECT id, fingerprint_sha256, not_after
            FROM device_certificates
            WHERE tenant_id = $1 AND device_id = $2 AND status = 'ACTIVE'
            ORDER BY created_at DESC
            """,
            tenant_id, device_id,
        )

    # Generate the new certificate (reuse the generate logic)
    # Load Device CA
    try:
        ca_key_pem = open(DEVICE_CA_KEY_PATH, "rb").read()
        ca_cert_pem = open(DEVICE_CA_CERT_PATH, "rb").read()
        ca_key = serialization.load_pem_private_key(ca_key_pem, password=None, backend=default_backend())
        ca_cert = x509.load_pem_x509_certificate(ca_cert_pem, default_backend())
    except FileNotFoundError:
        raise HTTPException(503, "Device CA not configured")

    # Generate new key pair
    device_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend(),
    )

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

    device_cert = builder.sign(ca_key, hashes.SHA256(), default_backend())

    cert_pem = device_cert.public_bytes(serialization.Encoding.PEM).decode()
    key_pem = device_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ).decode()

    fingerprint = device_cert.fingerprint(hashes.SHA256()).hex()
    serial_hex = format(device_cert.serial_number, "x")
    issuer_cn = ca_cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
    issuer_str = issuer_cn[0].value if issuer_cn else str(ca_cert.subject)

    # Store new cert and schedule old cert revocation
    scheduled_revoke_at = now + timedelta(hours=grace_hours)

    async with tenant_connection(pool, tenant_id) as conn:
        new_cert_row = await conn.fetchrow(
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
        "new_certificate": dict(new_cert_row),
        "cert_pem": cert_pem,
        "private_key_pem": key_pem,
        "ca_cert_pem": ca_cert_pem.decode(),
        "old_certificates": [
            {
                "id": c["id"],
                "fingerprint": c["fingerprint_sha256"],
                "status": "ACTIVE (will remain active for grace period)",
                "scheduled_revoke_at": scheduled_revoke_at.isoformat(),
            }
            for c in old_certs
        ],
        "grace_period_hours": grace_hours,
        "warning": "Save the private key now -- it will NOT be shown again. "
                   f"Old certificates will remain active for {grace_hours} hours.",
    }
```

**Note:** Consider extracting the cert generation logic into a shared helper function (e.g., `_generate_and_sign_cert(tenant_id, device_id, validity_days, pool)`) since it is duplicated between `generate_device_certificate` and `rotate_device_certificate`. Refactor to DRY it up.

---

## Step 2: CRL API Endpoint

Edit file: `services/ui_iot/routes/certificates.py`

Add an endpoint that generates the CRL on-demand:

```python
@router.get("/crl")
async def get_certificate_revocation_list(pool=Depends(get_db_pool)):
    """
    Generate and return a CRL (Certificate Revocation List) in PEM format.
    Includes all REVOKED certificates, signed by the Device CA.
    """
    # Load Device CA
    try:
        ca_key_pem = open(DEVICE_CA_KEY_PATH, "rb").read()
        ca_cert_pem = open(DEVICE_CA_CERT_PATH, "rb").read()
        ca_key = serialization.load_pem_private_key(ca_key_pem, password=None, backend=default_backend())
        ca_cert = x509.load_pem_x509_certificate(ca_cert_pem, default_backend())
    except FileNotFoundError:
        raise HTTPException(503, "Device CA not configured")

    # Fetch all revoked certificates (operator-level: no tenant filter for CRL)
    # CRL must contain ALL revoked certs across all tenants
    p = pool
    async with p.acquire() as conn:
        # Use superuser/operator role to bypass RLS for CRL generation
        await conn.execute("SET LOCAL ROLE pulse_app")
        await conn.execute("SELECT set_config('app.tenant_id', '__system__', true)")
        rows = await conn.fetch(
            """
            SELECT serial_number, revoked_at
            FROM device_certificates
            WHERE status = 'REVOKED' AND revoked_at IS NOT NULL
            ORDER BY revoked_at
            """
        )

    now = datetime.now(timezone.utc)
    builder = x509.CertificateRevocationListBuilder()
    builder = builder.issuer_name(ca_cert.subject)
    builder = builder.last_update(now)
    builder = builder.next_update(now + timedelta(hours=1))

    for row in rows:
        serial = int(row["serial_number"], 16)
        revoked_cert = (
            x509.RevokedCertificateBuilder()
            .serial_number(serial)
            .revocation_date(row["revoked_at"])
            .build()
        )
        builder = builder.add_revoked_certificate(revoked_cert)

    crl = builder.sign(ca_key, hashes.SHA256(), default_backend())
    crl_pem = crl.public_bytes(serialization.Encoding.PEM).decode()

    return Response(
        content=crl_pem,
        media_type="application/x-pem-file",
        headers={"Content-Disposition": "attachment; filename=device-crl.pem"},
    )
```

**Important:** The CRL generation needs to bypass tenant RLS since it must include revoked certs from ALL tenants. The query above uses `SET LOCAL ROLE pulse_app` with a system tenant context. Alternatively, use a direct connection without RLS context. Verify that the `pulse_operator` role can read all rows (the operator read policy created in 081 migration allows this).

---

## Step 3: Certificate Worker in ops_worker

Create file: `services/ops_worker/workers/certificate_worker.py`

This worker handles two periodic tasks:
1. **CRL regeneration** -- write CRL file to shared volume every hour
2. **Expiry alerting** -- check for certs expiring within 30 days, create alerts

```python
"""
Certificate lifecycle worker.
- Regenerates CRL every tick (hourly).
- Creates alerts for certificates expiring within 30 days.
"""
import logging
import os
from datetime import datetime, timezone, timedelta

import asyncpg

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

DEVICE_CA_CERT_PATH = os.getenv("DEVICE_CA_CERT_PATH", "/mosquitto/certs/device-ca.crt")
DEVICE_CA_KEY_PATH = os.getenv("DEVICE_CA_KEY_PATH", "/mosquitto/certs/device-ca.key")
CRL_OUTPUT_PATH = os.getenv("CRL_OUTPUT_PATH", "/mosquitto/certs/device-crl.pem")
CERT_EXPIRY_WARNING_DAYS = int(os.getenv("CERT_EXPIRY_WARNING_DAYS", "30"))


async def regenerate_crl(pool: asyncpg.Pool) -> None:
    """Regenerate the CRL file from all revoked certificates."""
    try:
        ca_key_pem = open(DEVICE_CA_KEY_PATH, "rb").read()
        ca_cert_pem = open(DEVICE_CA_CERT_PATH, "rb").read()
        ca_key = serialization.load_pem_private_key(ca_key_pem, password=None, backend=default_backend())
        ca_cert = x509.load_pem_x509_certificate(ca_cert_pem, default_backend())
    except FileNotFoundError:
        logger.warning("Device CA not found at %s -- skipping CRL generation", DEVICE_CA_CERT_PATH)
        return

    async with pool.acquire() as conn:
        # Bypass RLS for CRL generation (needs all tenants)
        await conn.execute("SET LOCAL ROLE pulse_app")
        await conn.execute("SELECT set_config('app.tenant_id', '__system__', true)")
        rows = await conn.fetch(
            """
            SELECT serial_number, revoked_at
            FROM device_certificates
            WHERE status = 'REVOKED' AND revoked_at IS NOT NULL
            ORDER BY revoked_at
            """
        )

    now = datetime.now(timezone.utc)
    builder = x509.CertificateRevocationListBuilder()
    builder = builder.issuer_name(ca_cert.subject)
    builder = builder.last_update(now)
    builder = builder.next_update(now + timedelta(hours=2))  # next update in 2h (we regenerate hourly)

    for row in rows:
        try:
            serial = int(row["serial_number"], 16)
        except (ValueError, TypeError):
            logger.warning("Invalid serial_number in device_certificates: %s", row["serial_number"])
            continue
        revoked_cert = (
            x509.RevokedCertificateBuilder()
            .serial_number(serial)
            .revocation_date(row["revoked_at"])
            .build()
        )
        builder = builder.add_revoked_certificate(revoked_cert)

    crl = builder.sign(ca_key, hashes.SHA256(), default_backend())
    crl_pem = crl.public_bytes(serialization.Encoding.PEM)

    # Write atomically (write to temp file, then rename)
    tmp_path = CRL_OUTPUT_PATH + ".tmp"
    try:
        with open(tmp_path, "wb") as f:
            f.write(crl_pem)
        os.rename(tmp_path, CRL_OUTPUT_PATH)
        logger.info(
            "CRL regenerated",
            extra={"revoked_count": len(rows), "path": CRL_OUTPUT_PATH},
        )
    except OSError as e:
        logger.error("Failed to write CRL file: %s", e)


async def check_expiring_certificates(pool: asyncpg.Pool) -> None:
    """
    Check for certificates expiring within CERT_EXPIRY_WARNING_DAYS.
    Create CERT_EXPIRING alerts for each one (idempotent).
    """
    warning_threshold = datetime.now(timezone.utc) + timedelta(days=CERT_EXPIRY_WARNING_DAYS)

    async with pool.acquire() as conn:
        # Bypass RLS to check all tenants
        await conn.execute("SET LOCAL ROLE pulse_app")
        await conn.execute("SELECT set_config('app.tenant_id', '__system__', true)")

        rows = await conn.fetch(
            """
            SELECT dc.id, dc.tenant_id, dc.device_id, dc.fingerprint_sha256,
                   dc.not_after, dc.common_name
            FROM device_certificates dc
            WHERE dc.status = 'ACTIVE'
              AND dc.not_after <= $1
              AND dc.not_after > now()
            ORDER BY dc.not_after ASC
            """,
            warning_threshold,
        )

    if not rows:
        logger.debug("No expiring certificates found within %d days", CERT_EXPIRY_WARNING_DAYS)
        return

    logger.info(
        "Found %d certificates expiring within %d days",
        len(rows), CERT_EXPIRY_WARNING_DAYS,
    )

    for row in rows:
        days_remaining = (row["not_after"] - datetime.now(timezone.utc)).days
        tenant_id = row["tenant_id"]
        device_id = row["device_id"]

        async with pool.acquire() as conn:
            await conn.execute("SET LOCAL ROLE pulse_app")
            await conn.execute(
                "SELECT set_config('app.tenant_id', $1, true)", tenant_id
            )

            # Check if an alert already exists for this cert (idempotent)
            existing = await conn.fetchval(
                """
                SELECT 1 FROM fleet_alert
                WHERE tenant_id = $1
                  AND device_id = $2
                  AND alert_type = 'CERT_EXPIRING'
                  AND status IN ('OPEN', 'ACKNOWLEDGED')
                  AND details->>'fingerprint' = $3
                LIMIT 1
                """,
                tenant_id, device_id, row["fingerprint_sha256"],
            )
            if existing:
                continue

            # Create alert
            import json
            import uuid

            alert_id = str(uuid.uuid4())
            await conn.execute(
                """
                INSERT INTO fleet_alert
                    (alert_id, tenant_id, device_id, alert_type, severity, status, details)
                VALUES ($1, $2, $3, 'CERT_EXPIRING', 'HIGH', 'OPEN', $4::jsonb)
                """,
                alert_id,
                tenant_id,
                device_id,
                json.dumps({
                    "fingerprint": row["fingerprint_sha256"],
                    "common_name": row["common_name"],
                    "expires_at": row["not_after"].isoformat(),
                    "days_remaining": days_remaining,
                    "message": f"Device certificate expires in {days_remaining} days",
                }),
            )
            logger.info(
                "Created CERT_EXPIRING alert",
                extra={
                    "tenant_id": tenant_id,
                    "device_id": device_id,
                    "fingerprint": row["fingerprint_sha256"][:16],
                    "days_remaining": days_remaining,
                },
            )


async def check_expired_certificates(pool: asyncpg.Pool) -> None:
    """Mark certificates that have passed their not_after date as EXPIRED."""
    async with pool.acquire() as conn:
        await conn.execute("SET LOCAL ROLE pulse_app")
        await conn.execute("SELECT set_config('app.tenant_id', '__system__', true)")

        result = await conn.execute(
            """
            UPDATE device_certificates
            SET status = 'EXPIRED', updated_at = now()
            WHERE status = 'ACTIVE' AND not_after < now()
            """
        )
        count = int(result.split()[-1]) if result else 0
        if count > 0:
            logger.info("Marked %d expired certificates as EXPIRED", count)


async def run_certificate_tick(pool: asyncpg.Pool) -> None:
    """
    Combined tick for certificate lifecycle tasks.
    Called by ops_worker main loop.
    """
    await regenerate_crl(pool)
    await check_expired_certificates(pool)
    await check_expiring_certificates(pool)
```

---

## Step 4: Register Worker in ops_worker main

Edit file: `services/ops_worker/main.py`

Add the import (after existing imports, around line 13):

```python
from workers.certificate_worker import run_certificate_tick
```

Add the worker to `asyncio.gather` in the `main()` function (around line 66-73). The certificate worker runs with two intervals:
- CRL regeneration: every 3600 seconds (1 hour)
- Expiry check: also every 3600 seconds (daily would suffice, but hourly is fine since it is idempotent)

```python
async def main() -> None:
    pool = await get_pool()
    await asyncio.gather(
        run_health_monitor(),
        run_metrics_collector(),
        worker_loop(run_escalation_tick, pool, interval=60),
        worker_loop(run_jobs_expiry_tick, pool, interval=60),
        worker_loop(run_commands_expiry_tick, pool, interval=60),
        worker_loop(run_report_tick, pool, interval=86400),
        worker_loop(run_certificate_tick, pool, interval=3600),  # hourly: CRL + expiry
    )
```

---

## Step 5: Add ops_worker Environment Variables

Edit file: `compose/docker-compose.yml`

Add to the ops-worker service environment:

```yaml
  ops-worker:
    environment:
      # ... existing env vars ...
      DEVICE_CA_CERT_PATH: "/mosquitto/certs/device-ca.crt"
      DEVICE_CA_KEY_PATH: "/mosquitto/certs/device-ca.key"
      CRL_OUTPUT_PATH: "/mosquitto/certs/device-crl.pem"
      CERT_EXPIRY_WARNING_DAYS: "30"
    volumes:
      # ... existing volumes ...
      - ./mosquitto/certs:/mosquitto/certs  # For CRL writes
```

---

## Step 6: Mosquitto CRL Reload

Mosquitto reads the CRL file at startup and does NOT automatically reload it when the file changes. To pick up CRL updates, Mosquitto needs a SIGHUP signal or restart.

**Option A: Send SIGHUP after CRL update** (preferred)

Modify `regenerate_crl()` in `certificate_worker.py` to send SIGHUP to Mosquitto after writing the CRL. Since ops_worker runs in a separate container, this requires either:
1. Docker socket access (not recommended for security)
2. A shared signal mechanism
3. Mosquitto dynamic security plugin

**Option B: Periodic Mosquitto restart** (simple but disruptive)

Not recommended -- causes brief connection drops.

**Option C: Use Mosquitto's `per_listener_settings` with auth plugin**

Beyond scope for this phase.

**Practical approach:** For now, add a comment in the code noting that Mosquitto needs a manual reload after CRL updates. In production, use a sidecar or orchestrator that sends SIGHUP to Mosquitto after the CRL file is updated.

Add to `regenerate_crl()` after writing the file:

```python
# NOTE: Mosquitto does not auto-reload CRL files.
# In production, send SIGHUP to Mosquitto after CRL update:
#   docker kill --signal=SIGHUP iot-mqtt
# Or use a sidecar container that watches the CRL file and signals Mosquitto.
logger.info(
    "CRL file updated -- Mosquitto may need SIGHUP to reload",
    extra={"path": CRL_OUTPUT_PATH},
)
```

---

## Verification

```bash
# 1. Generate initial cert for a device
curl -X POST http://localhost:8080/customer/devices/DEVICE-001/certificates/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF" | jq .
# Save the cert_pem and private_key_pem to files

# 2. Rotate the certificate
curl -X POST http://localhost:8080/customer/devices/DEVICE-001/certificates/rotate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF" \
  -d '{"validity_days": 365, "revoke_old_after_hours": 24}' | jq .
# Should return new cert + old cert still ACTIVE

# 3. List certificates -- should show both as ACTIVE
curl "http://localhost:8080/customer/certificates?device_id=DEVICE-001" \
  -H "Authorization: Bearer $TOKEN" | jq '.certificates[] | {id, fingerprint_sha256, status}'

# 4. Test MQTT with old cert -- should still work
mosquitto_pub --cafile compose/mosquitto/certs/combined-ca.crt \
  --cert /tmp/old-device.crt --key /tmp/old-device.key \
  -h localhost -p 8883 \
  -t "tenant/TENANT1/device/DEVICE-001/telemetry" \
  -m '{"ts":"2026-02-16T00:00:00Z","site_id":"site1","metrics":{"temp":22}}'

# 5. Test MQTT with new cert -- should also work
mosquitto_pub --cafile compose/mosquitto/certs/combined-ca.crt \
  --cert /tmp/new-device.crt --key /tmp/new-device.key \
  -h localhost -p 8883 \
  -t "tenant/TENANT1/device/DEVICE-001/telemetry" \
  -m '{"ts":"2026-02-16T00:00:01Z","site_id":"site1","metrics":{"temp":23}}'

# 6. Revoke the old certificate
curl -X POST http://localhost:8080/customer/certificates/1/revoke \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF" \
  -d '{"reason": "rotated"}' | jq .

# 7. Download CRL
curl http://localhost:8080/customer/crl \
  -H "Authorization: Bearer $TOKEN" -o /tmp/crl.pem
openssl crl -in /tmp/crl.pem -noout -text

# 8. Check ops_worker logs for CRL regeneration
docker compose -f compose/docker-compose.yml logs ops-worker --tail 20

# 9. Verify CRL file on disk
openssl crl -in compose/mosquitto/certs/device-crl.pem -noout -text

# 10. After SIGHUP to Mosquitto, old cert should be rejected
docker kill --signal=SIGHUP iot-mqtt
# Old cert publish should now fail:
mosquitto_pub --cafile compose/mosquitto/certs/combined-ca.crt \
  --cert /tmp/old-device.crt --key /tmp/old-device.key \
  -h localhost -p 8883 \
  -t "tenant/TENANT1/device/DEVICE-001/telemetry" \
  -m '{"ts":"2026-02-16T00:00:02Z","site_id":"site1","metrics":{"temp":24}}' 2>&1 \
  || echo "EXPECTED: Rejected by CRL"
```
