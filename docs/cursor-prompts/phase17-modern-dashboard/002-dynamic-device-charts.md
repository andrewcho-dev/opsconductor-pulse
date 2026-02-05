# Task 002: Dynamic Device Detail Charts

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

**THE PROBLEM**: The device detail page (`device.html`) renders 3 hardcoded SVG sparklines for battery_pct, temp_c, and rssi_dbm. Since Phase 14, devices can send arbitrary metrics (pressure_psi, humidity_pct, vibration_g, etc.). The Phase 16 API endpoint `GET /api/v2/devices/{device_id}/telemetry` returns ALL metrics dynamically. The device page needs to use this endpoint and create a Chart.js chart for every metric the device reports.

**Read first**:
- `services/ui_iot/templates/customer/device.html` — current device detail template. Note the 3 SVG sparklines (lines 32-51), the status pills (lines 19-25), and the events table (lines 53-79).
- `services/ui_iot/routes/customer.py` — the `get_device_detail` handler (lines 408-464). Note how it fetches from the OLD hardcoded `fetch_device_telemetry_influx` function and computes `sparkline_points`.
- `services/ui_iot/static/css/customer.css` — the chart CSS classes added in Task 001.

---

## Task

### 2.1 Create device charts JavaScript

**File**: `services/ui_iot/static/js/device_charts.js` (NEW)

Create a new JavaScript file that:
1. Reads `device_id` from a data attribute on the body element
2. Fetches telemetry from the API v2 endpoint
3. Discovers all metric keys from the response
4. Creates a Chart.js line chart for each metric
5. Shows the latest value above each chart

```javascript
/* device_charts.js — Dynamic metric charts for device detail page */

const METRIC_COLORS = [
    '#8ab4f8', '#2a9d8f', '#e76f51', '#f4a261',
    '#e9c46a', '#a855f7', '#06b6d4', '#f97316',
];

function formatMetricName(key) {
    return key.replace(/_/g, ' ').replace(/\b\w/g, function(c) { return c.toUpperCase(); });
}

function escapeHtml(str) {
    var d = document.createElement('div');
    d.appendChild(document.createTextNode(str));
    return d.innerHTML;
}

async function fetchTelemetry(deviceId, start, end, limit) {
    var url = '/api/v2/devices/' + encodeURIComponent(deviceId) + '/telemetry?limit=' + (limit || 120);
    if (start) url += '&start=' + encodeURIComponent(start);
    if (end) url += '&end=' + encodeURIComponent(end);

    var resp = await fetch(url, { credentials: 'include' });
    if (!resp.ok) return null;
    return await resp.json();
}

function getMetricKeys(telemetry) {
    var keys = {};
    for (var i = 0; i < telemetry.length; i++) {
        var metrics = telemetry[i].metrics;
        for (var key in metrics) {
            if (metrics.hasOwnProperty(key)) {
                keys[key] = true;
            }
        }
    }
    return Object.keys(keys).sort();
}

function createChart(canvasId, label, timestamps, values, color) {
    var ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: timestamps,
            datasets: [{
                label: label,
                data: values,
                borderColor: color,
                tension: 0.3,
                pointRadius: 0,
                borderWidth: 2,
                fill: false,
                spanGaps: true,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    type: 'time',
                    time: { tooltipFormat: 'HH:mm:ss', displayFormats: { minute: 'HH:mm', hour: 'HH:mm' } },
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#888', maxTicksLimit: 8 },
                },
                y: {
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#888' },
                },
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    mode: 'nearest',
                    intersect: false,
                    backgroundColor: '#2a2a4e',
                    borderColor: '#555',
                    borderWidth: 1,
                    titleColor: '#eee',
                    bodyColor: '#eee',
                },
            },
            interaction: { mode: 'nearest', axis: 'x', intersect: false },
        },
    });
}

// Store chart instances for cleanup on re-render
var _chartInstances = [];

function destroyCharts() {
    for (var i = 0; i < _chartInstances.length; i++) {
        _chartInstances[i].destroy();
    }
    _chartInstances = [];
}

async function renderCharts(deviceId, start, end) {
    var container = document.getElementById('metric-charts');
    if (!container) return;

    var data = await fetchTelemetry(deviceId, start, end, 120);
    if (!data || !data.telemetry || data.telemetry.length === 0) {
        container.innerHTML = '<div class="small">No telemetry data available for this time range.</div>';
        return;
    }

    // Reverse so oldest is first (for chart left-to-right)
    var telemetry = data.telemetry.slice().reverse();
    var metricKeys = getMetricKeys(telemetry);
    var timestamps = telemetry.map(function(t) { return t.timestamp; });

    // Destroy existing charts before re-rendering
    destroyCharts();
    container.innerHTML = '';

    metricKeys.forEach(function(key, idx) {
        var values = telemetry.map(function(t) {
            var v = t.metrics[key];
            if (v === true) return 1;
            if (v === false) return 0;
            return v !== undefined ? v : null;
        });
        var color = METRIC_COLORS[idx % METRIC_COLORS.length];

        // Find latest non-null value
        var latestVal = null;
        for (var i = values.length - 1; i >= 0; i--) {
            if (values[i] !== null) { latestVal = values[i]; break; }
        }
        var displayVal = latestVal !== null ? (typeof latestVal === 'number' ? latestVal.toFixed(2) : latestVal) : '—';

        var canvasId = 'chart-' + key;
        var wrapper = document.createElement('div');
        wrapper.className = 'chart-wrapper';
        wrapper.innerHTML =
            '<div class="chart-header">' +
            '  <span class="chart-label">' + escapeHtml(formatMetricName(key)) + '</span>' +
            '  <span class="chart-value" style="color:' + color + '">' + escapeHtml(String(displayVal)) + '</span>' +
            '</div>' +
            '<div class="chart-container">' +
            '  <canvas id="' + canvasId + '"></canvas>' +
            '</div>';
        container.appendChild(wrapper);

        var chart = createChart(canvasId, formatMetricName(key), timestamps, values, color);
        if (chart) _chartInstances.push(chart);
    });
}

// --- Time range control ---
var _currentRange = null;

function getTimeRange(range) {
    var now = new Date();
    var start = new Date(now);
    switch (range) {
        case '1h': start.setHours(now.getHours() - 1); break;
        case '6h': start.setHours(now.getHours() - 6); break;
        case '24h': start.setDate(now.getDate() - 1); break;
        case '7d': start.setDate(now.getDate() - 7); break;
        default: return { start: null, end: null };
    }
    return { start: start.toISOString(), end: now.toISOString() };
}

function setActiveRange(range) {
    _currentRange = range;
    var buttons = document.querySelectorAll('.time-range-controls button');
    buttons.forEach(function(btn) {
        btn.classList.toggle('active', btn.dataset.range === range);
    });
}

function onRangeClick(e) {
    var range = e.target.dataset.range;
    if (!range) return;
    setActiveRange(range);
    var deviceId = document.body.dataset.deviceId;
    if (!deviceId) return;
    var tr = getTimeRange(range);
    renderCharts(deviceId, tr.start, tr.end);
}

document.addEventListener('DOMContentLoaded', function() {
    var deviceId = document.body.dataset.deviceId;
    if (!deviceId) return;

    // Attach time range button handlers
    var controls = document.querySelector('.time-range-controls');
    if (controls) {
        controls.addEventListener('click', onRangeClick);
    }

    // Initial load — no time range (default last ~120 points)
    renderCharts(deviceId, null, null);
});
```

### 2.2 Update device detail template

**File**: `services/ui_iot/templates/customer/device.html`

Replace the entire file content. The key changes:
1. Add `data-device-id="{{ device_id }}"` to the body tag (via a wrapper div, since we can't modify `<body>` from a child template)
2. Replace the 3 static SVG sparklines with a dynamic `<div id="metric-charts">` container
3. Add time-range buttons
4. Keep the status pills and events table unchanged
5. Include the new JS file via `{% block head %}`

New template content:

```html
{% extends "customer/base.html" %}

{% block title %}Device {{ device_id }} - OpsConductor Pulse{% endblock %}

{% block head %}
<script src="/static/js/device_charts.js" defer></script>
{% endblock %}

{% block content %}
<div id="device-page" data-device-id="{{ device_id }}">

<div class="breadcrumb">
  <a href="/customer/dashboard">Dashboard</a> &gt;
  <a href="/customer/devices">Devices</a> &gt;
  {{ device_id }}
</div>

{% if dev %}
  <div class="metric-pills">
    <div class="pill">Site: <b>{{ dev.site_id }}</b></div>
    <div class="pill {{ dev.status }}">Status: <b>{{ dev.status }}</b></div>
    <div class="pill">Last Seen: <b>{{ dev.last_seen_at }}</b></div>
    {% if dev.battery_pct is not none %}<div class="pill">Battery: <b>{{ dev.battery_pct }}%</b></div>{% endif %}
    {% if dev.temp_c is not none %}<div class="pill">Temp: <b>{{ dev.temp_c }}°C</b></div>{% endif %}
    {% if dev.rssi_dbm is not none %}<div class="pill">RSSI: <b>{{ dev.rssi_dbm }} dBm</b></div>{% endif %}
    {% if dev.snr_db is not none %}<div class="pill">SNR: <b>{{ dev.snr_db }} dB</b></div>{% endif %}
  </div>
{% else %}
  <div class="small">No device_state row found yet for {{ device_id }}.</div>
{% endif %}

<h2>Telemetry Charts</h2>

<div class="time-range-controls">
  <button data-range="1h">1h</button>
  <button data-range="6h">6h</button>
  <button data-range="24h">24h</button>
  <button data-range="7d">7d</button>
</div>

<div id="metric-charts" class="metric-charts">
  <div class="small">Loading charts...</div>
</div>

<h2>Last 50 Events</h2>
{% if events|length == 0 %}
  <div class="small">No events found.</div>
{% else %}
<table>
  <thead>
    <tr>
      <th>Ingested</th>
      <th>Accepted</th>
      <th>Site</th>
      <th>Type</th>
      <th>Reject Reason</th>
    </tr>
  </thead>
  <tbody>
    {% for e in events %}
    <tr>
      <td>{{ e.ingested_at }}</td>
      <td><b>{{ e.accepted }}</b></td>
      <td>{{ e.site_id }}</td>
      <td>{{ e.msg_type }}</td>
      <td>{{ e.reject_reason }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>
{% endif %}

</div>
{% endblock %}
```

**Important**: The `data-device-id` attribute is on a wrapper `<div id="device-page">` (NOT on `<body>`, since child templates can't modify `<body>` attributes in Jinja2). The JavaScript reads it with:
```javascript
// In device_charts.js DOMContentLoaded handler, change to:
var deviceId = document.body.dataset.deviceId || document.getElementById('device-page').dataset.deviceId;
```

Wait — actually update the JS to read from the wrapper div. Change the two places in `device_charts.js` where `document.body.dataset.deviceId` appears to:

```javascript
var el = document.getElementById('device-page');
var deviceId = el ? el.dataset.deviceId : null;
```

Make sure BOTH references (in `onRangeClick` and in the `DOMContentLoaded` handler) use this pattern.

### 2.3 No route handler changes needed

The existing `get_device_detail` route handler still works. It fetches and computes sparkline_points, but the new template simply doesn't use `charts.battery_pts`, `charts.temp_pts`, `charts.rssi_pts` anymore. The JavaScript fetches telemetry independently from API v2. The route handler's extra computation is harmless.

---

## Files to Modify

| Action | Path | What changes |
|--------|------|--------------|
| CREATE | `services/ui_iot/static/js/device_charts.js` | Dynamic metric chart rendering via API v2 + Chart.js |
| MODIFY | `services/ui_iot/templates/customer/device.html` | Replace SVG sparklines with Chart.js containers + time-range buttons |

---

## Test

### Step 1: Run existing unit tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

### Step 2: Verify implementation

Read the files and confirm:
- [ ] `device_charts.js` fetches from `/api/v2/devices/{device_id}/telemetry`
- [ ] Metric discovery: `getMetricKeys` extracts all unique keys from telemetry data
- [ ] A Chart.js chart is created for EACH metric (not hardcoded 3)
- [ ] Each chart shows the latest value in the header
- [ ] Charts use dark theme (matching existing CSS: grid lines rgba, ticks #888)
- [ ] Boolean metrics converted to 0/1 for charting
- [ ] `spanGaps: true` handles null values in data
- [ ] Chart instances stored in `_chartInstances` and destroyed before re-render
- [ ] `escapeHtml` used for metric names (XSS prevention)
- [ ] Time-range buttons present: 1h, 6h, 24h, 7d
- [ ] `device.html` has `data-device-id="{{ device_id }}"` attribute
- [ ] `device.html` no longer has SVG `<polyline>` sparklines
- [ ] Events table preserved exactly as before
- [ ] Status pills preserved (battery, temp, rssi, snr)
- [ ] `device_charts.js` loaded with `defer` attribute
- [ ] Meta-refresh tag removed (charts update via time-range buttons)

---

## Acceptance Criteria

- [ ] Device detail page shows Chart.js charts for ALL metrics reported by device
- [ ] Charts auto-discover metrics from API v2 response (not hardcoded)
- [ ] Each chart shows metric name and latest value
- [ ] Time-range buttons (1h, 6h, 24h, 7d) reload charts with filtered data
- [ ] Charts styled to match dark theme
- [ ] XSS prevention (escapeHtml for metric names)
- [ ] Events table and status pills unchanged
- [ ] All existing tests pass

---

## Commit

```
Replace sparkline charts with dynamic Chart.js visualizations

Device detail page auto-discovers all metrics from API v2 and
creates interactive Chart.js line charts for each. Time-range
buttons for 1h/6h/24h/7d filtering. Replaces hardcoded 3-metric
SVG sparklines.

Phase 17 Task 2: Dynamic Device Charts
```
