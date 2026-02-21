# 135-005: Remaining Tables

## Task
Convert or evaluate 3 remaining table components.

---

## 1. DeliveryLogPage
**File**: `frontend/src/features/delivery/DeliveryLogPage.tsx`

Delivery log showing notification delivery history.

Define columns:
- `channel_name` or `channel_type` (sortable) — delivery channel
- `alert_id` (sortable) — related alert ID
- `status` (sortable) — Badge: delivered=default/green, failed=destructive, pending=secondary
- `sent_at` (sortable) — formatted timestamp
- `error` (non-sortable) — error message if failed, truncated

**Empty state**: "No delivery logs. Logs appear when notifications are sent."
**Pagination**: Server-side if the API supports it (delivery logs can be large). Use offset/limit pattern.

---

## 2. TimelineView (On-Call)
**File**: `frontend/src/features/oncall/TimelineView.tsx`

**Evaluate fit**: On-call timeline views typically display time-based visual layouts (Gantt-style bars, time slots, shift blocks) rather than tabular rows.

**Decision criteria**:
- If TimelineView renders a standard table of shifts/schedules with columns → convert to DataTable
- If it renders a visual timeline (horizontal bars, calendar-style grid, time blocks) → keep the current layout

**If NOT converting** (most likely), add this comment:
```typescript
// DataTable not used: TimelineView renders a visual timeline/Gantt-style layout
// for on-call schedules that doesn't map to standard table rows and columns.
```

**If converting** (unlikely), define columns:
- `responder` (sortable) — on-call person
- `start_at` (sortable) — shift start
- `end_at` (sortable) — shift end
- `layer` (sortable) — schedule layer name

---

## 3. NormalizedMetricDialog
**File**: `frontend/src/features/metrics/NormalizedMetricDialog.tsx`

**Evaluate fit**: This is a dialog (modal) for configuring metric normalizations. It likely contains a small configuration table within the dialog.

**Decision criteria**:
- If the table has < 5 rows and is part of a form/config dialog → DataTable may be overkill. Keep the raw table or simple list.
- If it's a substantial mapping table (10+ rows) with sorting needs → convert to DataTable.

**If NOT converting**, add this comment:
```typescript
// DataTable not used: Small configuration table within a dialog.
// DataTable would add unnecessary complexity for a few-row config display.
```

**If converting**, define columns based on the metric mapping fields (source_metric, normalized_name, unit, etc.).

---

## Verification
```bash
cd frontend && npm run build
npx tsc --noEmit
```
Visit:
- Delivery log page — verify DataTable with sorting and pagination
- On-call timeline — verify it still renders correctly (no changes if skipped)
- Metrics page → open NormalizedMetricDialog — verify it still works
