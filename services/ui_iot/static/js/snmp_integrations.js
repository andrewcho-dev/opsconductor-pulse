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

        if (!Array.isArray(integrations) || integrations.length === 0) {
            list.innerHTML = '<div>No SNMP integrations configured.</div>';
            return;
        }

        list.innerHTML = `<table class="w-full">
            <thead><tr>
                <th style="text-align:left;">Name</th>
                <th style="text-align:left;">Destination</th>
                <th style="text-align:left;">Status</th>
                <th style="text-align:right;">Actions</th>
            </tr></thead>
            <tbody>${integrations.map(i => `<tr>
                <td>${i.name}</td>
                <td style="font-family: monospace;">${i.snmp_host}:${i.snmp_port}</td>
                <td>${i.enabled ? 'Enabled' : 'Disabled'}</td>
                <td style="text-align:right;">
                    <button onclick="testIntegration('${i.id}')">Test</button>
                    <button onclick="deleteIntegration('${i.id}')">Delete</button>
                </td>
            </tr>`).join('')}</tbody>
        </table>`;
    } catch (e) {
        list.innerHTML = '<div style="color:#f88;">Error loading integrations.</div>';
    }
}

function openModal() {
    document.getElementById('snmp-form').reset();
    document.getElementById('integration-id').value = '';
    document.getElementById('modal-title').textContent = 'Add SNMP Integration';
    const modal = document.getElementById('snmp-modal');
    modal.classList.remove('hidden');
    modal.style.display = 'flex';
}

function closeModal() {
    const modal = document.getElementById('snmp-modal');
    modal.classList.add('hidden');
    modal.style.display = 'none';
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
        snmp_port: parseInt(document.getElementById('snmp-port').value, 10),
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
