# Prompt 004 — Frontend: Template Editor on Integration Form

Read `frontend/src/features/integrations/` — find the integration edit/create form for email and webhook types.

## Add Template Editor

For **email** integrations:
- Show a "Subject Template" text input (pre-filled with current `subject_template` from config_json)
- Show a "Body Template" textarea (pre-filled with current `body_template`)

For **webhook** integrations:
- Show a "Body Template" textarea (optional — if blank, raw alert payload is sent)

Both:
- Add a "Variables Reference" collapsible section below each textarea, showing the available variables fetched from `GET /customer/integrations/{id}/template-variables`
- Each variable shown as: `{{ variable_name }}` — description
- "Insert" button next to each variable inserts it at cursor position in the focused textarea

## Add API Function

In `frontend/src/services/api/integrations.ts`:

```typescript
export interface TemplateVariable {
  name: string;
  type: string;
  description: string;
}

export async function fetchTemplateVariables(integrationId: string): Promise<{
  variables: TemplateVariable[];
  syntax: string;
  example: string;
}> {
  return apiFetch(`/customer/integrations/${integrationId}/template-variables`);
}
```

## Acceptance Criteria

- [ ] Subject template input on email integration form
- [ ] Body template textarea on email and webhook forms
- [ ] Variables reference panel fetches from API
- [ ] Insert variable at cursor works
- [ ] `npm run build` passes
