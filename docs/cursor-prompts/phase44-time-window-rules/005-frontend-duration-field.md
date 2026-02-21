# Prompt 005 — Frontend: Add Duration Field to Alert Rule Form

## Context

The API now accepts `duration_seconds`. Customers need a way to set it in the UI when creating or editing alert rules.

## Your Task

Find the alert rule creation/edit form in the frontend. It will be somewhere in `frontend/src/features/` — likely named `AlertRulePage`, `AlertRuleForm`, `AlertRuleDialog`, or similar. Search for it by looking for files that reference `metric_name` and `operator` fields (those are existing alert rule form fields).

### Add a "Duration" field to the form

The field should:
- Label: **"Duration (seconds)"** or **"Alert after..."**
- Input type: number, min=0, step=1
- Default value: `0`
- Helper text: `"0 = alert immediately. Set to 60+ to require sustained condition."`
- Validation: must be a non-negative integer

### Wire it to the API

When the form submits (POST or PATCH), include `duration_seconds` in the request body. When the form loads an existing rule (edit mode), populate the field from `rule.duration_seconds`.

### Display it in the rule list/detail view

Wherever existing rules are displayed (rule list table or detail card), show the duration:
- If `duration_seconds === 0`: show `"Immediate"` or nothing
- If `duration_seconds > 0`: show `"${duration_seconds}s"` or `"${duration_seconds / 60}m"` if divisible by 60

### TypeScript types

Update the alert rule TypeScript type/interface to include `duration_seconds: number` (with a default of 0 if the API doesn't return it — use `?? 0`).

## Acceptance Criteria

- [ ] Alert rule creation form has a `duration_seconds` input field
- [ ] Editing an existing rule shows the current `duration_seconds` value
- [ ] Submitting the form includes `duration_seconds` in the API request body
- [ ] Rule list/detail view displays duration in a human-readable way
- [ ] TypeScript type updated — no TS errors (`npm run build` clean)
- [ ] `pytest -m unit -v` still passes (no backend changes in this prompt)
