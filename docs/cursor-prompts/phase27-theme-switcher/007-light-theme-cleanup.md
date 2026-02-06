# Phase 27.7: Light Theme Cleanup

## Task

Fix all remaining hardcoded dark-mode colors across the frontend.

## Elements to Fix

### 1. Charts (Priority)

**MetricGauge.tsx** — gauge text, labels, lines:
```typescript
const resolvedTheme = useUIStore((s) => s.resolvedTheme);
const isDark = resolvedTheme === "dark";

// Use these throughout:
const textColor = isDark ? "#fafafa" : "#18181b";
const mutedColor = isDark ? "#a1a1aa" : "#52525b";
const borderColor = isDark ? "#52525b" : "#d4d4d8";
```

**TimeSeriesChart.tsx** — axis, grid, labels:
```typescript
const axisStroke = isDark ? "#71717a" : "#52525b";
const gridStroke = isDark ? "#27272a" : "#e4e4e7";
const tickStroke = isDark ? "#3f3f46" : "#d4d4d8";
```

**UPlotChart.tsx** — if it has hardcoded colors, same pattern.

### 2. Status Badges

Search for hardcoded badge colors in:
- `frontend/src/components/`
- `frontend/src/features/`

Look for patterns like:
```typescript
// BAD - hardcoded
className="bg-green-500/20 text-green-400"

// GOOD - uses semantic colors or adapts
className="bg-green-100 text-green-800 dark:bg-green-500/20 dark:text-green-400"
```

Common badges to fix:
- Device status (ONLINE/STALE)
- Alert severity
- Connection status

### 3. Tables

Check if table headers or rows have hardcoded backgrounds:
```typescript
// BAD
className="bg-zinc-900"

// GOOD
className="bg-muted"
```

### 4. Cards

Should already use CSS variables (`bg-card`, `text-card-foreground`). Verify no hardcoded colors.

### 5. Sidebar

Check `AppSidebar.tsx` for any hardcoded colors not using CSS variables.

### 6. Alert/Toast Components

Check notification or alert components for hardcoded colors.

## How to Find Issues

```bash
# Search for hardcoded hex colors in TSX files
cd /home/opsconductor/simcloud/frontend/src
grep -r "#[0-9a-fA-F]\{6\}" --include="*.tsx" | grep -v node_modules
```

```bash
# Search for zinc/gray color classes without dark: variants
grep -rE "(bg|text|border)-(zinc|gray|slate)-[0-9]+" --include="*.tsx" | grep -v "dark:"
```

## Color Reference

| Element | Light Mode | Dark Mode |
|---------|------------|-----------|
| Text primary | #18181b | #fafafa |
| Text muted | #52525b | #a1a1aa |
| Border | #e4e4e7 | #27272a |
| Background | #ffffff | #09090b |
| Card bg | #ffffff | #18181b |

## Rebuild and Test

After each fix:
```bash
cd /home/opsconductor/simcloud/frontend && npm run build
cp -r dist/* ../services/ui_iot/spa/
cd ../compose && docker compose restart ui
```

Toggle to light theme and verify each element is readable.

## Files to Check

| File | Check For |
|------|-----------|
| `lib/charts/MetricGauge.tsx` | Hardcoded #fafafa, #a1a1aa |
| `lib/charts/TimeSeriesChart.tsx` | Hardcoded axis/grid colors |
| `lib/charts/UPlotChart.tsx` | Hardcoded colors |
| `features/dashboard/widgets/*.tsx` | Badge colors, text colors |
| `features/devices/*.tsx` | Status badges |
| `features/alerts/*.tsx` | Severity badges |
| `components/layout/*.tsx` | Sidebar, header colors |
