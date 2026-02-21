# Prompt 002 — Frontend: Bulk Import UI

## Create `frontend/src/features/devices/BulkImportPage.tsx`

Route: `/devices/import`

Layout:
1. **Upload step**: Drag-and-drop or file picker (accept `.csv`). Show required columns format hint: `name, device_type, site_id (optional), tags (optional)`.
2. **Results step** (after upload): Table showing per-row status:
   - Green checkmark for `status: "ok"` rows
   - Red X for `status: "error"` rows with message
   - Summary banner: "Imported 8 of 10 devices"
3. "Import Another File" button to reset.

## Add API client function in `frontend/src/services/api/devices.ts`

```typescript
export async function importDevicesCSV(file: File): Promise<ImportResult>

interface ImportResultRow {
  row: number;
  name: string;
  status: 'ok' | 'error';
  device_id?: string;
  message?: string;
}

interface ImportResult {
  total: number;
  imported: number;
  failed: number;
  results: ImportResultRow[];
}
```

## Wire into router and nav

- Add route `/devices/import` in `frontend/src/app/router.tsx`
- Add "Import Devices" link in device list page actions or sidebar under Devices section

## Acceptance Criteria
- [ ] BulkImportPage.tsx exists with file picker
- [ ] Per-row results table shown after upload
- [ ] Summary banner
- [ ] API client function added
- [ ] Route wired
- [ ] `npm run build` passes
