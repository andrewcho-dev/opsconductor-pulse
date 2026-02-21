# 135-004: OTA & Analytics Tables

## Task
Convert 4 OTA and analytics table pages from raw `<table>` to `DataTable`.

---

## 1. FirmwareListPage
**File**: `frontend/src/features/ota/FirmwareListPage.tsx`

Currently uses a raw table with header array mapping: `["Version", "Description", "Device Type", "File Size", "Checksum", "Created"]`.

Define columns:
- `version` (sortable) — monospace, bold (`font-mono font-medium`)
- `description` (sortable) — truncated text, max-w-[200px]
- `device_type` (sortable) — device type or "—"
- `file_size_bytes` (sortable) — formatted file size (KB/MB)
- `checksum_sha256` (non-sortable) — truncated, monospace, `text-xs`
- `created_at` (sortable) — formatted date

**Empty state**: "No firmware versions registered yet. Upload a firmware version to begin OTA updates."
**Loading**: `isLoading={isLoading}` from query hook.
**Pagination**: Client-side (firmware versions are typically small lists).

---

## 2. OtaCampaignsPage
**File**: `frontend/src/features/ota/OtaCampaignsPage.tsx`

Define columns:
- `name` (sortable) — campaign name, bold
- `status` (sortable) — Badge with color: CREATED=secondary, RUNNING=default, PAUSED=outline, COMPLETED=default/green, ABORTED=destructive
- `firmware_version` (sortable) — version string from related firmware
- `total_devices` (sortable) — total device count
- `progress` (non-sortable) — show "succeeded/total" with percentage, or a small progress indicator
- `created_at` (sortable) — formatted date
- `actions` (non-sortable) — DropdownMenu with:
  - "View Details" → navigate to campaign detail page
  - "Abort" (destructive, only for RUNNING/CREATED status) — keep existing abort handler

**Note**: This file contains a `window.confirm()` call for abort. Leave it for now — Phase 138 will replace it.

**Empty state**: "No OTA campaigns created yet."
**Pagination**: Client-side for now, server-side if API supports offset/limit.

---

## 3. OtaCampaignDetailPage
**File**: `frontend/src/features/ota/OtaCampaignDetailPage.tsx`

This page shows campaign details AND a per-device status table. Convert the **per-device status table** to DataTable.

Define columns for the device status table:
- `device_id` (sortable) — device ID, monospace
- `status` (sortable) — Badge: PENDING=secondary, DOWNLOADING=default, INSTALLING=default, SUCCEEDED=outline/green, FAILED=destructive
- `started_at` (sortable) — formatted timestamp or "—"
- `completed_at` (sortable) — formatted timestamp or "—"
- `error_message` (non-sortable) — error text if failed, truncated

Keep the campaign summary cards/info above the table unchanged.

**Empty state**: "No devices targeted in this campaign."
**Pagination**: Server-side if > 50 devices, client-side otherwise.

---

## 4. AnalyticsPage
**File**: `frontend/src/features/analytics/AnalyticsPage.tsx`

The analytics page may have a query results table that displays tabular data from analytics queries.

Define columns dynamically based on the query response columns:
```typescript
const columns = useMemo(() => {
  if (!queryResult?.columns) return [];
  return queryResult.columns.map((col: string) => ({
    accessorKey: col,
    header: col.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
    enableSorting: true,
  }));
}, [queryResult?.columns]);
```

**Empty state**: "Run a query to see results."
**Loading**: `isLoading={isLoading}` while query is executing.

If the AnalyticsPage table is very simple or already well-implemented, evaluate whether conversion is needed and document the decision.

---

## Verification
```bash
cd frontend && npm run build
npx tsc --noEmit
```
Visit OTA pages (/ota/firmware, /ota/campaigns, /ota/campaigns/:id) and Analytics page. Verify:
- Firmware list sorts by version, size, date
- Campaign list shows progress and status badges
- Campaign detail device table paginates for large campaigns
- Analytics results table renders dynamic columns
