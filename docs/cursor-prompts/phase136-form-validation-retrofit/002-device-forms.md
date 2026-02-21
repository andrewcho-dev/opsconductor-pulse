# 136-002: Device Forms

## Task
Convert device edit modals from raw `useState` to react-hook-form + zod.

## Files
- `frontend/src/features/devices/DeviceEditModal.tsx`
- `frontend/src/features/devices/EditDeviceModal.tsx`

**First**: Check if these two files are duplicates. If they serve the same purpose (edit device metadata), consolidate into a single component and update all imports. If they serve different purposes (e.g., one edits hardware info, another edits location), convert both.

## Current State (DeviceEditModal)
Uses ~15 useState calls: `model, manufacturer, serialNumber, macAddress, imei, iccid, hwRevision, fwVersion, latitude, longitude, address, notes, saving, geocoding, geocodeError`.

Has a large `useEffect` to initialize from `device` prop and manual `handleSubmit` with inline value transformation.

## Zod Schema
```typescript
const deviceEditSchema = z.object({
  model: z.string().max(100).optional(),
  manufacturer: z.string().max(100).optional(),
  serial_number: z.string().max(100).optional(),
  mac_address: z.string().regex(/^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$/, "Invalid MAC address format").optional().or(z.literal("")),
  imei: z.string().max(20).optional(),
  iccid: z.string().max(22).optional(),
  hw_revision: z.string().max(50).optional(),
  fw_version: z.string().max(50).optional(),
  latitude: z.coerce.number().min(-90).max(90).optional().or(z.literal("")),
  longitude: z.coerce.number().min(-180).max(180).optional().or(z.literal("")),
  address: z.string().max(500).optional(),
  notes: z.string().max(2000).optional(),
});

type DeviceEditFormValues = z.infer<typeof deviceEditSchema>;
```

**Note**: The MAC address regex validation is optional — only validate format if the field is non-empty. Use `.optional().or(z.literal(""))` for fields that can be left blank. For latitude/longitude, allow empty strings (user clears the field) or valid numbers.

## Migration Steps

### 1. Replace useState calls with useForm
```typescript
const form = useForm<DeviceEditFormValues>({
  resolver: zodResolver(deviceEditSchema),
  defaultValues: {
    model: device.model ?? "",
    manufacturer: device.manufacturer ?? "",
    serial_number: device.serial_number ?? "",
    mac_address: device.mac_address ?? "",
    // ... all fields from device prop
  },
});
```

### 2. Replace useEffect initialization
```typescript
useEffect(() => {
  if (open) {
    form.reset({
      model: device.model ?? "",
      manufacturer: device.manufacturer ?? "",
      // ... map all fields
    });
  }
}, [open, device]);
```

### 3. Convert form submission
```typescript
const onSubmit = async (values: DeviceEditFormValues) => {
  // Transform empty strings to null for API
  const update: DeviceUpdate = {
    model: values.model?.trim() || null,
    manufacturer: values.manufacturer?.trim() || null,
    latitude: values.latitude !== "" ? Number(values.latitude) : null,
    longitude: values.longitude !== "" ? Number(values.longitude) : null,
    // ... etc
  };
  await onSave(update);
  onClose();
};
```

### 4. Convert JSX
Replace each `<Input value={model} onChange={e => setModel(e.target.value)} />` with FormField:
```typescript
<FormField control={form.control} name="model" render={({ field }) => (
  <FormItem>
    <FormLabel>Model</FormLabel>
    <FormControl><Input {...field} placeholder="e.g., DHT22" /></FormControl>
    <FormMessage />
  </FormItem>
)} />
```

### 5. Preserve geocoding functionality
If there's a "Geocode" button that reverse-geocodes lat/lng to address, keep that functionality. Use `form.setValue("address", geocodedAddress)` to update the address field programmatically.

### 6. Keep non-form state
Keep `geocoding` and `geocodeError` as standalone state since they're UI state, not form data. Or move geocodeError to form errors via `form.setError("address", { message: "Geocoding failed" })`.

## Verification
```bash
cd frontend && npm run build
npx tsc --noEmit
```
- Edit a device → form pre-populated with existing values
- Enter invalid MAC address → see validation error
- Enter latitude > 90 → see validation error
- Submit valid changes → device updated
- Clear all optional fields → submit → works (null values sent)
