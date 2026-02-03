# Task 007: Email Integration UI

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Create/Modify".
> Verify your work against the acceptance criteria.
> Commit with the exact message in the "Commit" section when done.

---

## Context

Customers need a UI to manage their email integrations. This includes listing, creating, editing, and testing email destinations.

**Read first**:
- `services/ui_iot/templates/customer/snmp_integrations.html` (pattern)
- `services/ui_iot/static/js/snmp_integrations.js` (pattern)

**Depends on**: Tasks 003, 006

---

## Task

### 7.1 Create email integrations page template

Create `services/ui_iot/templates/customer/email_integrations.html`:

```html
{% extends "customer/base.html" %}

{% block title %}Email Integrations{% endblock %}

{% block content %}
<div class="container mx-auto px-4 py-8">
    <div class="flex justify-between items-center mb-6">
        <h1 class="text-2xl font-bold">Email Integrations</h1>
        <button id="btn-add-email" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded">
            Add Email Integration
        </button>
    </div>

    <div id="email-list" class="bg-white rounded-lg shadow">
        <div class="p-4 text-gray-500 text-center">Loading...</div>
    </div>
</div>

<!-- Modal -->
<div id="email-modal" class="fixed inset-0 bg-black bg-opacity-50 hidden items-center justify-center z-50">
    <div class="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 p-6 max-h-[90vh] overflow-y-auto">
        <h2 id="modal-title" class="text-xl font-bold mb-4">Add Email Integration</h2>
        <form id="email-form">
            <input type="hidden" id="integration-id" value="">

            <!-- Basic Info -->
            <div class="mb-4">
                <label class="block text-sm font-medium mb-1">Name</label>
                <input type="text" id="email-name" required class="w-full border rounded px-3 py-2" placeholder="Alert Emails">
            </div>

            <!-- SMTP Settings -->
            <div class="border-t pt-4 mt-4">
                <h3 class="font-medium mb-3">SMTP Settings</h3>
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-sm font-medium mb-1">SMTP Host</label>
                        <input type="text" id="smtp-host" required class="w-full border rounded px-3 py-2" placeholder="smtp.example.com">
                    </div>
                    <div>
                        <label class="block text-sm font-medium mb-1">Port</label>
                        <input type="number" id="smtp-port" value="587" class="w-full border rounded px-3 py-2">
                    </div>
                </div>
                <div class="grid grid-cols-2 gap-4 mt-3">
                    <div>
                        <label class="block text-sm font-medium mb-1">Username (optional)</label>
                        <input type="text" id="smtp-user" class="w-full border rounded px-3 py-2">
                    </div>
                    <div>
                        <label class="block text-sm font-medium mb-1">Password (optional)</label>
                        <input type="password" id="smtp-password" class="w-full border rounded px-3 py-2">
                    </div>
                </div>
                <div class="mt-3">
                    <label class="flex items-center">
                        <input type="checkbox" id="smtp-tls" checked class="mr-2">
                        <span class="text-sm">Use TLS (STARTTLS)</span>
                    </label>
                </div>
            </div>

            <!-- From Address -->
            <div class="border-t pt-4 mt-4">
                <h3 class="font-medium mb-3">From Address</h3>
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-sm font-medium mb-1">Email</label>
                        <input type="email" id="from-address" required class="w-full border rounded px-3 py-2" placeholder="alerts@example.com">
                    </div>
                    <div>
                        <label class="block text-sm font-medium mb-1">Name (optional)</label>
                        <input type="text" id="from-name" class="w-full border rounded px-3 py-2" placeholder="OpsConductor Alerts">
                    </div>
                </div>
            </div>

            <!-- Recipients -->
            <div class="border-t pt-4 mt-4">
                <h3 class="font-medium mb-3">Recipients</h3>
                <div class="mb-3">
                    <label class="block text-sm font-medium mb-1">To (comma-separated)</label>
                    <input type="text" id="recipients-to" required class="w-full border rounded px-3 py-2" placeholder="admin@example.com, oncall@example.com">
                </div>
                <div class="mb-3">
                    <label class="block text-sm font-medium mb-1">CC (optional)</label>
                    <input type="text" id="recipients-cc" class="w-full border rounded px-3 py-2">
                </div>
                <div class="mb-3">
                    <label class="block text-sm font-medium mb-1">BCC (optional)</label>
                    <input type="text" id="recipients-bcc" class="w-full border rounded px-3 py-2">
                </div>
            </div>

            <!-- Template -->
            <div class="border-t pt-4 mt-4">
                <h3 class="font-medium mb-3">Email Template</h3>
                <div class="mb-3">
                    <label class="block text-sm font-medium mb-1">Subject Template</label>
                    <input type="text" id="subject-template" class="w-full border rounded px-3 py-2" placeholder="[{severity}] {alert_type}: {device_id}">
                    <p class="text-xs text-gray-500 mt-1">Variables: {severity}, {alert_type}, {device_id}, {message}</p>
                </div>
                <div class="mb-3">
                    <label class="block text-sm font-medium mb-1">Format</label>
                    <select id="email-format" class="w-full border rounded px-3 py-2">
                        <option value="html">HTML</option>
                        <option value="text">Plain Text</option>
                    </select>
                </div>
            </div>

            <!-- Enabled -->
            <div class="border-t pt-4 mt-4">
                <label class="flex items-center">
                    <input type="checkbox" id="email-enabled" checked class="mr-2">
                    <span class="text-sm">Enabled</span>
                </label>
            </div>

            <!-- Error -->
            <div id="form-error" class="mt-4 p-3 bg-red-100 text-red-700 rounded hidden"></div>

            <!-- Buttons -->
            <div class="flex justify-end gap-2 mt-6">
                <button type="button" id="btn-cancel" class="px-4 py-2 border rounded">Cancel</button>
                <button type="submit" class="px-4 py-2 bg-blue-600 text-white rounded">Save</button>
            </div>
        </form>
    </div>
</div>

<script src="/static/js/email_integrations.js"></script>
{% endblock %}
```

### 7.2 Create JavaScript

Create `services/ui_iot/static/js/email_integrations.js`:

```javascript
document.addEventListener('DOMContentLoaded', function() {
    loadIntegrations();

    document.getElementById('btn-add-email').addEventListener('click', () => openModal());
    document.getElementById('btn-cancel').addEventListener('click', closeModal);
    document.getElementById('email-form').addEventListener('submit', saveIntegration);
});

async function loadIntegrations() {
    const list = document.getElementById('email-list');
    try {
        const response = await fetch('/customer/integrations/email', {credentials: 'include'});
        const integrations = await response.json();

        if (integrations.length === 0) {
            list.innerHTML = '<div class="p-8 text-center text-gray-500">No email integrations configured.</div>';
            return;
        }

        list.innerHTML = `<table class="w-full">
            <thead class="bg-gray-50"><tr>
                <th class="px-4 py-3 text-left">Name</th>
                <th class="px-4 py-3 text-left">SMTP Server</th>
                <th class="px-4 py-3 text-left">Recipients</th>
                <th class="px-4 py-3 text-left">Status</th>
                <th class="px-4 py-3 text-right">Actions</th>
            </tr></thead>
            <tbody class="divide-y">${integrations.map(i => `<tr>
                <td class="px-4 py-3">${escapeHtml(i.name)}</td>
                <td class="px-4 py-3 font-mono text-sm">${escapeHtml(i.smtp_host)}:${i.smtp_port}</td>
                <td class="px-4 py-3">${i.recipient_count} recipient${i.recipient_count !== 1 ? 's' : ''}</td>
                <td class="px-4 py-3"><span class="px-2 py-1 rounded text-xs ${i.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'}">${i.enabled ? 'Enabled' : 'Disabled'}</span></td>
                <td class="px-4 py-3 text-right">
                    <button onclick="testIntegration('${i.id}')" class="text-blue-600 hover:text-blue-800 mr-2">Test</button>
                    <button onclick="deleteIntegration('${i.id}')" class="text-red-600 hover:text-red-800">Delete</button>
                </td>
            </tr>`).join('')}</tbody>
        </table>`;
    } catch (e) {
        list.innerHTML = '<div class="p-4 text-red-600">Error loading integrations.</div>';
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function parseEmailList(str) {
    if (!str) return [];
    return str.split(',').map(e => e.trim()).filter(e => e);
}

function openModal() {
    document.getElementById('email-form').reset();
    document.getElementById('integration-id').value = '';
    document.getElementById('modal-title').textContent = 'Add Email Integration';
    document.getElementById('form-error').classList.add('hidden');
    document.getElementById('email-modal').classList.remove('hidden');
    document.getElementById('email-modal').classList.add('flex');
}

function closeModal() {
    document.getElementById('email-modal').classList.add('hidden');
    document.getElementById('email-modal').classList.remove('flex');
}

async function saveIntegration(e) {
    e.preventDefault();

    const data = {
        name: document.getElementById('email-name').value,
        smtp_config: {
            smtp_host: document.getElementById('smtp-host').value,
            smtp_port: parseInt(document.getElementById('smtp-port').value) || 587,
            smtp_user: document.getElementById('smtp-user').value || null,
            smtp_password: document.getElementById('smtp-password').value || null,
            smtp_tls: document.getElementById('smtp-tls').checked,
            from_address: document.getElementById('from-address').value,
            from_name: document.getElementById('from-name').value || 'OpsConductor Alerts',
        },
        recipients: {
            to: parseEmailList(document.getElementById('recipients-to').value),
            cc: parseEmailList(document.getElementById('recipients-cc').value),
            bcc: parseEmailList(document.getElementById('recipients-bcc').value),
        },
        template: {
            subject_template: document.getElementById('subject-template').value || '[{severity}] {alert_type}: {device_id}',
            format: document.getElementById('email-format').value,
        },
        enabled: document.getElementById('email-enabled').checked,
    };

    try {
        const response = await fetch('/customer/integrations/email', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            credentials: 'include',
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to create integration');
        }
        closeModal();
        loadIntegrations();
    } catch (e) {
        document.getElementById('form-error').textContent = e.message;
        document.getElementById('form-error').classList.remove('hidden');
    }
}

async function testIntegration(id) {
    try {
        const response = await fetch(`/customer/integrations/email/${id}/test`, {
            method: 'POST',
            credentials: 'include'
        });
        const result = await response.json();
        if (result.success) {
            alert(`Test email sent successfully to ${result.recipients_count} recipient(s)!`);
        } else {
            alert(`Test failed: ${result.error}`);
        }
    } catch (e) {
        alert('Error: ' + e.message);
    }
}

async function deleteIntegration(id) {
    if (!confirm('Delete this email integration?')) return;
    try {
        await fetch(`/customer/integrations/email/${id}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        loadIntegrations();
    } catch (e) {
        alert('Error: ' + e.message);
    }
}
```

### 7.3 Add page route

Add to `services/ui_iot/routes/customer.py`:

```python
@router.get("/email-integrations", include_in_schema=False)
async def email_integrations_page(request: Request):
    """Render email integrations page."""
    tenant_id = get_tenant_id()
    return templates.TemplateResponse(
        "customer/email_integrations.html",
        {"request": request, "tenant_id": tenant_id, "user": getattr(request.state, "user", None)},
    )
```

### 7.4 Add navigation link

Update `services/ui_iot/templates/customer/base.html` navigation to include:

```html
<a href="/customer/email-integrations" class="nav-link">Email Integrations</a>
```

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `services/ui_iot/templates/customer/email_integrations.html` |
| CREATE | `services/ui_iot/static/js/email_integrations.js` |
| MODIFY | `services/ui_iot/routes/customer.py` |
| MODIFY | `services/ui_iot/templates/customer/base.html` |

---

## Acceptance Criteria

- [ ] Email integrations page renders at /customer/email-integrations
- [ ] Can create email integration with SMTP settings
- [ ] Can configure recipients (to, cc, bcc)
- [ ] Can test integration from UI
- [ ] Can delete integration from UI
- [ ] Navigation link present in sidebar

**Test**:
```bash
# Start services and visit
open http://localhost:8080/customer/email-integrations
```

---

## Commit

```
Add email integrations UI

- Email integrations page template
- JavaScript for CRUD operations
- SMTP settings form
- Recipients configuration
- Template settings
- Page route and navigation link

Part of Phase 6: Email Delivery
```
