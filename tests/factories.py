from datetime import datetime, timezone


class FakeRecord(dict):
    """Dict subclass that supports attribute-style access (row.col)."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


def fake_tenant(overrides: dict | None = None) -> FakeRecord:
    record = FakeRecord(
        {
            "tenant_id": "tenant-a",
            "name": "Acme Corp",
            "stripe_customer_id": "cus_test123",
            "billing_email": "billing@example.com",
            "contact_email": "contact@example.com",
            "account_tier_id": "growth",
            "subscription_status": "active",
            "subscription_id": "sub_main_001",
            "plan_id": "basic",
            "trial_end": None,
            "created_at": datetime.now(timezone.utc),
        }
    )
    if overrides:
        record.update(overrides)
    return record


def fake_device(overrides: dict | None = None) -> FakeRecord:
    record = FakeRecord(
        {
            "tenant_id": "tenant-a",
            "device_id": "device-1",
            "site_id": "site-1",
            "status": "ONLINE",
            "last_seen_at": datetime.now(timezone.utc),
            "plan_id": "basic",
            "model": "TestModel",
            "tags": [],
        }
    )
    if overrides:
        record.update(overrides)
    return record


def fake_device_plan(overrides: dict | None = None) -> FakeRecord:
    record = FakeRecord(
        {
            "plan_id": "basic",
            "name": "Basic",
            "max_devices": 100,
            "price_monthly": 0,
            "stripe_price_id": "price_basic",
            "is_active": True,
        }
    )
    if overrides:
        record.update(overrides)
    return record


def fake_site(overrides: dict | None = None) -> FakeRecord:
    record = FakeRecord(
        {
            "site_id": "site-1",
            "tenant_id": "tenant-a",
            "name": "HQ",
            "location": "Test City",
            "latitude": 0.0,
            "longitude": 0.0,
            "created_at": datetime.now(timezone.utc),
        }
    )
    if overrides:
        record.update(overrides)
    return record


def fake_alert(overrides: dict | None = None) -> FakeRecord:
    record = FakeRecord(
        {
            "alert_id": 1,
            "tenant_id": "tenant-a",
            "device_id": "device-1",
            "alert_type": "temp_high",
            "severity": 3,
            "status": "OPEN",
            "created_at": datetime.now(timezone.utc),
            "trigger_count": 1,
        }
    )
    if overrides:
        record.update(overrides)
    return record
