# Task 002: Remove Legacy Template and Static Files

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Delete/modify only the files listed in "Files to Delete/Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

Task 1 removed all template-rendering routes from the backend. The Jinja HTML template files and legacy static JS/CSS files are now orphaned — nothing references them. This task deletes them and updates the Dockerfile to stop copying them.

**Read first**:
- `services/ui_iot/Dockerfile` — lines 14-15 copy templates and static
- `services/ui_iot/templates/` — all HTML files to delete
- `services/ui_iot/static/` — all JS/CSS files to delete

---

## Task

### 2.1 Delete all template files

Delete the entire templates directory and all files in it:

```
services/ui_iot/templates/customer/base.html
services/ui_iot/templates/customer/dashboard.html
services/ui_iot/templates/customer/devices.html
services/ui_iot/templates/customer/device.html
services/ui_iot/templates/customer/alerts.html
services/ui_iot/templates/customer/alert_rules.html
services/ui_iot/templates/customer/webhook_integrations.html
services/ui_iot/templates/customer/snmp_integrations.html
services/ui_iot/templates/customer/email_integrations.html
services/ui_iot/templates/customer/mqtt_integrations.html
services/ui_iot/templates/dashboard.html
services/ui_iot/templates/device.html
```

Delete the entire `services/ui_iot/templates/` directory.

### 2.2 Delete all legacy static files

Delete the entire static directory and all files in it:

```
services/ui_iot/static/css/customer.css
services/ui_iot/static/js/auth.js
services/ui_iot/static/js/live_dashboard.js
services/ui_iot/static/js/device_charts.js
services/ui_iot/static/js/alert_rules.js
services/ui_iot/static/js/webhook_integrations.js
services/ui_iot/static/js/snmp_integrations.js
services/ui_iot/static/js/email_integrations.js
services/ui_iot/static/js/mqtt_integrations.js
```

Delete the entire `services/ui_iot/static/` directory.

### 2.3 Update Dockerfile

**File**: `services/ui_iot/Dockerfile`

Remove these two COPY lines:

```dockerfile
COPY templates /app/templates
COPY static /app/static
```

The resulting Dockerfile should look like:

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py /app/app.py
COPY middleware /app/middleware
COPY db /app/db
COPY routes /app/routes
COPY schemas /app/schemas
COPY services /app/services
COPY utils /app/utils

EXPOSE 8080
ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
```

The SPA is served from `/app/spa` which is volume-mounted at runtime from `frontend/dist` (not baked into the image).

---

## Files to Delete/Modify

| Action | Path | What |
|--------|------|------|
| DELETE | `services/ui_iot/templates/` | Entire directory — all 12 HTML template files |
| DELETE | `services/ui_iot/static/` | Entire directory — all 9 JS/CSS files |
| MODIFY | `services/ui_iot/Dockerfile` | Remove COPY lines for templates and static |

---

## Test

### Step 1: Verify templates directory is gone

```bash
ls /home/opsconductor/simcloud/services/ui_iot/templates/ 2>&1 && echo "FAIL: templates still exist" || echo "OK: templates deleted"
```

Should show "OK: templates deleted".

### Step 2: Verify static directory is gone

```bash
ls /home/opsconductor/simcloud/services/ui_iot/static/ 2>&1 && echo "FAIL: static still exists" || echo "OK: static deleted"
```

Should show "OK: static deleted".

### Step 3: Verify Dockerfile has no template/static COPY

```bash
grep -n "templates\|static" /home/opsconductor/simcloud/services/ui_iot/Dockerfile || echo "OK: no template/static references"
```

Should show "OK: no template/static references".

### Step 4: Count remaining files

```bash
find /home/opsconductor/simcloud/services/ui_iot -name "*.html" | wc -l
```

Should be 0.

```bash
find /home/opsconductor/simcloud/services/ui_iot -name "*.css" -o -name "*.js" | wc -l
```

Should be 0 (no legacy JS/CSS in the backend).

---

## Acceptance Criteria

- [ ] All 12 HTML template files deleted
- [ ] All 9 JS/CSS static files deleted
- [ ] `templates/` directory no longer exists
- [ ] `static/` directory no longer exists
- [ ] Dockerfile no longer copies templates or static
- [ ] No `.html` files remain in `services/ui_iot/`
- [ ] No legacy `.js` or `.css` files remain in `services/ui_iot/`

---

## Commit

```
Delete legacy Jinja templates and static assets

Remove all 12 HTML template files and 9 JS/CSS static files.
Update Dockerfile to stop copying templates and static
directories. The React SPA is now the sole frontend.

Phase 22 Task 2: Remove Legacy Files
```
