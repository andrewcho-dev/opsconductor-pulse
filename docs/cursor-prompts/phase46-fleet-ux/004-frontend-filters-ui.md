# Prompt 004 — Frontend: Search Input + Status Filter in DeviceFilters

## Context

`DeviceFilters.tsx` currently shows pagination controls and a tag filter dialog. This prompt adds a search text input and a status filter dropdown — the two most important fleet navigation tools.

## Your Task

**Read `frontend/src/features/devices/DeviceFilters.tsx` fully** before making changes.

### Add to `DeviceFilters.tsx`

The component currently accepts pagination props. Extend its props interface:

```typescript
interface DeviceFiltersProps {
  // Existing pagination props (keep all of them)
  ...

  // New filter props
  q: string;
  onQChange: (q: string) => void;
  statusFilter: string;              // "" | "ONLINE" | "STALE" | "OFFLINE"
  onStatusFilterChange: (s: string) => void;
}
```

### Search Input

Add a text input above or beside the existing pagination controls:

```
[ 🔍 Search devices...          ] [Status ▼] [Tags ▼] [Pagination...]
```

- Placeholder: `"Search by device ID, model, serial, site, or address"`
- Debounce: 300ms before calling `onQChange` (use a local state + useEffect with setTimeout/clearTimeout — do NOT add a new library)
- Clear button (×) when input has a value
- On clear: call `onQChange("")`

### Status Filter Dropdown

A simple `<select>` or button group:

```
[ All ] [ Online ] [ Stale ] [ Offline ]
```

Options: `""` (All), `"ONLINE"`, `"STALE"`, `"OFFLINE"`

Display with status indicator dots matching the existing color scheme in DeviceTable (green = ONLINE, yellow = STALE, red = OFFLINE).

### Pagination display: show total

Update the pagination display from showing only `offset-limit range` to also showing total:
- Before: `"1–100"`
- After: `"1–100 of 847"`

The `total` prop must be added to the component's props and used here.

### Wire in `DeviceListPage.tsx`

Pass the new props down to `<DeviceFilters />`:
```tsx
<DeviceFilters
  q={filters.q}
  onQChange={(q) => setFilters(f => ({ ...f, q, offset: 0 }))}
  statusFilter={filters.status ?? ""}
  onStatusFilterChange={(s) => setFilters(f => ({ ...f, status: s || undefined, offset: 0 }))}
  total={data?.total ?? 0}
  // ... existing pagination props
/>
```

## Acceptance Criteria

- [ ] Search input visible on device list page
- [ ] Typing in search triggers a new API call (after 300ms debounce)
- [ ] Status filter buttons/dropdown visible
- [ ] Clicking a status filters to that status
- [ ] Pagination shows "X–Y of Z" with real total
- [ ] Changing any filter resets to page 1 (offset = 0)
- [ ] `npm run build` clean — no TypeScript errors
