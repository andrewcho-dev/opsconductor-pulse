# Task 002 — Fleet Overview Widget Shows Sensor Counts

## Context

The fleet overview widget (Phase 148e) shows device counts, health score, uptime, and alerts. It should also show sensor statistics now that sensors are a separate entity.

## Files to Modify

### 1. Backend: Add sensor stats to fleet summary

**File:** `services/ui_iot/routes/devices.py`

Find the fleet summary endpoint (`GET /api/v1/customer/devices/summary` or similar). Add sensor counts to the response:

```python
# Inside the fleet summary endpoint, add a sensor count query:
sensor_stats = await conn.fetchrow(
    """
    SELECT
        COUNT(*) AS total_sensors,
        COUNT(*) FILTER (WHERE status = 'active') AS active_sensors,
        COUNT(DISTINCT sensor_type) AS sensor_types,
        COUNT(DISTINCT device_id) AS devices_with_sensors
    FROM sensors
    WHERE tenant_id = $1
    """,
    tenant_id,
)

# Add to response:
result["total_sensors"] = sensor_stats["total_sensors"] or 0
result["active_sensors"] = sensor_stats["active_sensors"] or 0
result["sensor_types"] = sensor_stats["sensor_types"] or 0
result["devices_with_sensors"] = sensor_stats["devices_with_sensors"] or 0
```

Wrap in try/except for graceful degradation if the sensors table doesn't exist yet.

### 2. Frontend: Update FleetSummary type

**File:** `frontend/src/services/api/types.ts`

Add to `FleetSummary` interface:

```typescript
export interface FleetSummary {
  // ... existing fields ...
  total_sensors?: number;
  active_sensors?: number;
  sensor_types?: number;
  devices_with_sensors?: number;
}
```

### 3. Frontend: Update FleetOverviewRenderer

**File:** `frontend/src/features/dashboard/widgets/renderers/FleetOverviewRenderer.tsx`

In the composite layout, add sensor stats to the alert strip (bottom row) or as a new stat in the top row. Suggested approach — add a sensor count to the status breakdown section:

After the device status bars (Online/Stale/Offline), add a small sensor summary:

```tsx
<div className="flex items-center gap-1 text-xs text-muted-foreground">
  <span className="font-medium text-foreground">{summary.total_sensors ?? 0}</span>
  sensors across
  <span className="font-medium text-foreground">{summary.devices_with_sensors ?? 0}</span>
  devices
</div>
```

Or add it as a 4th metric in the status area alongside device counts.

## Verification

```bash
cd services/ui_iot && python3 -m compileall -q routes/devices.py
cd frontend && npx tsc --noEmit && npm run build
```
