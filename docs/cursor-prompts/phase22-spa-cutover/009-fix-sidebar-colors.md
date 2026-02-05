# Task 009: Fix Sidebar Menu Item Colors

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.

---

## Context

The sidebar menu items are nearly invisible — light gray text on a light gray background. The theme is supposed to be a dark theme (comment on line 6 of `index.css` says "OpsConductor Pulse Dark Theme"), but the `--sidebar` CSS variable is set to `hsl(0 0% 98%)` (near-white), which conflicts with the light-colored foreground variables.

The sidebar component uses `bg-sidebar` (which maps to `--sidebar`), and the text uses `text-sidebar-foreground` (which maps to `--sidebar-foreground: 0 0% 93%` — also near-white). White text on white background = invisible.

**Read first**:
- `frontend/src/index.css` — the full theme definition

---

## Task

### 9.1 Fix the sidebar background variable

**File**: `frontend/src/index.css`

Change line 41 from:

```css
  --sidebar: hsl(0 0% 98%);
```

To:

```css
  --sidebar: hsl(240 28% 10%);
```

This matches the `--sidebar-background` value on line 33, giving the sidebar a dark background consistent with the rest of the dark theme. The existing light-colored foreground variables (`--sidebar-foreground: 0 0% 93%`) will now be visible against this dark background.

### 9.2 Rebuild frontend

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
```

### 9.3 Restart UI container

```bash
cd /home/opsconductor/simcloud/compose && docker compose restart ui
```

---

## Files to Modify

| Action | Path | What changes |
|--------|------|--------------|
| MODIFY | `frontend/src/index.css` | Fix `--sidebar` to dark background matching the theme |

---

## Test

### Step 1: Verify build succeeds

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
```

### Step 2: Verify the CSS variable is correct in the built output

```bash
grep -c "0 0% 98%" /home/opsconductor/simcloud/frontend/dist/assets/index-*.css || echo "No near-white sidebar background"
```

Should show 0 or "No near-white sidebar background".

### Step 3: Visual verification

Open `https://192.168.10.53/` in the browser. The sidebar should have a dark background with visible light-colored menu items.

---

## Commit

```
Fix sidebar colors — dark background for dark theme

The --sidebar CSS variable was set to near-white (hsl 0 0% 98%),
conflicting with the light-colored sidebar-foreground text. Changed
to dark background (hsl 240 28% 10%) matching the theme.
```
