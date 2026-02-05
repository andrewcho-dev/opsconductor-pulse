# Task 001: Chart.js CDN Setup + Chart CSS

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

**THE PROBLEM**: The UI uses server-rendered SVG polyline sparklines for 3 hardcoded metrics. We need a client-side charting library to render dynamic, interactive charts for ALL device metrics.

**Read first**:
- `services/ui_iot/templates/customer/base.html` — the base template loaded by all customer pages. Note `{% block head %}` (line 6) in `<head>` and `auth.js` at bottom of `<body>` (line 32).
- `services/ui_iot/static/css/customer.css` — current styling: dark theme (#1a1a2e background), card class (#2a2a4e), chartbox class (line 33)

---

## Task

### 1.1 Add Chart.js CDN to base template

**File**: `services/ui_iot/templates/customer/base.html`

Add Chart.js and its date adapter via CDN scripts BEFORE the `{% block head %}` tag in `<head>` (after line 5, before line 6). This makes Chart.js available to all customer pages:

```html
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
```

So the `<head>` section becomes:
```html
<head>
    <title>{% block title %}OpsConductor Pulse{% endblock %}</title>
    <link rel="stylesheet" href="/static/css/customer.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
    {% block head %}{% endblock %}
</head>
```

The date-fns adapter bundle includes date-fns — no separate import needed.

### 1.2 Add chart CSS classes

**File**: `services/ui_iot/static/css/customer.css`

Add these classes at the end of the file (after the `.form-section h4` rule, around line 55):

```css
.chart-wrapper { background: #2a2a4e; border: 1px solid #333; border-radius: 10px; padding: 12px; margin-bottom: 16px; }
.chart-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.chart-label { font-size: 14px; color: #aaa; text-transform: uppercase; letter-spacing: 0.5px; }
.chart-value { font-size: 18px; font-weight: bold; color: #8ab4f8; }
.chart-container { position: relative; height: 200px; }
.metric-charts { margin: 20px 0; }
.time-range-controls { display: flex; gap: 8px; margin-bottom: 16px; }
.time-range-controls button { padding: 6px 14px; border: 1px solid #555; background: #2a2a4e; color: #eee; border-radius: 6px; cursor: pointer; font-family: monospace; font-size: 12px; }
.time-range-controls button.active { background: #8ab4f8; color: #1a1a2e; border-color: #8ab4f8; }
.ws-indicator { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; padding: 4px 10px; border-radius: 999px; background: #1a1a2e; border: 1px solid #333; }
.ws-indicator.connected { color: #4caf50; border-color: #4caf50; }
.ws-indicator.disconnected { color: #f44336; border-color: #f44336; }
.ws-dot { width: 8px; height: 8px; border-radius: 50%; background: currentColor; display: inline-block; }
.metric-pills { display: flex; flex-wrap: wrap; gap: 6px; margin: 10px 0; }
```

---

## Files to Modify

| Action | Path | What changes |
|--------|------|--------------|
| MODIFY | `services/ui_iot/templates/customer/base.html` | Add Chart.js + date adapter CDN scripts |
| MODIFY | `services/ui_iot/static/css/customer.css` | Add chart, time-range, WS indicator CSS classes |

---

## Test

### Step 1: Run existing unit tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

All existing tests must pass. CDN scripts and CSS classes don't affect tests.

### Step 2: Verify changes

Read the files and confirm:
- [ ] Chart.js CDN script in base.html `<head>` BEFORE `{% block head %}`
- [ ] chartjs-adapter-date-fns CDN script in base.html `<head>`
- [ ] `.chart-wrapper`, `.chart-header`, `.chart-label`, `.chart-value`, `.chart-container` classes in CSS
- [ ] `.time-range-controls` and `.time-range-controls button.active` classes
- [ ] `.ws-indicator`, `.ws-indicator.connected`, `.ws-indicator.disconnected`, `.ws-dot` classes
- [ ] `.metric-pills` class

---

## Acceptance Criteria

- [ ] Chart.js 4 available via CDN on all customer pages
- [ ] Date adapter available for time-axis support
- [ ] Chart container CSS matches dark theme (background #2a2a4e, border #333)
- [ ] Chart height fixed at 200px (responsive width)
- [ ] WebSocket indicator CSS ready for dashboard
- [ ] Time-range button CSS ready for device detail
- [ ] All existing tests pass

---

## Commit

```
Add Chart.js CDN and chart CSS classes

Chart.js 4 + date-fns adapter via jsDelivr CDN in base template.
CSS classes for chart wrappers, time-range controls, WebSocket
connection indicator, and metric pills.

Phase 17 Task 1: Chart.js Setup
```
