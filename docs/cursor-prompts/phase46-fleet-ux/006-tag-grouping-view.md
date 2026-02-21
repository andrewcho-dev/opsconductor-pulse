# Prompt 006 — Frontend: Tag Grouping View Toggle

## Context

Currently devices are shown in a flat list. This prompt adds a "Group by tag" toggle that organizes devices under their tag headings — useful for customers managing named groups of devices (e.g., "rack-a", "building-2", "critical").

## Your Task

### Step 1: Add a "Group by tag" toggle button

Add a view toggle to `DeviceListPage.tsx`, beside the existing filter controls:

```
[ List view ] [ Group by tag ]
```

State: `viewMode: "list" | "grouped"` — default `"list"`.

When `viewMode === "grouped"`, disable pagination (grouping shows all results) and hide the `DeviceFilters` pagination controls. Show a note: `"Showing all devices grouped by tag. Use list view for pagination."` Cap grouped view at 500 devices max — if `total > 500`, show a warning and keep pagination.

### Step 2: Implement grouped rendering

When `viewMode === "grouped"`, group the devices by tag:

```typescript
function groupDevicesByTag(devices: Device[]): Map<string, Device[]> {
  const groups = new Map<string, Device[]>();
  const untagged: Device[] = [];

  for (const device of devices) {
    if (!device.tags || device.tags.length === 0) {
      untagged.push(device);
    } else {
      for (const tag of device.tags) {
        if (!groups.has(tag)) groups.set(tag, []);
        groups.get(tag)!.push(device);
      }
    }
  }

  // Sort groups alphabetically
  const sorted = new Map([...groups.entries()].sort());

  // Add untagged at the end
  if (untagged.length > 0) sorted.set("(untagged)", untagged);

  return sorted;
}
```

Note: a device with 3 tags appears in 3 groups. This is intentional — it mirrors how tags work (a device belongs to all its tag groups simultaneously).

### Step 3: Render grouped view

For each tag group, render:
```
▼ rack-a (12 devices)
  [DeviceTable with those 12 devices — no pagination]

▼ rack-b (8 devices)
  [DeviceTable with those 8 devices — no pagination]

▼ (untagged) (3 devices)
  [DeviceTable with those 3 devices]
```

Each group is collapsible (clicking the header toggles open/closed). Default: all groups open.

Pass `showPagination={false}` to DeviceTable or equivalent — the grouped view shows all devices in the group, no pagination within a group.

### Step 4: Fetch all devices for grouping

When `viewMode === "grouped"`:
- Set `limit = 500` (or `total` if < 500) and `offset = 0` in the API call
- Do not show pagination controls

## Acceptance Criteria

- [ ] Toggle between list view and grouped view
- [ ] Grouped view shows devices organized under tag headings
- [ ] Each group is collapsible
- [ ] Devices with no tags appear under `(untagged)`
- [ ] Devices with multiple tags appear in each relevant group
- [ ] List view behavior is completely unchanged
- [ ] `npm run build` clean
