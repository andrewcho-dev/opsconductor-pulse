# Task 007: SNMP UI

> **CURSOR: EXECUTE THIS TASK**
>
> This is an implementation task. Read the instructions below and implement them.
> Modify the files listed in "Files to Create/Modify" section.
> Follow the acceptance criteria to verify your work.
> Commit with the message in the "Commit" section when done.

---

## Context

Customers need UI to manage their SNMP integrations. This includes listing, creating, editing, and testing SNMP destinations. The UI should follow the same patterns as the webhook integration UI.

**Read first**:
- `services/ui_iot/templates/customer/` (existing customer templates)
- `services/ui_iot/static/js/` (existing JavaScript)
- Existing webhook integration UI

**Depends on**: Tasks 003, 006

## Task

### 7.1 Create SNMP integrations page template

Create `services/ui_iot/templates/customer/snmp_integrations.html`:

```html
{% extends "customer/base.html" %}

{% block title %}SNMP Integrations - OpsConductor Pulse{% endblock %}

{% block content %}
<div class="container mx-auto px-4 py-8">
    <div class="flex justify-between items-center mb-6">
        <h1 class="text-2xl font-bold">SNMP Integrations</h1>
        <button id="btn-add-snmp" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded">
            Add SNMP Integration
        </button>
    </div>

    <!-- Integration List -->
    <div id="snmp-list" class="bg-white rounded-lg shadow">
        <div class="p-4 text-gray-500 text-center">Loading...</div>
    </div>
</div>

<!-- Add/Edit Modal -->
<div id="snmp-modal" class="fixed inset-0 bg-black bg-opacity-50 hidden items-center justify-center z-50">
    <div class="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        <div class="p-6">
            <h2 id="modal-title" class="text-xl font-bold mb-4">Add SNMP Integration</h2>

            <form id="snmp-form">
                <input type="hidden" id="integration-id" value="">

                <div class="mb-4">
                    <label class="block text-sm font-medium mb-1">Name</label>
                    <input type="text" id="snmp-name" required
                        class="w-full border rounded px-3 py-2"
                        placeholder="My SNMP Receiver">
                </div>

                <div class="mb-4">
                    <label class="block text-sm font-medium mb-1">Host</label>
                    <input type="text" id="snmp-host" required
                        class="w-full border rounded px-3 py-2"
                        placeholder="trap-receiver.example.com">
                    <p class="text-xs text-gray-500 mt-1">Hostname or IP address of your SNMP trap receiver</p>
                </div>

                <div class="mb-4">
                    <label class="block text-sm font-medium mb-1">Port</label>
                    <input type="number" id="snmp-port" value="162" min="1" max="65535"
                        class="w-full border rounded px-3 py-2">
                </div>

                <div class="mb-4">
                    <label class="block text-sm font-medium mb-1">SNMP Version</label>
                    <select id="snmp-version" class="w-full border rounded px-3 py-2">
                        <option value="2c">SNMPv2c (Community String)</option>
                        <option value="3">SNMPv3 (Authentication)</option>
                    </select>
                </div>

                <!-- SNMPv2c Config -->
                <div id="v2c-config">
                    <div class="mb-4">
                        <label class="block text-sm font-medium mb-1">Community String</label>
                        <input type="text" id="snmp-community"
                            class="w-full border rounded px-3 py-2"
                            placeholder="public">
                    </div>
                </div>

                <!-- SNMPv3 Config -->
                <div id="v3-config" class="hidden">
                    <div class="mb-4">
                        <label class="block text-sm font-medium mb-1">Username</label>
                        <input type="text" id="snmp-username"
                            class="w-full border rounded px-3 py-2">
                    </div>
                    <div class="mb-4">
                        <label class="block text-sm font-medium mb-1">Auth Protocol</label>
                        <select id="snmp-auth-protocol" class="w-full border rounded px-3 py-2">
                            <option value="SHA">SHA</option>
                            <option value="MD5">MD5</option>
                        </select>
                    </div>
                    <div class="mb-4">
                        <label class="block text-sm font-medium mb-1">Auth Password</label>
                        <input type="password" id="snmp-auth-password"
                            class="w-full border rounded px-3 py-2"
                            placeholder="Min 8 characters">
                    </div>
                    <div class="mb-4">
                        <label class="block text-sm font-medium mb-1">Privacy Protocol</label>
                        <select id="snmp-priv-protocol" class="w-full border rounded px-3 py-2">
                            <option value="AES">AES</option>
                            <option value="DES">DES</option>
                            <option value="">None</option>
                        </select>
                    </div>
                    <div class="mb-4" id="priv-password-group">
                        <label class="block text-sm font-medium mb-1">Privacy Password</label>
                        <input type="password" id="snmp-priv-password"
                            class="w-full border rounded px-3 py-2"
                            placeholder="Min 8 characters">
                    </div>
                </div>

                <div class="mb-4">
                    <label class="block text-sm font-medium mb-1">OID Prefix (Optional)</label>
                    <input type="text" id="snmp-oid-prefix"
                        class="w-full border rounded px-3 py-2"
                        placeholder="1.3.6.1.4.1.99999"
                        pattern="^[0-9.]+$">
                    <p class="text-xs text-gray-500 mt-1">Enterprise OID for trap varbinds</p>
                </div>

                <div class="mb-4">
                    <label class="flex items-center">
                        <input type="checkbox" id="snmp-enabled" checked class="mr-2">
                        <span class="text-sm">Enabled</span>
                    </label>
                </div>

                <div id="form-error" class="mb-4 p-3 bg-red-100 text-red-700 rounded hidden"></div>

                <div class="flex justify-end gap-2">
                    <button type="button" id="btn-cancel"
                        class="px-4 py-2 border rounded hover:bg-gray-100">
                        Cancel
                    </button>
                    <button type="submit"
                        class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                        Save
                    </button>
                </div>
            </form>
        </div>
    </div>
</div>

<!-- Test Result Modal -->
<div id="test-modal" class="fixed inset-0 bg-black bg-opacity-50 hidden items-center justify-center z-50">
    <div class="bg-white rounded-lg shadow-xl w-full max-w-md mx-4 p-6">
        <h2 class="text-xl font-bold mb-4">Test Result</h2>
        <div id="test-result"></div>
        <div class="mt-4 flex justify-end">
            <button id="btn-close-test" class="px-4 py-2 border rounded hover:bg-gray-100">
                Close
            </button>
        </div>
    </div>
</div>

<script src="/static/js/snmp_integrations.js"></script>
{% endblock %}
```

### 7.2 Create JavaScript for SNMP management

Create `services/ui_iot/static/js/snmp_integrations.js`:

```javascript
/**
 * SNMP Integrations Management
 */

document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('snmp-modal');
    const testModal = document.getElementById('test-modal');
    const form = document.getElementById('snmp-form');
    const versionSelect = document.getElementById('snmp-version');

    // Load integrations on page load
    loadIntegrations();

    // Show/hide v2c/v3 config based on version
    versionSelect.addEventListener('change', function() {
        const v2cConfig = document.getElementById('v2c-config');
        const v3Config = document.getElementById('v3-config');

        if (this.value === '2c') {
            v2cConfig.classList.remove('hidden');
            v3Config.classList.add('hidden');
        } else {
            v2cConfig.classList.add('hidden');
            v3Config.classList.remove('hidden');
        }
    });

    // Privacy password visibility
    document.getElementById('snmp-priv-protocol').addEventListener('change', function() {
        const privGroup = document.getElementById('priv-password-group');
        if (this.value) {
            privGroup.classList.remove('hidden');
        } else {
            privGroup.classList.add('hidden');
        }
    });

    // Add button
    document.getElementById('btn-add-snmp').addEventListener('click', function() {
        openModal();
    });

    // Cancel button
    document.getElementById('btn-cancel').addEventListener('click', function() {
        closeModal();
    });

    // Close test modal
    document.getElementById('btn-close-test').addEventListener('click', function() {
        testModal.classList.add('hidden');
        testModal.classList.remove('flex');
    });

    // Form submit
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        await saveIntegration();
    });

    // Click outside modal to close
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            closeModal();
        }
    });
});

async function loadIntegrations() {
    const list = document.getElementById('snmp-list');

    try {
        const response = await fetch('/customer/integrations/snmp', {
            credentials: 'include',
        });

        if (!response.ok) {
            throw new Error('Failed to load integrations');
        }

        const integrations = await response.json();

        if (integrations.length === 0) {
            list.innerHTML = `
                <div class="p-8 text-center text-gray-500">
                    <p class="mb-4">No SNMP integrations configured.</p>
                    <p>Click "Add SNMP Integration" to create one.</p>
                </div>
            `;
            return;
        }

        list.innerHTML = `
            <table class="w-full">
                <thead class="bg-gray-50">
                    <tr>
                        <th class="px-4 py-3 text-left text-sm font-medium">Name</th>
                        <th class="px-4 py-3 text-left text-sm font-medium">Destination</th>
                        <th class="px-4 py-3 text-left text-sm font-medium">Version</th>
                        <th class="px-4 py-3 text-left text-sm font-medium">Status</th>
                        <th class="px-4 py-3 text-right text-sm font-medium">Actions</th>
                    </tr>
                </thead>
                <tbody class="divide-y">
                    ${integrations.map(i => `
                        <tr>
                            <td class="px-4 py-3">${escapeHtml(i.name)}</td>
                            <td class="px-4 py-3 font-mono text-sm">${escapeHtml(i.snmp_host)}:${i.snmp_port}</td>
                            <td class="px-4 py-3">SNMPv${i.snmp_version}</td>
                            <td class="px-4 py-3">
                                <span class="px-2 py-1 rounded text-xs ${i.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}">
                                    ${i.enabled ? 'Enabled' : 'Disabled'}
                                </span>
                            </td>
                            <td class="px-4 py-3 text-right">
                                <button onclick="testIntegration('${i.id}')"
                                    class="text-blue-600 hover:underline mr-2">Test</button>
                                <button onclick="editIntegration('${i.id}')"
                                    class="text-blue-600 hover:underline mr-2">Edit</button>
                                <button onclick="deleteIntegration('${i.id}')"
                                    class="text-red-600 hover:underline">Delete</button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    } catch (error) {
        console.error('Error loading integrations:', error);
        list.innerHTML = `
            <div class="p-4 text-red-600">
                Error loading integrations. Please refresh the page.
            </div>
        `;
    }
}

function openModal(integration = null) {
    const modal = document.getElementById('snmp-modal');
    const title = document.getElementById('modal-title');
    const form = document.getElementById('snmp-form');

    form.reset();
    document.getElementById('form-error').classList.add('hidden');

    if (integration) {
        title.textContent = 'Edit SNMP Integration';
        document.getElementById('integration-id').value = integration.id;
        document.getElementById('snmp-name').value = integration.name;
        document.getElementById('snmp-host').value = integration.snmp_host;
        document.getElementById('snmp-port').value = integration.snmp_port;
        document.getElementById('snmp-version').value = integration.snmp_version;
        document.getElementById('snmp-oid-prefix').value = integration.snmp_oid_prefix || '';
        document.getElementById('snmp-enabled').checked = integration.enabled;

        // Trigger version change to show correct config
        document.getElementById('snmp-version').dispatchEvent(new Event('change'));
    } else {
        title.textContent = 'Add SNMP Integration';
        document.getElementById('integration-id').value = '';
        document.getElementById('snmp-port').value = '162';
    }

    modal.classList.remove('hidden');
    modal.classList.add('flex');
}

function closeModal() {
    const modal = document.getElementById('snmp-modal');
    modal.classList.add('hidden');
    modal.classList.remove('flex');
}

async function saveIntegration() {
    const errorDiv = document.getElementById('form-error');
    errorDiv.classList.add('hidden');

    const integrationId = document.getElementById('integration-id').value;
    const version = document.getElementById('snmp-version').value;

    // Build SNMP config based on version
    let snmpConfig;
    if (version === '2c') {
        snmpConfig = {
            version: '2c',
            community: document.getElementById('snmp-community').value || 'public',
        };
    } else {
        snmpConfig = {
            version: '3',
            username: document.getElementById('snmp-username').value,
            auth_protocol: document.getElementById('snmp-auth-protocol').value,
            auth_password: document.getElementById('snmp-auth-password').value,
        };
        const privProtocol = document.getElementById('snmp-priv-protocol').value;
        if (privProtocol) {
            snmpConfig.priv_protocol = privProtocol;
            snmpConfig.priv_password = document.getElementById('snmp-priv-password').value;
        }
    }

    const data = {
        name: document.getElementById('snmp-name').value,
        snmp_host: document.getElementById('snmp-host').value,
        snmp_port: parseInt(document.getElementById('snmp-port').value, 10),
        snmp_config: snmpConfig,
        snmp_oid_prefix: document.getElementById('snmp-oid-prefix').value || '1.3.6.1.4.1.99999',
        enabled: document.getElementById('snmp-enabled').checked,
    };

    try {
        const url = integrationId
            ? `/customer/integrations/snmp/${integrationId}`
            : '/customer/integrations/snmp';
        const method = integrationId ? 'PATCH' : 'POST';

        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify(data),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save integration');
        }

        closeModal();
        loadIntegrations();
    } catch (error) {
        errorDiv.textContent = error.message;
        errorDiv.classList.remove('hidden');
    }
}

async function editIntegration(id) {
    try {
        const response = await fetch(`/customer/integrations/snmp/${id}`, {
            credentials: 'include',
        });

        if (!response.ok) {
            throw new Error('Failed to load integration');
        }

        const integration = await response.json();
        openModal(integration);
    } catch (error) {
        alert('Error loading integration: ' + error.message);
    }
}

async function deleteIntegration(id) {
    if (!confirm('Are you sure you want to delete this SNMP integration?')) {
        return;
    }

    try {
        const response = await fetch(`/customer/integrations/snmp/${id}`, {
            method: 'DELETE',
            credentials: 'include',
        });

        if (!response.ok) {
            throw new Error('Failed to delete integration');
        }

        loadIntegrations();
    } catch (error) {
        alert('Error deleting integration: ' + error.message);
    }
}

async function testIntegration(id) {
    const testModal = document.getElementById('test-modal');
    const resultDiv = document.getElementById('test-result');

    resultDiv.innerHTML = '<p class="text-gray-500">Sending test trap...</p>';
    testModal.classList.remove('hidden');
    testModal.classList.add('flex');

    try {
        const response = await fetch(`/customer/integrations/snmp/${id}/test`, {
            method: 'POST',
            credentials: 'include',
        });

        const result = await response.json();

        if (result.success) {
            resultDiv.innerHTML = `
                <div class="p-4 bg-green-100 text-green-800 rounded">
                    <p class="font-bold">Success!</p>
                    <p>Test trap sent to ${escapeHtml(result.destination)}</p>
                    <p class="text-sm mt-2">Duration: ${result.duration_ms?.toFixed(0) || '-'}ms</p>
                </div>
            `;
        } else {
            resultDiv.innerHTML = `
                <div class="p-4 bg-red-100 text-red-800 rounded">
                    <p class="font-bold">Failed</p>
                    <p>${escapeHtml(result.error || 'Unknown error')}</p>
                </div>
            `;
        }
    } catch (error) {
        resultDiv.innerHTML = `
            <div class="p-4 bg-red-100 text-red-800 rounded">
                <p class="font-bold">Error</p>
                <p>${escapeHtml(error.message)}</p>
            </div>
        `;
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
```

### 7.3 Add route for SNMP page

Add to `services/ui_iot/routes/customer.py`:

```python
@router.get("/snmp-integrations", include_in_schema=False)
async def snmp_integrations_page(
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
):
    """Render SNMP integrations management page."""
    return templates.TemplateResponse(
        "customer/snmp_integrations.html",
        {"request": request, "tenant_id": tenant_id},
    )
```

### 7.4 Add navigation link

Update the customer dashboard navigation to include SNMP integrations:

In `services/ui_iot/templates/customer/base.html`, add to navigation:

```html
<nav>
    <!-- ... existing links ... -->
    <a href="/customer/integrations" class="nav-link">Webhook Integrations</a>
    <a href="/customer/snmp-integrations" class="nav-link">SNMP Integrations</a>
    <!-- ... -->
</nav>
```

### 7.5 Update integrations list page (optional)

If there's a combined integrations page, update it to show integration type:

```html
<td class="px-4 py-3">
    <span class="px-2 py-1 rounded text-xs ${i.type === 'snmp' ? 'bg-purple-100 text-purple-800' : 'bg-blue-100 text-blue-800'}">
        ${i.type.toUpperCase()}
    </span>
</td>
```

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `services/ui_iot/templates/customer/snmp_integrations.html` |
| CREATE | `services/ui_iot/static/js/snmp_integrations.js` |
| MODIFY | `services/ui_iot/routes/customer.py` (add page route) |
| MODIFY | `services/ui_iot/templates/customer/base.html` (add nav link) |

## Acceptance Criteria

- [ ] SNMP integrations page renders
- [ ] Can create SNMPv2c integration via UI
- [ ] Can create SNMPv3 integration via UI
- [ ] Can edit existing integration
- [ ] Can delete integration
- [ ] Can test integration
- [ ] Version toggle shows correct fields
- [ ] Error messages displayed
- [ ] Navigation link added

**Test**:
```bash
# Start services
docker compose up -d

# Open browser
open http://localhost:8080/customer/snmp-integrations

# Test flows:
# 1. Create SNMPv2c integration
# 2. Create SNMPv3 integration
# 3. Edit integration
# 4. Test integration
# 5. Delete integration
```

## Commit

```
Add SNMP integrations UI

- SNMP integrations management page
- Create/edit modal with v2c/v3 toggle
- Test delivery button
- JavaScript for CRUD operations
- Navigation link in customer dashboard

Part of Phase 4: SNMP and Alternative Outputs
```
