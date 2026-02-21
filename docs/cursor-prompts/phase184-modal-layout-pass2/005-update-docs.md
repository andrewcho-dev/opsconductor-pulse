# Task 5: Update Documentation

## Files to Update

1. `docs/development/frontend.md`
2. `docs/index.md`
3. `docs/services/ui-iot.md`

---

## 1. `docs/development/frontend.md`

### Frontmatter

- Set `last-verified: 2026-02-20`
- Add `184` to the `phases` array

### Content Changes

#### Update "Modal Sizing (Phase 183)" section

Rename to "Modal Sizing (Phases 183-184)" and add to the layout rules:

```markdown
- **Fieldset grouping:** For 8+ fields, group into logical fieldsets (Hardware, Location, Network) with `<fieldset className="space-y-3 rounded-md border p-4">` and `<legend>` labels.
- **Fieldset 2-column grid:** When a dialog has 2+ fieldsets, lay them out side-by-side in a `grid gap-4 sm:grid-cols-2` outer grid to halve vertical height.
- **Repeating sections as cards:** For user-addable rows (escalation levels, schedule layers), render each as a bordered card with a header (title + Remove button) and labeled fields in a grid.
```

Add to the prohibited patterns:

```markdown
- Unlabeled number inputs in grids (every field must have a label, even compact ones).
- 3+ header fields (Name, Type, Enabled) each on their own row (pack into a grid row).
```

---

## 2. `docs/index.md`

### Frontmatter

- Set `last-verified: 2026-02-20`
- Add `184` to the `phases` array

### Content Changes

No content changes — Phase 184 is an internal UI layout improvement.

---

## 3. `docs/services/ui-iot.md`

### Frontmatter

- Set `last-verified: 2026-02-20`
- Add `184` to the `phases` array

### Content Changes

No content changes — no route or API changes.

---

## Verification

- `docs/development/frontend.md` has updated modal sizing section with fieldset grouping rules
- All three docs have `184` in their `phases` array
- `last-verified` dates updated
