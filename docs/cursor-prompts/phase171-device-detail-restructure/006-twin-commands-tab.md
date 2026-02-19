# Task 6: Twin & Commands Tab

## Create component in `frontend/src/features/devices/` (e.g., `DeviceTwinCommandsTab.tsx`)

Consolidates DeviceTwinPanel + DeviceCommandPanel.

### Component Structure

```
TwinCommandsTab
├── Device Twin Section
│   ├── Section header: "Device Twin"
│   ├── Two-column layout:
│   │   ├── Desired State (editable JSON)
│   │   └── Reported State (read-only JSON)
│   ├── Diff view toggle (show delta between desired and reported)
│   ├── "Update Desired State" button
│   └── ETag-based conflict detection
│
└── Commands Section
    ├── Section header: "Commands"
    ├── If device has template with commands:
    │   ├── For each template_command:
    │   │   ├── Command card: display_name, description
    │   │   ├── Parameter form (auto-generated from parameters_schema JSON Schema)
    │   │   └── "Send" button
    │   └── Command history table (recent commands + status)
    ├── If no template commands:
    │   ├── Free-form command input
    │   │   ├── Command name input
    │   │   ├── Payload JSON editor
    │   │   └── "Send" button
    │   └── Command history table
    └── Command history table
        ├── Columns: command, status, sent_at, response
        └── Pagination
```

### Twin Section Implementation

Reuse the existing `DeviceTwinPanel` component's logic. The key functions already exist:
- `getDeviceTwin(deviceId)` → returns `{ desired, reported, delta, etag }`
- `updateDesiredState(deviceId, desired, etag)` → sends PATCH with conflict detection

The twin section should:
1. Show `desired` and `reported` as formatted JSON (use a code block or JSON tree view)
2. Allow editing `desired` via a JSON editor textarea
3. On save, call `updateDesiredState()` with the etag
4. Show diff/delta between desired and reported

### Commands Section — Template-Aware

If the device has a template, fetch its commands:

```typescript
const { data: template } = useQuery({
  queryKey: ["templates", device.template_id],
  queryFn: () => getTemplate(device.template_id!),
  enabled: !!device.template_id,
});
```

For each `template.commands`, render a command form card. The `parameters_schema` is a JSON Schema — use it to render form fields dynamically:

```typescript
// Simple JSON Schema → form field mapping:
// type: string → Input
// type: integer → Input type="number"
// type: boolean → Checkbox
// type: object → JSON editor
// enum → Select dropdown
```

For complex schemas, fall back to a JSON textarea for the payload.

### Command Dispatch

Reuse the existing `sendCommand(deviceId, payload)` function. The payload should include `command_key` from the template command plus the form values:

```typescript
await sendCommand(deviceId, {
  command: command.command_key,
  params: formValues,
});
```

## Verification

1. Twin section shows desired and reported state
2. Editing desired state and saving works with conflict detection
3. Template commands render as form cards
4. Sending a command updates the history table
5. Free-form command input works when no template commands
