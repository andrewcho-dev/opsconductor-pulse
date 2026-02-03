# Task 000: Fix Broken UI Before Testing

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> This task fixes UI bugs that must be resolved before writing tests against them.
> RUN THE TESTS in the Test section. Do not proceed if tests fail.

---

## Context

The customer UI has several broken or inconsistent elements that need fixing before we can write reliable tests. These issues were discovered during a manual review:

1. **`/customer/devices` nav link** — points to a JSON API endpoint, not an HTML page
2. **`/customer/alerts` nav link** — same problem, shows raw JSON in browser
3. **Email integration page** — uses Tailwind CSS classes but Tailwind is never imported; styling is completely different from webhook/SNMP pages
4. **Webhook and SNMP JS** — no HTML escaping (XSS risk); email JS has `escapeHtml()` but the others don't
5. **Template directory inconsistency** — `customer_dashboard.html` and `customer_device.html` are in root `/templates/`, but integration pages are in `/templates/customer/`

**Read first**:
- `services/ui_iot/templates/customer/base.html` (nav links, CSS)
- `services/ui_iot/routes/customer.py` (all routes — note which return HTML vs JSON)
- `services/ui_iot/static/js/webhook_integrations.js` (no escapeHtml)
- `services/ui_iot/static/js/snmp_integrations.js` (no escapeHtml)
- `services/ui_iot/static/js/email_integrations.js` (has escapeHtml — use as reference)
- `services/ui_iot/templates/customer/email_integrations.html` (Tailwind classes)
- `services/ui_iot/templates/customer/webhook_integrations.html` (dark theme)
- `services/ui_iot/templates/customer/snmp_integrations.html` (dark theme)

---

## Task

### 0.1 Create shared CSS file

Extract the inline `<style>` block from `customer/base.html` into a shared CSS file at `services/ui_iot/static/css/customer.css`.

The CSS should include all existing styles from base.html plus additional shared styles for:
- Tables (consistent styling for all integration pages)
- Modals (consistent overlay, positioning, sizing)
- Forms (consistent input/button styling)
- Cards (`.card` class used by webhook and SNMP pages)

In `customer/base.html`, replace the `<style>` block with:
```html
<link rel="stylesheet" href="/static/css/customer.css">
```

### 0.2 Create `/customer/devices` HTML page

Create `services/ui_iot/templates/customer/devices.html`:
- Extends `customer/base.html`
- Shows a table of devices for the current tenant
- Columns: Device ID, Site, Status, Last Seen, Battery (if available)
- Status badges with color coding (ONLINE=green, STALE=orange)
- Each device ID links to `/customer/devices/{device_id}`
- Data is rendered server-side (same pattern as the dashboard)

Modify the `/devices` route in `customer.py`:
- The current route returns JSON. Change it to return HTML when accessed by a browser.
- Add a query parameter `format=json` that returns the existing JSON response (for API consumers and tests).
- Default (no format param) returns the HTML template with device data embedded.
- This matches the pattern used by `/devices/{device_id}` which already has conditional rendering.

### 0.3 Create `/customer/alerts` HTML page

Create `services/ui_iot/templates/customer/alerts.html`:
- Extends `customer/base.html`
- Shows a table of recent alerts for the current tenant
- Columns: Severity, Alert Type, Device ID, Message, Timestamp, Status
- Severity badges with color coding (critical=red, warning=orange, info=blue)
- Each device ID links to `/customer/devices/{device_id}`
- Data is rendered server-side

Modify the `/alerts` route in `customer.py`:
- Same pattern as devices: HTML by default, `?format=json` for API.

### 0.4 Fix existing test assertions

After changing `/devices` and `/alerts` to return HTML by default, update the existing tests in `tests/api/test_customer_routes.py` that call these endpoints:
- `test_list_devices_with_token` — add `?format=json` to the request URL
- `test_list_devices_with_cookie` — add `?format=json` to the request URL
- `test_get_device_wrong_tenant_returns_404` — should still work (device detail endpoint)
- `test_list_alerts` — add `?format=json` to the request URL
- Any other test that calls `/customer/devices` or `/customer/alerts` and expects JSON

### 0.5 Fix email integration page styling

Rewrite `services/ui_iot/templates/customer/email_integrations.html`:
- Remove ALL Tailwind CSS classes
- Use the same dark theme, card layout, modal structure, and button styles as `webhook_integrations.html` and `snmp_integrations.html`
- Use the shared CSS classes from `customer.css`
- Keep all form fields and functionality identical

### 0.6 Add `escapeHtml` to webhook and SNMP JavaScript

In `services/ui_iot/static/js/webhook_integrations.js`, add the `escapeHtml` function (copy from email_integrations.js):
```javascript
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
```

Then wrap all user-provided data in template literals with `escapeHtml()`:
- `${i.name}` → `${escapeHtml(i.name)}`
- `${i.url || '-'}` → `${escapeHtml(i.url || '-')}`
- Fix `onclick` handlers: `'${i.integration_id}'` → `'${escapeHtml(i.integration_id)}'`

Do the same in `services/ui_iot/static/js/snmp_integrations.js`:
- `${i.name}` → `${escapeHtml(i.name)}`
- `${i.snmp_host}:${i.snmp_port}` → `${escapeHtml(i.snmp_host)}:${escapeHtml(String(i.snmp_port))}`
- Fix `onclick` handlers similarly

### 0.7 Move misplaced templates

Move the two misplaced template files into the `customer/` subdirectory:
```bash
mv services/ui_iot/templates/customer_dashboard.html services/ui_iot/templates/customer/dashboard.html
mv services/ui_iot/templates/customer_device.html services/ui_iot/templates/customer/device.html
```

Update the template references in the code:
- In `routes/customer.py`: `customer_dashboard.html` → `customer/dashboard.html`
- In `routes/customer.py`: `customer_device.html` → `customer/device.html`

### 0.8 Update nav links

In `customer/base.html`, the nav links for Devices and Alerts should already point to `/customer/devices` and `/customer/alerts` — verify these are correct after the route changes.

Add an `active` class to highlight the current page's nav link. Use Jinja2:
```html
<a href="/customer/dashboard" class="nav-link {% if request.url.path == '/customer/dashboard' %}active{% endif %}">Dashboard</a>
<a href="/customer/devices" class="nav-link {% if request.url.path.startswith('/customer/devices') %}active{% endif %}">Devices</a>
<a href="/customer/alerts" class="nav-link {% if request.url.path.startswith('/customer/alerts') %}active{% endif %}">Alerts</a>
<a href="/customer/webhooks" class="nav-link {% if request.url.path == '/customer/webhooks' %}active{% endif %}">Webhooks</a>
<a href="/customer/snmp-integrations" class="nav-link {% if request.url.path == '/customer/snmp-integrations' %}active{% endif %}">SNMP</a>
<a href="/customer/email-integrations" class="nav-link {% if request.url.path == '/customer/email-integrations' %}active{% endif %}">Email</a>
```

Add the `.active` style in `customer.css`:
```css
.nav-link.active { color: #fff; border-bottom: 2px solid #8ab4f8; }
```

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `services/ui_iot/static/css/customer.css` |
| CREATE | `services/ui_iot/templates/customer/devices.html` |
| CREATE | `services/ui_iot/templates/customer/alerts.html` |
| MOVE | `templates/customer_dashboard.html` → `templates/customer/dashboard.html` |
| MOVE | `templates/customer_device.html` → `templates/customer/device.html` |
| MODIFY | `services/ui_iot/templates/customer/base.html` |
| MODIFY | `services/ui_iot/templates/customer/email_integrations.html` |
| MODIFY | `services/ui_iot/routes/customer.py` |
| MODIFY | `services/ui_iot/static/js/webhook_integrations.js` |
| MODIFY | `services/ui_iot/static/js/snmp_integrations.js` |
| MODIFY | `tests/api/test_customer_routes.py` |

---

## Test

```bash
# 1. Rebuild UI container
cd compose && docker compose up -d --build ui

# 2. Wait for UI
sleep 5

# 3. Verify all nav links return HTML (not JSON)
source compose/.env
for path in /customer/dashboard /customer/devices /customer/alerts /customer/webhooks /customer/snmp-integrations /customer/email-integrations; do
    STATUS=$(curl -sf -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" http://${HOST_IP}:8080${path})
    CONTENT_TYPE=$(curl -sf -o /dev/null -w "%{content_type}" -H "Authorization: Bearer $TOKEN" http://${HOST_IP}:8080${path})
    echo "${path}: HTTP ${STATUS}, Content-Type: ${CONTENT_TYPE}"
done

# 4. Verify JSON endpoints still work
curl -sf -H "Authorization: Bearer $TOKEN" http://${HOST_IP}:8080/customer/devices?format=json | python3 -c "import sys,json; d=json.load(sys.stdin); print('Devices JSON:', type(d))"
curl -sf -H "Authorization: Bearer $TOKEN" http://${HOST_IP}:8080/customer/alerts?format=json | python3 -c "import sys,json; d=json.load(sys.stdin); print('Alerts JSON:', type(d))"

# 5. Run integration tests (verify existing tests still pass)
KEYCLOAK_URL=http://${HOST_IP}:8180 pytest tests/ -v --ignore=tests/e2e -x

# 6. Run E2E tests
KEYCLOAK_URL=http://${HOST_IP}:8180 UI_BASE_URL=http://${HOST_IP}:8080 RUN_E2E=1 pytest tests/e2e/ -v -x
```

---

## Acceptance Criteria

- [ ] Every nav link in customer/base.html navigates to an HTML page (not JSON)
- [ ] `/customer/devices` renders an HTML table of devices
- [ ] `/customer/alerts` renders an HTML table of alerts
- [ ] `/customer/devices?format=json` returns JSON (backward compatibility)
- [ ] `/customer/alerts?format=json` returns JSON (backward compatibility)
- [ ] All three integration pages (webhook, SNMP, email) use the same dark theme
- [ ] Email integration page has NO Tailwind CSS classes
- [ ] `escapeHtml()` is used in ALL three integration JS files
- [ ] All templates are in `templates/customer/` subdirectory
- [ ] Nav links highlight the current page
- [ ] All existing integration tests pass
- [ ] All E2E tests pass

---

## Commit

```
Fix broken customer UI pages and standardize design

- Add HTML pages for /customer/devices and /customer/alerts (were JSON-only)
- Standardize all integration pages on shared dark theme CSS
- Remove non-functional Tailwind CSS from email integration page
- Add escapeHtml() to webhook and SNMP JS (XSS prevention)
- Move all customer templates into customer/ subdirectory
- Add active nav link highlighting
- Extract shared CSS into static/css/customer.css

Part of Phase 9: Testing Overhaul
```
