# Task 2: Device Modals, Wizard Steps, Data Tabs, Groups

## Objective

Replace all raw `<select>`, `<input type="checkbox">`, and `<button>` elements in device-related modals, the setup wizard, sensor/transport data tabs, and device groups.

Refer to `000-start.md` for migration rules and import references.

## Files to Modify (9)

---

### 1. `frontend/src/features/devices/AddDeviceModal.tsx`

**Raw `<select>` violations:**
- **~Line 152** — Template picker (optional) during device provisioning. Renders a dropdown of available templates.

Replace with `Select`. Since template selection is optional, use a sentinel value like `"none"` for "No template" and convert to `""` or `null` in `onValueChange`.

**Add imports:** `Select, SelectContent, SelectItem, SelectTrigger, SelectValue`.

---

### 2. `frontend/src/features/devices/DeviceEditModal.tsx`

**Raw `<select>` violations:**
- **~Line 236** — Template picker when editing a device.

Same pattern as AddDeviceModal. Replace with `Select` + items.

**Add imports:** `Select, SelectContent, SelectItem, SelectTrigger, SelectValue`.

---

### 3. `frontend/src/features/devices/DeviceSensorsDataTab.tsx`

**Raw `<select>` violations:**
- **~Line 145** — Module template picker when assigning a module to a slot
- **~Line 285** — Template metric picker (from-template mode when adding a sensor)
- **~Line 425** — Sensor status selector (active/inactive/error) when editing a sensor

Replace all three with `Select` components. The module/metric pickers may have many items — that's fine, `SelectContent` handles scrolling.

**Add imports:** `Select, SelectContent, SelectItem, SelectTrigger, SelectValue`.

---

### 4. `frontend/src/features/devices/DeviceTransportTab.tsx`

**Raw `<input type="checkbox">` violations:**
- **~Line 234** — "Primary transport" flag checkbox when adding/editing a transport

This is a single boolean toggle. Replace with `Switch`:

```tsx
<div className="flex items-center gap-2">
  <Switch checked={isPrimary} onCheckedChange={setIsPrimary} id="primary-transport" />
  <Label htmlFor="primary-transport">Primary transport</Label>
</div>
```

**Add imports:** `Switch` from `@/components/ui/switch`; `Label` from `@/components/ui/label`.

---

### 5. `frontend/src/features/devices/DeviceGroupsPage.tsx`

**Raw `<select>` violations:**
- **~Line 278** — Device picker (add a device to a static group). This is a `<select>` listing available devices.
- **~Line 380** — Status filter selector (any/ONLINE/STALE) for dynamic group rule conditions

Replace both with `Select`. For the device picker, if there are many devices, `Select` with scrollable content is acceptable for now (a searchable combobox would be ideal but is out of scope for this compliance sweep).

**Raw `<button>` violations:**
- **~Line 201** — Button in group management actions area

Replace with `Button`.

**Add imports:** `Select, SelectContent, SelectItem, SelectTrigger, SelectValue`; `Button` (if not already imported).

---

### 6. `frontend/src/features/devices/wizard/SetupWizard.tsx`

**Raw `<select>` violations:**
- **~Line 200** — Site selector in the wizard's device details section

Replace with `Select`.

**Raw `<input type="checkbox">` violations:**
- **~Line 269** — Alert rule selection checkboxes (multi-select list of alert rules to apply to the new device)

This is a multi-select list pattern. Replace each `<input type="checkbox">` with `Checkbox`.

**Add imports:** `Select, SelectContent, SelectItem, SelectTrigger, SelectValue`; `Checkbox` from `@/components/ui/checkbox`.

---

### 7. `frontend/src/features/devices/wizard/Step1DeviceDetails.tsx`

**Raw `<select>` violations:**
- **~Line 46** — Template selector (dropdown of available device templates)
- **~Line 75** — Site selector (dropdown of available sites)

Replace both with `Select`. Use `"none"` as sentinel for optional selections.

**Add imports:** `Select, SelectContent, SelectItem, SelectTrigger, SelectValue`.

---

### 8. `frontend/src/features/devices/wizard/Step2TagsGroups.tsx`

**Raw `<input type="checkbox">` violations:**
- **~Line 44** — Device group membership checkboxes (multi-select: check groups to add the device to)

This is a multi-select list. Replace each `<input type="checkbox">` with `Checkbox`.

**Add imports:** `Checkbox` from `@/components/ui/checkbox`.

---

### 9. `frontend/src/features/devices/wizard/Step5AlertRules.tsx`

**Raw `<select>` violations:**
- **~Line 99** — Alert rule operator selector (GT/LT/GTE/LTE)
- **~Line 120** — Alert rule severity selector (Critical/Warning/Info)

Replace both with `Select`.

**Add imports:** `Select, SelectContent, SelectItem, SelectTrigger, SelectValue`.

---

## Verification

After all changes:

```bash
cd frontend && npx tsc --noEmit
```

- All 9 files compile without errors
- No raw `<select>`, `<input type="checkbox">`, or `<button>` remains in any of the 9 files
- Device setup wizard renders correctly through all 5 steps with styled form controls
- Add/Edit device modals show styled template pickers
- Sensors & Data tab shows styled dropdowns for module/metric/status selection
- Transport tab shows Switch toggle for "primary transport"
- Device groups page shows styled dropdowns and buttons
- Dark mode renders correctly for all replaced elements
