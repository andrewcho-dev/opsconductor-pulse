# 137-005: Device Groups, Connection Events & Certificates

## Task
Add seed functions for dynamic_device_groups, device_connection_events, and device_certificates.

## File
`scripts/seed_demo_data.py`

## 1. seed_dynamic_device_groups

Create 2 dynamic groups per tenant:

```python
groups = [
    {
        "group_id": "production-online",
        "name": "Production Devices",
        "description": "All devices currently online",
        "query_filter": {"status": "ONLINE"},
    },
    {
        "group_id": "high-priority",
        "name": "High Priority Sensors",
        "description": "Devices tagged as high priority",
        "query_filter": {"tags": ["priority-high"]},
    },
]

for tenant_id in TENANTS:
    for group in groups:
        await conn.execute("""
            INSERT INTO dynamic_device_groups (tenant_id, group_id, name, description, query_filter)
            VALUES ($1, $2, $3, $4, $5::jsonb)
            ON CONFLICT (tenant_id, group_id) DO NOTHING
        """, tenant_id, group["group_id"], group["name"],
            group["description"], json.dumps(group["query_filter"]))
```

## 2. seed_device_connection_events

Create connection events for demo devices (showing recent connection history):

```python
from datetime import datetime, timezone, timedelta

now = datetime.now(timezone.utc)

for tenant_id in TENANTS:
    devices = await conn.fetch(
        "SELECT device_id FROM device_registry WHERE tenant_id = $1 LIMIT 10",
        tenant_id
    )

    for i, device in enumerate(devices):
        device_id = device["device_id"]

        # Check if events already exist for this device
        existing = await conn.fetchval(
            "SELECT COUNT(*) FROM device_connection_events WHERE tenant_id = $1 AND device_id = $2",
            tenant_id, device_id
        )
        if existing > 0:
            continue

        # Create a CONNECTED event (1 hour ago)
        await conn.execute("""
            INSERT INTO device_connection_events (tenant_id, device_id, event_type, timestamp, details)
            VALUES ($1, $2, 'CONNECTED', $3, $4::jsonb)
        """, tenant_id, device_id,
            now - timedelta(hours=1, minutes=i * 5),
            json.dumps({"ip": f"10.0.{i}.{100 + i}", "protocol": "mqtt", "client_id": device_id}))

        # For the first 2 devices per tenant (the "stale" ones), add a DISCONNECTED event
        if i < 2:
            await conn.execute("""
                INSERT INTO device_connection_events (tenant_id, device_id, event_type, timestamp, details)
                VALUES ($1, $2, 'CONNECTION_LOST', $3, $4::jsonb)
            """, tenant_id, device_id,
                now - timedelta(minutes=30 + i * 10),
                json.dumps({"reason": "heartbeat_timeout"}))
```

## 3. seed_device_certificates

Create demo certificates for 5 devices per tenant. Since we can't generate real X.509 certs in the seed script easily, create plausible demo records:

```python
import hashlib

for tenant_id in TENANTS:
    devices = await conn.fetch(
        "SELECT device_id FROM device_registry WHERE tenant_id = $1 LIMIT 5",
        tenant_id
    )

    for i, device in enumerate(devices):
        device_id = device["device_id"]
        # Generate deterministic fingerprint
        fingerprint = hashlib.sha256(f"{tenant_id}:{device_id}:demo-cert".encode()).hexdigest()

        # Check existence by fingerprint (unique constraint)
        existing = await conn.fetchval(
            "SELECT COUNT(*) FROM device_certificates WHERE fingerprint_sha256 = $1",
            fingerprint
        )
        if existing > 0:
            continue

        # First 4 devices: ACTIVE cert, last device: EXPIRED cert
        status = "EXPIRED" if i == 4 else "ACTIVE"
        not_before = now - timedelta(days=365)
        not_after = now + timedelta(days=365) if status == "ACTIVE" else now - timedelta(days=30)

        # Minimal PEM placeholder (not a real cert, but looks like one)
        demo_pem = f"-----BEGIN CERTIFICATE-----\nDEMO-CERTIFICATE-{tenant_id}-{device_id}\n-----END CERTIFICATE-----"

        await conn.execute("""
            INSERT INTO device_certificates (
                tenant_id, device_id, cert_pem, fingerprint_sha256,
                common_name, issuer, serial_number, status,
                not_before, not_after
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (fingerprint_sha256) DO NOTHING
        """,
            tenant_id, device_id, demo_pem, fingerprint,
            f"{device_id}.{tenant_id}.iot.local",  # common_name
            "Demo IoT CA",  # issuer
            f"SN-{fingerprint[:16]}",  # serial_number
            status, not_before, not_after
        )
```

## Wire Up in main()
```python
await seed_dynamic_device_groups(pool)
await seed_device_connection_events(pool)
await seed_device_certificates(pool)
```

Place AFTER device seeding (depends on device_registry rows).

## Verification
```sql
SELECT tenant_id, group_id, name FROM dynamic_device_groups;
-- 4 rows (2 per tenant)
SELECT tenant_id, device_id, event_type, timestamp FROM device_connection_events ORDER BY timestamp DESC LIMIT 10;
-- Recent events for demo devices
SELECT tenant_id, device_id, status, common_name FROM device_certificates;
-- 10 rows (5 per tenant), mix of ACTIVE and EXPIRED
```
