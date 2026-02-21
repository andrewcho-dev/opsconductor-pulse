"""
Certificate lifecycle worker.
- Regenerates CRL every tick (hourly).
- Marks expired certs as EXPIRED.
- Creates alerts for certificates expiring within CERT_EXPIRY_WARNING_DAYS.
"""

import json
import logging
import os
from datetime import datetime, timezone, timedelta

import asyncpg
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from shared.config import require_env, optional_env

logger = logging.getLogger(__name__)

DEVICE_CA_CERT_PATH = optional_env("DEVICE_CA_CERT_PATH", "/mosquitto/certs/device-ca.crt")
DEVICE_CA_KEY_PATH = optional_env("DEVICE_CA_KEY_PATH", "/mosquitto/certs/device-ca.key")
CRL_OUTPUT_PATH = optional_env("CRL_OUTPUT_PATH", "/certs/device-crl.pem")
CERT_EXPIRY_WARNING_DAYS = int(optional_env("CERT_EXPIRY_WARNING_DAYS", "30"))


def _load_device_ca() -> tuple[object, x509.Certificate]:
    ca_key_pem = open(DEVICE_CA_KEY_PATH, "rb").read()
    ca_cert_pem = open(DEVICE_CA_CERT_PATH, "rb").read()
    ca_key = serialization.load_pem_private_key(
        ca_key_pem,
        password=None,
        backend=default_backend(),
    )
    ca_cert = x509.load_pem_x509_certificate(ca_cert_pem, default_backend())
    return ca_key, ca_cert


async def _notify_broker_crl_update() -> None:
    """Notify EMQX to reload TLS configuration after CRL update."""
    emqx_api_url = optional_env("EMQX_API_URL", "http://iot-mqtt:18083")
    emqx_api_user = optional_env("EMQX_API_USER", "admin")
    emqx_api_pass = require_env("EMQX_DASHBOARD_PASSWORD")

    try:
        import httpx

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.put(
                f"{emqx_api_url}/api/v5/listeners/ssl:default/restart",
                auth=(emqx_api_user, emqx_api_pass),
            )
            if resp.status_code < 300:
                logger.info("emqx_crl_reload_success")
            else:
                logger.warning(
                    "emqx_crl_reload_failed",
                    extra={"status": resp.status_code, "body": resp.text[:200]},
                )
    except Exception as e:
        logger.warning("emqx_crl_reload_error", extra={"error": str(e)})


async def regenerate_crl(pool: asyncpg.Pool) -> None:
    """Regenerate the CRL file from all revoked certificates."""
    try:
        ca_key, ca_cert = _load_device_ca()
    except FileNotFoundError:
        logger.warning(
            "Device CA not found at %s -- skipping CRL generation",
            DEVICE_CA_CERT_PATH,
        )
        return

    async with pool.acquire() as conn:
        async with conn.transaction():
            # Bypass tenant RLS for CRL generation (needs all tenants)
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
    builder = builder.next_update(now + timedelta(hours=2))  # we regenerate hourly

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

    os.makedirs(os.path.dirname(CRL_OUTPUT_PATH) or ".", exist_ok=True)
    tmp_path = CRL_OUTPUT_PATH + ".tmp"
    try:
        with open(tmp_path, "wb") as f:
            f.write(crl_pem)
        os.rename(tmp_path, CRL_OUTPUT_PATH)
        logger.info("CRL regenerated", extra={"revoked_count": len(rows), "path": CRL_OUTPUT_PATH})
    except OSError as e:
        logger.error("Failed to write CRL file: %s", e)
        return

    await _notify_broker_crl_update()


async def check_expired_certificates(pool: asyncpg.Pool) -> None:
    """Mark certificates that have passed their not_after date as EXPIRED."""
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("SET LOCAL ROLE pulse_operator")
            tenants = await conn.fetch(
                """
                SELECT DISTINCT tenant_id
                FROM device_certificates
                WHERE status = 'ACTIVE' AND not_after < now()
                """
            )

    updated_total = 0
    for row in tenants:
        tenant_id = row["tenant_id"]
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("SET LOCAL ROLE pulse_app")
                await conn.execute("SELECT set_config('app.tenant_id', $1, true)", tenant_id)
                result = await conn.execute(
                    """
                    UPDATE device_certificates
                    SET status = 'EXPIRED', updated_at = now()
                    WHERE status = 'ACTIVE' AND not_after < now()
                    """
                )
                try:
                    updated_total += int(result.split()[-1])
                except Exception:
                    pass

    if updated_total > 0:
        logger.info("Marked %d expired certificates as EXPIRED", updated_total)


async def check_expiring_certificates(pool: asyncpg.Pool) -> None:
    """
    Check for certificates expiring within CERT_EXPIRY_WARNING_DAYS.
    Create CERT_EXPIRING alerts for each one (idempotent).
    """
    warning_threshold = datetime.now(timezone.utc) + timedelta(days=CERT_EXPIRY_WARNING_DAYS)

    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("SET LOCAL ROLE pulse_operator")
            rows = await conn.fetch(
                """
                SELECT dc.tenant_id, dc.device_id, dc.fingerprint_sha256,
                       dc.not_after, dc.common_name, dr.site_id
                FROM device_certificates dc
                JOIN device_registry dr
                  ON dr.tenant_id = dc.tenant_id AND dr.device_id = dc.device_id
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

    logger.info("Found %d certificates expiring within %d days", len(rows), CERT_EXPIRY_WARNING_DAYS)

    for row in rows:
        tenant_id = row["tenant_id"]
        device_id = row["device_id"]
        site_id = row["site_id"] or "__unknown__"
        fingerprint = row["fingerprint_sha256"]
        not_after = row["not_after"]
        days_remaining = max(0, (not_after - datetime.now(timezone.utc)).days)

        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("SET LOCAL ROLE pulse_app")
                await conn.execute("SELECT set_config('app.tenant_id', $1, true)", tenant_id)

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
                    tenant_id,
                    device_id,
                    fingerprint,
                )
                if existing:
                    continue

                alert_fingerprint = f"cert_expiring:{device_id}:{fingerprint}"
                summary = f"Device certificate expires in {days_remaining} days"
                details = {
                    "fingerprint": fingerprint,
                    "common_name": row["common_name"],
                    "expires_at": not_after.isoformat(),
                    "days_remaining": days_remaining,
                    "message": summary,
                }

                await conn.execute(
                    """
                    INSERT INTO fleet_alert (
                        tenant_id, site_id, device_id, alert_type, fingerprint,
                        status, severity, confidence, summary, details
                    )
                    VALUES ($1, $2, $3, 'CERT_EXPIRING', $4,
                            'OPEN', 4, 1.0, $5, $6::jsonb)
                    ON CONFLICT DO NOTHING
                    """,
                    tenant_id,
                    site_id,
                    device_id,
                    alert_fingerprint,
                    summary,
                    json.dumps(details),
                )
                logger.info(
                    "Created CERT_EXPIRING alert",
                    extra={
                        "tenant_id": tenant_id,
                        "device_id": device_id,
                        "fingerprint": fingerprint[:16],
                        "days_remaining": days_remaining,
                    },
                )


async def run_certificate_tick(pool: asyncpg.Pool) -> None:
    """Combined tick for certificate lifecycle tasks."""
    await regenerate_crl(pool)
    await check_expired_certificates(pool)
    await check_expiring_certificates(pool)

