# Prompt 002 — Frontend: Download CSV Button

Read `frontend/src/features/devices/TelemetryChartsSection.tsx` fully.
Read `frontend/src/services/api/devices.ts`.

## Add Download Function

In `frontend/src/services/api/devices.ts`, add a download helper:

```typescript
export async function downloadTelemetryCSV(
  deviceId: string,
  range: string
): Promise<void> {
  // Use fetch directly to get blob (not apiFetch which returns JSON)
  const token = getAuthToken(); // use existing auth token getter pattern
  const response = await fetch(
    `/customer/devices/${deviceId}/telemetry/export?range=${range}`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  if (!response.ok) throw new Error(`Export failed: ${response.status}`);

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${deviceId}_telemetry_${range}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
```

Note: Look at how `apiFetch` gets the auth token in the existing codebase and reuse that same pattern.

## Update TelemetryChartsSection.tsx

Add a "Download CSV" button next to the existing time range selector:

- Uses the currently selected range to determine export scope
- On click: calls `downloadTelemetryCSV(deviceId, selectedRange)`
- While downloading: button shows spinner, disabled
- On error: shows brief error message

## Acceptance Criteria

- [ ] "Download CSV" button in TelemetryChartsSection
- [ ] Uses currently selected range
- [ ] Button disabled while downloading
- [ ] File downloads with correct name
- [ ] `npm run build` passes
