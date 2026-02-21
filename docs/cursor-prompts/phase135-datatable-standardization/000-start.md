# Phase 135 — DataTable Standardization

## Goal
Convert all 18 remaining raw `<table>` pages to the reusable `DataTable` component (`@/components/ui/data-table`) with sorting, pagination, loading skeletons, and empty states.

## Current State
- 3 of 21 table pages already use `DataTable`: AlertRulesPage, JobsPage, UsersPage
- The remaining 18 use raw `<table>` elements with manual styling, no sorting, no pagination, and ad-hoc loading/empty states

## DataTable Component API
Located at `frontend/src/components/ui/data-table.tsx`. Uses TanStack React Table v8 + Shadcn UI.

```typescript
interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[];
  data: TData[];
  totalCount?: number;           // enables server-side pagination
  pagination?: PaginationState;  // { pageIndex, pageSize }
  onPaginationChange?: OnChangeFn<PaginationState>;
  manualPagination?: boolean;
  isLoading?: boolean;
  skeletonRows?: number;         // default 5
  emptyState?: React.ReactNode;
  onRowClick?: (row: TData) => void;
}
```

## Execution Order
1. `001-batch1-high-traffic.md` — NotificationChannelsPage, EscalationPoliciesPage, RoutingRulesPanel, ReportsPage
2. `002-batch2-device-panels.md` — DeviceApiTokensPanel, DeviceCertificatesTab, DeviceCommandPanel, BulkImportPage
3. `003-batch3-operator-tables.md` — UserListPage, CertificateOverviewPage, TenantHealthMatrix
4. `004-batch4-ota-analytics.md` — FirmwareListPage, OtaCampaignsPage, OtaCampaignDetailPage, AnalyticsPage
5. `005-batch5-remaining.md` — DeliveryLogPage, TimelineView, NormalizedMetricDialog

## Verification (after all tasks)
```bash
cd frontend && npm run build    # no errors
npx tsc --noEmit                # no type errors
```
Manual: visit every converted page, verify sorting, pagination, loading skeleton, and empty state.
