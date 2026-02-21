# Task 001 -- Time-Window Aggregation Rules (WINDOW rule type)

## Goal

Add a new `WINDOW` rule type that applies an aggregation function (avg, min, max, count, sum) over a sliding time window before comparing to a threshold.

Example: "Alert when avg(temperature) > 80 over the last 5 minutes."

---

## 1. Database Migration

**File:** `db/migrations/08X_alert_window_rules.sql`

Check which number is available. If `081` is free, use `081`. Otherwise use the next free number.

```sql
BEGIN;

-- Add aggregation function column: avg, min, max, count, sum
ALTER TABLE alert_rules
    ADD COLUMN IF NOT EXISTS aggregation VARCHAR(10) NULL;

-- Add sliding window duration in seconds
ALTER TABLE alert_rules
    ADD COLUMN IF NOT EXISTS window_seconds INTEGER NULL;

-- Validate aggregation values
ALTER TABLE alert_rules
    ADD CONSTRAINT chk_aggregation_values
    CHECK (aggregation IS NULL OR aggregation IN ('avg', 'min', 'max', 'count', 'sum'));

-- Validate window_seconds range: 60s to 3600s (1 min to 1 hour)
ALTER TABLE alert_rules
    ADD CONSTRAINT chk_window_seconds_range
    CHECK (window_seconds IS NULL OR (window_seconds >= 60 AND window_seconds <= 3600));

-- If rule_type is WINDOW, aggregation and window_seconds must both be set
-- (enforced at application level, not DB constraint, to avoid migration pain)

COMMENT ON COLUMN alert_rules.aggregation IS 'Aggregation function for WINDOW rules: avg, min, max, count, sum';
COMMENT ON COLUMN alert_rules.window_seconds IS 'Sliding window duration in seconds for WINDOW rules (60-3600)';

COMMIT;
```

---

## 2. Backend -- Evaluator Changes

**File:** `services/evaluator_iot/evaluator.py`

### 2a. Add module-level sliding window buffer

At the top of the file, after the existing globals (around line 62, after `COUNTERS`), add:

```python
from collections import deque

# In-memory sliding window buffer for WINDOW rules.
# Key: (device_id, rule_id) -> deque of (timestamp: float, value: float)
_window_buffers: dict[tuple[str, str], deque] = {}
```

### 2b. Add window aggregation helper functions

Add these after the existing `evaluate_threshold` function (around line 406):

```python
AGGREGATION_FUNCTIONS = {
    "avg": lambda values: sum(values) / len(values) if values else None,
    "min": lambda values: min(values) if values else None,
    "max": lambda values: max(values) if values else None,
    "count": lambda values: len(values),
    "sum": lambda values: sum(values) if values else None,
}


def update_window_buffer(
    device_id: str,
    rule_id: str,
    timestamp: float,
    value: float,
    window_seconds: int,
) -> None:
    """Append a data point and evict stale entries."""
    key = (device_id, rule_id)
    buf = _window_buffers.setdefault(key, deque())
    buf.append((timestamp, value))
    cutoff = timestamp - window_seconds
    while buf and buf[0][0] < cutoff:
        buf.popleft()


def evaluate_window_aggregation(
    device_id: str,
    rule_id: str,
    aggregation: str,
    operator: str,
    threshold: float,
    window_seconds: int,
) -> bool:
    """
    Apply aggregation to the buffered values and compare to threshold.
    Returns True if condition is met (alert should fire).
    Returns False if insufficient data or condition not met.
    """
    key = (device_id, rule_id)
    buf = _window_buffers.get(key)
    if not buf or len(buf) < 2:
        return False  # need at least 2 data points for meaningful aggregation

    values = [v for _, v in buf]
    agg_fn = AGGREGATION_FUNCTIONS.get(aggregation)
    if agg_fn is None:
        return False

    aggregated_value = agg_fn(values)
    if aggregated_value is None:
        return False

    return evaluate_threshold(aggregated_value, operator, threshold)
```

### 2c. Update `fetch_tenant_rules` to include new columns

In `fetch_tenant_rules` (line 486), update the SELECT to include `aggregation` and `window_seconds`:

```python
async def fetch_tenant_rules(pg_conn, tenant_id):
    """Load enabled alert rules for a tenant from PostgreSQL."""
    rows = await pg_conn.fetch(
        """
        SELECT rule_id, name, rule_type, metric_name, operator, threshold, severity,
               site_ids, group_ids, conditions, match_mode, duration_seconds, duration_minutes,
               aggregation, window_seconds
        FROM alert_rules
        WHERE tenant_id = $1 AND enabled = true
        """,
        tenant_id
    )
    return [dict(r) for r in rows]
```

### 2d. Handle WINDOW rule type in the main evaluation loop

In the main loop where rule types are dispatched (around line 1201, after the `telemetry_gap` handler and before the `anomaly` handler), add a new block:

```python
if rule_type == "window":
    aggregation = rule.get("aggregation")
    window_seconds = rule.get("window_seconds")
    if not aggregation or not window_seconds:
        continue

    # Get the raw metric value from the latest snapshot
    raw_value = latest_metrics_snapshot.get(metric_name)
    if raw_value is not None:
        try:
            numeric_value = float(raw_value)
        except (TypeError, ValueError):
            continue
        now_ts_float = time.time()
        update_window_buffer(
            device_id, str(rule_id), now_ts_float, numeric_value, window_seconds
        )

    fired = evaluate_window_aggregation(
        device_id,
        str(rule_id),
        aggregation,
        operator,
        float(threshold),
        window_seconds,
    )
    if not fired:
        await close_alert(conn, tenant_id, fp_rule)
        continue

    if await is_silenced(conn, tenant_id, fp_rule):
        continue
    if await is_in_maintenance(
        conn, tenant_id, site_id=site_id, device_type=rule.get("device_type"),
    ):
        continue

    # Format human-readable summary
    window_display = f"{window_seconds // 60}m" if window_seconds >= 60 else f"{window_seconds}s"
    op_symbol = OPERATOR_SYMBOLS.get(operator, operator)
    summary = (
        f"{site_id}: {device_id} rule '{rule['name']}' triggered -- "
        f"{aggregation}({metric_name}) {op_symbol} {threshold} over {window_display}"
    )
    alert_id, inserted = await open_or_update_alert(
        conn, tenant_id, site_id, device_id,
        "WINDOW", fp_rule, rule_severity, 1.0, summary,
        {
            "rule_id": rule_id,
            "rule_name": rule["name"],
            "metric_name": metric_name,
            "aggregation": aggregation,
            "window_seconds": window_seconds,
            "operator": operator,
            "threshold": threshold,
        },
    )
    if inserted:
        log_event(
            logger, "alert created",
            tenant_id=tenant_id, device_id=device_id,
            alert_type="WINDOW", alert_id=str(alert_id),
        )
    continue
```

---

## 3. Backend -- API Changes

### 3a. Update Pydantic models

**File:** `services/ui_iot/routes/customer.py`

Update `AlertRuleCreate` (line 323) to add `aggregation` and `window_seconds` fields, and expand `rule_type`:

```python
class AlertRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    rule_type: Literal["threshold", "anomaly", "telemetry_gap", "window"] = "threshold"
    metric_name: str | None = Field(default=None, min_length=1, max_length=100)
    operator: str | None = None
    threshold: float | None = None
    severity: int = Field(default=3, ge=1, le=5)
    duration_seconds: int = Field(default=0, ge=0)
    duration_minutes: int | None = Field(default=None, ge=1)
    description: str | None = None
    site_ids: list[str] | None = None
    group_ids: list[str] | None = None
    conditions: List["RuleCondition"] | "RuleConditions" | None = None
    match_mode: Literal["all", "any"] = "all"
    anomaly_conditions: "AnomalyConditions | None" = None
    gap_conditions: "TelemetryGapConditions | None" = None
    enabled: bool = True
    aggregation: str | None = Field(default=None, description="Aggregation function for WINDOW rules: avg, min, max, count, sum")
    window_seconds: int | None = Field(default=None, ge=60, le=3600, description="Sliding window in seconds for WINDOW rules")
```

Do the same for `AlertRuleUpdate` (line 350), adding `aggregation` and `window_seconds` as optional fields:

```python
    aggregation: str | None = None
    window_seconds: int | None = Field(default=None, ge=60, le=3600)
```

Also update the `rule_type` field in `AlertRuleUpdate`:

```python
    rule_type: Literal["threshold", "anomaly", "telemetry_gap", "window"] | None = None
```

### 3b. Add validation in create_alert_rule_endpoint

**File:** `services/ui_iot/routes/alerts.py`

In `create_alert_rule_endpoint` (line 364), after the `telemetry_gap` handling block and before the `elif conditions_list:` block, add:

```python
    elif rule_type == "window":
        if body.aggregation is None:
            raise HTTPException(status_code=422, detail="aggregation is required for WINDOW rules")
        if body.aggregation not in ("avg", "min", "max", "count", "sum"):
            raise HTTPException(status_code=400, detail="aggregation must be one of: avg, min, max, count, sum")
        if body.window_seconds is None:
            raise HTTPException(status_code=422, detail="window_seconds is required for WINDOW rules")
        if body.metric_name is None or not METRIC_NAME_PATTERN.match(body.metric_name):
            raise HTTPException(status_code=400, detail="Invalid metric_name format")
        if body.operator is None or body.operator not in VALID_OPERATORS:
            raise HTTPException(status_code=400, detail="Invalid operator value")
        if body.threshold is None:
            raise HTTPException(status_code=422, detail="threshold is required for WINDOW rules")
        metric_name = body.metric_name
        operator = body.operator
        threshold = body.threshold
        conditions_payload = None
```

Similarly in `update_alert_rule_endpoint` (line 481), add the same validation when `body.rule_type == "window"`.

### 3c. Pass new fields through to db/queries.py

**File:** `services/ui_iot/db/queries.py`

Update `create_alert_rule` signature to accept `aggregation` and `window_seconds`:

```python
async def create_alert_rule(
    conn: asyncpg.Connection,
    tenant_id: str,
    name: str,
    metric_name: str | None,
    operator: str | None,
    threshold: float | None,
    severity: int = 3,
    description: str | None = None,
    site_ids: List[str] | None = None,
    group_ids: List[str] | None = None,
    conditions: Any | None = None,
    match_mode: str = "all",
    duration_seconds: int = 0,
    duration_minutes: int | None = None,
    enabled: bool = True,
    rule_type: str = "threshold",
    aggregation: str | None = None,
    window_seconds: int | None = None,
) -> Dict[str, Any]:
```

Update the INSERT SQL to include `aggregation` and `window_seconds`. Add them to the column list, VALUES list, and RETURNING clause.

Update `update_alert_rule` similarly -- add optional `aggregation` and `window_seconds` parameters and append to the dynamic SET clause.

Update `fetch_alert_rules` and `fetch_alert_rule` SELECT queries to include `aggregation, window_seconds`.

### 3d. Pass through from route to query function

In `create_alert_rule_endpoint` in `routes/alerts.py`, pass the new fields to `create_alert_rule`:

```python
            rule = await create_alert_rule(
                conn,
                tenant_id=tenant_id,
                name=body.name,
                # ... existing fields ...
                aggregation=body.aggregation,
                window_seconds=body.window_seconds,
            )
```

Same for `update_alert_rule_endpoint`, pass `aggregation=body.aggregation, window_seconds=body.window_seconds`.

### 3e. Update _with_rule_conditions

In `routes/customer.py`, in `_with_rule_conditions` (line 519), pass through the new fields:

```python
    # After the existing rule_type handling blocks, ensure aggregation and window_seconds are included:
    result["aggregation"] = result.get("aggregation")
    result["window_seconds"] = result.get("window_seconds")
```

---

## 4. Frontend Changes

### 4a. Update TypeScript types

**File:** `frontend/src/services/api/types.ts`

Add to `AlertRule` interface (after `gap_conditions`):

```typescript
  aggregation?: "avg" | "min" | "max" | "count" | "sum" | null;
  window_seconds?: number | null;
```

Update `rule_type` in `AlertRule`:

```typescript
  rule_type?: "threshold" | "anomaly" | "telemetry_gap" | "window";
```

Add to `AlertRuleCreate` interface:

```typescript
  rule_type?: "threshold" | "anomaly" | "telemetry_gap" | "window";
  aggregation?: "avg" | "min" | "max" | "count" | "sum";
  window_seconds?: number;
```

Add to `AlertRuleUpdate` interface:

```typescript
  rule_type?: "threshold" | "anomaly" | "telemetry_gap" | "window";
  aggregation?: "avg" | "min" | "max" | "count" | "sum" | null;
  window_seconds?: number | null;
```

### 4b. Update AlertRuleDialog

**File:** `frontend/src/features/alerts/AlertRuleDialog.tsx`

Update `RuleMode` type to include "window":

```typescript
type RuleMode = "simple" | "multi" | "anomaly" | "gap" | "window";
```

Add state variables (after `gapMinutes` state):

```typescript
const [windowAggregation, setWindowAggregation] = useState<string>("avg");
const [windowSeconds, setWindowSeconds] = useState<string>("300"); // 5 min default
```

Add a "Window Agg" button to the Rule Mode selector (after the "Data Gap" button):

```tsx
<Button
  type="button"
  variant={ruleMode === "window" ? "default" : "outline"}
  onClick={() => setRuleMode("window")}
>
  Window Aggregation
</Button>
```

Add a new section in the conditional rendering (after the gap section, before the closing `}`):

```tsx
) : ruleMode === "window" ? (
  <div className="space-y-3 rounded-md border border-border p-3">
    <div className="grid gap-2">
      <Label htmlFor="window-metric-name">Metric Name</Label>
      <Select value={metricName || undefined} onValueChange={setMetricName}>
        <SelectTrigger id="window-metric-name" className="w-full" disabled={metricsLoading}>
          <SelectValue placeholder={metricsLoading ? "Loading metrics..." : "Select metric"} />
        </SelectTrigger>
        <SelectContent>
          <SelectGroup>
            <SelectLabel>Normalized</SelectLabel>
            {normalizedMetrics.map((metric) => (
              <SelectItem key={metric.name} value={metric.name}>
                {metric.name}{metric.display_unit ? ` (${metric.display_unit})` : ""}
              </SelectItem>
            ))}
          </SelectGroup>
          <SelectGroup>
            <SelectLabel>Raw</SelectLabel>
            {rawMetrics.map((metric) => (
              <SelectItem key={metric.name} value={metric.name}>
                {metric.name}
              </SelectItem>
            ))}
          </SelectGroup>
        </SelectContent>
      </Select>
    </div>
    <div className="grid gap-2">
      <Label>Aggregation</Label>
      <Select value={windowAggregation} onValueChange={setWindowAggregation}>
        <SelectTrigger className="w-full">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="avg">Average (avg)</SelectItem>
          <SelectItem value="min">Minimum (min)</SelectItem>
          <SelectItem value="max">Maximum (max)</SelectItem>
          <SelectItem value="count">Count</SelectItem>
          <SelectItem value="sum">Sum</SelectItem>
        </SelectContent>
      </Select>
    </div>
    <div className="grid gap-2">
      <Label>Operator</Label>
      <Select value={operator} onValueChange={(v) => setOperator(v as RuleOperator)}>
        <SelectTrigger className="w-full">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="GT">&gt; (GT)</SelectItem>
          <SelectItem value="LT">&lt; (LT)</SelectItem>
          <SelectItem value="GTE">&ge; (GTE)</SelectItem>
          <SelectItem value="LTE">&le; (LTE)</SelectItem>
        </SelectContent>
      </Select>
    </div>
    <div className="grid gap-2">
      <Label htmlFor="window-threshold">Threshold</Label>
      <Input
        id="window-threshold"
        type="number"
        value={threshold}
        onChange={(e) => setThreshold(e.target.value)}
        required
        step="any"
      />
    </div>
    <div className="grid gap-2">
      <Label>Window Duration</Label>
      <Select value={windowSeconds} onValueChange={setWindowSeconds}>
        <SelectTrigger className="w-full">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="60">1 minute</SelectItem>
          <SelectItem value="120">2 minutes</SelectItem>
          <SelectItem value="300">5 minutes</SelectItem>
          <SelectItem value="600">10 minutes</SelectItem>
          <SelectItem value="900">15 minutes</SelectItem>
          <SelectItem value="1800">30 minutes</SelectItem>
          <SelectItem value="3600">1 hour</SelectItem>
        </SelectContent>
      </Select>
    </div>
    <p className="text-xs text-muted-foreground">
      Alert fires when {windowAggregation}({metricName || "metric"}) breaches the threshold
      over a {Number(windowSeconds) / 60}-minute sliding window.
    </p>
  </div>
```

Update the `handleSubmit` function to handle the window rule mode. In the `if (!isEditing)` block, add before the closing of the if/else chain:

```typescript
      } else if (ruleMode === "window") {
        payload.rule_type = "window";
        payload.metric_name = metricName;
        payload.operator = operator;
        payload.threshold = thresholdValue;
        payload.aggregation = windowAggregation as AlertRuleCreate["aggregation"];
        payload.window_seconds = Number(windowSeconds);
      }
```

In the update (isEditing) path, add:

```typescript
    } else if (ruleMode === "window") {
      updates.rule_type = "window";
      updates.metric_name = metricName;
      updates.operator = operator;
      updates.threshold = thresholdValue;
      updates.aggregation = windowAggregation as AlertRuleUpdate["aggregation"];
      updates.window_seconds = Number(windowSeconds);
      updates.conditions = null;
      updates.anomaly_conditions = null;
      updates.gap_conditions = null;
    }
```

Update the `useEffect` that populates form state from `rule` to handle `rule.rule_type === "window"`:

```typescript
      } else if (rule.rule_type === "window") {
        setRuleMode("window");
        setWindowAggregation(rule.aggregation ?? "avg");
        setWindowSeconds(String(rule.window_seconds ?? 300));
        setMetricName(rule.metric_name);
        setOperator(rule.operator as RuleOperator);
        setThreshold(String(rule.threshold));
```

### 4c. Update AlertRulesPage formatCondition

**File:** `frontend/src/features/alerts/AlertRulesPage.tsx`

In the `formatCondition` function (line 79), add handling for WINDOW rules at the top:

```typescript
  function formatCondition(rule: AlertRule) {
    if (rule.rule_type === "window" && rule.aggregation && rule.window_seconds) {
      const op = OPERATOR_LABELS[rule.operator] || rule.operator;
      const windowDisplay =
        rule.window_seconds >= 60
          ? `${rule.window_seconds / 60}m`
          : `${rule.window_seconds}s`;
      return `${rule.aggregation}(${rule.metric_name}) ${op} ${rule.threshold} over ${windowDisplay}`;
    }
    // ... existing logic unchanged ...
  }
```

---

## 5. Verification

```bash
# 1. Run migration
docker exec -i iot-postgres psql -U iot -d iotcloud < db/migrations/08X_alert_window_rules.sql

# 2. Verify columns exist
docker exec iot-postgres psql -U iot -d iotcloud -c "SELECT column_name FROM information_schema.columns WHERE table_name='alert_rules' AND column_name IN ('aggregation','window_seconds');"

# 3. Create a WINDOW rule via API
curl -X POST http://localhost:3000/customer/alert-rules \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "High avg temp 5m",
    "rule_type": "window",
    "metric_name": "temperature",
    "operator": "GT",
    "threshold": 80,
    "severity": 4,
    "aggregation": "avg",
    "window_seconds": 300
  }'

# 4. Verify validation rejects bad input
curl -X POST http://localhost:3000/customer/alert-rules \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Bad window rule",
    "rule_type": "window",
    "metric_name": "temperature",
    "operator": "GT",
    "threshold": 80,
    "severity": 4
  }'
# Expect 422: "aggregation is required for WINDOW rules"

# 5. Frontend: open AlertRuleDialog, select "Window Aggregation" mode,
#    create a rule, verify it shows in the table as "avg(temperature) > 80 over 5m"

# 6. E2E: Send 10 telemetry points with temperature > 80 over 5 minutes.
#    Verify evaluator creates a WINDOW alert.
```

---

## Commit

```
feat(alerts): add WINDOW rule type with sliding-window aggregation

- Migration: adds aggregation and window_seconds columns to alert_rules
- Evaluator: in-memory sliding window buffer, aggregation evaluation
- API: validates aggregation + window_seconds for WINDOW rule type
- Frontend: new "Window Aggregation" mode in AlertRuleDialog, formatted condition display
```
