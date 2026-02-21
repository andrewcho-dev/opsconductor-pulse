# 135-002: Customer-Facing Table Pages (Batch 2 — Device Panels)

## Task
Convert 4 device-related panel/page tables from raw `<table>` to `DataTable`.

---

## 1. DeviceApiTokensPanel
**File**: `frontend/src/features/devices/DeviceApiTokensPanel.tsx`

Define columns:
- `name` / `label` (sortable) — token name, bold
- `token_prefix` (non-sortable) — show first chars + `...` (masked)
- `created_at` (sortable) — formatted date
- `expires_at` (sortable) — formatted date, red text if expired
- `actions` (non-sortable) — Revoke button (destructive variant)

**Empty state**: "No API tokens for this device. Create a token to enable programmatic access."
**Loading**: `isLoading={isLoading}` from query hook.
**Pagination**: Client-side (tokens per device is small).

---

## 2. DeviceCertificatesTab
**File**: `frontend/src/features/devices/DeviceCertificatesTab.tsx`

Define columns:
- `common_name` (sortable) — certificate CN
- `fingerprint_sha256` (non-sortable) — truncated fingerprint, monospace font
- `status` (sortable) — Badge: ACTIVE=default, REVOKED=destructive, EXPIRED=secondary
- `not_before` (sortable) — formatted date
- `not_after` (sortable) — formatted date, red if expired
- `actions` (non-sortable) — Revoke button (destructive, only shown for ACTIVE certs)

**Note**: This file also contains a `window.confirm()` call for revoking certificates. Leave it for now — Phase 138 will replace it with AlertDialog.

**Empty state**: "No certificates uploaded for this device."
**Loading**: `isLoading={isLoading}` from query hook.

---

## 3. DeviceCommandPanel
**File**: `frontend/src/features/devices/DeviceCommandPanel.tsx`

Convert command history table. Define columns:
- `command_id` (sortable) — truncated UUID, monospace
- `command_type` (sortable) — command type text
- `status` (sortable) — Badge with status color (QUEUED=secondary, IN_PROGRESS=default, SUCCEEDED=outline/green, FAILED=destructive)
- `created_at` (sortable) — formatted timestamp
- `completed_at` (sortable) — formatted timestamp or "—"
- `actions` (non-sortable) — View details button if applicable

**Empty state**: "No commands sent to this device yet."
**Loading**: `isLoading={isLoading}` from query hook.

---

## 4. BulkImportPage
**File**: `frontend/src/features/devices/BulkImportPage.tsx`

Convert import results table. Define columns:
- `row` / `line` (sortable) — row number from import file
- `device_id` (sortable) — device ID from import
- `status` (sortable) — Badge: success=default, error=destructive, skipped=secondary
- `message` (non-sortable) — result message text

**Empty state**: "Upload a CSV file to see import results."
**Loading**: `isLoading={isLoading}` while import is processing.

---

## Imports Pattern
For each file, add:
```typescript
import { DataTable } from "@/components/ui/data-table";
import { type ColumnDef } from "@tanstack/react-table";
```

Remove unused `Table, TableHeader, TableBody, TableCell, TableHead, TableRow` imports if no other raw table remains in the file.

## Verification
```bash
cd frontend && npm run build
npx tsc --noEmit
```
Visit a device detail page and check each tab/panel. Verify sorting, loading skeleton, empty state, and that all action buttons still work.
