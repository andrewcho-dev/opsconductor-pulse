# Task 003: WebSocket Live Dashboard

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

**THE PROBLEM**: The customer dashboard reloads the ENTIRE page via `<meta http-equiv="refresh">` every N seconds. This causes visual flicker, loses scroll position, and wastes bandwidth. Phase 16 added a WebSocket endpoint (`/api/v2/ws`) that can push live alert data. The dashboard should use it.

**Read first**:
- `services/ui_iot/templates/customer/dashboard.html` — current dashboard: stat cards (lines 10-27), device table (lines 29-51), alert table (lines 53-75), delivery table (lines 77-99), meta-refresh (line 6)
- `services/ui_iot/routes/customer.py` — `customer_dashboard` handler (lines 303-329): fetches device_counts, devices, alerts, delivery_attempts
- `services/ui_iot/static/js/auth.js` — token refresh pattern. Note: `pulse_session` cookie is httpOnly (JS cannot read it directly)
- `services/ui_iot/routes/api_v2.py` — WebSocket endpoint at `/api/v2/ws?token=JWT`. The token must be passed explicitly.

**WebSocket auth challenge**: The `pulse_session` cookie is httpOnly, so JavaScript cannot read it. The WebSocket endpoint requires `?token=JWT`. Solution: the route handler reads the cookie value server-side and passes it to the template as a context variable.

---

## Task

### 3.1 Modify dashboard route handler to pass WS token

**File**: `services/ui_iot/routes/customer.py`

In the `customer_dashboard` function (around line 303), add `ws_token` to the template context. Find the `return templates.TemplateResponse(...)` call and add one key to the context dict:

```python
"ws_token": request.cookies.get("pulse_session", ""),
```

The context dict should now include:
```python
{
    "request": request,
    "refresh": UI_REFRESH_SECONDS,
    "tenant_id": tenant_id,
    "device_counts": device_counts,
    "devices": devices,
    "alerts": alerts,
    "delivery_attempts": delivery_attempts,
    "user": getattr(request.state, "user", None),
    "ws_token": request.cookies.get("pulse_session", ""),
}
```

### 3.2 Create live dashboard JavaScript

**File**: `services/ui_iot/static/js/live_dashboard.js` (NEW)

Create a JavaScript file that:
1. Connects to WebSocket for live alert updates
2. Periodically fetches device stats and updates stat cards via API v2
3. Shows a connection status indicator
4. Falls back to periodic polling if WebSocket fails

```javascript
/* live_dashboard.js — WebSocket live updates for the customer dashboard */

function escapeHtml(str) {
    var d = document.createElement('div');
    d.appendChild(document.createTextNode(str));
    return d.innerHTML;
}

// --- WebSocket connection ---

var _ws = null;
var _wsRetryCount = 0;
var _wsMaxRetries = 5;
var _wsRetryDelay = 5000;

function updateWsIndicator(connected) {
    var el = document.getElementById('ws-status');
    if (!el) return;
    if (connected) {
        el.className = 'ws-indicator connected';
        el.innerHTML = '<span class="ws-dot"></span> Live';
    } else {
        el.className = 'ws-indicator disconnected';
        el.innerHTML = '<span class="ws-dot"></span> Offline';
    }
}

function connectWebSocket() {
    var tokenEl = document.getElementById('dashboard-page');
    var token = tokenEl ? tokenEl.dataset.wsToken : '';
    if (!token) {
        updateWsIndicator(false);
        return;
    }

    var protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    var url = protocol + '//' + location.host + '/api/v2/ws?token=' + encodeURIComponent(token);

    try {
        _ws = new WebSocket(url);
    } catch (e) {
        updateWsIndicator(false);
        return;
    }

    _ws.onopen = function() {
        updateWsIndicator(true);
        _wsRetryCount = 0;
        // Subscribe to alerts
        _ws.send(JSON.stringify({ action: 'subscribe', type: 'alerts' }));
    };

    _ws.onmessage = function(event) {
        try {
            var msg = JSON.parse(event.data);
            if (msg.type === 'alerts') {
                updateAlertTable(msg.alerts || []);
                updateAlertCount(msg.alerts ? msg.alerts.length : 0);
            }
        } catch (e) {
            // Ignore parse errors
        }
    };

    _ws.onclose = function() {
        updateWsIndicator(false);
        _ws = null;
        // Auto-reconnect with backoff
        if (_wsRetryCount < _wsMaxRetries) {
            _wsRetryCount++;
            setTimeout(connectWebSocket, _wsRetryDelay * _wsRetryCount);
        }
    };

    _ws.onerror = function() {
        updateWsIndicator(false);
    };
}

// --- DOM updates ---

function updateAlertCount(count) {
    var el = document.getElementById('alert-count');
    if (el) el.textContent = count;
}

function updateAlertTable(alerts) {
    var tbody = document.getElementById('alert-tbody');
    if (!tbody) return;

    if (alerts.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="small">No open alerts.</td></tr>';
        return;
    }

    var html = '';
    for (var i = 0; i < alerts.length; i++) {
        var a = alerts[i];
        var sevClass = '';
        if (a.severity >= 5) sevClass = 'severity-critical';
        else if (a.severity >= 3) sevClass = 'severity-warning';
        else sevClass = 'severity-info';

        html += '<tr>' +
            '<td>' + escapeHtml(a.created_at || '') + '</td>' +
            '<td>' + escapeHtml(a.device_id || '') + '</td>' +
            '<td>' + escapeHtml(a.alert_type || '') + '</td>' +
            '<td class="' + sevClass + '">' + escapeHtml(String(a.severity || '')) + '</td>' +
            '<td>' + escapeHtml(a.summary || '') + '</td>' +
            '</tr>';
    }
    tbody.innerHTML = html;
}

function updateStatCards(devices) {
    var total = devices.length;
    var online = 0;
    var stale = 0;
    for (var i = 0; i < devices.length; i++) {
        if (devices[i].status === 'ONLINE') online++;
        else if (devices[i].status === 'STALE') stale++;
    }

    var elTotal = document.getElementById('stat-total');
    var elOnline = document.getElementById('stat-online');
    var elStale = document.getElementById('stat-stale');
    if (elTotal) elTotal.textContent = total;
    if (elOnline) elOnline.textContent = online;
    if (elStale) elStale.textContent = stale;
}

async function refreshDeviceStats() {
    try {
        var resp = await fetch('/api/v2/devices?limit=500', { credentials: 'include' });
        if (!resp.ok) return;
        var data = await resp.json();
        updateStatCards(data.devices || []);
    } catch (e) {
        // Silently fail — stat cards keep their last value
    }
}

// --- Initialization ---

document.addEventListener('DOMContentLoaded', function() {
    var page = document.getElementById('dashboard-page');
    if (!page) return;

    // Connect WebSocket for live alerts
    connectWebSocket();

    // Periodic device stats refresh (every 30 seconds)
    refreshDeviceStats();
    setInterval(refreshDeviceStats, 30000);
});
```

### 3.3 Update dashboard template

**File**: `services/ui_iot/templates/customer/dashboard.html`

Update the template to:
1. Replace `<meta http-equiv="refresh">` with a longer fallback (60s instead of 5s)
2. Add `data-ws-token` attribute for WebSocket auth
3. Add WebSocket connection indicator
4. Add IDs to elements that JS will update dynamically
5. Include the live dashboard script

New template content:

```html
{% extends "customer/base.html" %}

{% block title %}OpsConductor Pulse - Dashboard{% endblock %}

{% block head %}
<meta http-equiv="refresh" content="60">
<script src="/static/js/live_dashboard.js" defer></script>
{% endblock %}

{% block content %}
<div id="dashboard-page" data-ws-token="{{ ws_token }}">

<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
    <div></div>
    <div id="ws-status" class="ws-indicator disconnected">
        <span class="ws-dot"></span> Connecting...
    </div>
</div>

<div class="stats">
    <div class="stat-card">
        <div class="stat-value" id="stat-total">{{ device_counts.total }}</div>
        <div class="stat-label">Total Devices</div>
    </div>
    <div class="stat-card">
        <div class="stat-value status-online" id="stat-online">{{ device_counts.online }}</div>
        <div class="stat-label">Online</div>
    </div>
    <div class="stat-card">
        <div class="stat-value status-stale" id="stat-stale">{{ device_counts.stale }}</div>
        <div class="stat-label">Stale</div>
    </div>
    <div class="stat-card">
        <div class="stat-value" id="alert-count">{{ alerts|length }}</div>
        <div class="stat-label">Open Alerts</div>
    </div>
</div>

<h2>Devices</h2>
<table>
    <thead>
        <tr>
            <th>Device ID</th>
            <th>Site</th>
            <th>Status</th>
            <th>Last Seen</th>
            <th>Battery</th>
        </tr>
    </thead>
    <tbody>
        {% for d in devices %}
        <tr>
            <td><a href="/customer/devices/{{ d.device_id }}">{{ d.device_id }}</a></td>
            <td>{{ d.site_id }}</td>
            <td class="status-{{ d.status|lower }}">{{ d.status }}</td>
            <td>{{ d.last_seen_at }}</td>
            <td>{{ d.battery_pct }}%</td>
        </tr>
        {% endfor %}
    </tbody>
</table>

<h2>Open Alerts <span class="small">(live via WebSocket)</span></h2>
<table>
    <thead>
        <tr>
            <th>Time</th>
            <th>Device</th>
            <th>Type</th>
            <th>Severity</th>
            <th>Summary</th>
        </tr>
    </thead>
    <tbody id="alert-tbody">
        {% for a in alerts %}
        <tr>
            <td>{{ a.created_at }}</td>
            <td>{{ a.device_id }}</td>
            <td>{{ a.alert_type }}</td>
            <td class="severity-{{ a.severity|lower }}">{{ a.severity }}</td>
            <td>{{ a.summary }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>

<h2>Recent Webhook Deliveries</h2>
<table>
    <thead>
        <tr>
            <th>Time</th>
            <th>Job</th>
            <th>Status</th>
            <th>HTTP</th>
            <th>Latency</th>
        </tr>
    </thead>
    <tbody>
        {% for d in delivery_attempts %}
        <tr>
            <td>{{ d.finished_at }}</td>
            <td>{{ d.job_id }}</td>
            <td>{% if d.ok %}OK{% else %}FAILED{% endif %}</td>
            <td>{{ d.http_status or '-' }}</td>
            <td>{{ d.latency_ms }}ms</td>
        </tr>
        {% endfor %}
    </tbody>
</table>

<p class="small">
    Stats refresh: 30s | Alerts: live via WebSocket | Fallback refresh: 60s |
    <a href="/customer/devices">All Devices</a> |
    <a href="/customer/alerts">All Alerts</a>
</p>

</div>
{% endblock %}
```

---

## Files to Modify

| Action | Path | What changes |
|--------|------|--------------|
| MODIFY | `services/ui_iot/routes/customer.py` | Add ws_token to dashboard template context |
| CREATE | `services/ui_iot/static/js/live_dashboard.js` | WebSocket connection + live alert updates + periodic stat refresh |
| MODIFY | `services/ui_iot/templates/customer/dashboard.html` | WS indicator, dynamic IDs, remove 5s meta-refresh, include JS |

---

## Test

### Step 1: Run existing unit tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

### Step 2: Verify implementation

Read the files and confirm:
- [ ] `ws_token` added to dashboard template context in customer.py
- [ ] `live_dashboard.js` connects to `/api/v2/ws?token=...`
- [ ] Token read from `data-ws-token` attribute on `#dashboard-page`
- [ ] WS subscribes to alerts on connection
- [ ] Alert table updates via `updateAlertTable()` on WebSocket message
- [ ] Alert count updates via `updateAlertCount()` on WebSocket message
- [ ] Stat cards (total/online/stale) refresh every 30s via `/api/v2/devices`
- [ ] WebSocket auto-reconnect with backoff (max 5 retries)
- [ ] WS connection indicator shows "Live" (green) or "Offline" (red)
- [ ] `escapeHtml` used for all dynamic content (XSS prevention)
- [ ] Meta-refresh set to 60s (fallback only, not primary refresh)
- [ ] Dashboard template has IDs: `stat-total`, `stat-online`, `stat-stale`, `alert-count`, `alert-tbody`
- [ ] Protocol detection: uses `wss:` for HTTPS pages

---

## Acceptance Criteria

- [ ] Dashboard alert table updates in real-time via WebSocket (no page reload)
- [ ] Stat cards refresh every 30 seconds via API v2
- [ ] WebSocket connection indicator visible (green when connected, red when not)
- [ ] Auto-reconnect on WebSocket disconnect (exponential backoff)
- [ ] Falls back to 60s page refresh if JavaScript fails
- [ ] XSS prevention on all dynamic content
- [ ] All existing tests pass

---

## Commit

```
Add WebSocket live updates to customer dashboard

Alert table updates in real-time via WebSocket. Stat cards
refresh every 30s via API v2. Connection indicator shows
live/offline status. Auto-reconnect with backoff.

Phase 17 Task 3: WebSocket Live Dashboard
```
