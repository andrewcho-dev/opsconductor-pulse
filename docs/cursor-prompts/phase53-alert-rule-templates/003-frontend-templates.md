# Prompt 003 — Frontend: Load Template Selector

Read the alert rule create/edit form in `frontend/src/features/alerts/` — find where new alert rules are created.
Read `frontend/src/services/api/` for existing API client patterns.

## Add API Functions

In `frontend/src/services/api/alertRules.ts` (or existing alerts api file):

```typescript
export interface AlertRuleTemplate {
  template_id: string;
  device_type: string;
  name: string;
  metric_name: string;
  operator: 'GT' | 'LT' | 'GTE' | 'LTE';
  threshold: number;
  severity: number;
  duration_seconds: number;
  description: string;
}

export async function fetchAlertRuleTemplates(deviceType?: string): Promise<AlertRuleTemplate[]> {
  const params = deviceType ? `?device_type=${deviceType}` : '';
  const res = await apiFetch(`/customer/alert-rule-templates${params}`);
  return res.templates;
}

export async function applyAlertRuleTemplates(
  templateIds: string[],
  siteIds?: string[]
): Promise<{ created: Array<{id: number; name: string; template_id: string}>; skipped: string[] }> {
  return apiFetch('/customer/alert-rule-templates/apply', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ template_ids: templateIds, site_ids: siteIds }),
  });
}
```

## Update Alert Rule Create Form

Add a "Load from Template" section at the top of the create form:

1. A `<select>` dropdown showing all 12 templates grouped by device_type
2. When a template is selected, pre-fill the form fields (metric_name, operator, threshold, severity, duration_seconds, name, description, device_type)
3. User can modify any pre-filled value before saving

Also add an "Add All Defaults" button on the AlertListPage or alert rules list page:
- On click: calls `applyAlertRuleTemplates` with all 12 template_ids
- Shows a result toast: "Created X rules, skipped Y (already exist)"
- Refetches rule list

## Acceptance Criteria

- [ ] "Load from Template" dropdown exists on rule create form
- [ ] Selecting a template pre-fills all form fields
- [ ] "Add All Defaults" button calls apply endpoint
- [ ] Toast/notification shows created/skipped counts
- [ ] `npm run build` passes
