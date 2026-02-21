# Task 5: Dashboard, Analytics, Jobs, Sites, Roles, OTA, MQTT

## Objective

Replace all remaining raw `<select>`, `<input type="checkbox">`, and `<button>` elements across dashboard widgets, analytics, jobs, sites, roles, OTA campaign detail, and the MQTT test client.

Refer to `000-start.md` for migration rules and import references.

## Files to Modify (11)

---

### 1. `frontend/src/features/dashboard/WidgetConfigDialog.tsx`

**Raw `<input type="checkbox">` violations:**
- **~Line 665** — Radar chart metric multi-selector checkboxes (select 3-6 metrics for radar axes)

This is a multi-select list pattern. Replace each `<input type="checkbox">` with `Checkbox`:

```tsx
<Checkbox
  checked={selectedMetrics.includes(metric)}
  onCheckedChange={() => toggleMetric(metric)}
/>
```

Note: This file already imports shadcn `Select` and `Switch` for other fields. Only `Checkbox` is missing.

**Add imports:** `Checkbox` from `@/components/ui/checkbox`.

---

### 2. `frontend/src/features/dashboard/DashboardSelector.tsx`

**Raw `<button>` violations:**
- **~Line 145** — "Set as default" star icon button per dashboard entry
- **~Line 157** — "Delete" trash icon button per dashboard entry

Replace both with `Button variant="ghost" size="icon-sm"`.

**Add imports:** `Button` from `@/components/ui/button`.

---

### 3. `frontend/src/features/dashboard/AddWidgetDrawer.tsx`

**Raw `<button>` violations:**
- **~Line 99** — Widget type selector card (each widget option in the catalog is a raw `<button>`)

These function as selectable cards in a grid. Replace with `Button variant="outline" className="h-auto flex-col items-start gap-1 p-3 text-left"` to maintain the card-like appearance:

```tsx
<Button
  variant="outline"
  className="h-auto flex-col items-start gap-1 p-3 text-left"
  onClick={() => onSelectWidget(widget.type)}
>
  <span className="font-medium text-sm">{widget.label}</span>
  <span className="text-xs text-muted-foreground">{widget.description}</span>
</Button>
```

**Add imports:** `Button` from `@/components/ui/button`.

---

### 4. `frontend/src/features/dashboard/widgets/WidgetContainer.tsx`

**Raw `<button>` violations:**
- **~Line 75** — Configure (gear icon) button when editing dashboard, in header variant
- **~Line 84** — Remove (× icon) button when editing dashboard, in header variant
- **~Lines 100, 109** — Configure and Remove buttons in absolute overlay variant (widgets without title)
- **~Line 125** — "Configure widget" text link-style button in needs-configuration state

Replace all icon buttons with `Button variant="ghost" size="icon-sm"`. Replace the text button with `Button variant="link" size="sm"`.

**Add imports:** `Button` from `@/components/ui/button`.

---

### 5. `frontend/src/components/shared/WidgetErrorBoundary.tsx`

**Raw `<button>` violations:**
- **~Line 47** — "Try again" error recovery button in the widget error boundary fallback UI

Replace with `Button variant="outline" size="sm"`.

**Add imports:** `Button` from `@/components/ui/button`.

---

### 6. `frontend/src/features/jobs/CreateJobModal.tsx`

**Raw `<select>` violations:**
- **~Line 83** — Job target type selector (single device / device group / all devices)

Replace with `Select`.

**Add imports:** `Select, SelectContent, SelectItem, SelectTrigger, SelectValue`.

---

### 7. `frontend/src/features/analytics/AnalyticsPage.tsx`

**Raw `<input type="checkbox">` violations:**
- **~Line 327** — Device filter checkboxes (multi-select: pick which devices to include in the analytics query). Renders a scrollable list of devices with checkboxes.

This is a multi-select list. Replace each `<input type="checkbox">` with `Checkbox`. Note: This file already imports shadcn `Select` for other controls.

**Add imports:** `Checkbox` from `@/components/ui/checkbox`.

---

### 8. `frontend/src/features/sites/SitesPage.tsx`

**Raw `<button>` violations:**
- **~Line 27** — Site card clickable item (navigates to site detail page)

This is a navigation action. Replace with a `<Link>` component styled as a card, or wrap in `Button variant="ghost" asChild`:

```tsx
<Link
  to={`/sites/${site.site_id}`}
  className="block rounded-lg border p-4 hover:bg-accent transition-colors"
>
  {/* ... card content ... */}
</Link>
```

Using `<Link>` directly is preferred over `<Button asChild>` when the entire element is a navigation target.

**Add imports:** Ensure `Link` from `react-router-dom` is imported (may already be). Remove any raw `<button>` element.

---

### 9. `frontend/src/features/roles/RolesPage.tsx`

**Raw `<button>` violations:**
- **~Line 38** — Collapsible role section toggle button (expand/collapse to show permissions)

Replace with `Button variant="ghost"` with a chevron icon that rotates based on open/closed state:

```tsx
<Button variant="ghost" className="w-full justify-between" onClick={() => toggleRole(role.id)}>
  <span>{role.name}</span>
  <ChevronDown className={`h-4 w-4 transition-transform ${open ? "rotate-180" : ""}`} />
</Button>
```

**Add imports:** `Button` from `@/components/ui/button`.

---

### 10. `frontend/src/features/ota/OtaCampaignDetailPage.tsx`

**Raw `<button>` violations:**
- **~Line 208** — Campaign device status filter toggle button (e.g., "Pending")
- **~Line 224** — Another status filter toggle button (e.g., "Completed")

These are filter toggle pills. Replace with `Button variant="outline" size="sm"`, with the active filter using `variant="default"`:

```tsx
<Button
  variant={filter === "pending" ? "default" : "outline"}
  size="sm"
  onClick={() => setFilter("pending")}
>
  Pending ({counts.pending})
</Button>
```

**Add imports:** `Button` from `@/components/ui/button`.

---

### 11. `frontend/src/features/fleet/MqttTestClientPage.tsx`

**Raw `<input type="checkbox">` violations:**
- **~Line 252** — MQTT publish "Retain" flag checkbox (single boolean toggle)

Replace with `Switch`:

```tsx
<div className="flex items-center gap-1.5">
  <Switch
    id="pub-retain"
    checked={pubRetain}
    onCheckedChange={setPubRetain}
    disabled={!connected}
    size="sm"
  />
  <Label htmlFor="pub-retain" className="text-xs">Retain</Label>
</div>
```

**Raw `<button>` violations:**
- **~Line 294** — "Unsubscribe" × button inside each subscription badge

Replace with `Button variant="ghost" size="icon-sm"`:

```tsx
<Button
  variant="ghost"
  size="icon-sm"
  className="ml-0.5 h-4 w-4 rounded-full"
  onClick={() => handleUnsubscribe(t)}
>
  <X className="h-3 w-3" />
</Button>
```

**Add imports:** `Switch` from `@/components/ui/switch`; `Label` from `@/components/ui/label`. `Button` is already imported.

---

## Verification

After all changes:

```bash
cd frontend && npx tsc --noEmit
```

- All 11 files compile without errors
- No raw `<select>`, `<input type="checkbox">`, or `<button>` remains in any of the 11 files
- Dashboard widget config shows Checkbox components for radar metric selection
- Dashboard editor shows styled configure/remove buttons on widgets
- Widget error boundary shows a styled "Try again" button
- Analytics page shows Checkbox components for device multi-select
- Job creation modal shows styled target type dropdown
- Sites page uses Link-based navigation instead of raw buttons
- Roles page uses Button for collapsible sections
- OTA campaign detail uses Button for status filter toggles
- MQTT test client uses Switch for retain toggle and Button for unsubscribe
- Dark mode renders correctly for all replaced elements
