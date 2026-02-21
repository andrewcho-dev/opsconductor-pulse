# Phase 179: Design System Compliance — Select, Checkbox, Button

## Overview

Replace all remaining raw HTML form primitives (`<select>`, `<input type="checkbox">`, `<button>`) with their shadcn/ui equivalents across the entire frontend. This is the companion sweep to Phase 145 (which standardized modals, confirm dialogs, and page headers).

**Scope:** ~38 files across devices, alerts, notifications, operator, dashboard, and other feature areas.

## Migration Rules

Every transformation in this phase follows one of these rules:

| Raw Element | Replacement | When |
|-------------|-------------|------|
| `<select>` with `<option>`s | `Select` + `SelectTrigger` + `SelectValue` + `SelectContent` + `SelectItem` | Always |
| `<input type="checkbox">` | `Switch` | Single boolean toggle (enabled/disabled, retain flag, use TLS) |
| `<input type="checkbox">` | `Checkbox` | Item in a multi-select list (select devices, groups, metrics) or bulk select |
| `<button>` with icon only | `Button variant="ghost" size="icon-sm"` | Small icon actions (edit, delete, close) |
| `<button>` with text | `Button` or `Button variant="outline" size="sm"` | Standard actions |
| `<button>` that navigates | `Button asChild` wrapping `<Link>` | Navigation actions |
| `<button>` as clickable card | `Button variant="ghost"` with custom className | Clickable list items / card selections |

### Select Migration Pattern

**Before:**
```tsx
<select
  value={status}
  onChange={(e) => setStatus(e.target.value)}
  className="rounded border px-2 py-1 text-sm"
>
  <option value="">All</option>
  <option value="ONLINE">Online</option>
</select>
```

**After:**
```tsx
<Select value={status} onValueChange={setStatus}>
  <SelectTrigger className="w-[120px] h-8">
    <SelectValue placeholder="All" />
  </SelectTrigger>
  <SelectContent>
    <SelectItem value="all">All</SelectItem>
    <SelectItem value="ONLINE">Online</SelectItem>
  </SelectContent>
</Select>
```

**Notes:**
- `SelectItem value` must be a non-empty string. Use `"all"` or `"any"` as sentinel values, converting to `""` in `onValueChange` if the state uses empty string.
- For numeric values: `value={String(num)}` and `onValueChange={(v) => setNum(Number(v))}`.
- `SelectTrigger` renders a chevron automatically — do not add one manually.

### Checkbox / Switch Migration Pattern

**Toggle (before):**
```tsx
<input type="checkbox" checked={retain} onChange={(e) => setRetain(e.target.checked)} />
```

**Toggle (after — use Switch):**
```tsx
<Switch checked={retain} onCheckedChange={setRetain} />
```

**Multi-select list item (before):**
```tsx
<input type="checkbox" checked={selected.includes(id)} onChange={() => toggle(id)} />
```

**Multi-select list item (after — use Checkbox):**
```tsx
<Checkbox checked={selected.includes(id)} onCheckedChange={() => toggle(id)} />
```

### Button Migration Pattern

**Before:**
```tsx
<button onClick={handleClick} className="rounded bg-primary px-3 py-1 text-sm text-white">
  Save
</button>
```

**After:**
```tsx
<Button size="sm" onClick={handleClick}>Save</Button>
```

**Icon button (before):**
```tsx
<button onClick={onRemove} className="p-1 rounded hover:bg-muted">
  <X className="h-3 w-3" />
</button>
```

**Icon button (after):**
```tsx
<Button variant="ghost" size="icon-sm" onClick={onRemove}>
  <X className="h-3 w-3" />
</Button>
```

## Execution Order

1. `001-device-list-detail.md` — Device list page, filters, and detail sub-panels (7 files)
2. `002-device-modals-wizard.md` — Device modals, wizard steps, data tabs, groups (9 files)
3. `003-alerts-notifications.md` — Alert list, alert rules, digest, channels, routing, escalation, on-call (7 files)
4. `004-operator-pages.md` — NOC, user detail, audit log, tenant matrix, activity log (5 files)
5. `005-dashboard-remaining.md` — Dashboard widgets, analytics, jobs, sites, roles, OTA, MQTT test (11 files)
6. `006-update-docs.md` — Documentation updates

## Import References

Components to import (add to each file as needed):

```tsx
// Select family
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

// Checkbox (for multi-select lists)
import { Checkbox } from "@/components/ui/checkbox";

// Switch (for boolean toggles)
import { Switch } from "@/components/ui/switch";

// Button (if not already imported)
import { Button } from "@/components/ui/button";

// Label (for form labels next to Switch/Checkbox)
import { Label } from "@/components/ui/label";
```

## Files Modified Summary

| Task | Files |
|------|-------|
| 001 | DeviceListPage, DeviceFilters, DeviceAlertsSection, DeviceInfoCard, DeviceDetailPane, DeviceUptimePanel, DevicePlanPanel |
| 002 | AddDeviceModal, DeviceEditModal, DeviceSensorsDataTab, DeviceTransportTab, DeviceGroupsPage, wizard/SetupWizard, wizard/Step1DeviceDetails, wizard/Step2TagsGroups, wizard/Step5AlertRules |
| 003 | AlertListPage, AlertRuleDialog, DigestSettingsCard, ChannelModal, RoutingRulesPanel, EscalationPolicyModal, ScheduleModal |
| 004 | NOCPage, UserDetailPage, AuditLogPage, TenantHealthMatrix, ActivityLogPage |
| 005 | WidgetConfigDialog, DashboardSelector, AddWidgetDrawer, WidgetContainer, WidgetErrorBoundary, CreateJobModal, AnalyticsPage, SitesPage, RolesPage, OtaCampaignDetailPage, MqttTestClientPage |
| 006 | docs/development/frontend.md, docs/index.md, docs/services/ui-iot.md |

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```

After each task:
- No raw `<select>` elements remain in the modified files
- No raw `<input type="checkbox">` elements remain in the modified files
- No raw `<button>` elements remain in the modified files (excluding `components/ui/`)
- All dropdowns, toggles, and buttons match the design system's visual style
- Dark mode renders correctly (shadcn components respect CSS custom properties)
