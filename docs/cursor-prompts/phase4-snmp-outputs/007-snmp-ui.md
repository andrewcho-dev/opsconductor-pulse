# Task 007: SNMP UI

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Create/Modify".
> Verify your work against the acceptance criteria.
> Commit with the exact message in the "Commit" section when done.

---

## Context

Customers need UI to manage their SNMP integrations. This includes listing, creating, editing, and testing SNMP destinations.

**Read first**:
- `services/ui_iot/templates/customer/` (existing templates)
- `services/ui_iot/static/js/` (existing JavaScript)

**Depends on**: Tasks 003, 006

---

## Task

### 7.1 Create SNMP integrations page template

Create `services/ui_iot/templates/customer/snmp_integrations.html`:

```html
{% extends "customer/base.html" %}

{% block title %}SNMP Integrations{% endblock %}

{% block content %}
<div class="container mx-auto px-4 py-8">
    <div class="flex justify-between items-center mb-6">
        <h1 class="text-2xl font-bold">SNMP Integrations</h1>
        <button id="btn-add-snmp" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded">
            Add SNMP Integration
        </button>
    </div>

    <div id="snmp-list" class="bg-white rounded-lg shadow">
        <div class="p-4 text-gray-500 text-center">Loading...</div>
    </div>
</div>

<div id="snmp-modal" class="fixed inset-0 bg-black bg-opacity-50 hidden items-center justify-center z-50">
    <div class="bg-white rounded-lg shadow-xl w-full max-w-md mx-4 p-6">
        <h2 id="modal-title" class="text-xl font-bold mb-4">Add SNMP Integration</h2>
        <form id="snmp-form">
            <input type="hidden" id="integration-id" value="">
            <div class="mb-4">
                <label class="block text-sm font-medium mb-1">Name</label>
                <input type="text" id="snmp-name" required class="w-full border rounded px-3 py-2">
            </div>
            <div class="mb-4">
                <label class="block text-sm font-medium mb-1">Host</label>
                <input type="text" id="snmp-host" required class="w-full border rounded px-3 py-2">
            </div>
            <div class="mb-4">
                <label class="block text-sm font-medium mb-1">Port</label>
                <input type="number" id="snmp-port" value="162" class="w-full border rounded px-3 py-2">
            </div>
            <div class="mb-4">
                <label class="block text-sm font-medium mb-1">SNMP Version</label>
                <select id="snmp-version" class="w-full border rounded px-3 py-2">
                    <option value="2c">SNMPv2c</option>
                    <option value="3">SNMPv3</option>
                </select>
            </div>
            <div id="v2c-config">
                <div class="mb-4">
                    <label class="block text-sm font-medium mb-1">Community String</label>
                    <input type="text" id="snmp-community" class="w-full border rounded px-3 py-2" value="public">
                </div>
            </div>
            <div id="v3-config" class="hidden">
                <div class="mb-4">
                    <label class="block text-sm font-medium mb-1">Username</label>
                    <input type="text" id="snmp-username" class="w-full border rounded px-3 py-2">
                </div>
                <div class="mb-4">
                    <label class="block text-sm font-medium mb-1">Auth Password</label>
                    <input type="password" id="snmp-auth-password" class="w-full border rounded px-3 py-2">
                </div>
            </div>
            <div class="mb-4">
                <label class="flex items-center">
                    <input type="checkbox" id="snmp-enabled" checked class="mr-2">
                    <span class="text-sm">Enabled</span>
                </label>
            </div>
            <div id="form-error" class="mb-4 p-3 bg-red-100 text-red-700 rounded hidden"></div>
            <div class="flex justify-end gap-2">
                <button type="button" id="btn-cancel" class="px-4 py-2 border rounded">Cancel</button>
                <button type="submit" class="px-4 py-2 bg-blue-600 text-white rounded">Save</button>
            </div>
        </form>
    </div>
</div>

<script src="/static/js/snmp_integrations.js"></script>
{% endblock %}
```

### 7.2 Create JavaScript

Create `services/ui_iot/static/js/snmp_integrations.js`:

```javascript
document.addEventListener('DOMContentLoaded', function() {
    loadIntegrations();

    document.getElementById('snmp-version').addEventListener('change', function() {
        document.getElementById('v2c-config').classList.toggle('hidden', this.value !== '2c');
        document.getElementById('v3-config').classList.toggle('hidden', this.value !== '3');
    });

    document.getElementById('btn-add-snmp').addEventListener('click', () => openModal());
    document.getElementById('btn-cancel').addEventListener('click', closeModal);
    document.getElementById('snmp-form').addEventListener('submit', saveIntegration);
});

async function loadIntegrations() {
    const list = document.getElementById('snmp-list');
    try {
        const response = await fetch('/customer/integrations/snmp', {credentials: 'include'});
        const integrations = await response.json();

        if (integrations.length === 0) {
            list.innerHTML = '<div class="p-8 text-center text-gray-500">No SNMP integrations configured.</div>';
            return;
        }

        list.innerHTML = `<table class="w-full">
            <thead class="bg-gray-50"><tr>
                <th class="px-4 py-3 text-left">Name</th>
                <th class="px-4 py-3 text-left">Destination</th>
                <th class="px-4 py-3 text-left">Status</th>
                <th class="px-4 py-3 text-right">Actions</th>
            </tr></thead>
            <tbody class="divide-y">${integrations.map(i => `<tr>
                <td class="px-4 py-3">${i.name}</td>
                <td class="px-4 py-3 font-mono text-sm">${i.snmp_host}:${i.snmp_port}</td>
                <td class="px-4 py-3"><span class="px-2 py-1 rounded text-xs ${i.enabled ? 'bg-green-100' : 'bg-gray-100'}">${i.enabled ? 'Enabled' : 'Disabled'}</span></td>
                <td class="px-4 py-3 text-right">
                    <button onclick="testIntegration('${i.id}')" class="text-blue-600 mr-2">Test</button>
                    <button onclick="deleteIntegration('${i.id}')" class="text-red-600">Delete</button>
                </td>
            </tr>`).join('')}</tbody>
        </table>`;
    } catch (e) {
        list.innerHTML = '<div class="p-4 text-red-600">Error loading integrations.</div>';
    }
}

function openModal() {
    document.getElementById('snmp-form').reset();
    document.getElementById('integration-id').value = '';
    document.getElementById('modal-title').textContent = 'Add SNMP Integration';
    document.getElementById('snmp-modal').classList.remove('hidden');
    document.getElementById('snmp-modal').classList.add('flex');
}

function closeModal() {
    document.getElementById('snmp-modal').classList.add('hidden');
    document.getElementById('snmp-modal').classList.remove('flex');
}

async function saveIntegration(e) {
    e.preventDefault();
    const version = document.getElementById('snmp-version').value;
    const snmpConfig = version === '2c'
        ? {version: '2c', community: document.getElementById('snmp-community').value}
        : {version: '3', username: document.getElementById('snmp-username').value, auth_protocol: 'SHA', auth_password: document.getElementById('snmp-auth-password').value};

    const data = {
        name: document.getElementById('snmp-name').value,
        snmp_host: document.getElementById('snmp-host').value,
        snmp_port: parseInt(document.getElementById('snmp-port').value),
        snmp_config: snmpConfig,
        enabled: document.getElementById('snmp-enabled').checked,
    };

    try {
        const response = await fetch('/customer/integrations/snmp', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            credentials: 'include',
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail);
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
        const response = await fetch(`/customer/integrations/snmp/${id}/test`, {method: 'POST', credentials: 'include'});
        const result = await response.json();
        alert(result.success ? 'Test trap sent successfully!' : `Test failed: ${result.error}`);
    } catch (e) {
        alert('Error: ' + e.message);
    }
}

async function deleteIntegration(id) {
    if (!confirm('Delete this integration?')) return;
    try {
        await fetch(`/customer/integrations/snmp/${id}`, {method: 'DELETE', credentials: 'include'});
        loadIntegrations();
    } catch (e) {
        alert('Error: ' + e.message);
    }
}
```

### 7.3 Add page route

Add to `services/ui_iot/routes/customer.py`:

```python
@router.get("/snmp-integrations", include_in_schema=False)
async def snmp_integrations_page(
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
):
    """Render SNMP integrations page."""
    return templates.TemplateResponse(
        "customer/snmp_integrations.html",
        {"request": request, "tenant_id": tenant_id},
    )
```

### 7.4 Add navigation link

Update `services/ui_iot/templates/customer/base.html` navigation:

```html
<a href="/customer/snmp-integrations" class="nav-link">SNMP Integrations</a>
```

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `services/ui_iot/templates/customer/snmp_integrations.html` |
| CREATE | `services/ui_iot/static/js/snmp_integrations.js` |
| MODIFY | `services/ui_iot/routes/customer.py` |
| MODIFY | `services/ui_iot/templates/customer/base.html` |

---

## Acceptance Criteria

- [ ] SNMP integrations page renders
- [ ] Can create SNMPv2c integration
- [ ] Can create SNMPv3 integration
- [ ] Can test integration
- [ ] Can delete integration
- [ ] Navigation link present

**Test**:
```bash
# Start services and visit
open http://localhost:8080/customer/snmp-integrations
```

---

## Commit

```
Add SNMP integrations UI

- SNMP integrations page template
- JavaScript for CRUD operations
- Page route and navigation link

Part of Phase 4: SNMP and Alternative Outputs
```
