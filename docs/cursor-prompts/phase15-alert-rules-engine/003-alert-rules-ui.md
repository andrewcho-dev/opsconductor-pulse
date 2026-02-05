# Task 003: Alert Rules Customer UI

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

**THE PROBLEM**: Task 002 added the CRUD API for alert rules. Now customers need a UI page to manage their rules. The UI follows the same pattern as existing integration pages (webhooks, SNMP, email, MQTT).

**Read first**:
- `services/ui_iot/templates/customer/webhook_integrations.html` — the template pattern to replicate
- `services/ui_iot/static/js/webhook_integrations.js` — the JavaScript CRUD pattern to replicate
- `services/ui_iot/templates/customer/base.html` — the nav bar (lines 21-29)
- `services/ui_iot/static/css/customer.css` — existing CSS classes (`.card`, `.header-row`, `.modal-overlay`, `.form-row`, etc.)

---

## Task

### 3.1 Add nav link to base template

**File**: `services/ui_iot/templates/customer/base.html`

In the nav div (lines 21-29), add an "Alert Rules" link BETWEEN the "Alerts" link and the "Webhooks" link:

```html
<a href="/customer/alert-rules" class="nav-link {% if request.url.path == '/customer/alert-rules' %}active{% endif %}">Alert Rules</a>
```

So the nav order becomes: Dashboard | Devices | Alerts | **Alert Rules** | Webhooks | SNMP | Email | MQTT

### 3.2 Create alert rules template

**File**: `services/ui_iot/templates/customer/alert_rules.html` (NEW)

Create this file extending `customer/base.html`. Follow the EXACT same structure as `webhook_integrations.html`:

**Structure**:
```
{% extends "customer/base.html" %}
{% block title %}Alert Rules{% endblock %}
{% block content %}
  <div class="card">
    <div class="header-row">
      <h2>Alert Rules</h2>
      <button id="btn-add-rule">Add Rule</button>
    </div>
    <div id="rules-list" class="list-body">
      <div>Loading...</div>
    </div>
  </div>

  <!-- Modal for create/edit -->
  <div id="rule-modal" class="hidden modal-overlay">
    <div class="card modal">
      <h3 id="modal-title">Add Alert Rule</h3>
      <form id="rule-form">
        <input type="hidden" id="rule-id" value="">

        <div class="form-row">
          <label for="rule-name">Rule Name</label>
          <input type="text" id="rule-name" required maxlength="100" placeholder="e.g., Low Battery Warning">
        </div>

        <div class="form-row">
          <label for="rule-metric">Metric Name</label>
          <input type="text" id="rule-metric" required maxlength="100" placeholder="e.g., battery_pct, temp_c, pressure_psi">
        </div>

        <div class="form-row">
          <label for="rule-operator">Operator</label>
          <select id="rule-operator" required>
            <option value="LT">&lt; Less than</option>
            <option value="LTE">&le; Less than or equal</option>
            <option value="GT">&gt; Greater than</option>
            <option value="GTE">&ge; Greater than or equal</option>
          </select>
        </div>

        <div class="form-row">
          <label for="rule-threshold">Threshold</label>
          <input type="number" id="rule-threshold" required step="any" placeholder="e.g., 20.0">
        </div>

        <div class="form-row">
          <label for="rule-severity">Severity</label>
          <select id="rule-severity">
            <option value="5">5 - Critical</option>
            <option value="3" selected>3 - Warning</option>
            <option value="1">1 - Info</option>
          </select>
        </div>

        <div class="form-row">
          <label for="rule-description">Description (optional)</label>
          <input type="text" id="rule-description" maxlength="255" placeholder="Optional description">
        </div>

        <div class="form-row">
          <label for="rule-enabled">
            <input type="checkbox" id="rule-enabled" checked> Enabled
          </label>
        </div>

        <div id="form-error" class="hidden form-error"></div>
        <div class="form-actions">
          <button type="button" id="btn-cancel">Cancel</button>
          <button type="submit">Save</button>
        </div>
      </form>
    </div>
  </div>
{% endblock %}
{% block head %}
<script src="/static/js/alert_rules.js" defer></script>
{% endblock %}
```

### 3.3 Create alert rules JavaScript

**File**: `services/ui_iot/static/js/alert_rules.js` (NEW)

Create this file following the EXACT same pattern as `webhook_integrations.js`. The key functions:

**`escapeHtml(str)`**: Same XSS prevention function — create a text node and read innerHTML. Copy from webhook_integrations.js.

**`operatorLabel(op)`**: Convert operator codes to display symbols:
- GT → ">"
- LT → "<"
- GTE → ">="
- LTE → "<="

**`severityLabel(sev)`**: Convert severity numbers to display:
- 5 → "Critical"
- 3 → "Warning"
- 1 → "Info"
- default → severity number

**`loadRules()`**:
- `fetch('/customer/alert-rules?format=json', {credentials: 'include'})`
- Parse response JSON — expect `{tenant_id, rules: [...]}`
- Build HTML table with columns: Name, Metric, Condition (operator + threshold), Severity, Status (enabled/disabled), Actions (Edit, Delete)
- The "Condition" column should display like: `battery_pct < 20.0` (metric + operator symbol + threshold)
- Handle empty state: "No alert rules defined. Click 'Add Rule' to create one."

**`openModal(rule=null)`**:
- If `rule` is null: reset form for create mode, title "Add Alert Rule"
- If `rule` is provided: populate form fields for edit mode, title "Edit Alert Rule", set hidden rule-id
- Show modal

**`closeModal()`**: Hide modal, clear form error

**`saveRule(e)`**:
- Prevent default form submit
- Read form values: name, metric_name, operator, threshold (parseFloat), severity (parseInt), description, enabled
- If hidden rule-id is empty: POST to `/customer/alert-rules`
- If hidden rule-id has value: PATCH to `/customer/alert-rules/{rule_id}`
- On success: close modal, reload rules
- On error: display error in form-error div

**`deleteRule(ruleId)`**:
- `confirm('Delete this alert rule?')`
- DELETE `/customer/alert-rules/{ruleId}`
- On success: reload rules

**`editRule(ruleId)`**:
- GET `/customer/alert-rules/{ruleId}`
- Open modal with rule data

**DOMContentLoaded**:
- `loadRules()`
- Attach click handler to btn-add-rule → `openModal()`
- Attach click handler to btn-cancel → `closeModal()`
- Attach submit handler to rule-form → `saveRule(e)`

**All fetch calls must include `{credentials: 'include'}` and appropriate Content-Type headers for POST/PATCH.**

### 3.4 Verify the GET list endpoint returns template

**File**: `services/ui_iot/routes/customer.py`

In Task 002, the GET `/customer/alert-rules` endpoint was added. Verify it returns `templates.TemplateResponse("customer/alert_rules.html", ...)` for browser requests (not `?format=json`). The template context should include at minimum: `{"request": request, "tenant_id": tenant_id, "user": user}`.

---

## Files to Modify

| Action | Path | What changes |
|--------|------|--------------|
| MODIFY | `services/ui_iot/templates/customer/base.html` | Add "Alert Rules" nav link |
| CREATE | `services/ui_iot/templates/customer/alert_rules.html` | Alert rules page template |
| CREATE | `services/ui_iot/static/js/alert_rules.js` | JavaScript CRUD for alert rules |

---

## Test

### Step 1: Run existing unit tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

### Step 2: Verify UI files

Read the files and confirm:
- [ ] Nav link added between "Alerts" and "Webhooks" in base.html
- [ ] alert_rules.html extends customer/base.html
- [ ] Template has card layout with header-row (title + Add button)
- [ ] Template has modal with form fields: name, metric_name, operator (select), threshold (number), severity (select), description, enabled (checkbox)
- [ ] alert_rules.js has loadRules, openModal, closeModal, saveRule, deleteRule, editRule functions
- [ ] All fetch calls use `credentials: 'include'`
- [ ] escapeHtml function prevents XSS
- [ ] Table displays: Name, Metric, Condition, Severity, Status, Actions

---

## Acceptance Criteria

- [ ] "Alert Rules" nav link appears between "Alerts" and "Webhooks"
- [ ] `/customer/alert-rules` returns HTML page with rules table
- [ ] Modal form allows creating rules with all fields
- [ ] Edit mode pre-populates form from existing rule
- [ ] Delete shows confirmation dialog
- [ ] Severity displayed as "Critical"/"Warning"/"Info"
- [ ] Condition displayed as "metric operator threshold" (e.g., "battery_pct < 20.0")
- [ ] All existing unit tests pass

---

## Commit

```
Add customer UI page for managing alert rules

Card layout with HTML table, modal create/edit form, and
JavaScript CRUD. Supports metric name, operator, threshold,
severity, and description. Nav link added to customer sidebar.

Phase 15 Task 3: Alert Rules Customer UI
```
