# Phase 148d — Add Missing Widget Types to Backend Whitelist

## Problem

The `add_widget` endpoint in `services/ui_iot/routes/dashboards.py` validates `widget_type` against a hardcoded `WIDGET_TYPES` set (line 28-38). This set only contains the original 9 widget types. Phase 147 added `fleet_overview` and Phase 148 added 5 new types (`area_chart`, `stat_card`, `pie_chart`, `scatter`, `radar`) to the frontend, but the backend whitelist was never updated. Result: HTTP 400 on any attempt to add the new widget types.

## Fix — Single File Change

**File:** `services/ui_iot/routes/dashboards.py`

### Step 1: Update WIDGET_TYPES set (lines 28-38)

Replace the existing `WIDGET_TYPES` set:

```python
WIDGET_TYPES = {
    "kpi_tile",
    "line_chart",
    "bar_chart",
    "gauge",
    "table",
    "alert_feed",
    "fleet_status",
    "device_count",
    "health_score",
}
```

With:

```python
WIDGET_TYPES = {
    "kpi_tile",
    "line_chart",
    "bar_chart",
    "area_chart",
    "gauge",
    "table",
    "alert_feed",
    "fleet_status",
    "fleet_overview",
    "device_count",
    "health_score",
    "stat_card",
    "pie_chart",
    "scatter",
    "radar",
}
```

That's it — one set expansion. No other changes needed.

## Verification

After applying, restart the backend and try adding any of the new widget types from the dashboard UI. The 400 error should be gone and widgets should save successfully.

## Files Modified

- `services/ui_iot/routes/dashboards.py` — expand `WIDGET_TYPES` set (add 6 entries)
