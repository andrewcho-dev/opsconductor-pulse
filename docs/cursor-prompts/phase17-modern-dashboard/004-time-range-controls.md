# Task 004: Time-Range Controls + Enhanced Device List

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

**THE PROBLEM**: Two remaining UI gaps:
1. The device list page (`devices.html`) shows only battery_pct from the state JSONB. The API v2 returns the full state with ALL metrics. Customers want to see more metrics at a glance.
2. The device detail page has time-range buttons (Task 2) but the device list doesn't link to the enhanced detail page in a useful way.

**Read first**:
- `services/ui_iot/templates/customer/devices.html` — current device list. Shows: Device ID, Site, Status, Last Seen, Battery. Only 5 columns.
- `services/ui_iot/routes/customer.py` — `list_devices` handler (lines 372-405). Fetches from `fetch_devices` which extracts 4 hardcoded metrics from state JSONB.
- `services/ui_iot/db/queries.py` — `fetch_devices_v2` (added in Phase 16) returns full state JSONB.

---

## Task

### 4.1 Update device list template to show dynamic metrics

**File**: `services/ui_iot/templates/customer/devices.html`

The device list currently shows a hardcoded Battery column. We'll enhance it to show the full `state` JSONB as a summary while keeping the table clean.

**Approach**: Instead of adding columns for every possible metric (which would make the table very wide), add a "Metrics" column that shows a compact summary of all metrics. The existing Battery column is kept for backward compatibility.

Read the current devices.html first, then replace its `{% block content %}` with an enhanced version that:
1. Adds a "Metrics" column showing a compact summary of state keys
2. Keeps existing columns (Device ID, Site, Status, Last Seen, Battery)

However, the current route handler uses `fetch_devices` which only extracts 4 fields from state. To get the full state JSONB, the template needs the route handler to use `fetch_devices_v2` instead.

### 4.2 Update device list route handler

**File**: `services/ui_iot/routes/customer.py`

In the `list_devices` function (around line 372), change the query function from `fetch_devices` to `fetch_devices_v2` for the HTML case. The JSON format case can also use v2.

Find this line inside the `list_devices` function:
```python
devices = await fetch_devices(conn, tenant_id, limit=limit, offset=offset)
```

Change it to:
```python
devices = await fetch_devices_v2(conn, tenant_id, limit=limit, offset=offset)
```

Also add the import if not already present. Check that `fetch_devices_v2` is imported from `db.queries` in the import block at the top of customer.py. If it's not listed, add it to the import list:
```python
from db.queries import (
    ...,
    fetch_devices_v2,
    ...,
)
```

**Note**: `fetch_devices_v2` returns `state` as a full JSONB dict instead of individual `->>` extractions. This means `d.battery_pct` is no longer a top-level key — it's inside `d.state.battery_pct`. The template needs to handle both formats.

### 4.3 Update devices.html template

**File**: `services/ui_iot/templates/customer/devices.html`

Update the template to:
1. Read battery from `d.state` (the v2 query returns state as a dict, not extracted keys)
2. Add a "Metrics" column showing metric key count and names
3. Keep existing layout

Replace the template content:

```html
{% extends "customer/base.html" %}

{% block title %}Devices - OpsConductor Pulse{% endblock %}

{% block content %}
<h2>Devices</h2>

<table>
    <thead>
        <tr>
            <th>Device ID</th>
            <th>Site</th>
            <th>Status</th>
            <th>Last Seen</th>
            <th>Battery</th>
            <th>Metrics</th>
        </tr>
    </thead>
    <tbody>
        {% for d in devices %}
        <tr>
            <td><a href="/customer/devices/{{ d.device_id }}">{{ d.device_id }}</a></td>
            <td>{{ d.site_id }}</td>
            <td class="status-{{ d.status|lower }}">{{ d.status }}</td>
            <td>{{ d.last_seen_at }}</td>
            <td>
                {% if d.state and d.state.battery_pct is not none %}
                    {{ d.state.battery_pct }}%
                {% elif d.battery_pct is not none %}
                    {{ d.battery_pct }}%
                {% else %}
                    -
                {% endif %}
            </td>
            <td class="small">
                {% if d.state %}
                    {{ d.state|length }} metrics
                {% else %}
                    -
                {% endif %}
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>
{% endblock %}
```

**Note**: The battery column checks both `d.state.battery_pct` (v2 format) and `d.battery_pct` (v1 fallback) for backward compatibility. The "Metrics" column shows the count of keys in the state JSONB.

### 4.4 Update dashboard device table for consistency

**File**: `services/ui_iot/routes/customer.py`

In the `customer_dashboard` function (around line 303), the device fetch also uses the old `fetch_devices`. Update it to `fetch_devices_v2` as well, so the dashboard device table gets full state data:

Find this line inside `customer_dashboard`:
```python
devices = await fetch_devices(conn, tenant_id, limit=50, offset=0)
```

Change it to:
```python
devices = await fetch_devices_v2(conn, tenant_id, limit=50, offset=0)
```

### 4.5 Update dashboard template battery column

**File**: `services/ui_iot/templates/customer/dashboard.html`

The dashboard device table has a Battery column. Update it to handle both v1 and v2 data format:

Find:
```html
<td>{{ d.battery_pct }}%</td>
```

Replace with:
```html
<td>{% if d.state and d.state.battery_pct is not none %}{{ d.state.battery_pct }}%{% elif d.battery_pct is not none %}{{ d.battery_pct }}%{% else %}-{% endif %}</td>
```

---

## Files to Modify

| Action | Path | What changes |
|--------|------|--------------|
| MODIFY | `services/ui_iot/routes/customer.py` | Switch list_devices and customer_dashboard to fetch_devices_v2, add import |
| MODIFY | `services/ui_iot/templates/customer/devices.html` | Add Metrics column, handle v2 state format |
| MODIFY | `services/ui_iot/templates/customer/dashboard.html` | Update battery column for v2 state format |

---

## Test

### Step 1: Run existing unit tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

### Step 2: Verify implementation

Read the files and confirm:
- [ ] `list_devices` uses `fetch_devices_v2` (not `fetch_devices`)
- [ ] `customer_dashboard` uses `fetch_devices_v2` (not `fetch_devices`)
- [ ] `fetch_devices_v2` is imported in customer.py
- [ ] `devices.html` has 6 columns: Device ID, Site, Status, Last Seen, Battery, Metrics
- [ ] Battery column handles both `d.state.battery_pct` and `d.battery_pct` formats
- [ ] Metrics column shows key count from state JSONB
- [ ] Dashboard battery column handles both formats
- [ ] No broken Jinja2 template syntax

---

## Acceptance Criteria

- [ ] Device list shows metric count per device
- [ ] Battery column works with v2 query data
- [ ] Dashboard device table consistent with device list
- [ ] All existing tests pass

---

## Commit

```
Enhance device list with dynamic metric summary

Device list and dashboard use fetch_devices_v2 for full state
JSONB. New Metrics column shows per-device metric count.
Battery column handles both v1 and v2 data formats.

Phase 17 Task 4: Enhanced Device List
```
