# Task 2: DeviceEditModal Restructure

## File

`frontend/src/features/devices/DeviceEditModal.tsx`

## Current Problems

1. No explicit width — picks up default `sm:max-w-xl` (640px). Way too narrow for 14 fields.
2. All hardware identifiers in a flat `grid grid-cols-2` with no section grouping — just a wall of inputs.
3. Template selector spans `col-span-2` (full width) when it could share a row.
4. Location section only separated by a `border-t`, no section label.
5. Notes textarea at the bottom makes the form tall.

## Changes

### A. Widen to `sm:max-w-5xl` (1024px)

```tsx
// OLD (line 223):
<DialogContent>

// NEW:
<DialogContent className="sm:max-w-5xl">
```

### B. Group fields into 2-column fieldset layout

Replace the entire form body (lines 228-465) with a 2-column fieldset layout, similar to the EditTenantDialog approach:

```tsx
<form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
  {/* Template selector - full width at top */}
  <FormField
    control={form.control}
    name="template_id"
    render={({ field }) => (
      <FormItem>
        <FormLabel className="text-sm">Device Template</FormLabel>
        <FormControl>
          <Select
            value={(field.value ?? "") || "none"}
            onValueChange={(v) => field.onChange(v === "none" ? "" : v)}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="(none)" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">(none)</SelectItem>
              {templates.map((t) => (
                <SelectItem key={t.id} value={String(t.id)}>
                  {t.name} ({t.category}){t.source === "system" ? " [system]" : ""}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormControl>
        {templateChanged ? (
          <div className="text-xs text-yellow-600">
            Changing the template will not remove existing sensors.
          </div>
        ) : null}
        <FormMessage />
      </FormItem>
    )}
  />

  <div className="grid gap-4 sm:grid-cols-2">
    {/* Left column: Hardware Identifiers */}
    <fieldset className="space-y-3 rounded-md border p-4">
      <legend className="px-1 text-sm font-medium">Hardware</legend>
      <div className="grid gap-3 sm:grid-cols-2">
        <FormField name="model" ... />
        <FormField name="manufacturer" ... />
        <FormField name="serial_number" ... />
        <FormField name="mac_address" ... />
        <FormField name="hw_revision" ... />
        <FormField name="fw_version" ... />
      </div>
    </fieldset>

    {/* Right column: Network + Location */}
    <div className="space-y-4">
      <fieldset className="space-y-3 rounded-md border p-4">
        <legend className="px-1 text-sm font-medium">Network</legend>
        <div className="grid gap-3 sm:grid-cols-2">
          <FormField name="imei" ... />
          <FormField name="iccid" ... />
        </div>
      </fieldset>

      <fieldset className="space-y-3 rounded-md border p-4">
        <legend className="px-1 text-sm font-medium">Location</legend>
        <div className="grid gap-3 sm:grid-cols-2">
          <FormField name="latitude" ... />
          <FormField name="longitude" ... />
        </div>
        <FormField name="address" ... />  {/* Full width with Lookup button */}
      </fieldset>
    </div>
  </div>

  {/* Notes - full width */}
  <FormField name="notes" ... />

  {/* Footer */}
  <div className="flex justify-end gap-2">...</div>
</form>
```

### Detailed field placement

Keep all existing FormField render functions exactly as they are (including the `h-8 text-sm` classes on inputs). Just reorganize them into the fieldset structure above.

**Left fieldset "Hardware" (3 rows × 2 cols):**
- Row 1: Model + Manufacturer
- Row 2: Serial + MAC
- Row 3: HW Rev + FW Ver

**Right side, fieldset "Network" (1 row × 2 cols):**
- Row 1: IMEI + SIM/ICCID

**Right side, fieldset "Location":**
- Row 1: Latitude + Longitude (2-col grid)
- Row 2: Address (full width with Lookup button) — keep the existing `flex gap-1` layout
- Remove the "Note: Manually setting location..." text (unnecessary, self-evident)
- Remove the "Location — GPS coordinates preferred..." helper text (unnecessary)
- Keep the geocodeError display

**Full width below fieldsets:**
- Notes textarea (rows={2} is fine)

### Expected Layout

```
┌──────────────────────────────────────────────────────────────────┐
│ Edit Device                                                      │
│                                                                  │
│ [Device Template                                          ▼]    │
│                                                                  │
│ ┌─ Hardware ──────────────────┐ ┌─ Network ─────────────────┐  │
│ │ [Model     ] [Manufacturer] │ │ [IMEI       ] [SIM/ICCID] │  │
│ │ [Serial    ] [MAC Address ] │ └────────────────────────────┘  │
│ │ [HW Rev    ] [FW Version  ] │ ┌─ Location ────────────────┐  │
│ └─────────────────────────────┘ │ [Latitude   ] [Longitude ] │  │
│                                  │ [Address              🔍] │  │
│                                  └────────────────────────────┘  │
│ [Notes                                                       ]  │
│                                                                  │
│                              [Cancel]  [Save]                   │
└──────────────────────────────────────────────────────────────────┘
```

## Verification

```bash
cd frontend && npx tsc --noEmit
```

- Modal opens at 1024px with clearly grouped sections
- Hardware fields in left fieldset, Network + Location in right
- All form validation still works (MAC regex, lat/lng range)
- Geocode lookup button still works
- Dirty guard still works
- Template change warning still shows
