# 137-004: Dashboards, Message Routes & Export Jobs

## Task
Add seed functions for dashboards, dashboard_widgets, message_routes, and export_jobs.

## File
`scripts/seed_demo_data.py`

## 1. seed_dashboards

Create 1 default dashboard per tenant:

```python
for tenant_id in TENANTS:
    existing = await conn.fetchval(
        "SELECT COUNT(*) FROM dashboards WHERE tenant_id = $1 AND is_default = TRUE",
        tenant_id
    )
    if existing > 0:
        continue

    dashboard_id = await conn.fetchval("""
        INSERT INTO dashboards (tenant_id, user_id, name, description, is_default, layout)
        VALUES ($1, NULL, $2, $3, TRUE, $4::jsonb)
        RETURNING id
    """,
        tenant_id,
        "Fleet Overview",
        "Default dashboard showing fleet health at a glance",
        json.dumps([
            {"i": "w1", "x": 0, "y": 0, "w": 3, "h": 2},
            {"i": "w2", "x": 3, "y": 0, "w": 3, "h": 2},
            {"i": "w3", "x": 0, "y": 2, "w": 6, "h": 3},
            {"i": "w4", "x": 0, "y": 5, "w": 6, "h": 3},
        ])
    )
```

## 2. seed_dashboard_widgets

Create 4 widgets per dashboard:

```python
widgets = [
    {
        "widget_type": "kpi",
        "title": "Total Devices",
        "config": {"metric": "device_count", "format": "number"},
        "position": {"x": 0, "y": 0, "w": 3, "h": 2},
    },
    {
        "widget_type": "kpi",
        "title": "Open Alerts",
        "config": {"metric": "open_alert_count", "format": "number", "thresholds": {"warning": 5, "critical": 10}},
        "position": {"x": 3, "y": 0, "w": 3, "h": 2},
    },
    {
        "widget_type": "chart",
        "title": "Temperature Trend",
        "config": {"metric": "temp_c", "chart_type": "line", "time_range": "24h", "aggregation": "avg"},
        "position": {"x": 0, "y": 2, "w": 6, "h": 3},
    },
    {
        "widget_type": "table",
        "title": "Recent Alerts",
        "config": {"source": "alerts", "limit": 10, "columns": ["severity", "device_id", "message", "created_at"]},
        "position": {"x": 0, "y": 5, "w": 6, "h": 3},
    },
]

for tenant_id in TENANTS:
    dashboard_id = await conn.fetchval(
        "SELECT id FROM dashboards WHERE tenant_id = $1 AND is_default = TRUE",
        tenant_id
    )
    if not dashboard_id:
        continue

    existing_count = await conn.fetchval(
        "SELECT COUNT(*) FROM dashboard_widgets WHERE dashboard_id = $1",
        dashboard_id
    )
    if existing_count > 0:
        continue  # already seeded

    for widget in widgets:
        await conn.execute("""
            INSERT INTO dashboard_widgets (dashboard_id, widget_type, title, config, position)
            VALUES ($1, $2, $3, $4::jsonb, $5::jsonb)
        """, dashboard_id, widget["widget_type"], widget["title"],
            json.dumps(widget["config"]), json.dumps(widget["position"]))
```

## 3. seed_message_routes

Create 1 message route per tenant:

```python
routes_data = {
    "tenant-a": {
        "name": "Production Telemetry Forward",
        "topic_filter": "tenant/tenant-a/device/+/telemetry",
        "destination_type": "webhook",
        "destination_config": {
            "url": "https://analytics.acme-iot.example/ingest",
            "method": "POST",
            "headers": {"X-API-Key": "demo-key"}
        },
    },
    "tenant-b": {
        "name": "Alert Webhook",
        "topic_filter": "tenant/tenant-b/device/+/alerts",
        "destination_type": "webhook",
        "destination_config": {
            "url": "https://monitoring.nordic.example/webhook",
            "method": "POST"
        },
    },
}

for tenant_id, route in routes_data.items():
    existing = await conn.fetchval(
        "SELECT COUNT(*) FROM message_routes WHERE tenant_id = $1 AND name = $2",
        tenant_id, route["name"]
    )
    if existing > 0:
        continue
    await conn.execute("""
        INSERT INTO message_routes (tenant_id, name, topic_filter, destination_type, destination_config, is_enabled)
        VALUES ($1, $2, $3, $4, $5::jsonb, TRUE)
    """, tenant_id, route["name"], route["topic_filter"],
        route["destination_type"], json.dumps(route["destination_config"]))
```

## 4. seed_export_jobs

Create 1 completed export job per tenant:

```python
import uuid

for tenant_id in TENANTS:
    job_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"demo-export-{tenant_id}"))  # deterministic UUID
    existing = await conn.fetchval(
        "SELECT COUNT(*) FROM export_jobs WHERE id = $1", job_id
    )
    if existing > 0:
        continue

    await conn.execute("""
        INSERT INTO export_jobs (id, tenant_id, export_type, format, filters, status,
            file_path, file_size_bytes, row_count, created_by,
            started_at, completed_at, expires_at)
        VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, $8, $9, $10,
            NOW() - INTERVAL '3 hours', NOW() - INTERVAL '2 hours 55 minutes',
            NOW() + INTERVAL '21 hours')
    """, job_id, tenant_id, "devices", "csv",
        json.dumps({"status": "ONLINE"}), "COMPLETED",
        f"/exports/{tenant_id}/devices-export.csv", 15360, 30,
        f"demo-admin-{tenant_id}")
```

## Wire Up in main()
```python
await seed_dashboards(pool)
await seed_dashboard_widgets(pool)
await seed_message_routes(pool)
await seed_export_jobs(pool)
```

## Verification
```sql
SELECT tenant_id, name, is_default FROM dashboards;
-- 2 rows
SELECT d.name, COUNT(w.*) FROM dashboards d LEFT JOIN dashboard_widgets w ON d.id = w.dashboard_id GROUP BY d.name;
-- Each dashboard has 4 widgets
SELECT tenant_id, name, destination_type FROM message_routes;
-- 2 rows
SELECT tenant_id, export_type, status FROM export_jobs;
-- 2 rows, both COMPLETED
```
