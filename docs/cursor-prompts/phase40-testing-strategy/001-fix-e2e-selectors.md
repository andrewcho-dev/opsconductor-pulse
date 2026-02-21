# 001: Fix E2E Tests — Add Missing Element IDs to Frontend

## Problem
17 E2E tests fail because the React integration pages don't have the element IDs that E2E tests target. The tests expect `#btn-add-webhook`, `#webhook-list`, `#btn-add-snmp`, `#snmp-list`, etc.

## What to Do

### Step 1: Add test IDs to integration page components

The integration pages are at these exact paths:
- `frontend/src/features/integrations/WebhookPage.tsx`
- `frontend/src/features/integrations/SnmpPage.tsx`
- `frontend/src/features/integrations/EmailPage.tsx`
- `frontend/src/features/integrations/MqttPage.tsx`

Each page uses `<Dialog>` from shadcn for the create form. The E2E tests expect these IDs which **do NOT currently exist**:

**WebhookPage.tsx — add these IDs:**
- `id="btn-add-webhook"` on the "Add Webhook" `<Button>` element
- `id="webhook-list"` on the list/table container `<div>` that displays existing webhooks
- `id="webhook-modal"` on the `<Dialog>` component (or its `<DialogContent>`)
- `id="webhook-form"` on the `<form>` element inside the dialog
- `id="btn-cancel"` on the cancel button inside the dialog

IDs that **already exist** (do NOT duplicate): `webhook-name`, `webhook-url`

**SnmpPage.tsx — add these IDs:**
- `id="btn-add-snmp"` on the "Add SNMP" `<Button>`
- `id="snmp-list"` on the list container
- `id="snmp-modal"` on the `<Dialog>` / `<DialogContent>`
- `id="snmp-form"` on the `<form>`
- `id="snmp-version"` on the version `<Select>` component
- `id="btn-cancel"` on the cancel button

IDs that **already exist**: `snmp-name`, `snmp-host`, `snmp-port`, `snmp-community`, `snmp-username`, `snmp-auth-password`, `snmp-priv-password`, `v2c-config`, `v3-config`

**EmailPage.tsx — add these IDs:**
- `id="btn-add-email"` on the "Add Email" `<Button>`
- `id="email-list"` on the list container
- `id="email-modal"` on the `<Dialog>` / `<DialogContent>`
- `id="email-form"` on the `<form>`
- `id="btn-cancel"` on the cancel button

IDs that **already exist**: `email-name`, `smtp-host`, `smtp-port`, `from-address`, `recipients-to`

**MqttPage.tsx — add these IDs:**
- `id="btn-add-mqtt"` on the "Add MQTT" `<Button>`
- `id="mqtt-list"` on the list container
- `id="mqtt-modal"` on the `<Dialog>` / `<DialogContent>`
- `id="mqtt-form"` on the `<form>`
- `id="btn-cancel"` on the cancel button

### Step 2: Verify all E2E selectors have matching IDs

Read `tests/e2e/test_integration_crud.py` fully and grep for all `#` selectors. Cross-reference each one against the frontend components. Every `page.locator("#something")` must have a matching `id="something"` in the rendered HTML.

Also check `tests/e2e/test_page_load_performance.py` — it uses `#webhook-list`, `#snmp-list`, `#email-list` to verify page load.

### Step 3: Rebuild the SPA

After modifying frontend components:
```bash
cd frontend && npm run build && cd ..
```

Copy the build output to the SPA serving directory:
```bash
cp -r frontend/dist/* services/ui_iot/spa/
```

### Step 4: Verify

Run the integration CRUD E2E tests:
```bash
RUN_E2E=1 pytest tests/e2e/test_integration_crud.py -v --tb=short
```

Also run the page load performance tests that check these IDs:
```bash
RUN_E2E=1 pytest tests/e2e/test_page_load_performance.py -v --tb=short
```

## Reference Files
- `tests/e2e/test_integration_crud.py` — read fully to find ALL `#` selectors
- `tests/e2e/test_page_load_performance.py` — uses `#webhook-list`, `#snmp-list`, `#email-list`
- `tests/e2e/test_integrations.py` — uses `/customer/integrations` API
- `frontend/src/app/router.tsx` — routes: `/integrations/webhooks`, `/integrations/snmp`, `/integrations/email`, `/integrations/mqtt`

## Rules
- Only add `id` attributes. Do NOT change any component logic or styling.
- Every ID must be unique within the page.
- Use the exact IDs the tests expect (read the test files to find them).
- For Dialog components, add the `id` to `<DialogContent>` since that's the rendered DOM element.
