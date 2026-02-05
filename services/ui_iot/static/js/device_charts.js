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
    var el = document.getElementById('device-page');
    var deviceId = el ? el.dataset.deviceId : null;
    if (!deviceId) return;
    var tr = getTimeRange(range);
    renderCharts(deviceId, tr.start, tr.end);
}

document.addEventListener('DOMContentLoaded', function() {
    var el = document.getElementById('device-page');
    var deviceId = el ? el.dataset.deviceId : null;
    if (!deviceId) return;

    // Attach time range button handlers
    var controls = document.querySelector('.time-range-controls');
    if (controls) {
        controls.addEventListener('click', onRangeClick);
    }

    // Initial load — no time range (default last ~120 points)
    renderCharts(deviceId, null, null);
});
