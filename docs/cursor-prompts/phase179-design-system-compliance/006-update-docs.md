# Task 6: Update Documentation

## Objective

Update project documentation to reflect Phase 179's design system compliance sweep.

## Files to Update

1. `docs/development/frontend.md`
2. `docs/index.md`
3. `docs/services/ui-iot.md`

---

## 1. `docs/development/frontend.md`

### Frontmatter

- Set `last-verified: 2026-02-20`
- Add `179` to the `phases` array

### Content Changes

#### Update the "Prohibited Patterns" section under "UI Pattern Conventions"

Add these entries to the existing prohibited patterns list:

```markdown
- Raw `<select>` elements (use shadcn `Select` + `SelectTrigger` + `SelectContent` + `SelectItem`).
- Raw `<input type="checkbox">` elements (use `Switch` for boolean toggles, `Checkbox` for multi-select lists).
```

#### Add a "Form Primitives" section (after the "Prohibited Patterns" section)

```markdown
## Form Primitives (Phase 179)

All form controls must use design system components instead of raw HTML elements:

| Need | Component | Import |
|------|-----------|--------|
| Dropdown / picker | `Select` + `SelectTrigger` + `SelectValue` + `SelectContent` + `SelectItem` | `@/components/ui/select` |
| Boolean toggle (on/off) | `Switch` | `@/components/ui/switch` |
| Multi-select list item | `Checkbox` | `@/components/ui/checkbox` |
| Action trigger | `Button` | `@/components/ui/button` |

### Select notes
- `SelectItem value` must be a non-empty string. Use `"all"` or `"none"` as sentinel values.
- For numeric values: `value={String(num)}` and `onValueChange={(v) => setNum(Number(v))}`.
- `SelectTrigger` renders a chevron automatically — do not add one manually.

### Switch vs Checkbox
- **Switch** — Single boolean setting (enabled/disabled, feature flags, retain flag, use TLS). Standard for all on/off controls.
- **Checkbox** — Item in a multi-select list (select devices, groups, metrics) or bulk-select header/row checkboxes.
```

---

## 2. `docs/index.md`

### Frontmatter

- Set `last-verified: 2026-02-20`
- Add `179` to the `phases` array

### Content Changes

No new features to add — this phase is an internal compliance sweep, not a user-facing feature. No content changes needed beyond frontmatter.

---

## 3. `docs/services/ui-iot.md`

### Frontmatter

- Set `last-verified: 2026-02-20`
- Add `179` to the `phases` array

### Content Changes

No content changes needed — this phase does not affect routes, APIs, or service behavior. Only frontmatter updates.

---

## Verification

- All three docs have updated `last-verified` date and `179` in their `phases` array
- `docs/development/frontend.md` documents the prohibited raw form primitives and the replacement rules
- No stale information in updated sections
