# Task 002 -- Alert Deduplication

## Goal

When the evaluator detects a threshold breach that would create an alert identical to an already-open alert for the same device + rule, increment a `trigger_count` counter instead of creating a duplicate row. This dramatically reduces alert noise.

---

## 1. Database Migration

**File:** `db/migrations/08X_alert_dedup.sql` (use the next available number after task 001's migration)

```sql
BEGIN;

-- Track how many times an alert has been re-triggered while still open/acknowledged
ALTER TABLE fleet_alert
    ADD COLUMN IF NOT EXISTS trigger_count INTEGER NOT NULL DEFAULT 1;

-- Track when the alert was last re-triggered
ALTER TABLE fleet_alert
    ADD COLUMN IF NOT EXISTS last_triggered_at TIMESTAMPTZ NULL;

-- Link alert to the rule that created it (nullable for legacy/heartbeat alerts)
ALTER TABLE fleet_alert
    ADD COLUMN IF NOT EXISTS rule_id UUID NULL;

-- Backfill last_triggered_at from created_at for existing rows
UPDATE fleet_alert
SET last_triggered_at = created_at
WHERE last_triggered_at IS NULL;

-- Set default for new rows
ALTER TABLE fleet_alert
    ALTER COLUMN last_triggered_at SET DEFAULT now();

-- Index for the dedup lookup query
CREATE INDEX IF NOT EXISTS idx_fleet_alert_dedup
    ON fleet_alert (device_id, rule_id, status)
    WHERE status IN ('OPEN', 'ACKNOWLEDGED');

-- Note: We do NOT add a foreign key to alert_rules because:
-- 1. alert_rules uses (tenant_id, rule_id) as logical key but rule_id is UUID, not the PK
-- 2. Heartbeat/system alerts have no rule_id
-- 3. If a rule is deleted, we still want to keep the alert history

COMMENT ON COLUMN fleet_alert.trigger_count IS 'Number of times this alert has been triggered while open. Starts at 1.';
COMMENT ON COLUMN fleet_alert.last_triggered_at IS 'Timestamp of the most recent trigger (may differ from created_at if re-triggered).';
COMMENT ON COLUMN fleet_alert.rule_id IS 'The rule_id from alert_rules that created this alert. NULL for heartbeat/system alerts.';

COMMIT;
```

---

## 2. Backend -- Evaluator Changes

**File:** `services/evaluator_iot/evaluator.py`

### 2a. Add deduplication helper function

Add after the `close_alert` function (around line 203):

```python
async def deduplicate_or_create_alert(
    conn,
    tenant_id: str,
    site_id: str,
    device_id: str,
    alert_type: str,
    fingerprint: str,
    severity: int,
    confidence: float,
    summary: str,
    details: dict,
    rule_id: str | None = None,
) -> tuple[int | None, bool]:
    """
    Check for an existing open/acknowledged alert for the same device + rule.
    If found: increment trigger_count and update last_triggered_at, return (id, False).
    If not found: create a new alert, return (id, True).
    """
    if rule_id:
        existing = await conn.fetchrow(
            """
            SELECT id FROM fleet_alert
            WHERE device_id = $1
              AND rule_id = $2::uuid
              AND status IN ('OPEN', 'ACKNOWLEDGED')
            LIMIT 1
            """,
            device_id,
            rule_id,
        )
        if existing:
            await conn.execute(
                """
                UPDATE fleet_alert
                SET trigger_count = trigger_count + 1,
                    last_triggered_at = now(),
                    severity = $2,
                    summary = $3,
                    details = $4::jsonb
                WHERE id = $1
                """,
                existing["id"],
                severity,
                summary,
                json.dumps(details),
            )
            return existing["id"], False

    # No existing alert -- create new one
    COUNTERS["alerts_created"] += 1
    evaluator_alerts_created_total.labels(tenant_id=tenant_id).inc()
    row = await conn.fetchrow(
        """
        INSERT INTO fleet_alert
            (tenant_id, site_id, device_id, alert_type, fingerprint, status,
             severity, confidence, summary, details, rule_id, trigger_count, last_triggered_at)
        VALUES ($1, $2, $3, $4, $5, 'OPEN', $6, $7, $8, $9::jsonb, $10::uuid, 1, now())
        ON CONFLICT (tenant_id, fingerprint) WHERE (status IN ('OPEN', 'ACKNOWLEDGED'))
        DO UPDATE SET
          severity = EXCLUDED.severity,
          confidence = EXCLUDED.confidence,
          summary = EXCLUDED.summary,
          details = EXCLUDED.details,
          trigger_count = fleet_alert.trigger_count + 1,
          last_triggered_at = now()
        RETURNING id, (xmax = 0) AS inserted
        """,
        tenant_id, site_id, device_id, alert_type, fingerprint,
        severity, confidence, summary, json.dumps(details),
        rule_id,
    )
    if row:
        return row["id"], row["inserted"]
    return None, False
```

### 2b. Replace `open_or_update_alert` calls for rule-based alerts

In the main evaluation loop, for **threshold** alerts (around line 1317) and **WINDOW** alerts (added in task 001), replace:

```python
# OLD:
alert_id, inserted = await open_or_update_alert(
    conn, tenant_id, site_id, device_id,
    "THRESHOLD", fp_rule, rule_severity, 1.0, summary, details_dict,
)
```

With:

```python
# NEW:
alert_id, inserted = await deduplicate_or_create_alert(
    conn, tenant_id, site_id, device_id,
    "THRESHOLD", fp_rule, rule_severity, 1.0, summary, details_dict,
    rule_id=str(rule_id),
)
```

Do the same for:
- **WINDOW** alerts (alert_type "WINDOW")
- **ANOMALY** alerts (around line 1251, alert_type "ANOMALY")
- **Telemetry gap** alerts in `maybe_process_telemetry_gap_rule` (around line 328)

**Keep `open_or_update_alert` unchanged** for heartbeat alerts (`NO_HEARTBEAT` around line 1119) since those don't have a rule_id.

### 2c. Optionally update heartbeat alerts to pass rule_id=None

Heartbeat alerts can continue using `open_or_update_alert` as-is (they have no rule_id). No change needed.

---

## 3. Backend -- API Changes

### 3a. Update alert list query to include new columns

**File:** `services/ui_iot/routes/alerts.py`

In `list_alerts` (line 71), update the SELECT to include the new columns:

```python
            rows = await conn.fetch(
                f"""
                SELECT id AS alert_id, tenant_id, created_at, closed_at, device_id, site_id, alert_type,
                       fingerprint, status, severity, confidence, summary, details,
                       silenced_until, acknowledged_by, acknowledged_at,
                       escalation_level, escalated_at,
                       trigger_count, last_triggered_at, rule_id
                FROM fleet_alert
                WHERE {where}
                ORDER BY created_at DESC
                LIMIT {limit} OFFSET {offset}
                """,
                *params,
            )
```

### 3b. Update get_alert detail query

In `get_alert` (line 122), add `trigger_count, last_triggered_at, rule_id` to the SELECT:

```python
            row = await conn.fetchrow(
                """
                SELECT id AS alert_id, tenant_id, device_id, site_id, alert_type,
                       severity, confidence, summary, status, created_at,
                       trigger_count, last_triggered_at, rule_id
                FROM fleet_alert
                WHERE tenant_id = $1 AND id = $2
                """,
                tenant_id,
                alert_id,
            )
```

---

## 4. Frontend Changes

### 4a. Update TypeScript types

**File:** `frontend/src/services/api/types.ts`

Add to the `Alert` interface (after `escalated_at`):

```typescript
  trigger_count?: number;
  last_triggered_at?: string | null;
  rule_id?: string | null;
```

### 4b. Update AlertListPage to show trigger_count

**File:** `frontend/src/features/alerts/AlertListPage.tsx`

In the grid row for each alert (inside the `filteredAlerts.map` around line 281), add a trigger count indicator. In the "Device / Type" column cell (around line 309), add after the alert_type line:

```tsx
<div>
  <div className="font-medium">{alert.device_id}</div>
  <div className="text-xs text-muted-foreground">
    {alert.alert_type}
    {alert.trigger_count && alert.trigger_count > 1 && (
      <Badge variant="secondary" className="ml-2 text-[10px]">
        {alert.trigger_count}x
      </Badge>
    )}
  </div>
</div>
```

In the expanded alert details section (around line 362), add after the "Escalation level" line:

```tsx
<div>Triggered: {alert.trigger_count ?? 1} time{(alert.trigger_count ?? 1) !== 1 ? "s" : ""}</div>
<div>
  Last triggered:{" "}
  {alert.last_triggered_at
    ? formatTimeAgo(alert.last_triggered_at)
    : formatTimeAgo(alert.created_at)}
</div>
```

### 4c. Update grid header

The grid header column "Time" already exists. Consider adding a subtle note. Alternatively, in the Time column cell (around line 313), show both created_at and last_triggered_at if they differ:

```tsx
<div className="text-xs text-muted-foreground">
  {formatTimeAgo(alert.created_at)}
  {alert.trigger_count && alert.trigger_count > 1 && alert.last_triggered_at && (
    <div className="text-[10px] text-muted-foreground/70">
      last: {formatTimeAgo(alert.last_triggered_at)}
    </div>
  )}
</div>
```

---

## 5. Verification

```bash
# 1. Run migration
docker exec -i iot-postgres psql -U iot -d iotcloud < db/migrations/08X_alert_dedup.sql

# 2. Verify columns
docker exec iot-postgres psql -U iot -d iotcloud -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_name='fleet_alert' AND column_name IN ('trigger_count','last_triggered_at','rule_id');"

# 3. Create a threshold rule
curl -X POST http://localhost:3000/customer/alert-rules \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"Temp high","rule_type":"threshold","metric_name":"temperature","operator":"GT","threshold":50,"severity":3}'

# 4. Send 5 telemetry payloads that breach the threshold
# (device sends temperature > 50 five times)

# 5. Verify deduplication: should see 1 alert row, trigger_count=5
docker exec iot-postgres psql -U iot -d iotcloud -c "SELECT id, device_id, rule_id, trigger_count, last_triggered_at, created_at FROM fleet_alert WHERE status='OPEN' ORDER BY id DESC LIMIT 5;"

# 6. Frontend: open AlertListPage, verify the alert shows "5x" badge
#    and expanded details show "Triggered: 5 times"
```

---

## Commit

```
feat(alerts): deduplicate alerts with trigger_count and last_triggered_at

- Migration: adds trigger_count, last_triggered_at, rule_id to fleet_alert
- Evaluator: checks for existing open alert before creating duplicate
- API: returns trigger_count and last_triggered_at in alert list/detail
- Frontend: shows trigger count badge and last-triggered time in alert inbox
```
