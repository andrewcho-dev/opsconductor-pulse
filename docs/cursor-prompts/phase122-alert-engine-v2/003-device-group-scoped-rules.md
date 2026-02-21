# Task 003 -- Device-Group-Scoped Rules

## Goal

Allow an alert rule to target a single device group. When `device_group_id` is set on a rule, the evaluator only evaluates telemetry for devices that are members of that group. This complements the existing `group_ids` array (which uses ANY match) by adding a simpler, single-group scope.

---

## 1. Database Migration

**File:** `db/migrations/08X_rule_device_group.sql` (use the next available number after task 002's migration)

```sql
BEGIN;

-- Add single device group scoping column
-- This references device_groups(group_id) but we use a simple column
-- because the FK would need (tenant_id, group_id) composite key.
ALTER TABLE alert_rules
    ADD COLUMN IF NOT EXISTS device_group_id TEXT NULL;

COMMENT ON COLUMN alert_rules.device_group_id IS
    'If set, this rule only evaluates devices in this device group. NULL means evaluate all devices (or use group_ids array).';

-- Index for looking up rules by device_group_id
CREATE INDEX IF NOT EXISTS idx_alert_rules_device_group
    ON alert_rules (tenant_id, device_group_id)
    WHERE device_group_id IS NOT NULL;

COMMIT;
```

---

## 2. Backend -- Evaluator Changes

**File:** `services/evaluator_iot/evaluator.py`

### 2a. Update fetch_tenant_rules to include device_group_id

In `fetch_tenant_rules` (updated in task 001), add `device_group_id` to the SELECT:

```python
async def fetch_tenant_rules(pg_conn, tenant_id):
    """Load enabled alert rules for a tenant from PostgreSQL."""
    rows = await pg_conn.fetch(
        """
        SELECT rule_id, name, rule_type, metric_name, operator, threshold, severity,
               site_ids, group_ids, conditions, match_mode, duration_seconds, duration_minutes,
               aggregation, window_seconds, device_group_id
        FROM alert_rules
        WHERE tenant_id = $1 AND enabled = true
        """,
        tenant_id
    )
    return [dict(r) for r in rows]
```

### 2b. Add group membership resolution

Add a helper function and a per-tick cache. Place this after `fetch_metric_mappings` (around line 827):

```python
# Per-evaluation-cycle cache for device group membership
_group_member_cache: dict[tuple[str, str], set[str]] = {}


async def resolve_group_members(conn, tenant_id: str, group_id: str) -> set[str]:
    """
    Return the set of device_ids belonging to a device group.
    Results are cached per evaluation cycle (cache is cleared at cycle start).
    """
    cache_key = (tenant_id, group_id)
    if cache_key in _group_member_cache:
        return _group_member_cache[cache_key]

    rows = await conn.fetch(
        """
        SELECT device_id
        FROM device_group_members
        WHERE tenant_id = $1 AND group_id = $2
        """,
        tenant_id,
        group_id,
    )
    members = {row["device_id"] for row in rows}
    _group_member_cache[cache_key] = members
    return members
```

### 2c. Clear the cache at the start of each evaluation cycle

In the main loop, right after `conn = await pool.acquire()` (around line 1037), add:

```python
                _group_member_cache.clear()
```

### 2d. Add device_group_id filtering in the rule evaluation loop

In the main loop, in the per-rule iteration (around line 1161), after the existing `group_ids` check (around line 1176-1191), add the `device_group_id` filter:

```python
                        # Single device group scope: if rule has device_group_id,
                        # only evaluate devices in that group
                        device_group_id = rule.get("device_group_id")
                        if device_group_id:
                            group_members = await resolve_group_members(
                                conn, tenant_id, device_group_id
                            )
                            if device_id not in group_members:
                                continue
```

Place this **after** the existing `group_ids` check block (which checks `rule.get("group_ids")`) and **before** the `fp_rule` assignment (line 1193). This way both filters can co-exist -- `group_ids` uses ANY-of-multiple-groups, while `device_group_id` scopes to a single group.

---

## 3. Backend -- API Changes

### 3a. Update Pydantic models

**File:** `services/ui_iot/routes/customer.py`

Add `device_group_id` to `AlertRuleCreate` (after `group_ids`):

```python
    device_group_id: str | None = Field(default=None, description="Scope rule to a single device group")
```

Add to `AlertRuleUpdate`:

```python
    device_group_id: str | None = None
```

### 3b. Pass through in route handlers

**File:** `services/ui_iot/routes/alerts.py`

In `create_alert_rule_endpoint` (line 364), pass `device_group_id` to the query function:

```python
            rule = await create_alert_rule(
                conn,
                # ... existing params ...
                device_group_id=body.device_group_id,
            )
```

In `update_alert_rule_endpoint` (line 482), pass:

```python
            rule = await update_alert_rule(
                conn,
                # ... existing params ...
                device_group_id=body.device_group_id,
            )
```

### 3c. Update db/queries.py

**File:** `services/ui_iot/db/queries.py`

Update `create_alert_rule` function signature to add `device_group_id: str | None = None`.

Update the INSERT SQL to include `device_group_id` in the column list, VALUES, and RETURNING clause.

Update `update_alert_rule` to add `device_group_id: str | None = None` parameter and add to the dynamic SET clause:

```python
    if device_group_id is not None:
        sets.append(f"device_group_id = ${idx}")
        params.append(device_group_id if device_group_id else None)
        idx += 1
```

Update `fetch_alert_rules` and `fetch_alert_rule` SELECT queries to include `device_group_id`.

### 3d. Update _with_rule_conditions

**File:** `services/ui_iot/routes/customer.py`

In `_with_rule_conditions` (line 519), ensure `device_group_id` is passed through:

```python
    result["device_group_id"] = result.get("device_group_id")
```

---

## 4. Frontend Changes

### 4a. Update TypeScript types

**File:** `frontend/src/services/api/types.ts`

Add to `AlertRule` interface:

```typescript
  device_group_id?: string | null;
```

Add to `AlertRuleCreate`:

```typescript
  device_group_id?: string | null;
```

Add to `AlertRuleUpdate`:

```typescript
  device_group_id?: string | null;
```

### 4b. Update AlertRuleDialog

**File:** `frontend/src/features/alerts/AlertRuleDialog.tsx`

The dialog already has a multi-select for device groups (`selectedGroupIds`). Add a separate single-select for `device_group_id`.

Add state (after `selectedGroupIds`):

```typescript
const [selectedDeviceGroupId, setSelectedDeviceGroupId] = useState<string>("");
```

In the `useEffect` that populates from `rule`, add:

```typescript
setSelectedDeviceGroupId(rule.device_group_id ?? "");
```

In the reset path (when `!rule`):

```typescript
setSelectedDeviceGroupId("");
```

Add a new form section **before** the existing "Device Groups" multi-select section. This gives a clear single-group scope:

```tsx
<div className="grid gap-2">
  <Label>Scope to Device Group</Label>
  <Select
    value={selectedDeviceGroupId || "none"}
    onValueChange={(v) => setSelectedDeviceGroupId(v === "none" ? "" : v)}
  >
    <SelectTrigger className="w-full">
      <SelectValue placeholder="All devices (no group filter)" />
    </SelectTrigger>
    <SelectContent>
      <SelectItem value="none">All devices (no group filter)</SelectItem>
      {(deviceGroupsResponse?.groups ?? []).map((group: DeviceGroup) => (
        <SelectItem key={group.group_id} value={group.group_id}>
          {group.name} ({group.member_count ?? 0} devices)
        </SelectItem>
      ))}
    </SelectContent>
  </Select>
  <p className="text-xs text-muted-foreground">
    If set, this rule only evaluates devices in the selected group.
  </p>
</div>
```

Update `handleSubmit` to include `device_group_id` in both create and update payloads:

In the create path:

```typescript
      const payload: AlertRuleCreate = {
        name,
        // ... existing fields ...
        device_group_id: selectedDeviceGroupId || null,
      };
```

In the update path:

```typescript
    if (selectedDeviceGroupId !== (rule.device_group_id ?? "")) {
      updates.device_group_id = selectedDeviceGroupId || null;
    }
```

### 4c. Update AlertRulesPage table

**File:** `frontend/src/features/alerts/AlertRulesPage.tsx`

Optionally show the group scope in the table. Add a "Scope" column or append to the name column. A lightweight approach: in the Name cell, show a small badge if the rule is group-scoped:

```tsx
<TableCell className="font-medium">
  {rule.name}
  {rule.device_group_id && (
    <span className="ml-2 text-xs text-muted-foreground">
      [{rule.device_group_id}]
    </span>
  )}
</TableCell>
```

---

## 5. Verification

```bash
# 1. Run migration
docker exec -i iot-postgres psql -U iot -d iotcloud < db/migrations/08X_rule_device_group.sql

# 2. Verify column
docker exec iot-postgres psql -U iot -d iotcloud -c "SELECT column_name FROM information_schema.columns WHERE table_name='alert_rules' AND column_name='device_group_id';"

# 3. Create a device group with 2 devices
curl -X POST http://localhost:3000/customer/device-groups \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"Test Group","description":"for testing"}'
# Note the group_id returned

# 4. Add devices to the group
curl -X POST http://localhost:3000/customer/device-groups/{group_id}/members \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"device_ids":["device-A","device-B"]}'

# 5. Create a rule scoped to the group
curl -X POST http://localhost:3000/customer/alert-rules \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name":"Group temp high",
    "rule_type":"threshold",
    "metric_name":"temperature",
    "operator":"GT",
    "threshold":50,
    "severity":3,
    "device_group_id":"'$GROUP_ID'"
  }'

# 6. Send telemetry for device-A (in group) and device-C (not in group), both with temp > 50
# Verify: alert fires ONLY for device-A, not device-C

# 7. Verify in DB
docker exec iot-postgres psql -U iot -d iotcloud -c "SELECT device_id, status FROM fleet_alert WHERE status='OPEN' ORDER BY id DESC LIMIT 5;"

# 8. Frontend: open AlertRuleDialog, verify group dropdown appears,
#    select a group, save rule, verify the table shows [group_id] badge
```

---

## Commit

```
feat(alerts): scope alert rules to a single device group

- Migration: adds device_group_id column to alert_rules
- Evaluator: resolves group members and filters device evaluation
- API: accepts device_group_id in create/update alert rule
- Frontend: adds group selector dropdown to AlertRuleDialog
```
