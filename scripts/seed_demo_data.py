#!/usr/bin/env python3
"""Seed demo data for Pulse IoT platform."""
import argparse
import asyncio
import hashlib
import json
import os
import random
import math
from datetime import datetime, timedelta, timezone
import uuid
from uuid import uuid4

try:
    import asyncpg  # type: ignore
    import httpx  # type: ignore
except ModuleNotFoundError:
    # The compose seed service normally installs deps before running the script,
    # but if someone overrides the command (e.g. to pass --tables), that step may
    # be bypassed. Keep the seed script runnable in that scenario.
    import subprocess
    import sys

    subprocess.check_call([sys.executable, "-m", "pip", "install", "asyncpg", "httpx"])
    import asyncpg  # type: ignore
    import httpx  # type: ignore

PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "iotcloud")
PG_USER = os.getenv("PG_USER", "iot")
PG_PASS = os.environ["PG_PASS"]
KEYCLOAK_INTERNAL_URL = os.getenv("KEYCLOAK_INTERNAL_URL", "http://keycloak:8080")
KEYCLOAK_ADMIN_PASSWORD = os.environ.get("KEYCLOAK_ADMIN_PASSWORD", "admin_dev")

TENANTS = ["tenant-a", "tenant-b"]
SITES = {
    "tenant-a": ["warehouse-east", "warehouse-west", "cold-storage-1"],
    "tenant-b": ["factory-floor", "loading-dock", "office-hvac"],
}

RULES_TEMPLATE = [
    {"name": "Low Battery Warning", "metric_name": "battery_pct", "operator": "LT", "threshold": 25.0, "severity": 2, "description": "Battery below 25%"},
    {"name": "Critical Battery", "metric_name": "battery_pct", "operator": "LT", "threshold": 10.0, "severity": 1, "description": "Battery critically low"},
    {"name": "High Temperature", "metric_name": "temp_c", "operator": "GT", "threshold": 35.0, "severity": 3, "description": "Temperature exceeds 35°C"},
    {"name": "Freezing Alert", "metric_name": "temp_c", "operator": "LT", "threshold": 2.0, "severity": 2, "description": "Temperature near freezing"},
    {"name": "Weak Signal", "metric_name": "rssi_dbm", "operator": "LT", "threshold": -85.0, "severity": 4, "description": "Signal strength degraded"},
]


def now_utc():
    return datetime.now(timezone.utc)


def iter_devices():
    for tenant_id in TENANTS:
        for site_id in SITES[tenant_id]:
            for idx in range(1, 6):
                device_id = f"{site_id}-sensor-{idx:02d}"
                yield tenant_id, site_id, device_id


def pick_special_devices(devices):
    random.seed(42)
    stale = set()
    low_battery = set()
    high_temp = set()
    weak_signal = set()
    for tenant_id in TENANTS:
        tenant_devices = [d for d in devices if d[0] == tenant_id]
        stale.update(random.sample(tenant_devices, 2))
        low_battery.update(random.sample(tenant_devices, 2))
        high_temp.update(random.sample(tenant_devices, 1))
        weak_signal.update(random.sample(tenant_devices, 2))
    return stale, low_battery, high_temp, weak_signal


async def seed_tenants(pool):
    tenant_profiles = {
        "tenant-a": {
            "name": "Acme IoT Corp",
            "legal_name": "Acme IoT Corporation",
            "contact_email": "admin@acme-iot.example.com",
            "contact_name": "Jane Doe",
            "phone": "+1-555-0100",
            "industry": "Manufacturing",
            "company_size": "51-200",
            "address_line1": "123 Industrial Blvd",
            "address_line2": "Suite 400",
            "city": "Austin",
            "state_province": "TX",
            "postal_code": "78701",
            "country": "US",
            "data_residency_region": "us-east",
            "support_tier": "business",
            "sla_level": 99.95,
            "billing_email": "billing@acme-iot.example.com",
        },
        "tenant-b": {
            "name": "Nordic Sensors AB",
            "legal_name": "Nordic Sensors Aktiebolag",
            "contact_email": "ops@nordicsensors.example.com",
            "contact_name": "Erik Lindqvist",
            "phone": "+46-8-555-1234",
            "industry": "Agriculture",
            "company_size": "11-50",
            "address_line1": "Storgatan 12",
            "address_line2": None,
            "city": "Stockholm",
            "state_province": "Stockholm",
            "postal_code": "111 23",
            "country": "SE",
            "data_residency_region": "eu-west",
            "support_tier": "standard",
            "sla_level": 99.90,
            "billing_email": "finance@nordicsensors.example.com",
        },
    }
    async with pool.acquire() as conn:
        for tenant_id in TENANTS:
            profile = tenant_profiles.get(tenant_id) or {}
            name = profile.get("name") or tenant_id.replace("-", " ").title()
            await conn.execute(
                """
                INSERT INTO tenants (
                    tenant_id, name, status,
                    legal_name, contact_email, contact_name, phone,
                    industry, company_size,
                    address_line1, address_line2, city, state_province, postal_code, country,
                    data_residency_region, support_tier, sla_level,
                    billing_email
                )
                VALUES (
                    $1,$2,'ACTIVE',
                    $3,$4,$5,$6,
                    $7,$8,
                    $9,$10,$11,$12,$13,$14,
                    $15,$16,$17,
                    $18
                )
                ON CONFLICT (tenant_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    status = EXCLUDED.status,
                    legal_name = EXCLUDED.legal_name,
                    contact_email = EXCLUDED.contact_email,
                    contact_name = EXCLUDED.contact_name,
                    phone = EXCLUDED.phone,
                    industry = EXCLUDED.industry,
                    company_size = EXCLUDED.company_size,
                    address_line1 = EXCLUDED.address_line1,
                    address_line2 = EXCLUDED.address_line2,
                    city = EXCLUDED.city,
                    state_province = EXCLUDED.state_province,
                    postal_code = EXCLUDED.postal_code,
                    country = EXCLUDED.country,
                    data_residency_region = EXCLUDED.data_residency_region,
                    support_tier = EXCLUDED.support_tier,
                    sla_level = EXCLUDED.sla_level,
                    billing_email = EXCLUDED.billing_email
                """,
                tenant_id,
                name,
                profile.get("legal_name"),
                profile.get("contact_email"),
                profile.get("contact_name"),
                profile.get("phone"),
                profile.get("industry"),
                profile.get("company_size"),
                profile.get("address_line1"),
                profile.get("address_line2"),
                profile.get("city"),
                profile.get("state_province"),
                profile.get("postal_code"),
                profile.get("country"),
                profile.get("data_residency_region"),
                profile.get("support_tier"),
                profile.get("sla_level"),
                profile.get("billing_email"),
            )


async def ensure_subscription_plan_ids(pool):
    """Ensure demo subscriptions have plan_id so tier allocations can seed."""
    tenant_plans = {"tenant-a": "pro", "tenant-b": "starter"}
    async with pool.acquire() as conn:
        for tenant_id, plan_id in tenant_plans.items():
            try:
                await conn.execute(
                    """
                    UPDATE subscriptions
                    SET plan_id = $1
                    WHERE tenant_id = $2
                      AND plan_id IS NULL
                      AND status IN ('ACTIVE', 'TRIAL')
                    """,
                    plan_id,
                    tenant_id,
                )
            except Exception:
                # Subscriptions may not exist in all setups; keep seeding idempotent.
                return


async def seed_tier_allocations(pool):
    async with pool.acquire() as conn:
        try:
            subs = await conn.fetch(
                """
                SELECT subscription_id, plan_id
                FROM subscriptions
                WHERE status IN ('ACTIVE', 'TRIAL')
                  AND plan_id IS NOT NULL
                """
            )
        except Exception:
            return

        for sub in subs:
            defaults = await conn.fetch(
                "SELECT tier_id, slot_limit FROM plan_tier_defaults WHERE plan_id = $1",
                sub["plan_id"],
            )
            for d in defaults:
                await conn.execute(
                    """
                    INSERT INTO subscription_tier_allocations (subscription_id, tier_id, slot_limit)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (subscription_id, tier_id) DO NOTHING
                    """,
                    sub["subscription_id"],
                    d["tier_id"],
                    d["slot_limit"],
                )


async def seed_device_tiers(pool):
    async with pool.acquire() as conn:
        try:
            devices = await conn.fetch(
                "SELECT device_id, tenant_id FROM device_registry WHERE tier_id IS NULL LIMIT 20"
            )
            tiers = await conn.fetch(
                "SELECT tier_id FROM device_tiers WHERE is_active = true ORDER BY sort_order"
            )
        except Exception:
            return

        tier_ids = [t["tier_id"] for t in tiers]
        for i, dev in enumerate(devices):
            if tier_ids:
                await conn.execute(
                    "UPDATE device_registry SET tier_id = $1 WHERE device_id = $2 AND tenant_id = $3",
                    tier_ids[i % len(tier_ids)],
                    dev["device_id"],
                    dev["tenant_id"],
                )


async def seed_dynamic_device_groups(pool):
    """Seed dynamic device groups (idempotent)."""
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
    async with pool.acquire() as conn:
        for tenant_id in TENANTS:
            for group in groups:
                await conn.execute(
                    """
                    INSERT INTO dynamic_device_groups (tenant_id, group_id, name, description, query_filter)
                    VALUES ($1, $2, $3, $4, $5::jsonb)
                    ON CONFLICT (tenant_id, group_id) DO NOTHING
                    """,
                    tenant_id,
                    group["group_id"],
                    group["name"],
                    group["description"],
                    json.dumps(group["query_filter"]),
                )
    print("  ✓ dynamic_device_groups seeded")


async def seed_device_connection_events(pool):
    """Seed recent device connection events (idempotent per device)."""
    now = now_utc()
    async with pool.acquire() as conn:
        # If we've already populated demo-like events, don't append more.
        seeded = await conn.fetchval(
            "SELECT COUNT(*) FROM device_connection_events WHERE details->>'seed_source' = 'seed_demo_data'"
        )
        if seeded and int(seeded) > 0:
            print("  ✓ device_connection_events seeded")
            return
        # Backward-compatible check for earlier runs (details have protocol+client_id)
        legacy_seeded = await conn.fetchval(
            "SELECT COUNT(*) FROM device_connection_events WHERE details->>'protocol' = 'mqtt' AND details ? 'client_id'"
        )
        if legacy_seeded and int(legacy_seeded) > 0:
            print("  ✓ device_connection_events seeded")
            return

        for tenant_id in TENANTS:
            devices = await conn.fetch(
                "SELECT device_id FROM device_registry WHERE tenant_id = $1 ORDER BY device_id LIMIT 10",
                tenant_id,
            )
            for i, device in enumerate(devices):
                device_id = device["device_id"]
                existing = await conn.fetchval(
                    "SELECT COUNT(*) FROM device_connection_events WHERE tenant_id = $1 AND device_id = $2",
                    tenant_id,
                    device_id,
                )
                if existing and int(existing) > 0:
                    continue

                # CONNECTED event (1 hour ago)
                await conn.execute(
                    """
                    INSERT INTO device_connection_events (tenant_id, device_id, event_type, timestamp, details)
                    VALUES ($1, $2, 'CONNECTED', $3, $4::jsonb)
                    """,
                    tenant_id,
                    device_id,
                    now - timedelta(hours=1, minutes=i * 5),
                    json.dumps(
                        {
                            "ip": f"10.0.{i}.{100 + i}",
                            "protocol": "mqtt",
                            "client_id": device_id,
                            "seed_source": "seed_demo_data",
                        }
                    ),
                )

                # First 2 devices per tenant: add a CONNECTION_LOST event
                if i < 2:
                    await conn.execute(
                        """
                        INSERT INTO device_connection_events (tenant_id, device_id, event_type, timestamp, details)
                        VALUES ($1, $2, 'CONNECTION_LOST', $3, $4::jsonb)
                        """,
                        tenant_id,
                        device_id,
                        now - timedelta(minutes=30 + i * 10),
                        json.dumps({"reason": "heartbeat_timeout", "seed_source": "seed_demo_data"}),
                    )
    print("  ✓ device_connection_events seeded")


async def seed_device_certificates(pool):
    """Seed demo device certificate records (idempotent by fingerprint)."""
    now = now_utc()
    async with pool.acquire() as conn:
        for tenant_id in TENANTS:
            devices = await conn.fetch(
                "SELECT device_id FROM device_registry WHERE tenant_id = $1 ORDER BY device_id LIMIT 5",
                tenant_id,
            )
            for i, device in enumerate(devices):
                device_id = device["device_id"]
                fingerprint = hashlib.sha256(f"{tenant_id}:{device_id}:demo-cert".encode()).hexdigest()
                existing = await conn.fetchval(
                    "SELECT COUNT(*) FROM device_certificates WHERE fingerprint_sha256 = $1",
                    fingerprint,
                )
                if existing and int(existing) > 0:
                    continue

                status = "EXPIRED" if i == 4 else "ACTIVE"
                not_before = now - timedelta(days=365)
                not_after = now + timedelta(days=365) if status == "ACTIVE" else now - timedelta(days=30)

                demo_pem = (
                    "-----BEGIN CERTIFICATE-----\n"
                    f"DEMO-CERTIFICATE-{tenant_id}-{device_id}\n"
                    "-----END CERTIFICATE-----"
                )

                await conn.execute(
                    """
                    INSERT INTO device_certificates (
                        tenant_id, device_id, cert_pem, fingerprint_sha256,
                        common_name, issuer, serial_number, status,
                        not_before, not_after
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (fingerprint_sha256) DO NOTHING
                    """,
                    tenant_id,
                    device_id,
                    demo_pem,
                    fingerprint,
                    f"{device_id}.{tenant_id}.iot.local",
                    "Demo IoT CA",
                    f"SN-{fingerprint[:16]}",
                    status,
                    not_before,
                    not_after,
                )
    print("  ✓ device_certificates seeded")


async def seed_role_assignments(conn):
    """Assign Full Admin role to demo admin users."""
    full_admin = await conn.fetchrow(
        "SELECT id FROM roles WHERE name = 'Full Admin' AND is_system = true AND tenant_id IS NULL"
    )
    if not full_admin:
        print("  [skip] Full Admin role not found (run migration 080+081 first)")
        return

    role_id = full_admin["id"]
    for tenant_id in TENANTS:
        # Assign to demo admin user (sub = 'demo-admin-{tenant}')
        await conn.execute(
            """
            INSERT INTO user_role_assignments (tenant_id, user_id, role_id, assigned_by)
            VALUES ($1, $2, $3, 'seed-script')
            ON CONFLICT (tenant_id, user_id, role_id) DO NOTHING
            """,
            tenant_id,
            f"demo-admin-{tenant_id}",
            role_id,
        )
    print("  [ok] Role assignments seeded")


async def seed_device_registry(pool, devices):
    async with pool.acquire() as conn:
        for tenant_id, site_id, device_id in devices:
            token_hash = hashlib.sha256(f"tok-{device_id}".encode()).hexdigest()
            metadata = {
                "model": random.choice(["DHT22", "BME280", "SHT31"]),
                "installed": "2024-01-15",
            }
            await conn.execute(
                """
                INSERT INTO device_registry (tenant_id, device_id, site_id, status, provision_token_hash, fw_version, metadata)
                VALUES ($1,$2,$3,'ACTIVE',$4,$5,$6::jsonb)
                ON CONFLICT (tenant_id, device_id) DO NOTHING
                """,
                tenant_id,
                device_id,
                site_id,
                token_hash,
                random.choice(["1.0.0", "1.1.0", "1.2.3", "2.0.0"]),
                json.dumps(metadata),
            )


async def seed_device_state(pool, devices, stale, low_battery, high_temp, weak_signal):
    now = now_utc()
    stale_time = now - timedelta(minutes=2)
    async with pool.acquire() as conn:
        for tenant_id, site_id, device_id in devices:
            status = "STALE" if (tenant_id, site_id, device_id) in stale else "ONLINE"
            last_ts = stale_time if status == "STALE" else now
            battery = random.uniform(60, 100)
            temp = random.uniform(18, 26)
            rssi = random.uniform(-70, -50)
            humidity = random.uniform(40, 60)

            if (tenant_id, site_id, device_id) in low_battery:
                battery = random.uniform(15, 25)
            if (tenant_id, site_id, device_id) in high_temp:
                temp = random.uniform(32, 38)
            if (tenant_id, site_id, device_id) in weak_signal:
                rssi = random.uniform(-95, -85)

            state = {
                "battery_pct": round(battery, 1),
                "temp_c": round(temp, 1),
                "rssi_dbm": int(rssi),
                "humidity_pct": round(humidity, 1),
            }
            await conn.execute(
                """
                INSERT INTO device_state (
                    tenant_id, site_id, device_id, status,
                    last_heartbeat_at, last_telemetry_at, last_seen_at,
                    state
                )
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8::jsonb)
                ON CONFLICT (tenant_id, device_id) DO UPDATE SET
                    site_id = EXCLUDED.site_id,
                    status = EXCLUDED.status,
                    last_heartbeat_at = EXCLUDED.last_heartbeat_at,
                    last_telemetry_at = EXCLUDED.last_telemetry_at,
                    last_seen_at = EXCLUDED.last_seen_at,
                    state = EXCLUDED.state
                """,
                tenant_id,
                site_id,
                device_id,
                status,
                last_ts,
                last_ts,
                last_ts,
                json.dumps(state),
            )


async def seed_notification_channels(pool):
    """Seed demo notification channels for each tenant (idempotent)."""
    channels_by_tenant = {
        "tenant-a": [
            (
                "Ops Email",
                "email",
                {
                    "smtp": {"host": "mailpit", "port": 1025, "from": "alerts@acme-iot.example"},
                    "recipients": ["ops@acme-iot.example"],
                },
            ),
            (
                "Slack Webhook",
                "webhook",
                {"url": "https://hooks.slack.example/services/DEMO123", "secret": "demo-secret"},
            ),
            (
                "MQTT Alerts",
                "mqtt",
                {"broker_host": "iot-mqtt", "port": 1883, "topic": "alerts/acme"},
            ),
        ],
        "tenant-b": [
            (
                "Alert Notifications",
                "email",
                {
                    "smtp": {"host": "mailpit", "port": 1025, "from": "alerts@nordic.example"},
                    "recipients": ["monitoring@nordic.example"],
                },
            ),
            ("PagerDuty", "pagerduty", {"integration_key": "demo-pd-key-12345"}),
        ],
    }

    async with pool.acquire() as conn:
        for tenant_id in TENANTS:
            for name, channel_type, cfg in channels_by_tenant.get(tenant_id, []):
                existing = await conn.fetchval(
                    "SELECT COUNT(*) FROM notification_channels WHERE tenant_id = $1 AND name = $2",
                    tenant_id,
                    name,
                )
                if existing and int(existing) > 0:
                    continue
                await conn.execute(
                    """
                    INSERT INTO notification_channels (tenant_id, name, channel_type, config, is_enabled)
                    VALUES ($1, $2, $3, $4::jsonb, true)
                    """,
                    tenant_id,
                    name,
                    channel_type,
                    json.dumps(cfg or {}),
                )
    print("  ✓ notification_channels seeded")


async def seed_notification_routing_rules(pool):
    """Seed demo routing rules for each tenant (idempotent)."""
    async with pool.acquire() as conn:
        for tenant_id in TENANTS:
            if tenant_id == "tenant-a":
                email_name = "Ops Email"
                webhook_name = "Slack Webhook"
            else:
                email_name = "Alert Notifications"
                webhook_name = "PagerDuty"

            email_channel_id = await conn.fetchval(
                "SELECT channel_id FROM notification_channels WHERE tenant_id = $1 AND name = $2 ORDER BY channel_id LIMIT 1",
                tenant_id,
                email_name,
            )
            webhook_channel_id = await conn.fetchval(
                "SELECT channel_id FROM notification_channels WHERE tenant_id = $1 AND name = $2 ORDER BY channel_id LIMIT 1",
                tenant_id,
                webhook_name,
            )

            # Critical alerts -> email
            if email_channel_id:
                exists = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM notification_routing_rules
                    WHERE tenant_id = $1 AND channel_id = $2
                      AND min_severity = 1 AND alert_type IS NULL
                      AND throttle_minutes = 5
                    """,
                    tenant_id,
                    int(email_channel_id),
                )
                if not exists:
                    await conn.execute(
                        """
                        INSERT INTO notification_routing_rules
                            (tenant_id, channel_id, min_severity, alert_type, throttle_minutes, is_enabled)
                        VALUES ($1, $2, 1, NULL, 5, true)
                        """,
                        tenant_id,
                        int(email_channel_id),
                    )

            # All alerts -> webhook/pagerduty
            if webhook_channel_id:
                exists = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM notification_routing_rules
                    WHERE tenant_id = $1 AND channel_id = $2
                      AND min_severity IS NULL AND alert_type IS NULL
                      AND throttle_minutes = 15
                    """,
                    tenant_id,
                    int(webhook_channel_id),
                )
                if not exists:
                    await conn.execute(
                        """
                        INSERT INTO notification_routing_rules
                            (tenant_id, channel_id, min_severity, alert_type, throttle_minutes, is_enabled)
                        VALUES ($1, $2, NULL, NULL, 15, true)
                        """,
                        tenant_id,
                        int(webhook_channel_id),
                    )

    print("  ✓ notification_routing_rules seeded")


async def seed_escalation_policies(pool):
    """Seed a default escalation policy per tenant (idempotent)."""
    async with pool.acquire() as conn:
        for tenant_id in TENANTS:
            existing = await conn.fetchval(
                "SELECT COUNT(*) FROM escalation_policies WHERE tenant_id = $1 AND name = $2",
                tenant_id,
                "Default Escalation",
            )
            if not existing:
                await conn.execute(
                    """
                    INSERT INTO escalation_policies (tenant_id, name, description, is_default)
                    VALUES ($1, $2, $3, true)
                    """,
                    tenant_id,
                    "Default Escalation",
                    "Escalate unacknowledged alerts",
                )
            else:
                await conn.execute(
                    """
                    UPDATE escalation_policies
                    SET description = $3, is_default = true, updated_at = NOW()
                    WHERE tenant_id = $1 AND name = $2
                    """,
                    tenant_id,
                    "Default Escalation",
                    "Escalate unacknowledged alerts",
                )
    print("  ✓ escalation_policies seeded")


async def seed_escalation_levels(pool):
    """Seed escalation levels per tenant policy (idempotent)."""
    tenant_domains = {"tenant-a": "acme-iot.example", "tenant-b": "nordic.example"}
    async with pool.acquire() as conn:
        for tenant_id in TENANTS:
            policy_id = await conn.fetchval(
                """
                SELECT policy_id FROM escalation_policies
                WHERE tenant_id = $1 AND name = $2
                ORDER BY policy_id
                LIMIT 1
                """,
                tenant_id,
                "Default Escalation",
            )
            if not policy_id:
                continue

            domain = tenant_domains.get(tenant_id, "example")

            # Level 1
            await conn.execute(
                """
                INSERT INTO escalation_levels (policy_id, level_number, delay_minutes, notify_email, notify_webhook)
                VALUES ($1, 1, 15, $2, NULL)
                ON CONFLICT (policy_id, level_number) DO UPDATE SET
                    delay_minutes = EXCLUDED.delay_minutes,
                    notify_email = EXCLUDED.notify_email,
                    notify_webhook = EXCLUDED.notify_webhook
                """,
                int(policy_id),
                f"ops@{domain}",
            )

            # Level 2
            await conn.execute(
                """
                INSERT INTO escalation_levels (policy_id, level_number, delay_minutes, notify_email, notify_webhook)
                VALUES ($1, 2, 30, $2, $3)
                ON CONFLICT (policy_id, level_number) DO UPDATE SET
                    delay_minutes = EXCLUDED.delay_minutes,
                    notify_email = EXCLUDED.notify_email,
                    notify_webhook = EXCLUDED.notify_webhook
                """,
                int(policy_id),
                f"manager@{domain}",
                "https://hooks.slack.example/escalation",
            )
    print("  ✓ escalation_levels seeded")


async def seed_oncall_schedules(pool):
    """Seed on-call schedules (idempotent)."""
    schedules = {
        "tenant-a": {
            "name": "Primary On-Call",
            "description": "24/7 primary on-call rotation",
            "timezone": "America/New_York",
        },
        "tenant-b": {
            "name": "Business Hours",
            "description": "Business hours coverage",
            "timezone": "Europe/Stockholm",
        },
    }
    async with pool.acquire() as conn:
        for tenant_id in TENANTS:
            spec = schedules.get(tenant_id)
            if not spec:
                continue
            existing = await conn.fetchval(
                "SELECT schedule_id FROM oncall_schedules WHERE tenant_id = $1 AND name = $2 ORDER BY schedule_id LIMIT 1",
                tenant_id,
                spec["name"],
            )
            if existing:
                await conn.execute(
                    """
                    UPDATE oncall_schedules
                    SET description = $3, timezone = $4, updated_at = NOW()
                    WHERE tenant_id = $1 AND name = $2
                    """,
                    tenant_id,
                    spec["name"],
                    spec["description"],
                    spec["timezone"],
                )
            else:
                await conn.execute(
                    """
                    INSERT INTO oncall_schedules (tenant_id, name, description, timezone)
                    VALUES ($1, $2, $3, $4)
                    """,
                    tenant_id,
                    spec["name"],
                    spec["description"],
                    spec["timezone"],
                )
    print("  ✓ oncall_schedules seeded")


async def seed_oncall_layers(pool):
    """Seed on-call layers per schedule (idempotent)."""
    async with pool.acquire() as conn:
        # Tenant-a: Primary weekly rotation
        sched_a = await conn.fetchval(
            "SELECT schedule_id FROM oncall_schedules WHERE tenant_id = $1 AND name = $2 ORDER BY schedule_id LIMIT 1",
            "tenant-a",
            "Primary On-Call",
        )
        if sched_a:
            existing = await conn.fetchval(
                "SELECT layer_id FROM oncall_layers WHERE schedule_id = $1 AND layer_order = 0 ORDER BY layer_id LIMIT 1",
                int(sched_a),
            )
            if not existing:
                await conn.execute(
                    """
                    INSERT INTO oncall_layers (
                        schedule_id, name, rotation_type, shift_duration_hours,
                        handoff_day, handoff_hour, responders, layer_order
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8)
                    """,
                    int(sched_a),
                    "Primary",
                    "weekly",
                    168,
                    1,
                    9,
                    json.dumps(["demo-admin-tenant-a"]),
                    0,
                )

        # Tenant-b: Business hours daily rotation
        sched_b = await conn.fetchval(
            "SELECT schedule_id FROM oncall_schedules WHERE tenant_id = $1 AND name = $2 ORDER BY schedule_id LIMIT 1",
            "tenant-b",
            "Business Hours",
        )
        if sched_b:
            existing = await conn.fetchval(
                "SELECT layer_id FROM oncall_layers WHERE schedule_id = $1 AND layer_order = 0 ORDER BY layer_id LIMIT 1",
                int(sched_b),
            )
            if not existing:
                await conn.execute(
                    """
                    INSERT INTO oncall_layers (
                        schedule_id, name, rotation_type, shift_duration_hours,
                        handoff_day, handoff_hour, responders, layer_order
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8)
                    """,
                    int(sched_b),
                    "Weekday",
                    "daily",
                    8,
                    1,
                    8,
                    json.dumps(["demo-admin-tenant-b"]),
                    0,
                )
    print("  ✓ oncall_layers seeded")


async def seed_oncall_overrides(pool):
    """Seed an example on-call override (idempotent, optional)."""
    async with pool.acquire() as conn:
        sched_a = await conn.fetchval(
            "SELECT schedule_id FROM oncall_schedules WHERE tenant_id = $1 AND name = $2 ORDER BY schedule_id LIMIT 1",
            "tenant-a",
            "Primary On-Call",
        )
        if not sched_a:
            print("  ✓ oncall_overrides seeded")
            return

        start_at = now_utc() + timedelta(days=7)
        end_at = now_utc() + timedelta(days=8)

        existing = await conn.fetchval(
            """
            SELECT COUNT(*) FROM oncall_overrides
            WHERE schedule_id = $1 AND responder = $2 AND reason = $3
            """,
            int(sched_a),
            "demo-admin-tenant-a",
            "PTO coverage",
        )
        if not existing:
            await conn.execute(
                """
                INSERT INTO oncall_overrides (schedule_id, layer_id, responder, start_at, end_at, reason)
                VALUES ($1, NULL, $2, $3, $4, $5)
                """,
                int(sched_a),
                "demo-admin-tenant-a",
                start_at,
                end_at,
                "PTO coverage",
            )
    print("  ✓ oncall_overrides seeded")


async def seed_user_preferences(pool):
    """Seed user preferences for demo admin users (idempotent)."""
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO user_preferences (tenant_id, user_id, display_name, timezone, notification_prefs)
            VALUES ($1, $2, $3, $4, $5::jsonb)
            ON CONFLICT (tenant_id, user_id) DO NOTHING
            """,
            "tenant-a",
            "demo-admin-tenant-a",
            "Admin User",
            "America/New_York",
            json.dumps({"email_enabled": True, "push_enabled": True, "digest_frequency": "daily"}),
        )
        await conn.execute(
            """
            INSERT INTO user_preferences (tenant_id, user_id, display_name, timezone, notification_prefs)
            VALUES ($1, $2, $3, $4, $5::jsonb)
            ON CONFLICT (tenant_id, user_id) DO NOTHING
            """,
            "tenant-b",
            "demo-admin-tenant-b",
            "Nordic Admin",
            "Europe/Stockholm",
            json.dumps({"email_enabled": True, "push_enabled": False, "digest_frequency": "weekly"}),
        )
    print("  ✓ user_preferences seeded")


async def seed_firmware_versions(pool):
    """Seed firmware versions (idempotent)."""
    firmware_data = [
        {
            "version": "1.0.0",
            "description": "Initial release - basic telemetry and heartbeat",
            "file_url": "https://firmware.example.com/v1.0.0/firmware.bin",
            "file_size_bytes": 524288,
            "checksum_sha256": "a" * 64,
            "device_type": "sensor",
        },
        {
            "version": "1.1.0",
            "description": "Added OTA update support and improved power management",
            "file_url": "https://firmware.example.com/v1.1.0/firmware.bin",
            "file_size_bytes": 589824,
            "checksum_sha256": "b" * 64,
            "device_type": "sensor",
        },
    ]
    async with pool.acquire() as conn:
        for tenant_id in TENANTS:
            for fw in firmware_data:
                await conn.execute(
                    """
                    INSERT INTO firmware_versions (
                        tenant_id, version, description, file_url, file_size_bytes,
                        checksum_sha256, device_type, created_by
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (tenant_id, version, device_type) DO NOTHING
                    """,
                    tenant_id,
                    fw["version"],
                    fw["description"],
                    fw["file_url"],
                    fw["file_size_bytes"],
                    fw["checksum_sha256"],
                    fw["device_type"],
                    f"demo-admin-{tenant_id}",
                )
    print("  ✓ firmware_versions seeded")


async def seed_ota_campaigns(pool):
    """Seed a completed OTA campaign per tenant (idempotent)."""
    async with pool.acquire() as conn:
        for tenant_id in TENANTS:
            existing = await conn.fetchval(
                "SELECT COUNT(*) FROM ota_campaigns WHERE tenant_id = $1 AND name = $2",
                tenant_id,
                "Fleet Update to v1.1.0",
            )
            if existing and int(existing) > 0:
                continue

            fw_id = await conn.fetchval(
                """
                SELECT id FROM firmware_versions
                WHERE tenant_id = $1 AND version = $2 AND device_type = $3
                """,
                tenant_id,
                "1.1.0",
                "sensor",
            )
            if not fw_id:
                continue

            device_count = await conn.fetchval(
                "SELECT COUNT(*) FROM device_registry WHERE tenant_id = $1", tenant_id
            )
            total = int(device_count or 15)
            succeeded = max(total - 1, 0)
            failed = 1 if total > 0 else 0

            await conn.execute(
                """
                INSERT INTO ota_campaigns (
                    tenant_id, name, firmware_version_id, target_group_id,
                    rollout_strategy, rollout_rate, abort_threshold, status,
                    total_devices, succeeded, failed, started_at, completed_at, created_by
                )
                VALUES (
                    $1, $2, $3, $4,
                    $5, $6, $7, $8,
                    $9, $10, $11,
                    NOW() - INTERVAL '2 days', NOW() - INTERVAL '1 day', $12
                )
                """,
                tenant_id,
                "Fleet Update to v1.1.0",
                int(fw_id),
                "all",
                "linear",
                20,
                0.1,
                "COMPLETED",
                total,
                succeeded,
                failed,
                f"demo-admin-{tenant_id}",
            )
    print("  ✓ ota_campaigns seeded")


async def seed_ota_device_status(pool):
    """Seed per-device OTA status for the seeded campaigns (idempotent)."""
    async with pool.acquire() as conn:
        for tenant_id in TENANTS:
            campaign_id = await conn.fetchval(
                "SELECT id FROM ota_campaigns WHERE tenant_id = $1 AND name = $2",
                tenant_id,
                "Fleet Update to v1.1.0",
            )
            if not campaign_id:
                continue

            devices = await conn.fetch(
                "SELECT device_id FROM device_registry WHERE tenant_id = $1 ORDER BY device_id",
                tenant_id,
            )

            for i, device in enumerate(devices):
                status = "FAILED" if i == 0 else "SUCCESS"
                error_msg = "Checksum mismatch after download" if status == "FAILED" else None
                progress = 100 if status in ("SUCCESS", "FAILED") else 0
                await conn.execute(
                    """
                    INSERT INTO ota_device_status (
                        tenant_id, campaign_id, device_id, status,
                        progress_pct, started_at, completed_at, error_message
                    )
                    VALUES (
                        $1, $2, $3, $4,
                        $5,
                        NOW() - INTERVAL '2 days' + ($6 * INTERVAL '10 minutes'),
                        NOW() - INTERVAL '1 day' + ($6 * INTERVAL '5 minutes'),
                        $7
                    )
                    ON CONFLICT (tenant_id, campaign_id, device_id) DO NOTHING
                    """,
                    tenant_id,
                    int(campaign_id),
                    device["device_id"],
                    status,
                    progress,
                    i,
                    error_msg,
                )
    print("  ✓ ota_device_status seeded")


async def seed_dashboards(pool):
    """Seed one default dashboard per tenant (idempotent)."""
    default_layout = [
        {"i": "w1", "x": 0, "y": 0, "w": 3, "h": 2},
        {"i": "w2", "x": 3, "y": 0, "w": 3, "h": 2},
        {"i": "w3", "x": 0, "y": 2, "w": 6, "h": 3},
        {"i": "w4", "x": 0, "y": 5, "w": 6, "h": 3},
    ]
    async with pool.acquire() as conn:
        for tenant_id in TENANTS:
            existing = await conn.fetchval(
                "SELECT COUNT(*) FROM dashboards WHERE tenant_id = $1 AND is_default = TRUE",
                tenant_id,
            )
            if existing and int(existing) > 0:
                continue
            await conn.fetchval(
                """
                INSERT INTO dashboards (tenant_id, user_id, name, description, is_default, layout)
                VALUES ($1, NULL, $2, $3, TRUE, $4::jsonb)
                RETURNING id
                """,
                tenant_id,
                "Fleet Overview",
                "Default dashboard showing fleet health at a glance",
                json.dumps(default_layout),
            )
    print("  ✓ dashboards seeded")


async def seed_dashboard_widgets(pool):
    """Seed widgets for the default dashboard (idempotent)."""
    widgets = [
        {
            "widget_type": "kpi",
            "title": "Total Devices",
            "config": {"metric": "device_count", "format": "number"},
            "position": {"x": 0, "y": 0, "w": 3, "h": 2},
        },
        {
            "widget_type": "kpi",
            "title": "Open Alerts",
            "config": {
                "metric": "open_alert_count",
                "format": "number",
                "thresholds": {"warning": 5, "critical": 10},
            },
            "position": {"x": 3, "y": 0, "w": 3, "h": 2},
        },
        {
            "widget_type": "chart",
            "title": "Temperature Trend",
            "config": {
                "metric": "temp_c",
                "chart_type": "line",
                "time_range": "24h",
                "aggregation": "avg",
            },
            "position": {"x": 0, "y": 2, "w": 6, "h": 3},
        },
        {
            "widget_type": "table",
            "title": "Recent Alerts",
            "config": {
                "source": "alerts",
                "limit": 10,
                "columns": ["severity", "device_id", "message", "created_at"],
            },
            "position": {"x": 0, "y": 5, "w": 6, "h": 3},
        },
    ]
    async with pool.acquire() as conn:
        for tenant_id in TENANTS:
            dashboard_id = await conn.fetchval(
                "SELECT id FROM dashboards WHERE tenant_id = $1 AND is_default = TRUE ORDER BY id LIMIT 1",
                tenant_id,
            )
            if not dashboard_id:
                continue

            existing_count = await conn.fetchval(
                "SELECT COUNT(*) FROM dashboard_widgets WHERE dashboard_id = $1",
                int(dashboard_id),
            )
            if existing_count and int(existing_count) > 0:
                continue

            for widget in widgets:
                await conn.execute(
                    """
                    INSERT INTO dashboard_widgets (dashboard_id, widget_type, title, config, position)
                    VALUES ($1, $2, $3, $4::jsonb, $5::jsonb)
                    """,
                    int(dashboard_id),
                    widget["widget_type"],
                    widget["title"],
                    json.dumps(widget["config"]),
                    json.dumps(widget["position"]),
                )
    print("  ✓ dashboard_widgets seeded")


async def seed_message_routes(pool):
    """Seed message routing rules (idempotent)."""
    routes_data = {
        "tenant-a": {
            "name": "Production Telemetry Forward",
            "topic_filter": "tenant/tenant-a/device/+/telemetry",
            "destination_type": "webhook",
            "destination_config": {
                "url": "https://analytics.acme-iot.example/ingest",
                "method": "POST",
                "headers": {"X-API-Key": "demo-key"},
            },
        },
        "tenant-b": {
            "name": "Alert Webhook",
            "topic_filter": "tenant/tenant-b/device/+/alerts",
            "destination_type": "webhook",
            "destination_config": {"url": "https://monitoring.nordic.example/webhook", "method": "POST"},
        },
    }
    async with pool.acquire() as conn:
        for tenant_id, route in routes_data.items():
            existing = await conn.fetchval(
                "SELECT COUNT(*) FROM message_routes WHERE tenant_id = $1 AND name = $2",
                tenant_id,
                route["name"],
            )
            if existing and int(existing) > 0:
                continue
            await conn.execute(
                """
                INSERT INTO message_routes (tenant_id, name, topic_filter, destination_type, destination_config, is_enabled)
                VALUES ($1, $2, $3, $4, $5::jsonb, TRUE)
                """,
                tenant_id,
                route["name"],
                route["topic_filter"],
                route["destination_type"],
                json.dumps(route["destination_config"]),
            )
    print("  ✓ message_routes seeded")


async def seed_export_jobs(pool):
    """Seed one completed export job per tenant (idempotent)."""
    async with pool.acquire() as conn:
        for tenant_id in TENANTS:
            job_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"demo-export-{tenant_id}"))
            existing = await conn.fetchval("SELECT COUNT(*) FROM export_jobs WHERE id = $1", job_id)
            if existing and int(existing) > 0:
                continue
            await conn.execute(
                """
                INSERT INTO export_jobs (
                    id, tenant_id, export_type, format, filters, status,
                    file_path, file_size_bytes, row_count, created_by,
                    started_at, completed_at, expires_at
                )
                VALUES (
                    $1, $2, $3, $4, $5::jsonb, $6,
                    $7, $8, $9, $10,
                    NOW() - INTERVAL '3 hours', NOW() - INTERVAL '2 hours 55 minutes',
                    NOW() + INTERVAL '21 hours'
                )
                """,
                job_id,
                tenant_id,
                "devices",
                "csv",
                json.dumps({"status": "ONLINE"}),
                "COMPLETED",
                f"/exports/{tenant_id}/devices-export.csv",
                15360,
                30,
                f"demo-admin-{tenant_id}",
            )
    print("  ✓ export_jobs seeded")


async def seed_alert_rules(pool):
    rule_ids = {}
    async with pool.acquire() as conn:
        for tenant_id in TENANTS:
            for rule in RULES_TEMPLATE:
                # Deterministic IDs make the seed script idempotent across runs.
                rule_id = str(
                    uuid.uuid5(uuid.NAMESPACE_DNS, f"seed:{tenant_id}:alert-rule:{rule['name']}")
                )
                await conn.execute(
                    """
                    INSERT INTO alert_rules (
                        tenant_id, rule_id, name, enabled,
                        metric_name, operator, threshold, severity, description
                    )
                    VALUES ($1,$2,$3,true,$4,$5,$6,$7,$8)
                    ON CONFLICT (tenant_id, rule_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        enabled = EXCLUDED.enabled,
                        metric_name = EXCLUDED.metric_name,
                        operator = EXCLUDED.operator,
                        threshold = EXCLUDED.threshold,
                        severity = EXCLUDED.severity,
                        description = EXCLUDED.description
                    """,
                    tenant_id,
                    rule_id,
                    rule["name"],
                    rule["metric_name"],
                    rule["operator"],
                    rule["threshold"],
                    rule["severity"],
                    rule["description"],
                )
                rule_ids[(tenant_id, rule["name"])] = rule_id
    return rule_ids


async def seed_fleet_alerts(pool, devices, stale, low_battery, rule_ids):
    now = now_utc()
    async with pool.acquire() as conn:
        for tenant_id, site_id, device_id in devices:
            if (tenant_id, site_id, device_id) in stale:
                fp = f"NO_HEARTBEAT:{device_id}"
                exists_any = await conn.fetchval(
                    "SELECT COUNT(*) FROM fleet_alert WHERE tenant_id = $1 AND fingerprint = $2",
                    tenant_id,
                    fp,
                )
                if exists_any and int(exists_any) > 0:
                    continue
                await conn.execute(
                    """
                    INSERT INTO fleet_alert (
                        tenant_id, site_id, device_id, alert_type,
                        fingerprint, status, severity, confidence, summary, details
                    )
                    VALUES ($1,$2,$3,'NO_HEARTBEAT',$4,'OPEN',$5,$6,$7,$8::jsonb)
                    ON CONFLICT (tenant_id, fingerprint) WHERE (status='OPEN') DO NOTHING
                    """,
                    tenant_id,
                    site_id,
                    device_id,
                    fp,
                    4,
                    0.9,
                    f"Device {device_id} has not sent heartbeat",
                    json.dumps({"last_heartbeat_at": now.isoformat()}),
                )

            if (tenant_id, site_id, device_id) in low_battery:
                battery = random.uniform(15, 24)
                rule_id = rule_ids.get((tenant_id, "Low Battery Warning"))
                fp = f"RULE:{rule_id}:{device_id}"
                exists_any = await conn.fetchval(
                    "SELECT COUNT(*) FROM fleet_alert WHERE tenant_id = $1 AND fingerprint = $2",
                    tenant_id,
                    fp,
                )
                if exists_any and int(exists_any) > 0:
                    continue
                await conn.execute(
                    """
                    INSERT INTO fleet_alert (
                        tenant_id, site_id, device_id, alert_type,
                        fingerprint, status, severity, confidence, summary, details
                    )
                    VALUES ($1,$2,$3,'THRESHOLD',$4,'OPEN',$5,$6,$7,$8::jsonb)
                    ON CONFLICT (tenant_id, fingerprint) WHERE (status='OPEN') DO NOTHING
                    """,
                    tenant_id,
                    site_id,
                    device_id,
                    fp,
                    2,
                    0.8,
                    f"Low Battery Warning: {device_id} battery at {battery:.1f}%",
                    json.dumps({
                        "rule_id": rule_id,
                        "rule_name": "Low Battery Warning",
                        "metric_name": "battery_pct",
                        "metric_value": round(battery, 1),
                        "operator": "LT",
                        "threshold": 25.0,
                    }),
                )


async def seed_timescaledb(pool, devices):
    """Seed 7 days of telemetry data into TimescaleDB."""
    # Idempotency guard: don't append another 7 days every run.
    async with pool.acquire() as conn:
        existing = await conn.fetchval(
            "SELECT COUNT(*) FROM telemetry WHERE time > NOW() - INTERVAL '7 days' LIMIT 1"
        )
        if existing and int(existing) > 0:
            print("  [skip] telemetry already seeded in last 7 days")
            return

    start = now_utc() - timedelta(days=7)
    interval = timedelta(minutes=5)
    points_per_device = int((7 * 24 * 60) / 5)
    batch_size = 1000

    print(f"  Generating {points_per_device} points per device ({len(devices)} devices)...")

    async with pool.acquire() as conn:
        batch = []
        total_written = 0

        for tenant_id, site_id, device_id in devices:
            battery = 100.0
            rssi = -65.0
            seq = 0
            ts = start

            for _ in range(points_per_device):
                seq += 1
                battery -= 0.5 / 12
                if battery < 5 or random.random() < 0.005:
                    battery = 100.0
                daily_phase = (ts.hour + ts.minute / 60) / 24.0
                temp = 22 + (4 * (1 + math.sin(daily_phase * 2 * math.pi)) / 2) + random.uniform(-2, 2)
                rssi += random.uniform(-2, 2)
                rssi = max(-100, min(-30, rssi))
                humidity = 50 + random.uniform(-10, 10)

                metrics = {
                    "battery_pct": round(battery, 1),
                    "temp_c": round(temp, 1),
                    "rssi_dbm": int(rssi),
                    "humidity_pct": round(humidity, 1),
                }

                # Telemetry record
                batch.append((
                    ts,
                    tenant_id,
                    device_id,
                    site_id,
                    "telemetry",
                    seq,
                    json.dumps(metrics),
                ))

                # Heartbeat record
                batch.append((
                    ts,
                    tenant_id,
                    device_id,
                    site_id,
                    "heartbeat",
                    seq,
                    json.dumps({"seq": seq}),
                ))

                if len(batch) >= batch_size:
                    await conn.executemany(
                        """
                        INSERT INTO telemetry (time, tenant_id, device_id, site_id, msg_type, seq, metrics)
                        VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
                        ON CONFLICT DO NOTHING
                        """,
                        batch,
                    )
                    total_written += len(batch)
                    batch = []
                    if total_written % 10000 == 0:
                        print(f"  Written {total_written} records...")

                ts += interval

        # Write remaining batch
        if batch:
            await conn.executemany(
                """
                INSERT INTO telemetry (time, tenant_id, device_id, site_id, msg_type, seq, metrics)
                VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
                ON CONFLICT DO NOTHING
                """,
                batch,
            )
            total_written += len(batch)

        print(f"  Total: {total_written} telemetry records written")


async def verify_seed(pool):
    """Report row counts for all seeded tables."""
    print("\n" + "=" * 60)
    print("SEED VERIFICATION REPORT")
    print("=" * 60)

    tables = [
        "tenants",
        "device_registry",
        "device_state",
        "alert_rules",
        "fleet_alert",
        "notification_channels",
        "notification_routing_rules",
        "escalation_policies",
        "escalation_levels",
        "oncall_schedules",
        "oncall_layers",
        "oncall_overrides",
        "firmware_versions",
        "ota_campaigns",
        "ota_device_status",
        "dashboards",
        "dashboard_widgets",
        "message_routes",
        "export_jobs",
        "dynamic_device_groups",
        "device_connection_events",
        "device_certificates",
        "user_preferences",
        "roles",
        "permissions",
        "role_permissions",
    ]

    async with pool.acquire() as conn:
        all_ok = True
        for table in tables:
            try:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                status = "✓" if count and int(count) > 0 else "✗"
                if not count or int(count) == 0:
                    all_ok = False
                print(f"  {status} {table}: {int(count or 0)} rows")
            except Exception:
                print(f"  ? {table}: table not found (migration may not have run)")

    print("=" * 60)
    if all_ok:
        print("ALL TABLES SEEDED SUCCESSFULLY")
    else:
        print("WARNING: Some tables are empty. Check errors above.")
    print("=" * 60)


async def bootstrap_keycloak_profile():
    """Ensure Keycloak pulse realm has tenant_id in user profile attributes."""
    print("Bootstrapping Keycloak user profile...")

    async with httpx.AsyncClient(timeout=30) as client:
        # Get admin token
        token_resp = await client.post(
            f"{KEYCLOAK_INTERNAL_URL}/realms/master/protocol/openid-connect/token",
            data={
                "client_id": "admin-cli",
                "username": "admin",
                "password": KEYCLOAK_ADMIN_PASSWORD,
                "grant_type": "password",
            },
        )
        token_resp.raise_for_status()
        token = token_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Get current user profile config
        profile_resp = await client.get(
            f"{KEYCLOAK_INTERNAL_URL}/admin/realms/pulse/users/profile",
            headers=headers,
        )
        profile_resp.raise_for_status()
        profile = profile_resp.json()

        # Check if tenant_id attribute already exists
        attr_names = [a["name"] for a in profile.get("attributes", [])]
        if "tenant_id" in attr_names:
            print("  tenant_id attribute already exists — skipping.")
            return

        # Add tenant_id attribute
        profile.setdefault("attributes", []).append(
            {
                "name": "tenant_id",
                "displayName": "Tenant ID",
                "validations": {},
                "annotations": {},
                "permissions": {"view": ["admin", "user"], "edit": ["admin"]},
                "multivalued": False,
            }
        )

        put_resp = await client.put(
            f"{KEYCLOAK_INTERNAL_URL}/admin/realms/pulse/users/profile",
            headers=headers,
            json=profile,
        )
        put_resp.raise_for_status()
        print("  tenant_id attribute added to user profile.")


async def main():
    parser = argparse.ArgumentParser(description="Seed demo data")
    parser.add_argument(
        "--tables",
        type=str,
        default=None,
        help="Comma-separated table groups to seed (e.g., 'notifications,ota,dashboards'). Default: all.",
    )
    args = parser.parse_args()

    # Bootstrap Keycloak profile (idempotent)
    try:
        await bootstrap_keycloak_profile()
    except Exception as e:
        print(f"  Warning: Keycloak bootstrap skipped ({e})")

    devices = list(iter_devices())
    stale, low_battery, high_temp, weak_signal = pick_special_devices(devices)

    print("Connecting to PostgreSQL...")
    pool = await asyncpg.create_pool(
        host=PG_HOST,
        port=PG_PORT,
        database=PG_DB,
        user=PG_USER,
        password=PG_PASS,
        min_size=1,
        max_size=5,
    )

    # Wrappers (some seed fns need extra parameters).
    async def _seed_tenants():
        print("Seeding tenants...")
        await seed_tenants(pool)

    async def _seed_tiers():
        await ensure_subscription_plan_ids(pool)
        await seed_tier_allocations(pool)

    async def _seed_roles():
        async with pool.acquire() as conn:
            await seed_role_assignments(conn)

    async def _seed_devices():
        print("Seeding device_registry...")
        await seed_device_registry(pool, devices)
        await seed_device_tiers(pool)

    async def _seed_device_state():
        print("Seeding device_state...")
        await seed_device_state(pool, devices, stale, low_battery, high_temp, weak_signal)

    async def _seed_groups():
        await seed_dynamic_device_groups(pool)

    async def _seed_connections():
        await seed_device_connection_events(pool)

    async def _seed_certificates():
        await seed_device_certificates(pool)

    async def _seed_notifications():
        await seed_notification_channels(pool)
        await seed_notification_routing_rules(pool)

    async def _seed_escalation():
        await seed_escalation_policies(pool)
        await seed_escalation_levels(pool)

    async def _seed_oncall():
        await seed_oncall_schedules(pool)
        await seed_oncall_layers(pool)
        await seed_oncall_overrides(pool)

    async def _seed_preferences():
        await seed_user_preferences(pool)

    async def _seed_ota():
        await seed_firmware_versions(pool)
        await seed_ota_campaigns(pool)
        await seed_ota_device_status(pool)

    async def _seed_dashboards():
        await seed_dashboards(pool)
        await seed_dashboard_widgets(pool)

    async def _seed_routes():
        await seed_message_routes(pool)

    async def _seed_exports():
        await seed_export_jobs(pool)

    async def _seed_alerts():
        print("Seeding alert_rules...")
        rule_ids = await seed_alert_rules(pool)
        print("Seeding fleet_alert...")
        await seed_fleet_alerts(pool, devices, stale, low_battery, rule_ids)

    async def _seed_telemetry():
        print("Seeding TimescaleDB telemetry (7 days)...")
        await seed_timescaledb(pool, devices)

    # Dependency order matters; dict preserves insertion order.
    table_groups = {
        "tenants": [_seed_tenants],
        "tiers": [_seed_tiers],
        "roles": [_seed_roles],
        "devices": [_seed_devices, _seed_device_state],
        "groups": [_seed_groups],
        "connections": [_seed_connections],
        "certificates": [_seed_certificates],
        "notifications": [_seed_notifications],
        "escalation": [_seed_escalation],
        "oncall": [_seed_oncall],
        "preferences": [_seed_preferences],
        "ota": [_seed_ota],
        "dashboards": [_seed_dashboards],
        "routes": [_seed_routes],
        "exports": [_seed_exports],
        "alerts": [_seed_alerts],
        "telemetry": [_seed_telemetry],
    }

    async def run_fns(fns):
        for fn in fns:
            try:
                await fn()
            except Exception as e:
                print(f"  ✗ {fn.__name__} failed: {e}")

    if args.tables:
        selected = [t.strip() for t in args.tables.split(",") if t.strip()]
        for group_name in selected:
            if group_name not in table_groups:
                print(f"  ✗ Unknown table group: {group_name}")
                print(f"    Available: {', '.join(sorted(table_groups.keys()))}")
                continue
            await run_fns(table_groups[group_name])
    else:
        for _, fns in table_groups.items():
            await run_fns(fns)

    # Always verify at the end.
    await verify_seed(pool)

    print("Done!")
    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
