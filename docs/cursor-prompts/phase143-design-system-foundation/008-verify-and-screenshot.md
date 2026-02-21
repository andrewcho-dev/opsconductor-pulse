# Task 8: Build Verification and Visual Check

## Step 1: Type check

```bash
cd frontend && npx tsc --noEmit
```

Fix any TypeScript errors introduced by the changes.

## Step 2: Production build

```bash
cd frontend && npm run build
```

Fix any build errors.

## Step 3: Visual verification checklist

Start the dev server or rebuild the Docker container, then check each major page:

### Page background
- [ ] Light mode: page background is light gray (not pure white)
- [ ] Cards are white and visually distinct from the page background
- [ ] Sidebar blends with the page background (not jarring white)
- [ ] Dark mode: no regressions (should look the same as before)

### Spacing
- [ ] Dashboard page: `space-y-6` between sections
- [ ] Device list page: `space-y-6` between sections (was space-y-4)
- [ ] Alert list page: `space-y-6` between sections
- [ ] OTA pages: no double-padding wrapper
- [ ] All pages have consistent visual rhythm

### Typography
- [ ] Page titles are `text-xl font-semibold` (20px, not 24px)
- [ ] Card titles are `text-sm font-semibold` (14px)
- [ ] Body content is `text-sm` (14px) — no body content at 12px
- [ ] Timestamps and badges are the only things at `text-xs` (12px)
- [ ] No text smaller than 12px anywhere

### Cards
- [ ] All cards use `rounded-lg` (8px) — no `rounded-xl` anywhere
- [ ] No box shadows on cards (border only)
- [ ] Card padding is tighter (16px, was 24px)
- [ ] Card-to-card gaps are consistent

### Tables
- [ ] Table headers have uppercase treatment with muted color
- [ ] Table rows are ~44px height
- [ ] Table container has `rounded-lg` corners
- [ ] Pagination text is `text-sm`

### Status colors
- [ ] Device status dots use token colors (not hardcoded green/yellow/gray)
- [ ] Alert severity colors use token colors (not hardcoded red/orange/blue)
- [ ] Colors look correct in both light and dark mode

## Step 4: Fix any visual regressions

If any page looks broken after the changes, fix it. Common issues:
- Overflow clipping from `overflow-hidden` on rounded containers
- Text truncation from tighter padding
- Layout shifts from changed gap/padding values

## Step 5: Lint check

```bash
cd frontend && npx tsc --noEmit
```

Ensure zero errors before committing.
