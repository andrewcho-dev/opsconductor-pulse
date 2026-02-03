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
