# 137-002: On-Call Schedules & User Preferences

## Task
Add seed functions for oncall_schedules, oncall_layers, oncall_overrides, and user_preferences.

## File
`scripts/seed_demo_data.py`

## 1. seed_oncall_schedules

Create 1 schedule per tenant:

**Tenant-a**:
- `name="Primary On-Call"`, `description="24/7 primary on-call rotation"`, `timezone="America/New_York"`

**Tenant-b**:
- `name="Business Hours"`, `description="Business hours coverage"`, `timezone="Europe/Stockholm"`

**Idempotency**: Check existence before insert (or use a unique constraint if available on tenant_id + name).

## 2. seed_oncall_layers

Create 1-2 layers per schedule:

**Tenant-a Primary On-Call**:
- Layer 1: `name="Primary"`, `rotation_type="weekly"`, `shift_duration_hours=168`, `handoff_day=1` (Monday), `handoff_hour=9`, `responders=["demo-admin-tenant-a"]`, `layer_order=0`

**Tenant-b Business Hours**:
- Layer 1: `name="Weekday"`, `rotation_type="daily"`, `shift_duration_hours=8`, `handoff_day=1`, `handoff_hour=8`, `responders=["demo-admin-tenant-b"]`, `layer_order=0`

**Responders is JSONB**: Pass `json.dumps(["demo-admin-tenant-a"])`.

## 3. seed_oncall_overrides (optional)

Create 1 override per tenant (showing a PTO/coverage swap):
- `schedule_id` = fetched from oncall_schedules
- `responder="demo-admin-tenant-a"`, `start_at=NOW() + interval '7 days'`, `end_at=NOW() + interval '8 days'`
- `reason="PTO coverage"`

This is optional — the frontend should display even with 0 overrides. But adding one shows the feature works.

## 4. seed_user_preferences

Create preferences for each demo admin user:

**Tenant-a admin**:
```python
await conn.execute("""
    INSERT INTO user_preferences (tenant_id, user_id, display_name, timezone, notification_prefs)
    VALUES ($1, $2, $3, $4, $5::jsonb)
    ON CONFLICT (tenant_id, user_id) DO NOTHING
""",
    "tenant-a",
    "demo-admin-tenant-a",
    "Admin User",
    "America/New_York",
    json.dumps({"email_enabled": True, "push_enabled": True, "digest_frequency": "daily"})
)
```

**Tenant-b admin**:
```python
await conn.execute("""
    INSERT INTO user_preferences (tenant_id, user_id, display_name, timezone, notification_prefs)
    VALUES ($1, $2, $3, $4, $5::jsonb)
    ON CONFLICT (tenant_id, user_id) DO NOTHING
""",
    "tenant-b",
    "demo-admin-tenant-b",
    "Nordic Admin",
    "Europe/Stockholm",
    json.dumps({"email_enabled": True, "push_enabled": False, "digest_frequency": "weekly"})
)
```

## 5. Wire Up in main()

Add calls after notification/escalation seeding:
```python
await seed_oncall_schedules(pool)
await seed_oncall_layers(pool)
await seed_oncall_overrides(pool)  # optional
await seed_user_preferences(pool)
```

## Verification
```sql
SELECT tenant_id, name, timezone FROM oncall_schedules;
-- 2 rows
SELECT s.name, l.name, l.rotation_type, l.responders FROM oncall_layers l JOIN oncall_schedules s ON l.schedule_id = s.schedule_id;
-- 2 rows
SELECT tenant_id, user_id, timezone FROM user_preferences;
-- 2 rows
```
