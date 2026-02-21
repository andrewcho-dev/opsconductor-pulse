# Phase 89 — Bulk CSV Import Improvements

## File to modify
`frontend/src/features/devices/BulkImportPage.tsx`

This page exists from Phase 76 with basic CSV upload. Improve it as follows.

## Improvement 1: CSV Template Download

Add a "Download CSV Template" button/link above the file input that triggers
a client-side download of:

```
device_id,name,model,site_id,tags
example-device-001,My Sensor,sensor-v2,site-abc,"env=prod,region=us-east"
```

Use a Blob URL approach:
```typescript
const csv = "device_id,name,model,site_id,tags\n...";
const blob = new Blob([csv], { type: 'text/csv' });
const url = URL.createObjectURL(blob);
const a = document.createElement('a');
a.href = url; a.download = 'device-import-template.csv'; a.click();
URL.revokeObjectURL(url);
```

## Improvement 2: Client-Side Preview Table

After the user selects a file (onChange on the file input):
1. Parse the CSV client-side using `FileReader` + manual split (no external lib)
2. Show a preview table of up to 10 rows:

```
device_id | name | model | site_id | tags
----------|------|-------|---------|-----
...       | ...  | ...   | ...     | ...
```

3. Validate each row:
   - `device_id`: required, must match `/^[a-z0-9][a-z0-9-_]*$/`
   - Highlight invalid cells with `bg-red-100 text-red-700`
4. Show "N rows total, X valid, Y invalid"
5. "Import N valid rows" button — disabled if any validation errors exist in the
   parsed rows (not just the visible 10)

## Improvement 3: Error Rows After Submit

After POST /devices/import response:
- If response has `errors: Array<{ row: number; device_id: string; reason: string }>`:
  - Show a red banner: "X rows failed to import"
  - Expandable `<details>` table with columns: Row | Device ID | Reason
  - "Download Error Report" button — exports the errors array as CSV:
    `row,device_id,reason\n1,bad-device,Duplicate device ID\n...`

## No backend changes required.
The backend already returns errors in the import response (or gracefully handles
partial imports). If the backend doesn't return an `errors` field yet, handle
gracefully with `response.errors ?? []`.
