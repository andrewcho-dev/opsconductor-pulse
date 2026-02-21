Find form inputs that are missing associated labels.

Run this to find Input components without a label association:

```bash
grep -rn '<Input' frontend/src/ --include="*.tsx" -l
```

Read each file and check whether each `<Input>` has either:
- A `<Label htmlFor="input-id">` element with a matching `id` on the input, OR
- An `aria-label` prop directly on the input, OR
- An `aria-labelledby` pointing to a visible label element

If none of these are present, the input is unlabeled. Fix it:

```tsx
// Option 1: Label with htmlFor (preferred — visible label)
<Label htmlFor="device-name">Device Name</Label>
<Input id="device-name" placeholder="Enter device name" />

// Option 2: aria-label (for inputs where a visible label isn't practical)
<Input aria-label="Search devices" placeholder="Search..." />
```

Focus on the most-used forms first:
- Device provisioning wizard
- Alert rule creation dialog (`AlertRuleDialog.tsx`)
- User creation forms
- Notification channel config forms

Placeholder text is NOT a label — `placeholder="Search"` does not satisfy accessibility requirements. If the only label-like thing is a placeholder, add a proper aria-label.
