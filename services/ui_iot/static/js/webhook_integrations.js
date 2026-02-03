document.addEventListener('DOMContentLoaded', function() {
    loadIntegrations();
    document.getElementById('btn-add-webhook').addEventListener('click', openModal);
    document.getElementById('btn-cancel').addEventListener('click', closeModal);
    document.getElementById('webhook-form').addEventListener('submit', saveIntegration);
});

async function loadIntegrations() {
    const list = document.getElementById('webhook-list');
    try {
        const response = await fetch('/customer/integrations', {credentials: 'include'});
        if (!response.ok) {
            throw new Error('Failed to load integrations');
        }
        const data = await response.json();
        const integrations = Array.isArray(data.integrations) ? data.integrations : [];

        if (integrations.length === 0) {
            list.innerHTML = '<div>No webhook integrations configured.</div>';
            return;
        }

        list.innerHTML = `<table class="w-full">
            <thead><tr>
                <th style="text-align:left;">Name</th>
                <th style="text-align:left;">URL</th>
                <th style="text-align:left;">Status</th>
                <th style="text-align:right;">Actions</th>
            </tr></thead>
            <tbody>${integrations.map(i => `<tr>
                <td>${i.name}</td>
                <td style="font-family: monospace;">${i.url || '-'}</td>
                <td>${i.enabled ? 'Enabled' : 'Disabled'}</td>
                <td style="text-align:right;">
                    <button onclick="testIntegration('${i.integration_id}')">Test</button>
                    <button onclick="deleteIntegration('${i.integration_id}')">Delete</button>
                </td>
            </tr>`).join('')}</tbody>
        </table>`;
    } catch (e) {
        list.innerHTML = '<div style="color:#f88;">Error loading integrations.</div>';
    }
}

function openModal() {
    document.getElementById('webhook-form').reset();
    document.getElementById('integration-id').value = '';
    document.getElementById('modal-title').textContent = 'Add Webhook Integration';
    const errorBox = document.getElementById('form-error');
    errorBox.textContent = '';
    errorBox.classList.add('hidden');
    const modal = document.getElementById('webhook-modal');
    modal.classList.remove('hidden');
    modal.style.display = 'flex';
}

function closeModal() {
    const modal = document.getElementById('webhook-modal');
    modal.classList.add('hidden');
    modal.style.display = 'none';
}

async function saveIntegration(e) {
    e.preventDefault();
    const data = {
        name: document.getElementById('webhook-name').value,
        webhook_url: document.getElementById('webhook-url').value,
        enabled: document.getElementById('webhook-enabled').checked,
    };

    try {
        const response = await fetch('/customer/integrations', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            credentials: 'include',
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to save integration');
        }
        closeModal();
        loadIntegrations();
    } catch (e) {
        const errorBox = document.getElementById('form-error');
        errorBox.textContent = e.message;
        errorBox.classList.remove('hidden');
    }
}

async function testIntegration(id) {
    try {
        const response = await fetch(`/customer/integrations/${id}/test`, {method: 'POST', credentials: 'include'});
        const result = await response.json();
        alert(result.success ? 'Test delivery sent successfully!' : `Test failed: ${result.error}`);
    } catch (e) {
        alert('Error: ' + e.message);
    }
}

async function deleteIntegration(id) {
    if (!confirm('Delete this integration?')) return;
    try {
        await fetch(`/customer/integrations/${id}`, {method: 'DELETE', credentials: 'include'});
        loadIntegrations();
    } catch (e) {
        alert('Error: ' + e.message);
    }
}
