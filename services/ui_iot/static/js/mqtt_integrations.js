document.addEventListener('DOMContentLoaded', function() {
    loadIntegrations();

    document.getElementById('btn-add-mqtt').addEventListener('click', () => openModal());
    document.getElementById('btn-cancel').addEventListener('click', closeModal);
    document.getElementById('mqtt-form').addEventListener('submit', saveIntegration);
});

async function loadIntegrations() {
    const list = document.getElementById('mqtt-list');
    try {
        const response = await fetch('/customer/integrations/mqtt', {credentials: 'include'});
        const integrations = await response.json();

        if (!Array.isArray(integrations) || integrations.length === 0) {
            list.innerHTML = '<div>No MQTT integrations configured.</div>';
            return;
        }

        list.innerHTML = `<table class="w-full">
            <thead><tr>
                <th style="text-align:left;">Name</th>
                <th style="text-align:left;">Topic</th>
                <th style="text-align:left;">QoS</th>
                <th style="text-align:left;">Status</th>
                <th style="text-align:right;">Actions</th>
            </tr></thead>
            <tbody>${integrations.map(i => `<tr>
                <td>${escapeHtml(i.name)}</td>
                <td style="font-family: monospace;">${escapeHtml(i.mqtt_topic)}</td>
                <td>${escapeHtml(String(i.mqtt_qos))}</td>
                <td>${i.enabled ? 'Enabled' : 'Disabled'}</td>
                <td style="text-align:right;">
                    <button onclick="testIntegration('${escapeHtml(i.id)}')">Test</button>
                    <button onclick="deleteIntegration('${escapeHtml(i.id)}')">Delete</button>
                </td>
            </tr>`).join('')}</tbody>
        </table>`;
    } catch (e) {
        list.innerHTML = '<div style="color:#f88;">Error loading integrations.</div>';
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function openModal() {
    document.getElementById('mqtt-form').reset();
    document.getElementById('modal-title').textContent = 'Add MQTT Integration';
    document.getElementById('form-error').classList.add('hidden');
    document.getElementById('mqtt-modal').classList.remove('hidden');
    document.getElementById('mqtt-modal').style.display = 'flex';
}

function closeModal() {
    document.getElementById('mqtt-modal').classList.add('hidden');
    document.getElementById('mqtt-modal').style.display = 'none';
}

async function saveIntegration(e) {
    e.preventDefault();

    const data = {
        name: document.getElementById('mqtt-name').value,
        mqtt_topic: document.getElementById('mqtt-topic').value,
        mqtt_qos: parseInt(document.getElementById('mqtt-qos').value, 10) || 1,
        mqtt_retain: document.getElementById('mqtt-retain').checked,
        enabled: document.getElementById('mqtt-enabled').checked,
    };

    try {
        const response = await fetch('/customer/integrations/mqtt', {
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
        const response = await fetch(`/customer/integrations/mqtt/${id}/test`, {
            method: 'POST',
            credentials: 'include'
        });
        const result = await response.json();
        if (result.success) {
            alert('Test MQTT publish succeeded!');
        } else {
            alert(`Test failed: ${result.error}`);
        }
    } catch (e) {
        alert('Error: ' + e.message);
    }
}

async function deleteIntegration(id) {
    if (!confirm('Delete this MQTT integration?')) return;
    try {
        await fetch(`/customer/integrations/mqtt/${id}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        loadIntegrations();
    } catch (e) {
        alert('Error: ' + e.message);
    }
}
