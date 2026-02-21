# Task 001 — Fix SensorListPage Select Crash

## File

`frontend/src/features/devices/SensorListPage.tsx`

## Problem

The page crashes on load with:

```
A <Select.Item /> must have a value prop that is not an empty string
```

Three `<SelectItem value="">` elements pass empty strings, which Radix Select rejects.

## Fix

Replace empty string `""` with the sentinel value `"all"` in three places:

### 1. State initialization

Change:
```tsx
const [typeFilter, setTypeFilter] = useState<string>("");
const [statusFilter, setStatusFilter] = useState<string>("");
const [deviceFilter, setDeviceFilter] = useState<string>("");
```

To:
```tsx
const [typeFilter, setTypeFilter] = useState<string>("all");
const [statusFilter, setStatusFilter] = useState<string>("all");
const [deviceFilter, setDeviceFilter] = useState<string>("all");
```

### 2. SelectItem values

Change all three "All ..." SelectItems from `value=""` to `value="all"`:

```tsx
<SelectItem value="all">All Types</SelectItem>
```
```tsx
<SelectItem value="all">All Status</SelectItem>
```
```tsx
<SelectItem value="all">All Devices</SelectItem>
```

### 3. API query parameter mapping

Where the filters are passed to the API call, convert `"all"` back to `undefined`:

Change:
```tsx
sensor_type: typeFilter || undefined,
status: statusFilter || undefined,
device_id: deviceFilter || undefined,
```

To:
```tsx
sensor_type: typeFilter === "all" ? undefined : typeFilter,
status: statusFilter === "all" ? undefined : statusFilter,
device_id: deviceFilter === "all" ? undefined : deviceFilter,
```

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```

Then navigate to `/app/sensors` in the browser — the page should load without crashing.
