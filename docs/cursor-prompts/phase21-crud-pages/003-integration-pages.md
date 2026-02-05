# Task 003: Integration Pages — Webhook, SNMP, Email, MQTT

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Create/modify only the files listed in "Files to Create/Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

Task 1 created API functions and hooks for all four integration types. This task implements the four integration management pages. All four pages follow the same UX pattern: a card list of integrations with create/edit dialog, delete confirmation, test delivery button, and enable/disable toggle. They differ only in form fields.

**Read first**:
- `frontend/src/features/integrations/WebhookPage.tsx` — current stub (same for Snmp/Email/Mqtt)
- `frontend/src/hooks/use-integrations.ts` — all integration hooks
- `frontend/src/services/api/types.ts` — integration types from Task 1
- `frontend/src/features/alerts/AlertRulesPage.tsx` — CRUD pattern from Task 2
- `frontend/src/services/auth/AuthProvider.tsx` — useAuth() for role checks

---

## Task

### 3.1 Create shared integration components

These components are used by all four integration pages.

#### DeleteIntegrationDialog

**File**: `frontend/src/features/integrations/DeleteIntegrationDialog.tsx` (NEW)

A confirmation dialog for deleting any integration. Props: `name` (integration name), `open`, `onClose`, `onConfirm`, `isPending`.

- Shows "Delete integration '{name}'?"
- "Delete" button (destructive variant) calls `onConfirm`
- Disabled while `isPending` is true

#### TestDeliveryButton

**File**: `frontend/src/features/integrations/TestDeliveryButton.tsx` (NEW)

A button that triggers test delivery and shows result. Props: `onTest` (async function), `disabled`.

- Button text: "Test"
- While testing: show spinner + "Testing..."
- On success: show green "Delivered" text for 3 seconds
- On error: show red error message for 5 seconds
- Uses local state for test result display

### 3.2 Implement WebhookPage

**File**: `frontend/src/features/integrations/WebhookPage.tsx` (REPLACE)

The simplest integration page. Webhook form fields:
- **Name** — text input (required)
- **Webhook URL** — text input (required, full URL like `https://example.com/hook`)
- **Enabled** — switch toggle

Page layout:
1. **PageHeader** with "Webhooks", count description, "Add Webhook" button (customer_admin only)
2. **Card grid** (responsive, 1-2 columns) showing each webhook:
   - Card header: integration name + enabled switch
   - Card body: URL (displayed as-is from API, may be redacted)
   - Card footer: Test button, Edit button, Delete button (customer_admin only)
3. Loading/empty/error states

Webhook-specific details:
- The webhook list endpoint returns `{ integrations: [...] }` (not an array directly)
- Use `useWebhooks()` hook which returns `WebhookListResponse`
- Access webhooks as `data?.integrations`
- Create/edit dialog uses `WebhookIntegrationCreate` / `WebhookIntegrationUpdate`
- The `integration_id` field is used as the ID (not `id`)

### 3.3 Implement SnmpPage

**File**: `frontend/src/features/integrations/SnmpPage.tsx` (REPLACE)

Same card pattern as WebhookPage but with SNMP-specific fields.

SNMP form fields:
- **Name** — text input (required)
- **SNMP Host** — text input (required)
- **SNMP Port** — number input (default: 162)
- **SNMP Version** — select: "2c" or "3"
- **OID Prefix** — text input (default: "1.3.6.1.4.1.99999")
- **Enabled** — switch toggle

Version-specific fields (shown/hidden based on version selection):
- If v2c: **Community String** — text input (required)
- If v3: **Username**, **Auth Protocol** (select: MD5/SHA/SHA256), **Auth Password**, optionally **Privacy Protocol** (select: DES/AES/AES256), **Privacy Password**

SNMP-specific details:
- List endpoint returns array directly (not wrapped in object)
- Use `useSnmpIntegrations()` hook
- Access as `data` (the array itself), not `data?.integrations`
- ID field is `id` (not `integration_id`)
- Card shows: host:port, version badge, OID prefix
- Create payload includes nested `snmp_config` object (v2c or v3)

### 3.4 Implement EmailPage

**File**: `frontend/src/features/integrations/EmailPage.tsx` (REPLACE)

Email form fields:
- **Name** — text input (required)
- **SMTP Host** — text input (required)
- **SMTP Port** — number input (default: 587)
- **SMTP TLS** — switch toggle (default: true)
- **SMTP Username** — text input (optional)
- **SMTP Password** — password input (optional)
- **From Address** — text/email input (required)
- **From Name** — text input (optional, default: "OpsConductor Alerts")
- **To Recipients** — text input (comma-separated email addresses)
- **CC** — text input (comma-separated, optional)
- **Subject Template** — text input (default: `[{severity}] {alert_type}: {device_id}`)
- **Format** — select: "html" or "text"
- **Enabled** — switch toggle

Email-specific details:
- List returns array directly
- Use `useEmailIntegrations()` hook
- ID field is `id`
- Card shows: SMTP host:port, from address, recipient count, format badge
- Create payload has nested `smtp_config`, `recipients`, and `template` objects
- Recipients input: split comma-separated string into array for the `to` field
- Template variables hint: `{severity}`, `{alert_type}`, `{device_id}`, `{message}`, `{timestamp}`

### 3.5 Implement MqttPage

**File**: `frontend/src/features/integrations/MqttPage.tsx` (REPLACE)

MQTT form fields:
- **Name** — text input (required)
- **MQTT Topic** — text input (required, e.g., `alerts/tenant-1/critical`)
- **QoS** — select: 0 (At most once), 1 (At least once), 2 (Exactly once)
- **Retain** — switch toggle (default: false)
- **Enabled** — switch toggle

MQTT-specific details:
- List returns array directly
- Use `useMqttIntegrations()` hook
- ID field is `id`
- Card shows: topic, QoS badge, retain badge
- Simplest form after webhooks — only 5 fields

---

## Implementation Pattern (applies to all 4 pages)

Each page follows this exact pattern:

```
1. PageHeader with title, count, "Add" button
2. Loading: Skeleton cards
3. Empty: EmptyState with relevant icon
4. Error: Red error message
5. Cards: Grid of integration cards
   - Each card has:
     - Name in header + enabled switch
     - Key details in body (URL/host/topic etc.)
     - Footer: Test | Edit | Delete (customer_admin only)
6. Create/Edit Dialog (shadcn Dialog)
   - Form with type-specific fields
   - Save button calls create or update mutation
   - Error message from API displayed
7. Delete Dialog (shared component)
8. Test delivery (shared component)
```

Each page should have its own dialog component defined in the same file or a separate file — whichever keeps the code readable. For simpler forms (Webhook, MQTT), inline in the same file is fine. For complex forms (SNMP, Email), a separate dialog file is recommended.

Role-based visibility:
- `customer_admin`: can create, edit, delete, toggle, test
- `customer_viewer`: can view list only, no action buttons

---

## Files to Create/Modify

| Action | Path | What |
|--------|------|------|
| CREATE | `frontend/src/features/integrations/DeleteIntegrationDialog.tsx` | Shared delete confirmation |
| CREATE | `frontend/src/features/integrations/TestDeliveryButton.tsx` | Shared test delivery button |
| MODIFY | `frontend/src/features/integrations/WebhookPage.tsx` | Full webhook CRUD (replace stub) |
| MODIFY | `frontend/src/features/integrations/SnmpPage.tsx` | Full SNMP CRUD (replace stub) |
| MODIFY | `frontend/src/features/integrations/EmailPage.tsx` | Full email CRUD (replace stub) |
| MODIFY | `frontend/src/features/integrations/MqttPage.tsx` | Full MQTT CRUD (replace stub) |

---

## Test

### Step 1: Verify build

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
```

### Step 2: Verify TypeScript

```bash
cd /home/opsconductor/simcloud/frontend && npx tsc --noEmit
```

### Step 3: Verify implementation

Read the files and confirm:
- [ ] All 4 pages show card grid of integrations
- [ ] Each card shows name, key details, enabled switch
- [ ] Create dialog with correct fields per type
- [ ] Edit dialog prefills with existing data
- [ ] Delete confirmation dialog
- [ ] Test delivery button with success/error feedback
- [ ] Webhook uses `data?.integrations` (wrapped response)
- [ ] SNMP/Email/MQTT use `data` directly (array response)
- [ ] SNMP form toggles v2c/v3 fields based on version
- [ ] Email form splits comma-separated recipients into array
- [ ] CRUD buttons only visible for customer_admin
- [ ] Loading, empty, and error states on all pages

### Step 4: Verify backend tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

---

## Acceptance Criteria

- [ ] Webhook page: card list with name, URL, create/edit/delete/test
- [ ] SNMP page: card list with host:port, version, create/edit/delete/test
- [ ] Email page: card list with SMTP host, recipients, create/edit/delete/test
- [ ] MQTT page: card list with topic, QoS, create/edit/delete/test
- [ ] Shared delete confirmation dialog
- [ ] Shared test delivery button with status feedback
- [ ] All CRUD operations role-gated to customer_admin
- [ ] API error messages displayed in dialogs
- [ ] Loading/empty/error states on all 4 pages
- [ ] `npm run build` succeeds
- [ ] All Python tests pass

---

## Commit

```
Implement webhook, SNMP, email, and MQTT integration pages

Card-based CRUD for all four integration types with
create/edit dialogs, delete confirmation, test delivery,
and role-gated access. Shared components for delete
and test operations.

Phase 21 Task 3: Integration Pages
```
