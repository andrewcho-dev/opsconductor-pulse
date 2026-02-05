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
