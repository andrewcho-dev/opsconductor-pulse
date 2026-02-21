# Phase 104 — Frontend: Duration Field in Alert Rule Modal

## Context

Find the Alert Rules UI. It is likely:
- `frontend/src/pages/AlertRules.jsx` (or `.tsx`)
- `frontend/src/components/AlertRuleModal.jsx`
- Or similar — search with: `grep -rn "alert_rule\|AlertRule\|alert-rule" frontend/src --include="*.jsx" --include="*.tsx" -l`

Read the existing Create/Edit modal for alert rules before making any changes.

## Change 1: Add duration_minutes field to the form

In the modal's form (after the `threshold` field), add:

```jsx
<div className="form-group">
  <label htmlFor="duration_minutes">Duration (minutes)</label>
  <input
    id="duration_minutes"
    type="number"
    min="1"
    placeholder="Instant (leave blank)"
    value={form.duration_minutes ?? ""}
    onChange={(e) =>
      setForm({
        ...form,
        duration_minutes: e.target.value === "" ? null : parseInt(e.target.value, 10),
      })
    }
    className="form-control"
  />
  <small className="form-text text-muted">
    Fire only after condition holds for this many minutes. Leave blank to fire immediately.
  </small>
</div>
```

Adjust className to match the existing form style.

## Change 2: Include duration_minutes in submit payload

In the form submit handler (the function that calls the API), ensure
`duration_minutes` is included:

```js
const payload = {
  // ... existing fields ...
  duration_minutes: form.duration_minutes || null,
};
```

## Change 3: Populate duration_minutes when editing

In the code that pre-fills the form when editing an existing rule:

```js
setForm({
  // ... existing fields ...
  duration_minutes: rule.duration_minutes ?? null,
});
```

## Change 4: Display duration_minutes in the rules table (optional)

If there is a table listing alert rules, add a "Duration" column:

```jsx
<td>{rule.duration_minutes ? `${rule.duration_minutes} min` : "Instant"}</td>
```

## Verify

```bash
npm run build --prefix frontend 2>&1 | tail -5
```

Expected: build succeeds with no errors.
