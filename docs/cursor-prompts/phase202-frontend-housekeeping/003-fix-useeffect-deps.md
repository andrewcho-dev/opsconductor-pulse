# Task 3: Fix useEffect Dependency Arrays

## Context

`frontend/src/features/alerts/AlertRuleDialog.tsx:425-436` includes `form` (the `useForm()` return value) in a `useEffect` dependency array. The `form` object's reference changes on every render, causing the effect to run far more often than intended. This can cause form fields to reset unexpectedly.

## Actions

1. Read `frontend/src/features/alerts/AlertRuleDialog.tsx` in full.

2. Find the `useEffect` at approximately line 425. The dependency array includes `form`. The issue is that `form` from `react-hook-form` is not stable across renders.

3. Replace `form` in the dependency array with the specific stable methods you actually use inside the effect. For example, if the effect calls `form.setValue(...)`, use:
   ```typescript
   const { setValue } = form;  // Destructure once, these are stable references

   useEffect(() => {
     if (!open || !isEditing) return;
     // ... use setValue directly, not form.setValue
     setValue("sensor_device_id", match.device_id, { shouldDirty: false });
   }, [open, isEditing, targetingMode, rule?.sensor_id, sensorDeviceId, allSensorsForEdit, setValue]);
   //                                                                                        ↑ stable
   ```

4. Apply the same fix to the second `useEffect` at approximately line 438-446 if `form` or `form.reset` appears in its dependency array.

5. Verify that the effects still function correctly after the change — the logic inside should be identical, only the dependency reference changes.

6. Search for other `useEffect` calls in the file (and other files in `features/alerts/`) that include `form` directly in deps and apply the same pattern.

## Verification

```bash
# No useEffect with form as direct dep
grep -A5 'useEffect' frontend/src/features/alerts/AlertRuleDialog.tsx | grep -E '\bform\b'
# Should return zero results OR only for destructured stable methods, not the form object itself
```
