# Task 4: Update Documentation

## Objective

Update project documentation to reflect Phase 183's modal sizing and layout overhaul.

## Files to Update

1. `docs/development/frontend.md`
2. `docs/index.md`
3. `docs/services/ui-iot.md`

---

## 1. `docs/development/frontend.md`

### Frontmatter

- Set `last-verified: 2026-02-20`
- Add `183` to the `phases` array
- Add to `sources`: `frontend/src/features/alerts/AlertRuleDialog.tsx`

### Content Changes

#### Add "Modal Sizing Guidelines (Phase 183)" section

Add after the "Modals & Dialogs" subsection in "UI Pattern Conventions":

```markdown
### Modal Sizing (Phase 183)

The default `DialogContent` width is `sm:max-w-xl` (640px). Override with an explicit class when needed:

| Tier | Class | Width | Use for |
|------|-------|-------|---------|
| S | `sm:max-w-sm` | 384px | Confirmations, 1-field dialogs |
| M | `sm:max-w-md` | 448px | Simple forms (2-3 fields), assign/change dialogs |
| L | (default) | 640px | Standard forms (4-8 fields) |
| XL | `sm:max-w-2xl` | 672px | Forms with tables or 10+ fields |
| 2XL | `sm:max-w-3xl` | 768px | Complex multi-section forms (e.g., AlertRuleDialog) |

#### Layout rules

- **Multi-column grids:** Use `grid gap-4 sm:grid-cols-2` to put related short fields side by side (Severity + Duration, Operator + Threshold, First Name + Last Name).
- **No scroll when avoidable:** Wider dialog + 2-column layout should eliminate scrolling for most forms. Only add `max-h-[85vh] overflow-y-auto` when content is truly unbounded (e.g., multi-condition rules with user-added rows).
- **Full-width fields:** Description, textarea, toggles, and fields with long help text should span full width.
```

#### Update "Prohibited Patterns" list

Add to the existing prohibited patterns:

```markdown
- Leaving default dialog width for forms with 6+ fields (use a wider tier or 2-column layout).
- Single-column layout for forms where fields naturally pair (use `sm:grid-cols-2`).
- Raw `<input>` elements in dialogs (use `Input` component — Phase 179).
```

---

## 2. `docs/index.md`

### Frontmatter

- Set `last-verified: 2026-02-20`
- Add `183` to the `phases` array

### Content Changes

No content changes needed — the modal sizing is an internal UI improvement, not a user-facing feature.

---

## 3. `docs/services/ui-iot.md`

### Frontmatter

- Set `last-verified: 2026-02-20`
- Add `183` to the `phases` array

### Content Changes

No content changes needed — this phase is frontend-only with no route or API changes.

---

## Verification

- `docs/development/frontend.md` has modal sizing guidelines with the tier table
- `docs/development/frontend.md` prohibits default width for complex forms
- All three docs have `183` in their `phases` array
- `last-verified` dates updated
