document.addEventListener('DOMContentLoaded', function() {
    loadRules();
    document.getElementById('btn-add-rule').addEventListener('click', function() {
        openModal();
    });
    document.getElementById('btn-cancel').addEventListener('click', closeModal);
    document.getElementById('rule-form').addEventListener('submit', saveRule);
});

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function operatorLabel(op) {
    if (op === 'GT') return '>';
    if (op === 'LT') return '<';
    if (op === 'GTE') return '>=';
    if (op === 'LTE') return '<=';
    return op;
}

function severityLabel(sev) {
    if (sev === 5) return 'Critical';
    if (sev === 3) return 'Warning';
    if (sev === 1) return 'Info';
    return String(sev);
}

async function loadRules() {
    const list = document.getElementById('rules-list');
    try {
        const response = await fetch('/customer/alert-rules?format=json', {credentials: 'include'});
        if (!response.ok) {
            throw new Error('Failed to load alert rules');
        }
        const data = await response.json();
        const rules = Array.isArray(data.rules) ? data.rules : [];

        if (rules.length === 0) {
            list.innerHTML = "<div>No alert rules defined. Click 'Add Rule' to create one.</div>";
            return;
        }

        list.innerHTML = `<table class="w-full">
            <thead><tr>
                <th style="text-align:left;">Name</th>
                <th style="text-align:left;">Metric</th>
                <th style="text-align:left;">Condition</th>
                <th style="text-align:left;">Severity</th>
                <th style="text-align:left;">Status</th>
                <th style="text-align:right;">Actions</th>
            </tr></thead>
            <tbody>${rules.map(rule => {
                const condition = `${rule.metric_name} ${operatorLabel(rule.operator)} ${rule.threshold}`;
                return `<tr>
                    <td>${escapeHtml(rule.name || '')}</td>
                    <td style="font-family: monospace;">${escapeHtml(rule.metric_name || '')}</td>
                    <td>${escapeHtml(condition)}</td>
                    <td>${escapeHtml(severityLabel(rule.severity))}</td>
                    <td>${rule.enabled ? 'Enabled' : 'Disabled'}</td>
                    <td style="text-align:right;">
                        <button onclick="editRule('${escapeHtml(rule.rule_id)}')">Edit</button>
                        <button onclick="deleteRule('${escapeHtml(rule.rule_id)}')">Delete</button>
                    </td>
                </tr>`;
            }).join('')}</tbody>
        </table>`;
    } catch (e) {
        list.innerHTML = '<div style="color:#f88;">Error loading alert rules.</div>';
    }
}

function openModal(rule) {
    document.getElementById('rule-form').reset();
    document.getElementById('rule-id').value = '';
    const errorBox = document.getElementById('form-error');
    errorBox.textContent = '';
    errorBox.classList.add('hidden');

    if (rule) {
        document.getElementById('modal-title').textContent = 'Edit Alert Rule';
        document.getElementById('rule-id').value = rule.rule_id || '';
        document.getElementById('rule-name').value = rule.name || '';
        document.getElementById('rule-metric').value = rule.metric_name || '';
        document.getElementById('rule-operator').value = rule.operator || 'LT';
        document.getElementById('rule-threshold').value = rule.threshold != null ? rule.threshold : '';
        document.getElementById('rule-severity').value = rule.severity != null ? String(rule.severity) : '3';
        document.getElementById('rule-description').value = rule.description || '';
        document.getElementById('rule-enabled').checked = rule.enabled !== false;
    } else {
        document.getElementById('modal-title').textContent = 'Add Alert Rule';
        document.getElementById('rule-enabled').checked = true;
        document.getElementById('rule-severity').value = '3';
    }

    const modal = document.getElementById('rule-modal');
    modal.classList.remove('hidden');
    modal.style.display = 'flex';
}

function closeModal() {
    const modal = document.getElementById('rule-modal');
    modal.classList.add('hidden');
    modal.style.display = 'none';
}

async function saveRule(e) {
    e.preventDefault();
    const ruleId = document.getElementById('rule-id').value;
    const name = document.getElementById('rule-name').value;
    const metricName = document.getElementById('rule-metric').value;
    const operator = document.getElementById('rule-operator').value;
    const thresholdValue = parseFloat(document.getElementById('rule-threshold').value);
    const severity = parseInt(document.getElementById('rule-severity').value, 10);
    const descriptionValue = document.getElementById('rule-description').value;
    const enabled = document.getElementById('rule-enabled').checked;

    if (Number.isNaN(thresholdValue)) {
        const errorBox = document.getElementById('form-error');
        errorBox.textContent = 'Threshold must be a number';
        errorBox.classList.remove('hidden');
        return;
    }

    const payload = {
        name: name,
        metric_name: metricName,
        operator: operator,
        threshold: thresholdValue,
        severity: severity,
        description: descriptionValue && descriptionValue.trim() ? descriptionValue.trim() : null,
        enabled: enabled,
    };

    try {
        const url = ruleId ? `/customer/alert-rules/${ruleId}` : '/customer/alert-rules';
        const response = await fetch(url, {
            method: ruleId ? 'PATCH' : 'POST',
            headers: {'Content-Type': 'application/json'},
            credentials: 'include',
            body: JSON.stringify(payload),
        });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to save alert rule');
        }
        closeModal();
        loadRules();
    } catch (e) {
        const errorBox = document.getElementById('form-error');
        errorBox.textContent = e.message;
        errorBox.classList.remove('hidden');
    }
}

async function deleteRule(ruleId) {
    if (!confirm('Delete this alert rule?')) return;
    try {
        await fetch(`/customer/alert-rules/${ruleId}`, {method: 'DELETE', credentials: 'include'});
        loadRules();
    } catch (e) {
        alert('Error: ' + e.message);
    }
}

async function editRule(ruleId) {
    try {
        const response = await fetch(`/customer/alert-rules/${ruleId}`, {credentials: 'include'});
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to fetch alert rule');
        }
        const rule = await response.json();
        openModal(rule);
    } catch (e) {
        alert('Error: ' + e.message);
    }
}
