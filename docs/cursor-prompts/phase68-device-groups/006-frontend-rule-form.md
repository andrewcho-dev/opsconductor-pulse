# Prompt 006 — Frontend: Group Selector in Alert Rule Form

Read `frontend/src/features/alerts/AlertRuleDialog.tsx`.

## Add Group Selector

In the alert rule create/edit form, add a "Device Groups" multi-select alongside the existing "Sites" selector:

- Fetch available groups via `fetchDeviceGroups()`
- Multi-select: user can pick 0 or more groups
- Selected groups passed as `group_ids` array in the rule create/update payload

Add `group_ids?: string[]` to the AlertRule TypeScript type in `types.ts` if not already present.

## Acceptance Criteria

- [ ] Group selector in AlertRuleDialog
- [ ] Selected groups included in form submission as `group_ids`
- [ ] `group_ids` in AlertRule TypeScript type
- [ ] `npm run build` passes
