# Task 002: Create Webhook Integration UI Page

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Create/Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

Webhook integrations have full API support (CRUD + test delivery) but no UI page. SNMP and Email both have UI pages. The webhook nav link currently points to `/customer/integrations` which is a JSON API endpoint — clicking it shows raw JSON in the browser.

**Read first**:
- `services/ui_iot/templates/customer/snmp_integrations.html` (pattern to follow)
- `services/ui_iot/static/js/snmp_integrations.js` (pattern to follow)
- `services/ui_iot/routes/customer.py` lines 286-303 (SNMP/Email HTML route pattern)
- `services/ui_iot/routes/customer.py` lines 429-446 (webhook list API — returns `{tenant_id, integrations}`)
- `services/ui_iot/routes/customer.py` lines 1032-1054 (webhook create API — POST, fields: name, webhook_url, enabled)
- `services/ui_iot/routes/customer.py` lines 1074-1104 (webhook update API — PATCH, fields: name, webhook_url, enabled)
- `services/ui_iot/routes/customer.py` lines 1107-1120 (webhook delete API — DELETE, returns 204)
- `services/ui_iot/routes/customer.py` lines 1283+ (test delivery — POST `/integrations/{id}/test`)

**Depends on**: Task 001 (base template with nav)

---

## Task

### 2.1 Create `services/ui_iot/templates/customer/webhook_integrations.html`

Follow the SNMP template pattern exactly:

1. Extend `customer/base.html`
2. Title block: "Webhook Integrations"
3. Content block with:
   - Header row: "Webhook Integrations" title + "Add Webhook" button
   - `<div id="webhook-list">Loading...</div>` for the integration table
   - Modal form with fields:
     - Name (text input, required)
     - Webhook URL (text input, required)
     - Enabled (checkbox, default checked)
   - Hidden input for integration-id (for edit mode)
   - Error display div
   - Cancel and Save buttons
4. Load `/static/js/webhook_integrations.js` at the bottom

### 2.2 Create `services/ui_iot/static/js/webhook_integrations.js`

Follow the SNMP JS pattern exactly. Functions needed:

**`loadIntegrations()`**:
- Fetch GET `/customer/integrations` with `{credentials: 'include'}`
- Response format is `{tenant_id, integrations: [...]}` — use `data.integrations`
- Each integration has: `integration_id`, `name`, `url` (redacted), `enabled`, `created_at`
- Render table with columns: Name, URL, Status, Actions (Test, Delete)
- If empty, show "No webhook integrations configured."

**`openModal()`**: Reset form, show modal
**`closeModal()`**: Hide modal

**`saveIntegration(e)`**:
- Read form fields: name, webhook_url, enabled
- POST to `/customer/integrations` with `{name, webhook_url, enabled}`
- Content-Type: application/json, credentials: include
- On success: close modal, reload list
- On error: show error detail in form

**`testIntegration(id)`**:
- POST to `/customer/integrations/{id}/test` with `{credentials: 'include'}`
- Alert success or failure message

**`deleteIntegration(id)`**:
- Confirm dialog
- DELETE `/customer/integrations/{id}` with `{credentials: 'include'}`
- Reload list

### 2.3 Add HTML-serving route in `services/ui_iot/routes/customer.py`

Add a new route right after the email-integrations route (around line 303):

```python
@router.get("/webhooks", include_in_schema=False)
async def webhooks_page(request: Request):
    """Render webhook integrations page."""
    tenant_id = get_tenant_id()
    return templates.TemplateResponse(
        "customer/webhook_integrations.html",
        {"request": request, "tenant_id": tenant_id, "user": getattr(request.state, "user", None)},
    )
```

### 2.4 Fix the nav link in `services/ui_iot/templates/customer/base.html`

Change the webhook nav link from:
```html
<a href="/customer/integrations" class="nav-link">Webhook Integrations</a>
```

To:
```html
<a href="/customer/webhooks" class="nav-link">Webhook Integrations</a>
```

This points to the new HTML page route, not the JSON API endpoint.

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `services/ui_iot/templates/customer/webhook_integrations.html` |
| CREATE | `services/ui_iot/static/js/webhook_integrations.js` |
| MODIFY | `services/ui_iot/routes/customer.py` (add HTML-serving route) |
| MODIFY | `services/ui_iot/templates/customer/base.html` (fix nav link) |

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

# 4. Verify webhook page renders HTML (not JSON)
curl -s -b "pulse_session=$TOKEN" http://192.168.10.53:8080/customer/webhooks | head -5
# Should show HTML starting with <!DOCTYPE html> or {% extends %} rendered output

# 5. Verify webhook page has nav bar
curl -s -b "pulse_session=$TOKEN" http://192.168.10.53:8080/customer/webhooks | grep -c "nav-link"
# Expected: 6

# 6. Verify webhook page loads JS
curl -s -b "pulse_session=$TOKEN" http://192.168.10.53:8080/customer/webhooks | grep "webhook_integrations.js"
# Expected: line with script src

# 7. Verify nav link points to /customer/webhooks (not /customer/integrations)
curl -s -b "pulse_session=$TOKEN" http://192.168.10.53:8080/customer/dashboard | grep "Webhook Integrations" | grep -o 'href="[^"]*"'
# Expected: href="/customer/webhooks"

# 8. Verify SNMP page still works
curl -s -b "pulse_session=$TOKEN" http://192.168.10.53:8080/customer/snmp-integrations | grep -c "nav-link"
# Expected: 6

# 9. Verify email page still works
curl -s -b "pulse_session=$TOKEN" http://192.168.10.53:8080/customer/email-integrations | grep -c "nav-link"
# Expected: 6

# 10. Verify the JSON API still works (unchanged)
curl -s -H "Authorization: Bearer $TOKEN" http://192.168.10.53:8080/customer/integrations | python3 -c "import sys,json; d=json.load(sys.stdin); print('API OK, integrations:', len(d.get('integrations',[])))"

# 11. Run integration tests
cd /home/opsconductor/simcloud && pytest tests/ -v --ignore=tests/e2e -x

# 12. Run E2E tests
KEYCLOAK_URL=http://192.168.10.53:8180 UI_BASE_URL=http://192.168.10.53:8080 RUN_E2E=1 pytest tests/e2e/ -v -x
```

**ALL tests must pass. E2E tests must NOT be skipped.**

---

## Acceptance Criteria

- [ ] `/customer/webhooks` renders an HTML page (not JSON)
- [ ] Webhook page extends `customer/base.html` with nav bar
- [ ] Webhook page has "Add Webhook" button
- [ ] Webhook page loads `webhook_integrations.js`
- [ ] JS fetches from `/customer/integrations` and renders table
- [ ] JS can create webhook (POST), delete (DELETE), test (POST /test)
- [ ] Nav link updated from `/customer/integrations` to `/customer/webhooks`
- [ ] All 6 nav links work across all customer pages
- [ ] JSON API at `/customer/integrations` still works unchanged
- [ ] SNMP and Email pages unaffected
- [ ] Integration tests pass
- [ ] E2E tests pass (RUN_E2E=1, NOT skipped)

---

## Commit

```
Add webhook integration UI page

Webhook integrations had API routes but no UI. Created HTML template,
JavaScript, and page-serving route following the SNMP/Email pattern.
Fixed nav link to point to the new page instead of the JSON endpoint.

- customer/webhook_integrations.html (extends base, modal form)
- webhook_integrations.js (CRUD + test delivery)
- GET /customer/webhooks route serves the page
- Nav link updated from /customer/integrations to /customer/webhooks

Part of Phase 8: Customer UI Fix
```
