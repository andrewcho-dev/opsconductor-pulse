# Task 007: Templates

## Context

Routes are implemented. Now we need templates for the customer dashboard and updates to the operator dashboard to show auth context.

**Read first**:
- `services/ui_iot/templates/dashboard.html` (existing operator template)
- `services/ui_iot/templates/device.html` (existing device detail template)
- `services/ui_iot/routes/customer.py` (template context passed)
- `services/ui_iot/routes/operator.py` (template context passed)

**Depends on**: Tasks 004, 005, 006

## Task

### 7.1 Create `services/ui_iot/templates/customer_dashboard.html`

A simplified, tenant-scoped dashboard for customers.

**Template structure**:

```html
<!DOCTYPE html>
<html>
<head>
    <title>OpsConductor Pulse - Dashboard</title>
    <meta http-equiv="refresh" content="{{ refresh }}">
    <style>
        /* Copy base styles from dashboard.html */
        /* Simplified color scheme for customer view */
        body { font-family: monospace; margin: 20px; background: #1a1a2e; color: #eee; }
        .header { display: flex; justify-content: space-between; align-items: center; }
        .tenant-badge { background: #4a4a6a; padding: 4px 12px; border-radius: 4px; }
        .user-info { font-size: 0.9em; color: #aaa; }
        .stats { display: flex; gap: 20px; margin: 20px 0; }
        .stat-card { background: #2a2a4e; padding: 15px; border-radius: 8px; }
        .stat-value { font-size: 2em; font-weight: bold; }
        .stat-label { color: #888; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #333; }
        th { background: #2a2a4e; }
        .status-online { color: #4caf50; }
        .status-stale { color: #ff9800; }
        .severity-critical { color: #f44336; }
        .severity-warning { color: #ff9800; }
        .logout-btn { background: #4a4a6a; color: #fff; padding: 8px 16px;
                      text-decoration: none; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>OpsConductor Pulse</h1>
        <div>
            <span class="tenant-badge">Tenant: {{ tenant_id }}</span>
            <span class="user-info">{{ user.email }}</span>
            <a href="/logout" class="logout-btn">Logout</a>
        </div>
    </div>

    <!-- Stats cards -->
    <div class="stats">
        <div class="stat-card">
            <div class="stat-value">{{ device_counts.total }}</div>
            <div class="stat-label">Total Devices</div>
        </div>
        <div class="stat-card">
            <div class="stat-value status-online">{{ device_counts.online }}</div>
            <div class="stat-label">Online</div>
        </div>
        <div class="stat-card">
            <div class="stat-value status-stale">{{ device_counts.stale }}</div>
            <div class="stat-label">Stale</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{{ alerts|length }}</div>
            <div class="stat-label">Open Alerts</div>
        </div>
    </div>

    <!-- Devices table -->
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

    <!-- Alerts table -->
    <h2>Open Alerts</h2>
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
        <tbody>
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

    <!-- Recent Deliveries -->
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

    <p style="color: #666; font-size: 0.8em;">
        Auto-refresh: {{ refresh }}s |
        <a href="/customer/devices">All Devices</a> |
        <a href="/customer/alerts">All Alerts</a>
    </p>
</body>
</html>
```

**Key differences from operator dashboard**:
- Shows tenant_id prominently
- No settings panel (customers can't change settings)
- No cross-tenant data
- No quarantine section (operator-only concern)
- No provisioning panel
- Simplified stats

### 7.2 Create `services/ui_iot/templates/customer_device.html`

Device detail view for customers (based on existing device.html).

**Template structure**:
- Copy structure from `device.html`
- Remove any tenant-switching UI
- Add tenant badge in header
- Add logout button
- Keep sparkline charts
- Keep event history table
- Add breadcrumb: Dashboard > Devices > {device_id}

### 7.3 Modify `services/ui_iot/templates/dashboard.html`

Update for operator context.

**Changes to add**:

1. Add operator badge in header:
```html
<div class="header">
    <h1>OpsConductor Pulse <span class="operator-badge">OPERATOR VIEW</span></h1>
    <div>
        <span class="user-info">{{ user.email }} ({{ user.role }})</span>
        <a href="/logout" class="logout-btn">Logout</a>
    </div>
</div>
```

2. Add CSS for operator badge:
```css
.operator-badge {
    background: #ff9800;
    color: #000;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.7em;
    vertical-align: middle;
}
```

3. Add tenant column to all tables (if not already present)

4. Update links to use operator routes:
```html
<!-- Before -->
<a href="/device/{{ d.device_id }}">{{ d.device_id }}</a>

<!-- After -->
<a href="/operator/tenants/{{ d.tenant_id }}/devices/{{ d.device_id }}">{{ d.device_id }}</a>
```

5. Update settings form action:
```html
<!-- Before -->
<form method="post" action="/settings">

<!-- After -->
<form method="post" action="/operator/settings">
```

6. Conditionally show settings panel (only for operator_admin):
```html
{% if user.role == 'operator_admin' %}
<div class="settings-panel">
    <!-- settings form -->
</div>
{% endif %}
```

### 7.4 Modify `services/ui_iot/templates/device.html`

Update for operator context.

**Changes**:
1. Add operator badge
2. Add logout button
3. Update breadcrumb to use operator route
4. Pass tenant_id in template context

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `services/ui_iot/templates/customer_dashboard.html` |
| CREATE | `services/ui_iot/templates/customer_device.html` |
| MODIFY | `services/ui_iot/templates/dashboard.html` |
| MODIFY | `services/ui_iot/templates/device.html` |

## Acceptance Criteria

- [ ] Customer dashboard shows tenant badge
- [ ] Customer dashboard has no settings panel
- [ ] Customer dashboard links go to `/customer/*` routes
- [ ] Operator dashboard shows "OPERATOR VIEW" badge
- [ ] Operator dashboard shows user email and role
- [ ] Operator dashboard links go to `/operator/*` routes
- [ ] Settings panel only visible for operator_admin
- [ ] Both dashboards have logout button
- [ ] Device detail pages have correct breadcrumbs

## Commit

```
Add customer dashboard template, update operator templates

- customer_dashboard.html: tenant-scoped, simplified view
- customer_device.html: device detail for customers
- dashboard.html: add operator badge, auth context, role-based settings
- device.html: update links for operator routes

Part of Phase 1: Customer Read-Only Dashboard
```
