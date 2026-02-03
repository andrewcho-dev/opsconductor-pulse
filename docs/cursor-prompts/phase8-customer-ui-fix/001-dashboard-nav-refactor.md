# Task 001: Refactor Customer Dashboard and Device Pages to Use Base Template

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Create/Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

The customer dashboard (`customer_dashboard.html`) and device detail page (`customer_device.html`) are standalone HTML files with no navigation. A base template (`customer/base.html`) exists with a proper nav bar linking to Dashboard, Devices, Alerts, Webhook Integrations, SNMP Integrations, and Email Integrations — but the two most important pages don't use it.

The SNMP and Email integration pages extend `customer/base.html` and have the nav. The dashboard and device detail do not. Customers see a dead-end dashboard with no way to reach any integration pages.

**Read first**:
- `services/ui_iot/templates/customer/base.html` (the nav bar and base layout)
- `services/ui_iot/templates/customer_dashboard.html` (standalone, no nav)
- `services/ui_iot/templates/customer_device.html` (standalone, no nav)
- `services/ui_iot/templates/customer/snmp_integrations.html` (example of extending base.html)

**Depends on**: None

---

## Task

### 1.1 Refactor `customer_dashboard.html` to extend `customer/base.html`

Rewrite `services/ui_iot/templates/customer_dashboard.html` so that:

1. It extends `customer/base.html` using `{% extends "customer/base.html" %}`
2. The page title is in a `{% block title %}` block
3. All dashboard content (stats cards, device table, alerts table, delivery table) goes inside `{% block content %}`
4. Remove the duplicate `<html>`, `<head>`, `<body>`, header, logout button, and inline styles — these come from base.html now
5. Keep all dashboard-specific styles in a `<style>` tag inside the content block (or a `{% block styles %}` block if base.html supports it — check first)
6. Keep the `<meta http-equiv="refresh">` for auto-refresh — add it inside a `{% block head %}` or put it in the content block as a JS equivalent (`setTimeout(() => location.reload(), {{ refresh }} * 1000)`)
7. Keep the `<script src="/static/js/auth.js"></script>` — base.html already includes it, so don't duplicate it

The dashboard must still:
- Show tenant badge and user email (base.html already handles this via `{{ tenant_id }}` and `{{ user.email }}`)
- Show device stats cards (Total, Online, Stale, Open Alerts)
- Show devices table with links to `/customer/devices/{device_id}`
- Show alerts table
- Show delivery attempts table
- Auto-refresh

### 1.2 Refactor `customer_device.html` to extend `customer/base.html`

Same approach as the dashboard:

1. Extend `customer/base.html`
2. Move device detail content into `{% block content %}`
3. Remove duplicate HTML boilerplate, header, styles that base.html provides
4. Keep device-specific styles and content
5. Keep the auto-refresh and sparkline SVG logic

### 1.3 Merge styles if needed

Compare the styles in `customer_dashboard.html` and `customer_device.html` with `customer/base.html`. If the dashboard or device page defines styles that are not in base.html but are needed (stat cards, table styles, sparkline styles, status/severity colors), add them to `customer/base.html` so all pages get them.

Styles to check:
- `.stats`, `.stat-card`, `.stat-value`, `.stat-label` (dashboard)
- `table`, `th`, `td` styles (dashboard)
- `.status-online`, `.status-stale` (dashboard)
- `.severity-critical`, `.severity-warning` (dashboard)
- Sparkline/SVG styles (device detail)

### 1.4 Verify the route still passes correct template variables

Check `services/ui_iot/routes/customer.py` line 271. The dashboard route renders `customer_dashboard.html` with variables: `request`, `refresh`, `tenant_id`, `device_counts`, `devices`, `alerts`, `delivery_attempts`, `user`.

After refactoring, the template path should stay the same (`customer_dashboard.html`) OR move to `customer/dashboard.html` — either way, update the route to match.

If you move the file to `customer/dashboard.html`, update the route at line 271 to:
```python
return templates.TemplateResponse(
    "customer/dashboard.html",
    {...}
)
```

Same for device detail at line 328 — if moved to `customer/device.html`, update accordingly.

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| MODIFY | `services/ui_iot/templates/customer/base.html` (add shared styles) |
| MODIFY | `services/ui_iot/templates/customer_dashboard.html` (refactor to extend base) |
| MODIFY | `services/ui_iot/templates/customer_device.html` (refactor to extend base) |
| MODIFY | `services/ui_iot/routes/customer.py` (update template paths if files moved) |

---

## Test

```bash
# 1. Rebuild UI
cd compose && docker compose up -d --build ui

# 2. Wait for UI
sleep 3

# 3. Get a token
TOKEN=$(curl -s -X POST http://192.168.10.53:8180/realms/pulse/protocol/openid-connect/token \
    -d "grant_type=password" \
    -d "client_id=pulse-ui" \
    -d "username=customer1" \
    -d "password=test123" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 4. Verify dashboard renders HTML with nav links
curl -s -b "pulse_session=$TOKEN" http://192.168.10.53:8080/customer/dashboard | grep -c "nav-link"
# Expected: 6 (one per nav link)

# 5. Verify nav links exist
curl -s -b "pulse_session=$TOKEN" http://192.168.10.53:8080/customer/dashboard | grep -o 'href="/customer/[^"]*"' | sort
# Expected:
# href="/customer/alerts"
# href="/customer/dashboard"
# href="/customer/devices"
# href="/customer/email-integrations"
# href="/customer/integrations"  (or /customer/webhooks - will fix in task 002)
# href="/customer/snmp-integrations"

# 6. Verify dashboard still shows stats
curl -s -b "pulse_session=$TOKEN" http://192.168.10.53:8080/customer/dashboard | grep -c "stat-card"
# Expected: 4

# 7. Verify device detail page also has nav
DEVICE_ID=$(curl -s -H "Authorization: Bearer $TOKEN" http://192.168.10.53:8080/customer/devices | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['devices'][0]['device_id'] if d['devices'] else 'test-device-a1')")
curl -s -b "pulse_session=$TOKEN" "http://192.168.10.53:8080/customer/devices/$DEVICE_ID" | grep -c "nav-link"
# Expected: 6

# 8. Run integration tests
cd /home/opsconductor/simcloud && pytest tests/ -v --ignore=tests/e2e -x

# 9. Run E2E tests
KEYCLOAK_URL=http://192.168.10.53:8180 UI_BASE_URL=http://192.168.10.53:8080 RUN_E2E=1 pytest tests/e2e/ -v -x
```

**ALL tests must pass. E2E tests must NOT be skipped.**

---

## Acceptance Criteria

- [ ] Customer dashboard extends `customer/base.html`
- [ ] Customer device detail extends `customer/base.html`
- [ ] Nav bar visible on dashboard with 6 links
- [ ] Nav bar visible on device detail with 6 links
- [ ] Dashboard still shows stat cards, device table, alerts, deliveries
- [ ] Device detail still shows device info and sparklines
- [ ] Auto-refresh still works on both pages
- [ ] No duplicate `<html>`, `<head>`, `<body>` tags
- [ ] Integration tests pass
- [ ] E2E tests pass (RUN_E2E=1, NOT skipped)

---

## Commit

```
Refactor customer dashboard and device pages to use base template

Customer dashboard and device detail were standalone HTML with no
navigation. Refactored to extend customer/base.html so they get
the shared nav bar linking to all integration management pages.

- Dashboard extends base.html with nav bar
- Device detail extends base.html with nav bar
- Shared styles moved to base template
- All 6 nav links visible on every customer page

Part of Phase 8: Customer UI Fix
```
