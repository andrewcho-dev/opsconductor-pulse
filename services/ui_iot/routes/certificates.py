"""Device certificate management (X.509)."""

import hashlib
import os
from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding as asym_padding, rsa
from cryptography.x509.oid import NameOID
from pydantic import BaseModel, Field

from routes.customer import *  # noqa: F401,F403
from middleware.tenant import require_operator

# Path to Device CA cert and key for signing operations
DEVICE_CA_CERT_PATH = os.getenv("DEVICE_CA_CERT_PATH", "/mosquitto/certs/device-ca.crt")
DEVICE_CA_KEY_PATH = os.getenv("DEVICE_CA_KEY_PATH", "/mosquitto/certs/device-ca.key")
ROTATION_GRACE_HOURS = int(os.getenv("ROTATION_GRACE_HOURS", "24"))

router = APIRouter(
    prefix="/api/v1/customer",
    tags=["certificates"],
    dependencies=[
        Depends(JWTBearer()),
        Depends(inject_tenant_context),
        Depends(require_customer),
    ],
)

operator_router = APIRouter(
    prefix="/api/v1/operator",
    tags=["certificates"],
    dependencies=[
        Depends(JWTBearer()),
        Depends(inject_tenant_context),
        Depends(require_operator),
    ],
)


def _cert_validity_window(cert: x509.Certificate) -> tuple[datetime, datetime]:
    # cryptography 42+ provides *_utc properties; keep fallback for older versions.
    not_before = getattr(cert, "not_valid_before_utc", None) or cert.not_valid_before
    not_after = getattr(cert, "not_valid_after_utc", None) or cert.not_valid_after
    if not_before.tzinfo is None:
        not_before = not_before.replace(tzinfo=timezone.utc)
    if not_after.tzinfo is None:
        not_after = not_after.replace(tzinfo=timezone.utc)
    return not_before, not_after


def _verify_signed_by_ca(cert: x509.Certificate, ca_cert: x509.Certificate) -> None:
    """Raise if cert is not signed by ca_cert."""
    pub = ca_cert.public_key()
    if isinstance(pub, rsa.RSAPublicKey):
        pub.verify(
            cert.signature,
            cert.tbs_certificate_bytes,
            asym_padding.PKCS1v15(),
            cert.signature_hash_algorithm,
        )
    elif isinstance(pub, ec.EllipticCurvePublicKey):
        pub.verify(
            cert.signature,
            cert.tbs_certificate_bytes,
            ec.ECDSA(cert.signature_hash_algorithm),
        )
    else:
        raise ValueError("Unsupported CA public key type")


class CertificateUpload(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=200)
    cert_pem: str = Field(..., min_length=50)


class RevokeRequest(BaseModel):
    reason: str = Field(default="manual_revocation", max_length=100)


class CertGenerateRequest(BaseModel):
    validity_days: int = Field(default=365, ge=1, le=3650)


class RotateRequest(BaseModel):
    validity_days: int = Field(default=365, ge=1, le=3650)
    revoke_old_after_hours: int | None = Field(default=None, ge=1, le=720)


def _load_device_ca() -> tuple[object, x509.Certificate, bytes]:
    try:
        ca_key_pem = open(DEVICE_CA_KEY_PATH, "rb").read()
        ca_cert_pem = open(DEVICE_CA_CERT_PATH, "rb").read()
        ca_key = serialization.load_pem_private_key(
            ca_key_pem,
            password=None,
            backend=default_backend(),
        )
        ca_cert = x509.load_pem_x509_certificate(ca_cert_pem, default_backend())
        return ca_key, ca_cert, ca_cert_pem
    except FileNotFoundError:
        raise HTTPException(503, "Device CA not configured")


def _generate_signed_device_certificate(
    tenant_id: str,
    device_id: str,
    validity_days: int,
    ca_key,
    ca_cert: x509.Certificate,
) -> tuple[str, str, str, str, str]:
    """Return (cn, cert_pem, key_pem, fingerprint_hex, serial_hex)."""
    device_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )

    cn = f"{tenant_id}/{device_id}"
    now = datetime.now(timezone.utc)
    not_after = now + timedelta(days=validity_days)

    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, cn),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "OpsConductor Pulse"),
        ]
    )

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
                digital_signature=True,
                key_encipherment=True,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH]),
            critical=False,
        )
    )

    device_cert = builder.sign(
        private_key=ca_key,
        algorithm=hashes.SHA256(),
        backend=default_backend(),
    )

    cert_pem = device_cert.public_bytes(serialization.Encoding.PEM).decode()
    key_pem = device_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ).decode()

    fingerprint = device_cert.fingerprint(hashes.SHA256()).hex()
    serial_hex = format(device_cert.serial_number, "x")
    return cn, cert_pem, key_pem, fingerprint, serial_hex

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
        params: list[object] = [tenant_id]
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


@operator_router.get("/certificates")
async def list_all_certificates(
    tenant_id: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    pool=Depends(get_db_pool),
):
    """Fleet-wide certificate list (operator-only).

    Uses pulse_operator role to bypass RLS and does not require tenant context.
    """
    conditions: list[str] = ["TRUE"]
    params: list[object] = []
    idx = 1

    if tenant_id:
        conditions.append(f"tenant_id = ${idx}")
        params.append(tenant_id)
        idx += 1

    if status:
        status_upper = status.upper()
        if status_upper not in ("ACTIVE", "REVOKED", "EXPIRED"):
            raise HTTPException(400, "Invalid status filter")
        conditions.append(f"status = ${idx}")
        params.append(status_upper)
        idx += 1

    where = " AND ".join(conditions)

    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("SET LOCAL ROLE pulse_operator")

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
                limit,
                offset,
            )

            total = await conn.fetchval(
                f"SELECT COUNT(*) FROM device_certificates WHERE {where}",
                *params,
            )

    return {
        "certificates": [dict(r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/certificates", status_code=201)
async def upload_certificate(body: CertificateUpload, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()

    try:
        cert = x509.load_pem_x509_certificate(body.cert_pem.encode(), default_backend())
    except Exception:
        raise HTTPException(400, "Invalid PEM certificate")

    cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
    common_name = cn[0].value if cn else ""
    issuer_cn = cert.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)
    issuer_str = issuer_cn[0].value if issuer_cn else str(cert.issuer)
    serial_hex = format(cert.serial_number, "x")
    fingerprint = cert.fingerprint(hashes.SHA256()).hex()
    not_before, not_after = _cert_validity_window(cert)

    expected_cn = f"{tenant_id}/{body.device_id}"
    if common_name != expected_cn:
        raise HTTPException(
            400,
            f"Certificate CN '{common_name}' does not match expected '{expected_cn}'",
        )

    try:
        ca_cert_pem = open(DEVICE_CA_CERT_PATH, "rb").read()
        ca_cert = x509.load_pem_x509_certificate(ca_cert_pem, default_backend())
        if cert.issuer != ca_cert.subject:
            raise HTTPException(400, "Certificate issuer does not match trusted Device CA")
        _verify_signed_by_ca(cert, ca_cert)
    except FileNotFoundError:
        raise HTTPException(503, "Device CA not configured -- cannot validate certificate")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "Certificate not signed by trusted Device CA")

    now = datetime.now(timezone.utc)
    if now < not_before:
        raise HTTPException(400, "Certificate not yet valid")
    if now > not_after:
        raise HTTPException(400, "Certificate has expired")

    async with tenant_connection(pool, tenant_id) as conn:
        exists = await conn.fetchval(
            "SELECT 1 FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
            tenant_id,
            body.device_id,
        )
        if not exists:
            raise HTTPException(404, "Device not found")

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
            tenant_id,
            body.device_id,
            body.cert_pem,
            fingerprint,
            common_name,
            issuer_str,
            serial_hex,
            not_before,
            not_after,
        )

    return dict(row)


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
            cert_id,
            tenant_id,
        )
    if not row:
        raise HTTPException(404, "Certificate not found")
    return dict(row)


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
            cert_id,
            tenant_id,
            body.reason,
        )
    if not row:
        raise HTTPException(404, "Certificate not found or already revoked")
    return dict(row)


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


@operator_router.get("/ca-bundle")
async def get_operator_ca_bundle():
    # No tenant context required; CA bundle is global.
    return await get_ca_bundle()


@router.post("/devices/{device_id}/certificates/generate", status_code=201)
async def generate_device_certificate(
    device_id: str,
    body: CertGenerateRequest = CertGenerateRequest(),
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()

    async with tenant_connection(pool, tenant_id) as conn:
        exists = await conn.fetchval(
            "SELECT 1 FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
            tenant_id,
            device_id,
        )
        if not exists:
            raise HTTPException(404, "Device not found")

    ca_key, ca_cert, ca_cert_pem = _load_device_ca()
    cn, cert_pem, key_pem, fingerprint, serial_hex = _generate_signed_device_certificate(
        tenant_id=tenant_id,
        device_id=device_id,
        validity_days=body.validity_days,
        ca_key=ca_key,
        ca_cert=ca_cert,
    )
    issuer_cn = ca_cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
    issuer_str = issuer_cn[0].value if issuer_cn else str(ca_cert.subject)
    now = datetime.now(timezone.utc)
    not_after = now + timedelta(days=body.validity_days)

    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO device_certificates
                (tenant_id, device_id, cert_pem, fingerprint_sha256, common_name,
                 issuer, serial_number, status, not_before, not_after)
            VALUES ($1, $2, $3, $4, $5, $6, $7, 'ACTIVE', $8, $9)
            RETURNING id, fingerprint_sha256, common_name, status, not_before, not_after, created_at
            """,
            tenant_id,
            device_id,
            cert_pem,
            fingerprint,
            cn,
            issuer_str,
            serial_hex,
            now,
            not_after,
        )

    return {
        "certificate": dict(row),
        "cert_pem": cert_pem,
        "private_key_pem": key_pem,
        "ca_cert_pem": ca_cert_pem.decode(),
        "warning": "Save the private key now -- it will NOT be shown again.",
    }


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
    4. Old certs can be revoked manually (or after grace period by operator policy)
    """
    tenant_id = get_tenant_id()
    grace_hours = body.revoke_old_after_hours or ROTATION_GRACE_HOURS

    async with tenant_connection(pool, tenant_id) as conn:
        exists = await conn.fetchval(
            "SELECT 1 FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
            tenant_id,
            device_id,
        )
        if not exists:
            raise HTTPException(404, "Device not found")

        old_certs = await conn.fetch(
            """
            SELECT id, fingerprint_sha256, not_after
            FROM device_certificates
            WHERE tenant_id = $1 AND device_id = $2 AND status = 'ACTIVE'
            ORDER BY created_at DESC
            """,
            tenant_id,
            device_id,
        )

    ca_key, ca_cert, ca_cert_pem = _load_device_ca()
    cn, cert_pem, key_pem, fingerprint, serial_hex = _generate_signed_device_certificate(
        tenant_id=tenant_id,
        device_id=device_id,
        validity_days=body.validity_days,
        ca_key=ca_key,
        ca_cert=ca_cert,
    )
    issuer_cn = ca_cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
    issuer_str = issuer_cn[0].value if issuer_cn else str(ca_cert.subject)
    now = datetime.now(timezone.utc)
    not_after = now + timedelta(days=body.validity_days)

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
            tenant_id,
            device_id,
            cert_pem,
            fingerprint,
            cn,
            issuer_str,
            serial_hex,
            now,
            not_after,
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


@router.get("/crl")
async def get_certificate_revocation_list(pool=Depends(get_db_pool)):
    """
    Generate and return a CRL (Certificate Revocation List) in PEM format.
    Includes all REVOKED certificates, signed by the Device CA.
    """
    ca_key, ca_cert, _ = _load_device_ca()

    # CRL must include revoked certs across all tenants -> use pulse_operator to bypass RLS.
    p = pool
    async with p.acquire() as conn:
        async with conn.transaction():
            await conn.execute("SET LOCAL ROLE pulse_operator")
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

