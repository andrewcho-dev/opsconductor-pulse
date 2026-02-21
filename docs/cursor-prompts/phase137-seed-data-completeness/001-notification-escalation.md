# 137-001: Notification Channels & Escalation Policies

## Task
Add seed functions for notification_channels, notification_routing_rules, escalation_policies, and escalation_levels.

## File
`scripts/seed_demo_data.py`

## Existing Pattern to Follow
```python
async def seed_example(pool):
    async with pool.acquire() as conn:
        for tenant_id in TENANTS:
            await conn.execute("""
                INSERT INTO example_table (tenant_id, name, ...)
                VALUES ($1, $2, ...)
                ON CONFLICT ... DO NOTHING
            """, tenant_id, ...)
    print(f"  ✓ example_table seeded")
```

## 1. seed_notification_channels

Create 3 channels per tenant:

**Tenant-a (Acme IoT Corp)**:
1. Email channel: `name="Ops Email"`, `channel_type="email"`, `config={"smtp": {"host": "mailpit", "port": 1025, "from": "alerts@acme-iot.example"}, "recipients": ["ops@acme-iot.example"]}`
2. Webhook channel: `name="Slack Webhook"`, `channel_type="webhook"`, `config={"url": "https://hooks.slack.example/services/DEMO123", "secret": "demo-secret"}`
3. MQTT channel: `name="MQTT Alerts"`, `channel_type="mqtt"`, `config={"broker_host": "iot-mqtt", "port": 1883, "topic": "alerts/acme"}`

**Tenant-b (Nordic Sensors AB)**:
1. Email channel: `name="Alert Notifications"`, `channel_type="email"`, `config={"smtp": {"host": "mailpit", "port": 1025, "from": "alerts@nordic.example"}, "recipients": ["monitoring@nordic.example"]}`
2. Webhook channel: `name="PagerDuty"`, `channel_type="pagerduty"`, `config={"integration_key": "demo-pd-key-12345"}`

**Idempotency**: Use `ON CONFLICT (tenant_id, name) DO NOTHING` — but check if the table has a unique constraint on (tenant_id, name). If not, check existence before insert:
```python
existing = await conn.fetchval(
    "SELECT COUNT(*) FROM notification_channels WHERE tenant_id = $1 AND name = $2",
    tenant_id, channel_name
)
if existing == 0:
    await conn.execute("INSERT INTO ...")
```

**Config must be JSONB**: Use `json.dumps(config_dict)` when passing to asyncpg, or pass the dict directly if asyncpg handles JSONB conversion.

## 2. seed_notification_routing_rules

Create 2 routing rules per tenant (after channels are inserted):

1. Critical alerts → email: `min_severity=1`, `alert_type=NULL` (any type), `channel_id` = email channel ID, `throttle_minutes=5`
2. All alerts → webhook: `min_severity=NULL` (any severity), `channel_id` = webhook channel ID, `throttle_minutes=15`

**Must fetch channel_id after insert**:
```python
email_channel_id = await conn.fetchval(
    "SELECT channel_id FROM notification_channels WHERE tenant_id = $1 AND name = $2",
    tenant_id, "Ops Email"  # or appropriate name
)
```

## 3. seed_escalation_policies

Create 1 policy per tenant:
- `name="Default Escalation"`, `description="Escalate unacknowledged alerts"`, `is_default=TRUE`

## 4. seed_escalation_levels

Create 2 levels per policy (after policies inserted):
- Level 1: `delay_minutes=15`, `notify_email="ops@{tenant-domain}"`, `notify_webhook=NULL`
- Level 2: `delay_minutes=30`, `notify_email="manager@{tenant-domain}"`, `notify_webhook="https://hooks.slack.example/escalation"`

**Must fetch policy_id after insert**:
```python
policy_id = await conn.fetchval(
    "SELECT policy_id FROM escalation_policies WHERE tenant_id = $1 AND name = $2",
    tenant_id, "Default Escalation"
)
```

## 5. Wire Up in main()

Add calls to `main()` in dependency order:
```python
await seed_notification_channels(pool)
await seed_notification_routing_rules(pool)
await seed_escalation_policies(pool)
await seed_escalation_levels(pool)
```

Place these AFTER tenant and device seeding (they depend on tenants existing).

## Verification
```bash
docker compose --profile seed run --rm seed
# Should print:
#   ✓ notification_channels seeded
#   ✓ notification_routing_rules seeded
#   ✓ escalation_policies seeded
#   ✓ escalation_levels seeded
```

Check DB:
```sql
SELECT tenant_id, name, channel_type FROM notification_channels;
-- Should show 5 rows (3 for tenant-a, 2 for tenant-b)
SELECT tenant_id, channel_id, min_severity FROM notification_routing_rules;
-- Should show 4 rows (2 per tenant)
```
