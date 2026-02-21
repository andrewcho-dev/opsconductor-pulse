# Phase 131 -- X.509 Certificate Device Identity

## Overview

Add mutual-TLS (mTLS) authentication for IoT devices using X.509 client certificates on MQTT port 8883. This replaces username/password auth for devices that present a valid client certificate signed by the platform's device CA.

**Depends on:** Phase 120 (Backend Security Hardening completed).

## Architecture

```
Device (client cert) --TLS--> Mosquitto 8883 (require_certificate true)
                                   |
                         use_identity_as_username true
                         CN = "{tenant_id}/{device_id}"
                                   |
                         ACL pattern matches tenant/{tenant_id}/device/{device_id}/#
                                   |
                         ingest_iot validates cert status in device_certificates table
```

- A separate Device CA (not the server TLS CA) signs all device certificates
- Mosquitto validates the client cert chain against the Device CA on port 8883
- The cert CN encodes `{tenant_id}/{device_id}`, which Mosquitto maps to the MQTT username
- Ingest validates the device has an ACTIVE certificate in the `device_certificates` table
- Port 1883 remains internal (Docker network) for service communication -- no client certs

## Execution Order

| # | File | Commit Scope |
|---|------|-------------|
| 1 | `001-certificate-infrastructure.md` | DB migration + CA script + REST API for certificate CRUD |
| 2 | `002-mutual-tls-mqtt.md` | Mosquitto mTLS config + ACL + ingest_iot cert auth |
| 3 | `003-certificate-lifecycle.md` | Rotation, CRL, expiry alerts in ops_worker |
| 4 | `004-certificate-management-ui.md` | React UI for cert management (device + operator) |

## Key Files Modified

### Backend
- `db/migrations/081_device_certificates.sql` -- new migration
- `services/ui_iot/routes/certificates.py` -- new route module
- `services/ui_iot/app.py` -- register certificates router
- `services/ingest_iot/ingest.py` -- cert-based auth path
- `services/ops_worker/main.py` -- CRL + expiry workers
- `services/ops_worker/workers/certificate_worker.py` -- new worker module

### Infrastructure
- `scripts/generate_device_ca.sh` -- new script
- `compose/mosquitto/mosquitto.conf` -- mTLS config on 8883
- `compose/mosquitto/acl.conf` -- CN-based ACL patterns
- `compose/docker-compose.yml` -- volume mounts for device CA + CRL

### Frontend
- `frontend/src/features/devices/DeviceCertificatesTab.tsx` -- new component
- `frontend/src/features/operator/CertificateOverviewPage.tsx` -- new page
- `frontend/src/services/api/certificates.ts` -- new API client
- `frontend/src/app/router.tsx` -- new routes

## Verification (End-to-End)

After all four commits:

```bash
# 1. Generate device CA
./scripts/generate_device_ca.sh

# 2. Restart Mosquitto with mTLS
docker compose -f compose/docker-compose.yml restart mqtt

# 3. Generate a device certificate via API
curl -X POST http://localhost:8080/customer/devices/DEVICE-001/certificates/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq .

# 4. Save returned cert + key, then test MQTT connection
mosquitto_pub \
  --cafile compose/mosquitto/certs/ca.crt \
  --cert /tmp/device.crt \
  --key /tmp/device.key \
  -h localhost -p 8883 \
  -t "tenant/TENANT1/device/DEVICE-001/telemetry" \
  -m '{"ts":"2026-02-16T00:00:00Z","site_id":"site1","metrics":{"temp":22}}'

# 5. Verify ingest accepted the message
curl http://localhost:8081/health | jq .counters

# 6. Revoke the certificate
curl -X POST http://localhost:8080/customer/certificates/{id}/revoke \
  -H "Authorization: Bearer $TOKEN"

# 7. Verify revoked cert is rejected (after CRL update)
# Same mosquitto_pub command should fail or message should be quarantined
```
