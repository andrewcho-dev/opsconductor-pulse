# Task 3: Alerts, Notifications, Escalation, On-Call

## Objective

Replace all raw `<select>`, `<input type="checkbox">`, and `<button>` elements in alert management, notification channel/routing configuration, escalation policy, and on-call schedule pages.

Refer to `000-start.md` for migration rules and import references.

## Files to Modify (7)

---

### 1. `frontend/src/features/alerts/AlertListPage.tsx`

**Raw `<select>` violations:**
- **~Line 467** — Page size selector (10/25/50/100 per page) in the pagination controls

Replace with `Select`. Use `onValueChange={(v) => setPageSize(Number(v))}` since the value is numeric.

**Raw `<input type="checkbox">` violations:**
- **~Line 262** — Bulk-select header checkbox (select all visible alerts). This controls whether all rows are selected.
- **~Line 282** — Per-row checkbox on each alert for bulk actions (acknowledge/close multiple)

Both are multi-select/bulk-select patterns. Replace with `Checkbox`:

Header checkbox (select all):
```tsx
<Checkbox
  checked={allSelected}
  onCheckedChange={(checked) => checked ? selectAll() : deselectAll()}
/>
```

Per-row checkbox:
```tsx
<Checkbox
  checked={selectedIds.has(alert.alert_id)}
  onCheckedChange={() => toggleSelection(alert.alert_id)}
/>
```

**Add imports:** `Select, SelectContent, SelectItem, SelectTrigger, SelectValue`; `Checkbox`.

---

### 2. `frontend/src/features/alerts/AlertRuleDialog.tsx`

**Raw `<input type="checkbox">` violations:**
- **~Line 1513** — Device group membership checkbox in the alert rule configuration (multi-select: which device groups does this rule apply to)

This file already imports shadcn `Select` for other fields. Replace the checkbox with `Checkbox` component.

**Add imports:** `Checkbox` from `@/components/ui/checkbox`.

---

### 3. `frontend/src/features/alerts/DigestSettingsCard.tsx`

**Raw `<select>` violations:**
- **~Line 59** — Digest email frequency selector (daily/weekly/disabled)

Replace with `Select`.

**Add imports:** `Select, SelectContent, SelectItem, SelectTrigger, SelectValue`.

---

### 4. `frontend/src/features/notifications/ChannelModal.tsx`

**Raw `<select>` violations:**
- **~Line 116** — Channel type selector (slack/pagerduty/teams/webhook/email/snmp/mqtt). This determines which config fields are shown.
- **~Line 179** — HTTP method selector (POST/PUT) for webhook channel configuration

Replace both with `Select`.

**Raw `<input type="checkbox">` violations:**
- **~Line 134** — "Is Enabled" toggle checkbox for the notification channel. This is a single boolean toggle → replace with `Switch`.
- **~Line 281** — "Use TLS" checkbox for SMTP email channel configuration. Also a single boolean toggle → replace with `Switch`.

For the Switch replacements, use the label+switch pattern:
```tsx
<div className="flex items-center justify-between">
  <Label htmlFor="channel-enabled">Enabled</Label>
  <Switch id="channel-enabled" checked={enabled} onCheckedChange={setEnabled} />
</div>
```

**Add imports:** `Select, SelectContent, SelectItem, SelectTrigger, SelectValue`; `Switch` from `@/components/ui/switch`; `Label` from `@/components/ui/label`.

---

### 5. `frontend/src/features/notifications/RoutingRulesPanel.tsx`

**Raw `<select>` violations:**
- **~Line 173** — Channel picker for the routing rule draft (which notification channel to route to)
- **~Line 185** — Minimum severity selector for the routing rule (severity threshold)
- **~Line 247** — Deliver-on event selector (OPEN/CLOSED/ACKNOWLEDGED — which alert events trigger delivery)

This file has an inline form built entirely from raw HTML elements. Replace all three `<select>` elements with `Select` components. Keep the inline form layout (do not refactor to a Dialog — that's out of scope for this compliance sweep).

The channel picker may need to map channel objects to string values:
```tsx
<Select value={draft.channel_id ?? ""} onValueChange={(v) => setDraft({ ...draft, channel_id: v })}>
  <SelectTrigger className="w-full h-8">
    <SelectValue placeholder="Select channel" />
  </SelectTrigger>
  <SelectContent>
    {channels.map((ch) => (
      <SelectItem key={ch.id} value={ch.id}>{ch.name}</SelectItem>
    ))}
  </SelectContent>
</Select>
```

**Add imports:** `Select, SelectContent, SelectItem, SelectTrigger, SelectValue`.

---

### 6. `frontend/src/features/escalation/EscalationPolicyModal.tsx`

**Raw `<select>` violations:**
- **~Line 222** — On-call schedule picker per escalation level (which schedule to escalate to)

Note: This file already imports shadcn `Checkbox` but still uses a raw `<select>`. Replace the select with `Select`.

**Add imports:** `Select, SelectContent, SelectItem, SelectTrigger, SelectValue`.

---

### 7. `frontend/src/features/oncall/ScheduleModal.tsx`

**Raw `<select>` violations:**
- **~Line 78** — Timezone selector for an on-call schedule (this may have many options — IANA timezone list)
- **~Line 101** — Rotation type selector per layer (daily/weekly/custom)

Replace both with `Select`. For the timezone selector, `SelectContent` handles scroll automatically. If the list is very long (300+ timezones), this is acceptable for now — a searchable combobox would be better but is out of scope.

**Add imports:** `Select, SelectContent, SelectItem, SelectTrigger, SelectValue`.

---

## Verification

After all changes:

```bash
cd frontend && npx tsc --noEmit
```

- All 7 files compile without errors
- No raw `<select>`, `<input type="checkbox">`, or `<button>` remains in any of the 7 files
- Alert list page shows styled page-size dropdown and styled checkboxes for bulk select
- Alert rule dialog shows Checkbox components for device group selection
- Notification channel modal shows styled dropdowns for channel type and HTTP method, Switch toggles for enabled/TLS
- Routing rules panel shows styled dropdowns inline
- Escalation policy modal shows styled schedule picker
- On-call schedule modal shows styled timezone and rotation type pickers
- Dark mode renders correctly for all replaced elements
